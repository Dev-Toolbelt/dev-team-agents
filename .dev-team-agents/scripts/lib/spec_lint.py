"""Mechanical check of the spec layer — skills/shared/spec-gate/SKILL.md § Mechanical Check.

Usage: python3 spec_lint.py <repo-root>

Prints one line per finding (`[spec-lint] ERROR|WARN <path>: <message>`) and exits 1 when any
ERROR was found, 0 otherwise. A repository without docs/specs/ is a no-op.

A file under docs/specs/ is a spec-gate spec when it has a frontmatter block or an
`### Acceptance Criteria` heading; any other document there is not this format and is skipped.
A spec without a `status:` key predates the field: its own structural findings, missing
`depends_on` targets included, are reported as WARN. A sprint task that links a missing spec, or
cites a scenario ID its spec does not define, is an ERROR whatever the spec's age.

In the gated docs layout only (project.json `docs_layout`, scripts/lib/doc-layouts.json), every
sprint task whose Status is not Done is also checked against the Definition of Ready
(skills/shared/doc-flow/SKILL.md § Definition of Ready). Each failure prints
`[NOT-READY] TASK-NNN: <reason>`. It does not change the exit code: a gap is normal while a
stage is still being planned, so the Stop hook reports it once per set like a WARN, and the
execution gate (spec-gate § Scope Lock) refuses the task on the line itself:

- Contract — `<feature>-contract.md` in the `specs` doc (linked from the task or beside its spec) has an
  open point under its `### Open Points` heading (.dev-team-agents/templates/contract-template.md): every `- ` or
  `* ` line at column 0 up to the next heading is one (an indented sub-bullet is not), except the
  single bullet `- none`.

Every path this check opens — a sprint task's reference or a map folder — must resolve inside the
repository (no `..`, no symlinked parent leading out) and is read with a 1 MiB cap.
- Design — a spec whose `touches` includes `frontend` needs the `design-flows` doc
  `<feature>.md` (.dev-team-agents/templates/design-flow-template.md) with at least one `### States` table whose
  header names `State`, `Frame / PNG` and `Status` columns; every row needs Status `approved`
  and its `Frame / PNG` cell must name an existing `.png` inside the `design-screens` doc's
  `<feature>/` folder (a bare file name is read relative to that folder).
- Evals — a spec with `ai: true` in its frontmatter needs the `evals` doc to hold a
  `## <feature>` heading.
"""

import os
import re
import subprocess
import sys

STATUSES = ("draft", "approved", "implemented")
LAYERS = ("backend", "frontend", "database", "mobile")
SCENARIO_RE = re.compile(r"^\*\*Scenario\b(.*?)\*\*", re.M)
SCENARIO_ID_RE = re.compile(r"^(?:\s*\[[^\]]*\])?\s*(S\d+)\s*(?:\[[^\]]*\]\s*)?:")
TOKEN_RE = re.compile(r"\[spec:([A-Za-z0-9._-]+)#(S\d+)\]")
TOKEN_GREP = r"\[spec:[A-Za-z0-9._-]+#S[0-9]+\]"
PLACEHOLDER_REASONS = ("", "-", "tbd", "todo", "n/a", "[why]", "...", "…")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def safe(value, limit=60):
    """Repository text, quoted and stripped of control characters — the Stop hook
    feeds the report back to the model, so it must never read as an instruction."""
    return repr(CONTROL_RE.sub("?", str(value))[:limit])


class Report:
    def __init__(self, root):
        self.root = root
        self.lines = []
        self.errors = 0

    def add(self, level, path, message):
        rel = safe(os.path.relpath(path, self.root), 200)
        self.lines.append("[spec-lint] {} {}: {}".format(level, rel, message))
        if level == "ERROR":
            self.errors += 1

    def not_ready(self, task_id, reason):
        self.lines.append("[NOT-READY] {}: {}".format(CONTROL_RE.sub("?", str(task_id))[:20], reason))


def regular(path):
    """A regular file, not a symlink — a committed link could point outside the repository."""
    return os.path.isfile(path) and not os.path.islink(path)


