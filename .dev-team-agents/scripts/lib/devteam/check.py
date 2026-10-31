"""`devteam check` -- the branch diff against the decisions the base branch has accepted (ADR-0049).

Three sources are compared with what the branch changed (merge-base with the base, plus
the working tree):

* Accepted ADRs whose `**Applies to:**` globs match a changed path (glob semantics of
  `scripts/hooks/stop/03h-adr-scope-check.sh` and skills/shared/adr/SKILL.md § Applies To:
  `*` crosses `/`, `?` is one character, everything else literal);
* `reuse-guidelines` rows with a `detection` regex, on added lines, honouring `scope` and
  `severity` (the parsing and matching of `scripts/reuse-lint.sh`; the regex runs in
  `grep -E` under a time limit, so a catastrophic pattern becomes a lead, never a hang);
* the number-changed rule: a changed line alters a numeric literal bound to a name that an
  applicable ADR's text cites with the old value.

A finding is a `conflict` only when its source is committed on the base branch, applies to
that very path and, for a reuse row, is not advisory.
Everything else is a `lead`. Sources are read as they are on the base (`git show`), so a
branch edit of an ADR or a rule cannot hide a conflict; the edit is a lead of its own.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import sys
from decimal import Decimal, InvalidOperation

from .errors import EnvError, UsageError

_LIB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB not in sys.path:
    sys.path.append(_LIB)
import docs_root  # noqa: E402
from index_lint import ADR_NAME_RE  # noqa: E402

CONFLICT = "conflict"
LEAD = "lead"

MAX_PATTERNS = 50
MAX_PATTERN_LEN = 200
MAX_LINE_LEN = 2000
MAX_FILE_BYTES = 1048576
GIT_TIMEOUT = 30
GREP_TIMEOUT = 2
EXCLUDE = ".dev-team-agents"
SEP = "\x1f"
_CONTROL = re.compile(r"[\x00-\x09\x0b-\x1f\x7f]")
_STATUS_RE = re.compile(r"^\*\*Status(?::\*\*|\*\*:)\s*Accepted", re.M)
_APPLIES_RE = re.compile(r"^\*\*Applies to(?::\*\*|\*\*:).*$", re.M)
_NUMBER_RE = re.compile(r"(?<![\w.])([A-Za-z_][A-Za-z0-9_]*)\s*(?::=|=(?![=>])|:(?!:))\s*(-?\d+(?:\.\d+)?)(?![\w.])")


def _git(root, *args, check=True):
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", *args], cwd=root, capture_output=True, check=False,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        if check:
            raise EnvError("git {} timed out after {}s".format(args[0], GIT_TIMEOUT))
        return None
    if check and proc.returncode != 0:
        raise EnvError(
            "git {} failed: {}".format(args[0], proc.stderr.decode("utf-8", "replace").strip()[:200])
        )
    return proc.stdout.decode("utf-8", "replace") if proc.returncode == 0 else None


def _show(root, ref, path):
    return _git(root, "show", "{}:{}".format(ref, path), check=False)


def resolve_base(root, base):
    """`(ref, how)`: the explicit `--base`, else origin's default branch (then the usual names)."""
    if base:
        if base.startswith("-"):
            raise UsageError("--base must be a git ref, not an option")
        candidates = [(base, "--base")]
    else:
        head = _git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
        candidates = [(head.strip(), "origin default branch")] if head and head.strip() else []
        candidates += [(c, "fallback") for c in ("origin/main", "origin/master", "main", "master")]
    for ref, how in candidates:
        if _git(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}", check=False):
            return ref, how
    raise EnvError(
        "base ref not found: {}".format(base or "no origin default branch, origin/main or main"),
        hint="Fetch it, or pass --base <ref>.",
    )


def _glob_regex(glob):
    return re.compile("".join(".*" if c == "*" else "." if c == "?" else re.escape(c) for c in glob))


def _globs(text):
    """The backticked patterns of the first `**Applies to:**` line, as compiled globs."""
    match = _APPLIES_RE.search(text)
    if not match:
        return []
    spans = re.findall(r"`([^`]+)`", match.group(0)[:2000])
    out = []
    for span in spans:
        span = _CONTROL.sub("", span)
        if span and len(span) <= MAX_PATTERN_LEN:
            out.append(_glob_regex(span))
        if len(out) >= MAX_PATTERNS:
            break
    return out


