"""Project identity and the committed ``project.json`` (ADR-0008).

The file holds identity and topology, never a preference:

    {"schema": 1, "project_id": "<uuid4>", "context_paths": ["docs"]}

It is committed so the identity survives a re-clone, a directory move and a
machine change — the three events that would otherwise orphan the project's
memory in ``data/projects/<project_id>/``.
"""

from __future__ import annotations

import re
import subprocess
import uuid
from pathlib import Path

from . import jsonio
from .errors import EnvError, UsageError

PROJECT_DIR = ".dev-team-agents"
PROJECT_FILE = "project.json"
SCHEMA = 1
DEFAULT_CONTEXT_PATHS = ["docs"]

#: Where the project's own state lives. Distinct from ``schema``, which describes
#: this file's format: a project can be on the current schema and an older layout.
#:
#: 1 — memory in the project (``.dev-team-agents/user-data/``), the v2 and M1 shape
#: 2 — memory in the data store (``data/projects/<project_id>/``), project clean
#:
#: A project is **never** moved between layouts automatically. The CLI reports that
#: an upgrade is available and `devteam upgrade` performs it with confirmation, so
#: the fallback is scoped by an explicit recorded version rather than living
#: indefinitely in the readers.
LAYOUT_MEMORY_IN_PROJECT = 1
LAYOUT_MEMORY_IN_STORE = 2
CURRENT_LAYOUT = LAYOUT_MEMORY_IN_STORE
#: The pointer the bash hooks read to find the state directory in one file read,
#: instead of a subprocess per `state_get`.
STATE_DIR_POINTER = "state-dir"
LEGACY_MEMORY_DIR = "user-data"

# `fullmatch`, not `$`: `$` also matches before a trailing newline, so a
# project_id carrying one passed validation and then became a directory name
# with an embedded newline under data/projects/.
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def project_file(root):
    return Path(root) / PROJECT_DIR / PROJECT_FILE


def resolve_root(start=None):
    """Find the project root for ``start``.

    Preference order: an existing ``project.json`` at or above ``start``, then
    the git top level, then ``start`` itself. Looking for the marker first means
    running the CLI from a subdirectory of an already-bound project never
    creates a second identity.
    """
    base = Path(start).resolve() if start else Path.cwd().resolve()
    for candidate in [base] + list(base.parents):
        if project_file(candidate).exists():
            return candidate
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(base),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return base
    if out.returncode == 0:
        top = out.stdout.decode("utf-8", "replace").strip()
        if top:
            return Path(top).resolve()
    return base


def validate(data, source="project.json"):
    """Raise on anything the rest of the CLI would have to defend against."""
    if not isinstance(data, dict):
        raise EnvError("{}: expected a JSON object".format(source))

    schema = data.get("schema")
    if not isinstance(schema, int) or isinstance(schema, bool) or schema < 1:
        raise EnvError("{}: 'schema' must be a positive integer".format(source))
    if schema > SCHEMA:
        raise EnvError(
            "{}: schema {} is newer than this CLI understands (max {})".format(
                source, schema, SCHEMA
            ),
            hint="Update dev-team-agents — an older CLI must not rewrite a newer file.",
        )

    pid = data.get("project_id")
    if not isinstance(pid, str) or not _UUID_RE.fullmatch(pid):
        raise EnvError("{}: 'project_id' must be a lowercase UUID string".format(source))

    layout_value = data.get("layout", LAYOUT_MEMORY_IN_PROJECT)
    if not isinstance(layout_value, int) or isinstance(layout_value, bool) or layout_value < 1:
        raise EnvError("{}: 'layout' must be a positive integer".format(source))
    if layout_value > CURRENT_LAYOUT:
        raise EnvError(
            "{}: layout {} is newer than this CLI understands (max {})".format(
                source, layout_value, CURRENT_LAYOUT
            ),
            hint="Update dev-team-agents.",
        )

    paths_value = data.get("context_paths", DEFAULT_CONTEXT_PATHS)
    if not isinstance(paths_value, list) or not paths_value:
        raise EnvError("{}: 'context_paths' must be a non-empty list".format(source))
    for item in paths_value:
        if not isinstance(item, str) or not item.strip():
            raise EnvError("{}: every context path must be a non-empty string".format(source))
        candidate = Path(item)
        if candidate.is_absolute():
            raise EnvError(
                "{}: context path '{}' must be relative to the project root".format(
                    source, item
                )
            )
        if ".." in candidate.parts:
            raise EnvError(
                "{}: context path '{}' must stay inside the project".format(source, item)
            )
    return data