def read(path):
    """The file's text, or None when it cannot be read — one bad file never aborts the run.

    The sprint reader's guarded read (ADR-0044): no symlink, a regular file, at most
    ``MAX_FILE_BYTES`` (1 MiB), so a crafted document cannot make the lint slow or huge.
    """
    from devteam import backlog

    return backlog.read_text(path)


def inside(root, path):
    """Whether ``path`` resolves inside ``root`` — a `..` in a sprint reference or a
    symlinked parent folder (docs/specs -> /elsewhere) must never lead the lint out."""
    real_root = os.path.realpath(root)
    return os.path.realpath(path).startswith(real_root + os.sep)


def repo_file(root, rel):
    """``root/rel`` normalised, or None when it leaves the repository."""
    path = os.path.normpath(os.path.join(root, *rel.split("/")))
    return path if inside(root, path) else None


def contained(root, path):
    """A regular file (not a symlink) that resolves inside ``root``."""
    return bool(path) and regular(path) and inside(root, path)


def split_frontmatter(text):
    body = re.sub(r"^\s*<!--.*?-->\s*", "", text, count=1, flags=re.S)
    if not body.startswith("---\n"):
        return None, text
    end = body.find("\n---", 4)
    if end == -1:
        return None, text
    fields, last = {}, None
    for line in body[4:end].splitlines():
        line = line.split("#", 1)[0].rstrip()
        item = re.match(r"^\s+-\s+(.*)$", line) or re.match(r"^-\s+(.*)$", line)
        if item and last is not None:
            current = fields.get(last)
            fields[last] = (current if isinstance(current, list) else []) + [item.group(1).strip().strip("'\"")]
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            fields[key.strip()] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            fields[key.strip()] = value.strip("'\"")
        last = key.strip()
    return fields, body[end + 4:]


def spec_name(entry):
    entry = os.path.basename(entry.strip())
    return entry[:-3] if entry.endswith(".md") else entry


def scenario_ids(body):
    found, missing = [], 0
    for match in SCENARIO_RE.finditer(body):
        ident = SCENARIO_ID_RE.match(match.group(1))
        if ident:
            found.append(ident.group(1))
        else:
            missing += 1
    return found, missing


def amendment_entries(body):
    section = re.search(r"^### Amendment Log\s*\n(.*?)(?=^#{1,3} |^---\s*$|\Z)", body, re.M | re.S)
    if not section:
        return []
    entries = []
    for line in section.group(1).splitlines():
        if line.startswith("- "):
            entries.append(line[2:])
        elif entries and line.startswith("  "):
            entries[-1] += " " + line.strip()
    return [e for e in entries if not e.startswith("YYYY-MM-DD")]


def check_amendments(report, path, body, level):
    for entry in amendment_entries(body):
        parts = [p.strip() for p in entry.split("|")]
        if len(parts) < 4 or parts[-1].lower() in PLACEHOLDER_REASONS:
            report.add(level, path, "Amendment Log entry without a reason: {}".format(safe(entry)))


def load_specs(report, spec_dir):
    specs, contracts = {}, []
    for name in sorted(os.listdir(spec_dir)):
        path = os.path.join(spec_dir, name)
        if not name.endswith(".md") or not regular(path):
            continue
        if name.endswith("-contract.md"):
            contracts.append(path)
            continue
        text = read(path)
        if text is None:
            report.add("WARN", path, "unreadable, skipped")
            continue
        fields, body = split_frontmatter(text)
        if fields is None and not re.search(r"^### Acceptance Criteria", text, re.M):
            continue
        specs[name[:-3]] = {"path": path, "fields": fields, "body": body}
    return specs, contracts