class Adr:
    def __init__(self, path, text, on_base, edited):
        self.path = path
        self.text = text
        self.on_base = on_base
        self.edited = edited
        name = os.path.basename(path)
        number = re.match(r"^(?:adr-)?(\d+)-", name, re.I)
        self.id = "ADR-{}".format(number.group(1)) if number else name
        title = re.search(r"^# (.*)$", text, re.M)
        self.title = re.sub(r"^ADR-\d+:\s*", "", _CONTROL.sub("", title.group(1)))[:120] if title else name
        self.accepted = bool(_STATUS_RE.search(text))
        self.globs = _globs(text) if self.accepted else []

    @property
    def blocking(self):
        return self.on_base

    def governs(self, path):
        return path != self.path and any(g.fullmatch(path) for g in self.globs)

    def cites(self, name, value):
        pattern = (
            r"\b{}\b[`*_ ]*(?:(?:is|are|=|==|:|of|to|at|equals|set to|defaults to|default of|stays at)\s+|[=:]\s*)?"
            r"[`'\"]?{}(?!\w|\.\d)"
        ).format(re.escape(name), re.escape(value))
        return re.search(pattern, self.text, re.I) is not None


def _read_worktree(root, rel):
    path = os.path.join(root, rel)
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def _adr_dirs(root):
    docs = docs_root.write_root(root)
    return ["{}/development/adrs".format(docs), "{}/adr".format(docs)]


def load_adrs(root, base, merge_base):
    """ADRs as they are on `base`; `edited` compares the branch copy with the merge-base copy,
    so a decision that only moved on the base after the branch point is not a branch edit."""
    adrs = {}
    for directory in _adr_dirs(root):
        listing = _git(root, "ls-tree", "-r", "--name-only", "-z", base, "--", directory, check=False) or ""
        names = {p for p in listing.split("\0") if p}
        full = os.path.join(root, directory)
        if os.path.isdir(full) and not os.path.islink(full):
            names |= {"{}/{}".format(directory, n) for n in os.listdir(full)}
        for rel in sorted(names):
            if "/" in rel[len(directory) + 1:] or not ADR_NAME_RE.match(os.path.basename(rel)):
                continue
            old = _show(root, base, rel)
            new = _read_worktree(root, rel)
            if old is None and new is None:
                continue
            origin = _show(root, merge_base, rel)
            adrs[rel] = Adr(rel, old if old is not None else new, old is not None, origin is not None and origin != new)
    return adrs


