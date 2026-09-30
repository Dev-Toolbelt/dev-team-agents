"""Project identity and the committed ``project.json`` (ADR-0008).

The file holds identity and topology, never a preference:

    {"schema": 1, "project_id": "<uuid4>", "context_paths": ["docs"]}

It is committed so the identity survives a re-clone, a directory move and a
machine change — the three events that would otherwise orphan the project's
memory in ``data/projects/<project_id>/``.

Under layout 2 the project's state is split in two (ADR-0013): portable memory in
``data/projects/<project_id>/`` and machine-local state in
``data/machines/<machine-id>/projects/<project_id>/``. Together with this committed
file they are enough to rebuild a bind from scratch, which is what makes a store
restored on a second machine usable.
"""

from __future__ import annotations

import re
import subprocess
import uuid
from pathlib import Path

from . import jsonio
from .errors import EnvError, UsageError

PROJECT_DIR = ".dev-team-agents"
#: Where a v2 install lived before v2.1.0 moved it to the project root, with its
#: memory beside it at ``.claude/user-data/`` and its docs at ``.claude/docs/``.
#: Recognised by `bind` (its links are v2 artifacts), `hooks` (its settings entries
#: are ours) and `migrate` (which converts it); never written.
PRE_ROOT_DIR = ".claude/dev-team-agents"
PRE_ROOT_MEMORY_DIR = ".claude/user-data"
PRE_ROOT_DOCS_DIR = ".claude/docs"
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
#: The pointers the bash hooks and the agent context order read, each in one file
#: read instead of a subprocess per lookup. Two, because layout 2 has two
#: directories: `state-dir` names the machine-local one (`state.json`, the markers)
#: and `memory-dir` names the portable one (`session-summary.md`).
#:
#: `memory-dir` is not speculative: `skills/shared/project-context/SKILL.md` step 4 is
#: `<state-dir>/session-summary.md`, so every agent in the framework was reading a
#: pointer to find the episodic layer. Repointing `state-dir` at the machine subtree
#: without adding this one left them all looking in a directory that has no summary.
STATE_DIR_POINTER = "state-dir"
MEMORY_DIR_POINTER = "memory-dir"
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
    # Imported locally: `paths` is not otherwise a dependency of this module, and
    # `state_dir_for_layout` below already imports it the same way to sidestep a
    # cycle risk rather than take it on at module load time.
    from . import paths

    for item in paths_value:
        if not isinstance(item, str) or not item.strip():
            raise EnvError("{}: every context path must be a non-empty string".format(source))
        candidate = Path(item)
        # `candidate.is_absolute()` alone only answers for the platform this
        # process happens to run on: `WindowsPath("/etc").is_absolute()` is
        # False (no drive letter), which let a POSIX-absolute string through a
        # committed `project.json` read on Windows. `project.json` is committed
        # and can be authored on any platform, so both flavours are checked
        # regardless of which one is running this validation.
        if candidate.is_absolute() or paths.is_absolute_on_any_platform(item):
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


def _require_id(root, project_id):
    pid = project_id
    if pid is None:
        data = load(root)
        pid = data["project_id"] if data else None
    if not pid:
        raise EnvError("cannot resolve the memory directory without a project_id")
    return pid


def memory_dir(root, project_id=None):
    """Where this project's **portable** memory lives, per its recorded layout.

    Session summary, project preferences — what the user wrote. Under layout 1 this
    is the same directory as :func:`state_dir`, because v2 kept both together.
    """
    from . import paths

    if layout(root) >= LAYOUT_MEMORY_IN_STORE:
        return paths.project_data_dir(_require_id(root, project_id))
    return legacy_memory_dir(root)


def state_dir(root, project_id=None):
    """Where this project's **machine-local** state lives (ADR-0013).

    ``state.json`` and the dot-markers: the installed version, the session id, the
    last update check — facts about this machine, not about the project.
    """
    from . import paths

    if layout(root) >= LAYOUT_MEMORY_IN_STORE:
        return paths.machine_project_dir(_require_id(root, project_id))
    return legacy_memory_dir(root)


def memory_dir_for_layout(root, project_id, target_layout):
    """Where portable memory lives under a given layout — used to plan a move."""
    from . import paths

    if target_layout >= LAYOUT_MEMORY_IN_STORE:
        return paths.project_data_dir(project_id)
    return legacy_memory_dir(root)


def state_dir_for_layout(root, project_id, target_layout):
    """Where machine-local state lives under a given layout."""
    from . import paths

    if target_layout >= LAYOUT_MEMORY_IN_STORE:
        return paths.machine_project_dir(project_id)
    return legacy_memory_dir(root)


def _write_pointer(root, name, resolved):
    target = Path(root) / PROJECT_DIR / name
    target.parent.mkdir(parents=True, exist_ok=True)
    # `with_name`, not `with_suffix`: `state-dir` has no suffix, but `memory-dir`
    # would have had `-dir` replaced rather than `.tmp` appended.
    tmp = target.with_name(name + ".tmp")
    tmp.write_text(str(resolved) + "\n", encoding="utf-8")
    tmp.replace(target)
    # `.as_posix()` on the manifest key only: this record's "path" feeds the
    # exclude block and the manifest alongside every artifact bind.py mints, all
    # of which are forward-slash (see bind.py's `_vendored_tree`). `resolved`
    # itself stays a native, absolute path — it is written to a pointer file a
    # shell hook reads back on this same machine, not compared as a string.
    return {"path": (Path(PROJECT_DIR) / name).as_posix(), "kind": "pointer"}


def write_pointers(root, project_id=None):
    """Record both resolved directories, for the hooks and the agent context order.

    `state-dir` names :func:`state_dir` because `scripts/lib/state.sh` resolves
    `state.json` through it; `memory-dir` names :func:`memory_dir` because the
    canonical context-loading order reads the session summary through it.

    Returns one manifest record per pointer. Both are projections of state that lives
    elsewhere, so a stale one is a bug rather than a user edit to preserve — which is
    why **every** path that changes where either directory resolves must call this.
    Missing that call from the store relocation made `state_get` return an empty
    string for every key, silently.
    """
    return [
        _write_pointer(root, STATE_DIR_POINTER, state_dir(root, project_id)),
        _write_pointer(root, MEMORY_DIR_POINTER, memory_dir(root, project_id)),
    ]


def write_state_pointer(root, project_id=None):
    """Backwards-compatible single-record form. Writes both pointers."""
    return write_pointers(root, project_id)[0]


def upgrade_available(root):
    """True when this project is on an older layout than the CLI implements."""
    return layout(root) < CURRENT_LAYOUT