def check_spec(report, name, spec):
    path, fields, body = spec["path"], spec["fields"], spec["body"]
    if fields is None:
        report.add("WARN", path, "no frontmatter (legacy spec, treated as approved) — add status, touches and depends_on")
        fields = {}
    elif "status" not in fields:
        report.add("WARN", path, "no status: key (legacy spec) — treated as approved")
    legacy = "status" not in fields
    level = "WARN" if legacy else "ERROR"
    if not legacy and fields["status"] not in STATUSES:
        report.add("ERROR", path, "status {} is not one of {}".format(safe(fields["status"]), ", ".join(STATUSES)))
    touches = fields.get("touches", [])
    if not isinstance(touches, list):
        report.add(level, path, "touches must be a list ([a, b] or one '- item' per line)")
    else:
        for layer in touches:
            if layer not in LAYERS:
                report.add(level, path, "touches {} is not one of {}".format(safe(layer), ", ".join(LAYERS)))
    ids, missing = scenario_ids(body)
    spec["ids"] = set(ids)
    if missing:
        report.add(level, path, "{} scenario(s) without an S<n> ID".format(missing))
    for ident in sorted({i for i in ids if ids.count(i) > 1}):
        report.add(level, path, "scenario ID {} is used more than once".format(ident))
    if not legacy:
        check_amendments(report, path, body, "ERROR")
    return legacy


def check_dependencies(report, specs):
    graph = {}
    legacy = {n for n, s in specs.items() if "status" not in (s["fields"] or {})}
    for name, spec in specs.items():
        deps = (spec["fields"] or {}).get("depends_on", [])
        deps = deps if isinstance(deps, list) else [deps] if deps else []
        graph[name] = []
        for dep in deps:
            target = spec_name(dep)
            if target in specs:
                graph[name].append(target)
            else:
                report.add("WARN" if name in legacy else "ERROR", spec["path"],
                           "depends_on {} names no spec in docs/specs/".format(safe(dep)))
    state = {}

    def visit(node, trail):
        state[node] = "open"
        for nxt in graph[node]:
            if state.get(nxt) == "open":
                cycle = trail[trail.index(nxt):] + [nxt]
                level = "WARN" if set(cycle) <= legacy else "ERROR"
                report.add(level, specs[node]["path"], "dependency cycle: {}".format(" → ".join(safe(n) for n in cycle)))
            elif nxt not in state:
                visit(nxt, trail + [nxt])
        state[node] = "done"

    for node in sorted(graph):
        if node not in state:
            visit(node, [node])


def check_contracts(report, specs, contracts):
    for path in contracts:
        feature = os.path.basename(path)[: -len("-contract.md")]
        if feature not in specs:
            report.add("ERROR", path, "contract has no spec {} beside it".format(safe(feature + ".md")))
        text = read(path)
        if text is None:
            report.add("WARN", path, "unreadable, skipped")
            continue
        fields, body = split_frontmatter(text)
        if fields is not None:
            check_amendments(report, path, body, "ERROR")


def check_tasks(report, root, specs):
    # The sprint task block has one reader, shared with `devteam backlog` (ADR-0044): it decides
    # where a task's fields end and which files are sprint files (no symlink, no oversized file).
    from devteam import backlog

    for sprint in backlog.sprint_files(root):
        # Named from the root as given, so a report path never turns into `../../private/var/…`.
        path = os.path.join(root, "docs", "backlog", "sprints", sprint.name)
        if not regular(path):
            continue
        text = backlog.read_text(sprint)
        if text is None:
            report.add("WARN", path, "unreadable, skipped")
            continue
        for task in backlog.parse(text)["tasks"]:
            linked = []
            for ref in task["spec_refs"]:
                if not contained(root, repo_file(root, ref)):
                    report.add("ERROR", path, "{} links {}, which does not exist".format(safe(task["id"]), safe(ref)))
                elif not ref.endswith("-contract.md"):
                    linked.append(spec_name(ref))
            if not task["covers"] or not linked:
                continue
            known = set().union(*(specs.get(n, {}).get("ids", set()) for n in linked))
            for ident in task["covers"]:
                if ident not in known:
                    report.add("ERROR", path, "{} covers {}, which {} does not define".format(
                        safe(task["id"]), ident, ", ".join(safe(n + ".md") for n in linked)))


OPEN_POINTS_HEAD_RE = re.compile(r"^#{2,3}[ \t]+Open Points[ \t]*$", re.M | re.I)
STATES_HEAD_RE = re.compile(r"^#{2,3}[ \t]+States[ \t]*$", re.M | re.I)
ANY_HEAD_RE = re.compile(r"^#{1,6}[ \t]", re.M)
# Column 0 only: an indented sub-bullet details its parent point, it is not another one.
LIST_ITEM_RE = re.compile(r"^[-*][ \t]+(.*)$")
PNG_COLUMN = "frame / png"


