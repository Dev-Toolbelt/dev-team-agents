#!/usr/bin/env python3
"""Fail when shipped content restates a claim known to be wrong.

Facts live in helpers/canonical-facts.json: each entry is a case-insensitive regex for the
wrong claim, optional `allow` regexes for lines that cite it on purpose (to say it is
retired), the reason, and the primary source. Only Markdown under the configured `paths`
is scanned.

Exit codes: 0 clean, 1 findings, 2 the config itself is broken.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REQUIRED = ("id", "pattern", "why", "source")


def load_facts(config_path):
    try:
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"canonical-facts: cannot read {config_path}: {exc}") from None
    if not isinstance(data, dict):
        raise SystemExit(f"canonical-facts: {config_path} must hold a JSON object")
    facts = data.get("facts")
    paths = data.get("paths")
    if (not isinstance(facts, list) or not isinstance(paths, list) or not paths
            or not all(isinstance(p, str) and p for p in paths)):
        raise SystemExit(f"canonical-facts: {config_path} needs non-empty `paths` and `facts` lists")
    compiled, seen = [], set()
    for entry in facts:
        if not isinstance(entry, dict):
            raise SystemExit(f"canonical-facts: every entry in `facts` must be an object, got {entry!r}")
        allow_list = entry.get("allow", [])
        if not isinstance(allow_list, list) or not all(isinstance(a, str) for a in allow_list):
            raise SystemExit(f"canonical-facts: entry {entry.get('id', '?')} needs `allow` as a list of strings")
        missing = [k for k in REQUIRED if not isinstance(entry.get(k), str) or not entry[k]]
        if missing:
            raise SystemExit(f"canonical-facts: entry {entry.get('id', '?')} lacks {', '.join(missing)}")
        if entry["id"] in seen:
            raise SystemExit(f"canonical-facts: duplicate id {entry['id']}")
        seen.add(entry["id"])
        try:
            pattern = re.compile(entry["pattern"], re.IGNORECASE)
            allow = [re.compile(a, re.IGNORECASE) for a in allow_list]
        except re.error as exc:
            raise SystemExit(f"canonical-facts: entry {entry['id']} has an invalid regex: {exc}") from None
        compiled.append((entry, pattern, allow))
    return paths, compiled


def scan(root, paths, facts):
    """Return findings, or None when no configured path exists under root."""
    findings, scanned = [], False
    for rel in paths:
        base = root / rel
        if not base.is_dir():
            continue
        scanned = True
        for md in sorted(base.rglob("*.md")):
            # Regular files inside the tree only: a symlinked or special file (FIFO) is skipped.
            if md.is_symlink() or not md.is_file():
                continue
            try:
                lines = md.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                print(f"canonical-facts: skipped unreadable {md}: {exc}", file=sys.stderr)
                continue
            for number, line in enumerate(lines, 1):
                for entry, pattern, allow in facts:
                    if pattern.search(line) and not any(a.search(line) for a in allow):
                        findings.append((md.relative_to(root).as_posix(), number, entry))
    return findings if scanned else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO), help="tree to scan (default: this repository)")
    parser.add_argument("--config", default=str(REPO / "helpers" / "canonical-facts.json"))
    parser.add_argument("--quiet", action="store_true", help="print nothing when clean")
    args = parser.parse_args(argv)

    try:
        paths, facts = load_facts(args.config)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    findings = scan(Path(args.root), paths, facts)
    if findings is None:
        print(f"canonical-facts: none of {', '.join(paths)} exists under {args.root} — nothing was scanned",
              file=sys.stderr)
        return 2
    if findings:
        print("canonical-facts: claims known to be wrong")
        for path, number, entry in findings:
            print(f"  · {path}:{number} [{entry['id']}] {entry['why']} — {entry['source']}")
        return 1
    if not args.quiet:
        print("canonical-facts: clean ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
