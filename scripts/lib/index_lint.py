"""Mechanical check of the project's retrieval indexes.

Usage: python3 index_lint.py <repo-root>

Covers the two indexes agents grep instead of opening documents, plus the lifecycle line of plan
documents:

- <docs>/wiki/README.md — skills/shared/docs-sync/references/wiki-format.md
- <adr-dir>/README.md — skills/shared/adr/SKILL.md § ADR Index; the ADR directory is resolved the
  way scripts/new-adr.sh resolves it (<docs>/development/adrs/, else <docs>/adr/)
- <docs>/development/plan-*.md — skills/shared/docs-sync/SKILL.md § Document Lifecycle

<docs> is the project's docs write root, the first `context_paths` entry (docs_root.py).

Prints one line per finding (`[index-lint] ERROR|WARN <path>: <message>`) and exits 1 when any
ERROR was found, 0 otherwise. Only an index row pointing at a file that does not exist is an
ERROR — it sends the lookup somewhere that is not there. Everything else (missing Tags, an
unindexed document, drift, thin keywords, an unfilled placeholder, a plan without a status) is a
WARN: a project that predates these rules carries many of them, and blocking every Stop on that
backlog would teach people to ignore the hook.
"""

import os
import re
import sys

# -I leaves this file's directory off sys.path; it is the shipped lib dir, docs_root.py beside it.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import docs_root  # noqa: E402

MIN_TERMS = 4
ADR_NAME_RE = re.compile(r"^(?:(?:adr|ADR)-)?[0-9]+-.*\.md$")
# First cell: a backticked path (the documented format) or a markdown link to it.
ROW_RE = re.compile(r"^\|\s*(?:`([^`]+)`|\[[^\]]*\]\(([^)\s]+)\))\s*\|(.*)\|\s*$")
TAGS_RE = re.compile(r"^\*\*Tags:\*\*\s*(.*?)\s*$", re.M)
STATUS_RE = re.compile(r"^\s*(?:[-*]\s*)?\**status\**\s*:", re.I | re.M)
PLACEHOLDERS = ("[status]", "[keywords]", "[read it when]")
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
        self.lines.append("[index-lint] {} {}: {}".format(level, rel, message))
        if level == "ERROR":
            self.errors += 1


def regular(path):
    """A regular file, not a symlink — a committed link could point outside the repository."""
    return os.path.isfile(path) and not os.path.islink(path)


def inside(root, path):
    """`path` is a real directory inside the repository — no link anywhere on the way.
    A symlinked docs/, docs/wiki or ADR directory could point at $HOME and make every
    Stop walk it, printing names from outside the repository into the hook banner."""
    if not os.path.isdir(path):
        return False
    real_root = os.path.realpath(root)
    return os.path.realpath(path).startswith(real_root + os.sep) and os.path.realpath(path) == os.path.join(
        real_root, os.path.relpath(path, root))


def plain_entry(rel):
    """A row's path stays inside its folder: never absolute, never `..`."""
    return not (os.path.isabs(rel) or rel.startswith("/") or ".." in rel.split("/"))


def exists_exactly(base, rel):
    """`rel` names a regular file under `base` with this exact spelling. A plain
    isfile() is case-insensitive on macOS and case-sensitive on Linux, so a row
    passing locally would fail in CI."""
    path = base
    for part in rel.split("/"):
        try:
            if part not in os.listdir(path):
                return False
        except OSError:
            return False
        path = os.path.join(path, part)
    return regular(path)