def sections(text, heading_re):
    """The text under every heading ``heading_re`` matches, each up to the next heading."""
    found = []
    for head in heading_re.finditer(text):
        # Searched from an offset, never on a slice: a copy per heading was quadratic.
        nxt = ANY_HEAD_RE.search(text, head.end())
        found.append(text[head.end(): nxt.start() if nxt else len(text)])
    return found


def strip_comments(text):
    """``text`` without its `<!-- … -->` comments, in one linear pass.

    An unclosed `<!--` keeps the rest of the text, as the regex it replaces did, but
    without rescanning to the end once per unclosed opener.
    """
    out, pos = [], 0
    while True:
        start = text.find("<!--", pos)
        if start == -1:
            break
        end = text.find("-->", start + 4)
        if end == -1:
            break
        out.append(text[pos:start])
        pos = end + 3
    out.append(text[pos:])
    return "".join(out)


def open_points(text):
    """The items under a contract's `### Open Points` heading; the single `- none` is zero."""
    body = sections(strip_comments(text), OPEN_POINTS_HEAD_RE)
    items = [m.group(1).strip() for line in (body[0] if body else "").splitlines()
             for m in [LIST_ITEM_RE.match(line)] if m]
    if len(items) == 1 and items[0].rstrip(".").strip().lower() == "none":
        return []
    return items


def state_rows(text):
    """``(rows, error)`` — each row a ``(state, png, status)`` from every `### States` table."""
    bodies = sections(strip_comments(text), STATES_HEAD_RE)
    if not bodies:
        return None, "has no ### States table"
    rows = []
    for body in bodies:
        header = None
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|"):
                if header is not None:
                    break
                continue
            cells = [c.strip().strip("`").strip() for c in line.strip("|").split("|")]
            if header is None:
                header = [c.lower() for c in cells]
                if not {"state", PNG_COLUMN, "status"} <= set(header):
                    return None, "has a ### States table without State, Frame / PNG and Status columns"
                continue
            if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                continue
            cell = dict(zip(header, cells))
            rows.append((cell.get("state", ""), cell.get(PNG_COLUMN, ""), cell.get("status", "")))
    if not rows:
        return None, "has no rows in its ### States table"
    return rows, None


def screen_png(root, screens, feature, cell):
    """The PNG a `Frame / PNG` cell names, when it is a .png inside ``<screens>/<feature>/``."""
    if not screens or not cell.lower().endswith(".png") or CONTROL_RE.search(cell):
        return None
    folder = os.path.join(screens, feature)
    path = os.path.normpath(os.path.join(folder if "/" not in cell else root, cell))
    if not path.startswith(os.path.normpath(folder) + os.sep):
        return None
    return path


def layout_dir(root, key):
    """The map's directory for ``key`` under the project's layout, absolute, or None."""
    import docs_root

    rel = docs_root.doc_path(root, key)
    return os.path.join(root, *rel.strip("/").split("/")) if rel else None


def contracts_for(root, task, linked):
    """The task's contracts: the ones it links plus each linked spec's, in the `specs` doc."""
    paths = [repo_file(root, ref) for ref in task["spec_refs"] if ref.endswith("-contract.md")]
    specs_dir = layout_dir(root, "specs")
    for name in linked if specs_dir else []:
        beside = os.path.normpath(os.path.join(specs_dir, name + "-contract.md"))
        if beside not in paths:
            paths.append(beside)
    return [p for p in paths if contained(root, p)]