class Row:
    def __init__(self, raw, cells):
        self.raw = raw
        (self.name, self.type, _rule, self.detect, self.ref, self.scope, self.severity) = cells
        # Back-references are refused, as scripts/reuse-lint.sh does: they make BSD grep exponential.
        self.mechanical = self.type == "code-pattern" and bool(self.detect) and not re.search(r"\\[1-9]", self.detect)
        self.timed_out = False

    def first_matches(self, files):
        """For each `(path, lines)` in `files`, the index into `lines` of the first one matching
        `detection` under `grep -E`. One grep per row for the whole branch: a spawn per file costs
        minutes on a large one. Raises `subprocess.TimeoutExpired` past `GREP_TIMEOUT`."""
        if not self.mechanical or self.timed_out:
            return {}
        owners, chunks = [], []
        for path, lines in files:
            for index, (_, text) in enumerate(lines):
                owners.append((path, index))
                chunks.append(text[:MAX_LINE_LEN].replace("\n", " "))
        if not chunks:
            return {}
        data = "\n".join(chunks) + "\n"
        try:
            proc = subprocess.run(
                ["grep", "-aEn", "-e", self.detect], input=data.encode("utf-8", "replace"),
                capture_output=True, check=False, timeout=GREP_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            self.timed_out = True
            raise
        if proc.returncode != 0:  # 1 no match, 2 invalid pattern: either way, no finding
            return {}
        hits = {}
        for out in proc.stdout.splitlines():
            number = out.split(b":", 1)[0]
            if not number.isdigit() or not 0 < int(number) <= len(owners):
                continue
            path, index = owners[int(number) - 1]
            hits.setdefault(path, index)
        return hits

    def in_scope(self, path):
        if not self.scope or self.scope == "*":
            return True
        return any(fnmatch.fnmatchcase(path, g.strip()) for g in self.scope.split(",") if g.strip())


def _clean(cell):
    cell = (cell or "").strip()
    if cell.startswith("`"):
        cell = cell[1:]
    if cell.endswith("`"):
        cell = cell[:-1]
    return cell


def parse_rows(text):
    # Must match the row parsing and scope/severity semantics of scripts/reuse-lint.sh.
    """The registry's rows, as `scripts/reuse-lint.sh` reads them (`\\|` is a literal pipe)."""
    rows = []
    for raw in (text or "").splitlines():
        if not raw.startswith("|"):
            continue
        parts = raw.replace("\\|", SEP).split("|")
        parts += [""] * (9 - len(parts))
        cells = [_clean(p).replace(SEP, "|") for p in parts[1:8]]
        name, kind = cells[0], cells[1]
        if not name or name == "name" or "---" in name:
            continue
        # cells: name, type, rule, detection, canonical_ref, scope, severity (added is unused here)
        rows.append(Row(raw.strip(), (name[:120], kind, cells[2], cells[3], cells[4][:120], cells[5], cells[6])))
    return rows


def load_rows(root, base, merge_base):
    try:
        rel = docs_root.doc_path(root, "reuse-guidelines")
    except (KeyError, OSError, ValueError):
        rel = ""
    if not rel:
        return [], []
    old = _show(root, base, rel)
    new = _read_worktree(root, rel)
    origin = _show(root, merge_base, rel)
    base_rows = parse_rows(old) if old is not None else []
    branch_raw = {r.raw for r in parse_rows(new)} if new is not None else set()
    origin_raw = {r.raw for r in parse_rows(origin)} if origin is not None else set()
    # Rows are read as they are on the base; a row the branch rewrote or dropped stays a
    # conflict source and is reported as an edit of its own. A row that reached the base
    # after the branch point was never the branch's to keep.
    for row in base_rows:
        row.edited = row.raw in origin_raw and row.raw not in branch_raw
    base_raw = {r.raw for r in base_rows}
    base_names = {r.name for r in base_rows}
    extra = [r for r in parse_rows(new) if r.raw not in base_raw and r.name not in base_names] if new is not None else []
    return base_rows, extra


def _changes(root, merge_base):
    """`{path: {"deleted": bool, "added": [(line, text)], "removed": [text]}}` for the branch."""
    spec = ["--", ".", ":(exclude){}".format(EXCLUDE)]
    names = _git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--name-status", "-z", merge_base, *spec)
    parts = [p for p in names.split("\0") if p]
    changes = {}
    for status, path in zip(parts[0::2], parts[1::2]):
        if "\n" in path:
            continue
        info = changes.setdefault(path, {"deleted": status.startswith("D"), "added": [], "removed": []})
        if info["deleted"]:
            continue
        diff = _git(root, "diff", "--no-ext-diff", "--no-textconv", "--no-color", "--unified=0",
                    merge_base, "--", path, check=False) or ""
        number = 0
        for line in diff.splitlines():
            hunk = re.match(r"^@@ -\S+ \+(\d+)", line)
            if hunk:
                number = int(hunk.group(1))
            elif number and line.startswith("+") and not line.startswith("+++"):
                info["added"].append((number, line[1:]))
                number += 1
            elif line.startswith("-") and not line.startswith("---"):
                info["removed"].append(line[1:])
    untracked = _git(root, "ls-files", "-z", "--others", "--exclude-standard", "--", ".", ":(exclude){}".format(EXCLUDE), check=False) or ""
    for path in (p for p in untracked.split("\0") if p):
        full = os.path.join(root, path)
        if "\n" in path or os.path.islink(full) or not os.path.isfile(full) or os.path.getsize(full) > MAX_FILE_BYTES:
            continue
        text = _read_worktree(root, path)
        if text is None or "\0" in text:
            continue
        changes[path] = {"deleted": False, "added": list(enumerate(text.splitlines(), 1)), "removed": []}
    return changes


def _number_changes(info):
    removed = {}
    for line in info["removed"]:
        for name, value in _NUMBER_RE.findall(line[:MAX_LINE_LEN]):
            removed.setdefault(name, []).append(value)
    for number, line in info["added"]:
        for name, new in _NUMBER_RE.findall(line[:MAX_LINE_LEN]):
            for old in removed.get(name, []):
                try:
                    if Decimal(old) != Decimal(new):
                        yield name, old, new, number
                except InvalidOperation:
                    continue


def _finding(kind, source_type, source, path, reason, line=None, ref=None):
    body = {"kind": kind, "source": source, "source_type": source_type, "path": path, "reason": reason}
    if line is not None:
        body["line"] = line
    if ref:
        body["ref"] = ref
    return body


def run(path=None, base=None):
    start = os.path.abspath(path or ".")
    if not os.path.isdir(start):
        raise EnvError("not a directory: {}".format(start))
    top = _git(start, "rev-parse", "--show-toplevel", check=False)
    if not top or not top.strip():
        raise EnvError("not a git repository: {}".format(start))
    root = top.strip()
    ref, how = resolve_base(root, base)
    merge_base = (_git(root, "merge-base", ref, "HEAD", check=False) or "").strip()
    if not merge_base:
        raise EnvError("no merge-base between {} and HEAD".format(ref), hint="Fetch the base, or pass --base <ref>.")

    changes = _changes(root, merge_base)
    adrs = load_adrs(root, ref, merge_base)
    base_rows, branch_rows = load_rows(root, ref, merge_base)
    findings, seen = [], set()

    def add(finding):
        key = (finding["kind"], finding["source"], finding["path"], finding.get("line"), finding["reason"])
        if key not in seen:
            seen.add(key)
            findings.append(finding)

    for row in base_rows:
        if getattr(row, "edited", False):
            add(_finding(LEAD, "reuse", row.name, "reuse-guidelines", "this branch edits or drops reuse rule '{}', a decision already on {}".format(row.name, ref)))

    for adr in adrs.values():
        if adr.edited:
            add(_finding(LEAD, "adr", adr.id, adr.path, "this branch edits {}, a decision already on {}".format(adr.id, ref)))

    reuse_hits = {}
    for row in base_rows + branch_rows:
        if row.type != "code-pattern":
            continue
        files = [(p_, i_["added"]) for p_, i_ in sorted(changes.items()) if row.in_scope(p_)]
        try:
            reuse_hits[id(row)] = row.first_matches(files)
        except subprocess.TimeoutExpired:
            reuse_hits[id(row)] = {}
            if files:
                add(_finding(LEAD, "reuse", row.name, files[0][0],
                             "detection timed out after {}s for rule '{}'; check was not run for it".format(GREP_TIMEOUT, row.name),
                             ref=row.ref))

    for path_, info in sorted(changes.items()):
        for adr in adrs.values():
            if not adr.governs(path_):
                continue
            kind = CONFLICT if adr.blocking else LEAD
            found = False
            for name, old, new, line in _number_changes(info):
                if adr.cites(name, old):
                    found = True
                    add(_finding(kind, "adr", adr.id, path_, "{} changed from {} to {}, but {} ({}) cites {}".format(
                        name, old, new, adr.id, adr.title, old), line=line, ref=adr.path))
            if not found:
                add(_finding(LEAD, "adr", adr.id, path_, "{} ({}) governs this path; re-read it".format(adr.id, adr.title), ref=adr.path))

        for row in base_rows + branch_rows:
            if row.type == "code-pattern" and row.in_scope(path_):
                hit = reuse_hits.get(id(row), {}).get(path_)
                if hit is not None:
                    line = info["added"][hit][0]
                    committed = row in base_rows
                    kind = CONFLICT if committed and row.severity != "advisory" else LEAD
                    add(_finding(kind, "reuse", row.name, path_,
                                 "matches '{}' rule, use {} instead".format(row.name, row.ref), line=line, ref=row.ref))
            elif row.type == "path-convention" and not info["deleted"] and row.in_scope(path_):
                name_glob, _, required = row.detect[len("path:"):].partition("=>") if row.detect.startswith("path:") else ("", "", "")
                if name_glob and required and fnmatch.fnmatchcase(os.path.basename(path_), name_glob) and not path_.startswith(required):
                    committed = row in base_rows
                    kind = CONFLICT if committed and row.severity != "advisory" else LEAD
                    add(_finding(kind, "reuse", row.name, path_, "violates '{}' path-convention, must live under {}".format(row.name, required), ref=row.ref))

    conflicts = [f for f in findings if f["kind"] == CONFLICT]
    return {
        "path": root,
        "base": ref,
        "base_resolved_from": how,
        "merge_base": merge_base,
        "changed_files": len(changes),
        "sources": {"adrs": sum(1 for a in adrs.values() if a.globs), "reuse_rules": len(base_rows) + len(branch_rows)},
        "findings": findings,
        "conflicts": len(conflicts),
        "leads": len(findings) - len(conflicts),
        "problems": conflicts,
    }


def render(result, limit=20):
    lines = ["checked {} changed file(s) against {} (merge-base {}, from {})".format(
        result["changed_files"], result["base"], result["merge_base"][:10], result["base_resolved_from"])]
    for label, kind in (("CONFLICT", CONFLICT), ("lead", LEAD)):
        items = [f for f in result["findings"] if f["kind"] == kind]
        for finding in items[: limit if kind == LEAD else None]:
            where = finding["path"] + (":{}".format(finding["line"]) if "line" in finding else "")
            lines.append("{} [{}] {} -- {}".format(label, finding["source"], where, finding["reason"]))
        if len(items) > limit and kind == LEAD:
            lines.append("... and {} more lead(s); see --json".format(len(items) - limit))
    if not result["findings"]:
        lines.append("no findings")
    return "\n".join(lines)