def read(path):
    """The file's text, or None when it cannot be read — one bad file never aborts the run."""
    if not regular(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def normalize(keywords):
    return ", ".join(term.strip() for term in keywords.split(",") if term.strip())


def term_count(keywords):
    return len([term for term in keywords.split(",") if term.strip()])


def index_rows(text):
    """`{entry: [cells after the first]}` for every table row whose first cell is a backticked
    path. Rows naming a directory (the legacy `## Domains` table) are not entries."""
    rows = {}
    for line in text.splitlines():
        match = ROW_RE.match(line.strip())
        if not match:
            continue
        entry = match.group(1) or match.group(2)
        # A link to a web page is not an entry; an anchor names a section of one.
        if match.group(2) and ("://" in entry or entry.startswith("mailto:")):
            continue
        entry = entry.split("#", 1)[0]
        if not entry or entry.endswith("/"):
            continue
        rows[entry] = [cell.strip() for cell in match.group(3).split("|")]
    return rows


def check_wiki(root, report, docs="docs"):
    wiki = os.path.join(root, docs, "wiki")
    if not inside(root, wiki):
        return
    index_path = os.path.join(wiki, "README.md")
    index = read(index_path)
    if index is None:
        return
    rows = index_rows(index)
    for entry, cells in sorted(rows.items()):
        if not plain_entry(entry):
            report.add("WARN", index_path, "row {} is not a path inside {}/wiki/".format(safe(entry), docs))
            continue
        if not exists_exactly(wiki, entry):
            report.add("ERROR", index_path, "row {} points at a file that does not exist".format(safe(entry)))
            continue
        if cells and term_count(cells[0]) < MIN_TERMS:
            report.add("WARN", index_path, "row {} has fewer than {} keywords".format(safe(entry), MIN_TERMS))
    for dirpath, dirnames, filenames in os.walk(wiki):
        dirnames[:] = sorted(d for d in dirnames if not os.path.islink(os.path.join(dirpath, d)))
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            # A domain folder's own README.md is a landing page, not an entry.
            if not name.endswith(".md") or name == "README.md":
                continue
            entry = os.path.relpath(path, wiki).replace(os.sep, "/")
            text = read(path)
            if text is None:
                continue
            tags = TAGS_RE.search(text)
            if not tags:
                report.add("WARN", path, "no **Tags:** line — its index row has nothing to copy")
            elif term_count(tags.group(1)) < MIN_TERMS:
                report.add("WARN", path, "**Tags:** has fewer than {} terms".format(MIN_TERMS))
            if entry not in rows:
                report.add("WARN", path, "no row in {}/wiki/README.md — the keyword lookup never finds it".format(docs))
            elif tags and rows[entry] and normalize(rows[entry][0]) != normalize(tags.group(1)):
                report.add("WARN", path, "index Keywords differ from the entry's **Tags:**")


def adr_dir(root, docs="docs"):
    """The directory scripts/new-adr.sh resolves: the first that holds ADRs, else the
    first that exists."""
    found = [os.path.join(root, docs, *c) for c in (("development", "adrs"), ("adr",))]
    found = [path for path in found if inside(root, path)]
    for path in found:
        if any(ADR_NAME_RE.match(name) for name in os.listdir(path)):
            return path
    return found[0] if found else None


def check_adrs(root, report, docs="docs"):
    directory = adr_dir(root, docs)
    if directory is None:
        return
    adrs = sorted(n for n in os.listdir(directory) if ADR_NAME_RE.match(n) and regular(os.path.join(directory, n)))
    index_path = os.path.join(directory, "README.md")
    index = read(index_path)
    if index is None:
        if adrs:
            report.add("WARN", directory, "{} ADRs and no README.md index".format(len(adrs)))
        return
    rows = index_rows(index)
    for name, cells in sorted(rows.items()):
        if not plain_entry(name):
            report.add("WARN", index_path, "row {} is not a path inside the ADR directory".format(safe(name)))
            continue
        if not exists_exactly(directory, name):
            report.add("ERROR", index_path, "row {} points at a file that does not exist".format(safe(name)))
            continue
        joined = " ".join(cells)
        if any(placeholder in joined for placeholder in PLACEHOLDERS):
            report.add("WARN", index_path, "row {} still has an unfilled placeholder".format(safe(name)))
        elif len(cells) > 1 and term_count(cells[1]) < MIN_TERMS:
            report.add("WARN", index_path, "row {} has fewer than {} keywords".format(safe(name), MIN_TERMS))
    for name in adrs:
        if name not in rows:
            report.add("WARN", os.path.join(directory, name), "no row in the ADR index")


def check_plans(root, report, docs="docs"):
    directory = os.path.join(root, docs, "development")
    if not inside(root, directory):
        return
    for name in sorted(os.listdir(directory)):
        if not (name.startswith("plan-") and name.endswith(".md")):
            continue
        path = os.path.join(directory, name)
        text = read(path)
        if text is None:
            continue
        head = "\n".join(text.splitlines()[:15])
        if not STATUS_RE.search(head):
            report.add("WARN", path, "no **Status:** line near the top — readers cannot tell whether it is current")


def main(argv):
    if len(argv) != 2:
        print("usage: index_lint.py <repo-root>", file=sys.stderr)
        return 2
    root = os.path.abspath(argv[1])
    report = Report(root)
    docs = docs_root.write_root(root)
    check_wiki(root, report, docs)
    check_adrs(root, report, docs)
    check_plans(root, report, docs)
    for line in report.lines:
        print(line)
    return 1 if report.errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception:  # noqa: BLE001 — the lint failing must never look like a finding
        sys.exit(3)
