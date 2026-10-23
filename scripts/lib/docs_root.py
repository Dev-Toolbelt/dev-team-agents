"""The project's docs write root: the first `context_paths` entry of project.json.

The single answer for every bash script and lint that writes or checks the wiki,
the ADR directory or docs/development/ (skills/shared/project-context/SKILL.md
§ Context Loading Order). `project.load` validates the file, so an absolute,
escaping or ill-typed entry never reaches a caller: anything that cannot be read
or validated answers `docs`, the default every project starts with.

Usage: python3 -I docs_root.py <project-root>   → prints the relative write root
"""

import os
import posixpath
import re
import sys

DEFAULT = "docs"
MAX_LEN = 200
# fullmatch, not match: `$` also matches before a trailing newline, and the shell's
# $(...) strips that newline — "..\n" would come back as "..".
SAFE_RE = re.compile(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")

# -I leaves the script's own directory off sys.path; this one is the shipped lib dir.
# Appended, so nothing in it can shadow the standard library.
_LIB = os.path.dirname(os.path.abspath(__file__))
if _LIB not in sys.path:
    sys.path.append(_LIB)


def write_root(root):
    try:
        from devteam import project

        data = project.load(root)
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


if __name__ == "__main__":
    print(write_root(sys.argv[1] if len(sys.argv) > 1 else "."))
