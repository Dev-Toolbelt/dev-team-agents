"""Mechanical check of the spec layer — skills/shared/spec-gate/SKILL.md § Mechanical Check.

Usage: python3 spec_lint.py <repo-root>

Prints one line per finding (`[spec-lint] ERROR|WARN <path>: <message>`) and exits 1 when any
ERROR was found, 0 otherwise. A repository without docs/specs/ is a no-op.

A file under docs/specs/ is a spec-gate spec when it has a frontmatter block or an
`### Acceptance Criteria` heading; any other document there is not this format and is skipped.
A spec without a `status:` key predates the field: its own structural findings, missing
`depends_on` targets included, are reported as WARN. A sprint task that links a missing spec, or
cites a scenario ID its spec does not define, is an ERROR whatever the spec's age.
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


def regular(path):
    """A regular file, not a symlink — a committed link could point outside the repository."""
    return os.path.isfile(path) and not os.path.islink(path)


def read(path):
    """The file's text, or None when it cannot be read — one bad file never aborts the run."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


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
    sprint_dir = os.path.join(root, "docs", "backlog", "sprints")
    if not os.path.isdir(sprint_dir):
        return
    for name in sorted(os.listdir(sprint_dir)):
        path = os.path.join(sprint_dir, name)
        if not name.endswith(".md") or name == "sprints.md" or not regular(path):
            continue
        text = read(path)
        if text is None:
            report.add("WARN", path, "unreadable, skipped")
            continue
        for block in re.split(r"^### (?=TASK-\d+)", text, flags=re.M)[1:]:
            task = block.split(None, 1)[0]
            spec_line = re.search(r"^\*\*Spec\*\*:\s*(.*)$", block, re.M)
            if not spec_line:
                continue
            linked = []
            for ref in re.findall(r"docs/specs/[A-Za-z0-9._/-]+\.md", spec_line.group(1)):
                if not regular(os.path.join(root, ref)):
                    report.add("ERROR", path, "{} links {}, which does not exist".format(safe(task), safe(ref)))
                elif not ref.endswith("-contract.md"):
                    linked.append(spec_name(ref))
            covers = re.search(r"^\*\*Covers\*\*:\s*(.*)$", block, re.M)
            if not covers or not linked:
                continue
            known = set().union(*(specs.get(n, {}).get("ids", set()) for n in linked))
            for ident in re.findall(r"\bS\d+\b", covers.group(1)):
                if ident not in known:
                    report.add("ERROR", path, "{} covers {}, which {} does not define".format(
                        safe(task), ident, ", ".join(safe(n + ".md") for n in linked)))


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
    if not os.path.isdir(spec_dir):
        return 0
    report = Report(root)
    specs, contracts = load_specs(report, spec_dir)
    for name, spec in specs.items():
        check_spec(report, name, spec)
    check_dependencies(report, specs)
    check_contracts(report, specs, contracts)
    check_tasks(report, root, specs)
    check_coverage(report, root, specs)
    for line in report.lines:
        print(line)
    return 1 if report.errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # a lint failure is not a spec finding: spec-lint.sh treats 3 as a no-op
        sys.exit(3)
