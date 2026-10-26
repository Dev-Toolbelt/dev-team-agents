"""The project's docs write root: the first `context_paths` entry of project.json.

The single answer for every bash script and lint that writes or checks the wiki,
the ADR directory or docs/development/ (skills/shared/project-context/SKILL.md
§ Context Loading Order). `project.load` validates the file, so an absolute,
escaping or ill-typed entry never reaches a caller: anything that cannot be read
or validated answers `docs`, the default every project starts with.

It also answers the docs layout (project.json `docs_layout`, ADR-0045) and the path
`doc-layouts.json`, beside this file, maps a fact category to under that layout.

Usage: python3 -I docs_root.py <project-root>                → the relative write root
       python3 -I docs_root.py --layout <project-root>       → `development` or `gated`
       python3 -I docs_root.py --path <key> <project-root>   → `<write-root>/<path>`, or an
                                                               empty line when the layout has
                                                               no such doc; exit 2 on an unknown key
       python3 -I docs_root.py --readonly <project-root>     → the read-only paths, one per line
"""

import json
import os
import posixpath
import re
import sys

DEFAULT = "docs"
DEFAULT_LAYOUT = "development"
MAX_LEN = 200
# fullmatch, not match: `$` also matches before a trailing newline, and the shell's
# $(...) strips that newline — "..\n" would come back as "..".
SAFE_RE = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")

# -I leaves the script's own directory off sys.path; this one is the shipped lib dir.
# Appended, so nothing in it can shadow the standard library.
_LIB = os.path.dirname(os.path.abspath(__file__))
if _LIB not in sys.path:
    sys.path.append(_LIB)


LAYOUTS_FILE = os.path.join(_LIB, "doc-layouts.json")


def layouts_map():
    """The parsed doc-layouts.json. Raises when it is missing or malformed."""
    with open(LAYOUTS_FILE, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("docs"), dict):
        raise ValueError("doc-layouts.json: no 'docs' object")
    return data


def layout(root):
    """The project's docs layout; the map's default when absent, unknown or unreadable."""
    try:
        data = layouts_map()
    except (OSError, ValueError):
        return DEFAULT_LAYOUT
    default = data.get("default_layout", DEFAULT_LAYOUT)
    try:
        from devteam import project

        value = project.docs_layout(root)
    except Exception:  # noqa: BLE001 — same rule as write_root: never a crash
        return default
    return value if value in (data.get("layouts") or []) else default


def doc_path(root, key):
    """``<write_root>/<path>`` for ``key`` under the project's layout, "" when null.

    Raises ``KeyError`` for a key the map does not define.
    """
    docs = layouts_map()["docs"]
    if key not in docs:
        raise KeyError(key)
    rel = docs[key].get(layout(root))
    if not rel:
        return ""
    return "{}/{}".format(write_root(root), rel)


def readonly_paths(root):
    """Every read-only path the project's layout defines, as ``doc_path`` prints it."""
    docs = layouts_map()["docs"]
    current = layout(root)
    root_rel = write_root(root)
    return [
        "{}/{}".format(root_rel, entry[current])
        for entry in docs.values()
        if entry.get("readonly") and entry.get(current)
    ]


def writable_paths(root):
    """Every owner-doc path the project's layout defines that agents may write, as
    ``doc_path`` prints it — the map's non-read-only entries; what the embedded learn
    pass may stage (skills/shared/feature-learn/SKILL.md § Embedded Commit Capture)."""
    docs = layouts_map()["docs"]
    current = layout(root)
    root_rel = write_root(root)
    # Two keys may share one document (backlog-index and dod in the gated layout): list it once.
    seen = []
    for entry in docs.values():
        if not entry.get("readonly") and entry.get(current):
            path = "{}/{}".format(root_rel, entry[current])
            if path not in seen:
                seen.append(path)
    return seen


def _identity(root):
    """The validated project.json, read so that a bad ``docs_layout`` alone never costs
    ``context_paths``: the file is validated again without that key, under the same rules.

    ``layout()`` answers the default layout for such a file, because ``project.load``
    refuses it; the write root still comes from ``context_paths``.
    """
    from devteam import jsonio, project

    try:
        return project.load(root)
    except Exception:  # noqa: BLE001 — retried below without the layout key
        pass
    data = jsonio.read_json(project.project_file(root))
    if not isinstance(data, dict) or "docs_layout" not in data:
        return None
    rest = {key: value for key, value in data.items() if key != "docs_layout"}
    return project.validate(rest, source=str(project.project_file(root)))


def write_root(root):
    try:
        data = _identity(root)
    except Exception:  # noqa: BLE001 — an unreadable identity means the default, never a crash
        return DEFAULT
    paths = (data or {}).get("context_paths") or [DEFAULT]
    return _safe(paths[0])


def _safe(value):
    """``value`` when it is a plain relative folder path, else ``DEFAULT``.

    Checked on the exact string that is returned, never trimmed into shape after
    validating: trimming " .." after ``project.validate`` accepted it would yield ``..``. The value reaches shell
    variables, ``grep -E`` patterns, ``mkdir`` and agent-facing hook banners, so only
    letters, digits, ``.``, ``_``, ``-`` and ``/`` pass, no component may be ``..`` or
    start with ``-``, and the project root itself (``.``) is not a docs folder.
    """
    if not isinstance(value, str) or len(value) > MAX_LEN:
        return DEFAULT
    # Callers match it against git's repo-relative paths, so `./docs/` must read `docs`.
    normalized = posixpath.normpath(value) if value else ""
    if not SAFE_RE.fullmatch(normalized):
        return DEFAULT
    parts = normalized.split("/")
    if any(part in (".", "..") or part.startswith("-") for part in parts):
        return DEFAULT
    return normalized


def main(argv):
    args = list(argv)
    if not args or not args[0].startswith("--"):
        print(write_root(args[0] if args else "."))
        return 0
    flag = args.pop(0)
    if flag == "--path":
        if not args:
            print("usage: docs_root.py --path <key> [<project-root>]", file=sys.stderr)
            return 2
        key = args.pop(0)
        try:
            print(doc_path(args[0] if args else ".", key))
        except KeyError:
            print("docs_root.py: unknown doc key {!r}".format(key[:80]), file=sys.stderr)
            return 2
        return 0
    root = args[0] if args else "."
    if flag == "--layout":
        print(layout(root))
        return 0
    if flag in ("--readonly", "--writable"):
        for path in (readonly_paths if flag == "--readonly" else writable_paths)(root):
            print(path)
        return 0
    print("usage: docs_root.py [--layout | --path <key> | --readonly | --writable] [<project-root>]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