def ready_reasons(root, task, linked, specs):
    reasons = []
    for path in contracts_for(root, task, linked):
        count = len(open_points(read(path) or ""))
        if count:
            reasons.append("contract {} has {} open point(s)".format(safe(os.path.relpath(path, root), 200), count))
    flows, screens, evals = (layout_dir(root, k) for k in ("design-flows", "design-screens", "evals"))
    for name in linked:
        fields = (specs.get(name) or {}).get("fields") or {}
        touches = fields.get("touches", [])
        label = safe(name)
        if isinstance(touches, list) and "frontend" in touches:
            flow = os.path.join(flows, name + ".md") if flows else None
            text = read(flow) if contained(root, flow) else None
            if text is None:
                reasons.append("spec {} touches frontend but has no screen flow {}".format(
                    label, safe(os.path.relpath(flow, root), 200) if flow else "(no design-flows doc)"))
            else:
                rows, error = state_rows(text)
                if error:
                    reasons.append("screen flow of {} {}".format(label, error))
                for state, cell, status in rows or []:
                    png = screen_png(root, screens, name, cell)
                    if status.lower() != "approved":
                        reasons.append("state {} of {} is not approved".format(safe(state), label))
                    elif png is None:
                        reasons.append("state {} of {} names no PNG inside the design-screens {}/ folder".format(
                            safe(state), label, label))
                    elif not contained(root, png):
                        reasons.append("state {} of {} is approved but {} does not exist".format(
                            safe(state), label, safe(os.path.relpath(png, root), 200)))
        if str(fields.get("ai", "")).lower() == "true":
            text = read(evals) if contained(root, evals) else None
            heading = re.compile(r"^##[ \t]+" + re.escape(name) + r"[ \t]*$", re.M)
            if text is None or not heading.search(text):
                reasons.append("spec {} is ai: true but the evals doc has no ## {} section".format(label, label))
    return reasons


def check_ready(report, root, specs):
    """Definition of Ready for every open sprint task — gated layout only."""
    import docs_root
    from devteam import backlog

    if docs_root.layout(root) != "gated":
        return
    for sprint in backlog.sprint_files(root):
        text = backlog.read_text(sprint)
        if text is None:
            continue
        for task in backlog.parse(text)["tasks"]:
            if task["status"] == "done":
                continue
            linked = [spec_name(r) for r in task["spec_refs"]
                      if not r.endswith("-contract.md") and contained(root, repo_file(root, r))]
            for reason in ready_reasons(root, task, linked, specs):
                report.not_ready(task["id"], reason)


def tests_required(root):
    for name in ("CLAUDE.md", "AGENTS.md"):
        path = os.path.join(root, name)
        if regular(path) and re.search(r"TESTS_REQUIRED\s*[:=]\s*no\b", read(path) or ""):
            return False
    return True


def referenced_tokens(root):
    """Tokens in tracked and untracked, non-ignored files outside docs/ and Markdown.

    `git grep` on the worktree reads regular files only and skips symlinks, devices and
    FIFOs, so a link to a device or to a file outside the repository cannot hang the hook
    or widen what it reads. `-I` skips binaries. None when the search itself failed.
    """
    try:
        found = subprocess.run(
            ["git", "-C", root, "grep", "-I", "--untracked", "-hoE", TOKEN_GREP,
             "--", ".", ":!docs/", ":!.dev-team-agents/", ":!*.md"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if found.returncode not in (0, 1):
        return None
    return set(TOKEN_RE.findall(found.stdout))


def check_coverage(report, root, specs):
    implemented = {n: s for n, s in specs.items() if (s["fields"] or {}).get("status") == "implemented"}
    if not implemented or not tests_required(root):
        return
    tokens = referenced_tokens(root)
    if tokens is None:
        return
    for name, spec in sorted(implemented.items()):
        uncovered = sorted(i for i in spec["ids"] if (name, i) not in tokens)
        if uncovered:
            report.add("WARN", spec["path"], "implemented, but no test carries [spec:{}#…] for {}".format(
                CONTROL_RE.sub("?", name)[:60], ", ".join(uncovered)))


def main(argv):
    root = os.path.abspath(argv[1] if len(argv) > 1 else ".")
    spec_dir = os.path.join(root, "docs", "specs")
    # A symlinked docs/specs (or parent) that leads out of the repository is not this one's spec layer.
    if not os.path.isdir(spec_dir) or not inside(root, spec_dir):
        return 0
    report = Report(root)
    specs, contracts = load_specs(report, spec_dir)
    for name, spec in specs.items():
        check_spec(report, name, spec)
    check_dependencies(report, specs)
    check_contracts(report, specs, contracts)
    check_tasks(report, root, specs)
    check_ready(report, root, specs)
    check_coverage(report, root, specs)
    for line in report.lines:
        print(line)
    return 1 if report.errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # a lint failure is not a spec finding: spec-lint.sh treats 3 as a no-op
        sys.exit(3)