def load(root):
    """Return the validated project file, or ``None`` when absent."""
    data = jsonio.read_json(project_file(root))
    if data is None:
        return None
    return validate(data, source=str(project_file(root)))


def ensure(root, context_paths=None):
    """Create ``project.json`` when absent; never regenerate an existing one.

    Returns ``(data, created)``. An existing identity is preserved, which is
    what makes ``devteam bind`` idempotent.
    """
    existing = load(root)
    if existing is not None:
        if context_paths:
            merged = list(existing.get("context_paths", DEFAULT_CONTEXT_PATHS))
            for item in context_paths:
                if item not in merged:
                    merged.append(item)
            if merged != existing.get("context_paths"):
                existing["context_paths"] = merged
                validate(existing, source=str(project_file(root)))
                jsonio.write_json_atomic(
                    project_file(root), existing, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None
                )
        return existing, False

    # A project that already carries in-project memory starts on layout 1 and needs
    # an explicit `devteam upgrade`; one that never had a v2 install is born on the
    # current layout, so it is clean from the first bind and has nothing to move.
    born_layout = (
        LAYOUT_MEMORY_IN_PROJECT if legacy_memory_dir(root).is_dir() else CURRENT_LAYOUT
    )
    data = {
        "schema": SCHEMA,
        "project_id": str(uuid.uuid4()),
        "layout": born_layout,
        "context_paths": list(context_paths or DEFAULT_CONTEXT_PATHS),
    }
    validate(data, source=str(project_file(root)))
    jsonio.write_json_atomic(
        project_file(root), data, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None
    )
    return data, True


def reassign_identity(root):
    """Give the project a brand-new ``project_id``.

    Used by ``doctor`` on the fork case, where two checkouts inherited the same
    identity. The old memory is left where it is — it belongs to whichever
    checkout keeps the original id.
    """
    data = load(root)
    if data is None:
        raise UsageError("{} has no {} to reassign".format(root, PROJECT_FILE))
    previous = data["project_id"]
    data["project_id"] = str(uuid.uuid4())
    jsonio.write_json_atomic(
        project_file(root), data, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None
    )
    return previous, data["project_id"]


def context_paths(root):
    data = load(root)
    if data is None:
        return list(DEFAULT_CONTEXT_PATHS)
    return list(data.get("context_paths", DEFAULT_CONTEXT_PATHS))


def layout(root):
    """The recorded layout, defaulting to 1 for a project that predates the key."""
    data = load(root)
    if data is None:
        return LAYOUT_MEMORY_IN_PROJECT
    return int(data.get("layout", LAYOUT_MEMORY_IN_PROJECT))


def set_layout(root, value):
    data = load(root)
    if data is None:
        raise UsageError("{} is not a bound project".format(root))
    data["layout"] = int(value)
    validate(data, source=str(project_file(root)))
    jsonio.write_json_atomic(
        project_file(root), data, mode=jsonio.PROJECT_FILE_MODE, dir_mode=None
    )
    return data


def legacy_memory_dir(root):
    """The in-project memory directory, whether or not it is still in use."""
    return Path(root) / PROJECT_DIR / LEGACY_MEMORY_DIR


def memory_dir(root, project_id=None):
    """Where this project's memory lives, according to its recorded layout."""
    from . import paths

    if layout(root) >= LAYOUT_MEMORY_IN_STORE:
        pid = project_id
        if pid is None:
            data = load(root)
            pid = data["project_id"] if data else None
        if not pid:
            raise EnvError("cannot resolve the memory directory without a project_id")
        return paths.project_data_dir(pid)
    return legacy_memory_dir(root)


def memory_dir_for_layout(root, project_id, target_layout):
    """Where memory lives under a given layout — used to plan a move between them."""
    from . import paths

    if target_layout >= LAYOUT_MEMORY_IN_STORE:
        return paths.project_data_dir(project_id)
    return legacy_memory_dir(root)


def write_state_pointer(root, project_id=None):
    """Record the resolved memory directory for the bash hooks to read."""
    target = Path(root) / PROJECT_DIR / STATE_DIR_POINTER
    resolved = memory_dir(root, project_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(str(resolved) + "\n", encoding="utf-8")
    tmp.replace(target)
    return {"path": str(Path(PROJECT_DIR) / STATE_DIR_POINTER), "kind": "pointer"}


def upgrade_available(root):
    """True when this project is on an older layout than the CLI implements."""
    return layout(root) < CURRENT_LAYOUT
