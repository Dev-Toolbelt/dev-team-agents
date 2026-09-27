"""``data/registry.json`` — the list of bound projects.

Keyed by ``project_id``, so a project that moves keeps its entry and its memory.
Every mutation runs under the store lock, because two sessions in two projects
can bind or sync at the same time.
"""

from __future__ import annotations

import time
from pathlib import Path

from . import jsonio, paths
from .errors import ConflictError, EnvError
from .lock import store_lock

SCHEMA = 1
VALID_MODES = ("link", "copy", "vendored")


def _empty():
    return {"schema": SCHEMA, "projects": {}}


def load():
    data = jsonio.read_json(paths.registry_file(), default=None)
    if data is None:
        return _empty()
    if not isinstance(data, dict) or not isinstance(data.get("projects"), dict):
        raise EnvError(
            "{} is not a valid registry".format(paths.registry_file()),
            hint="Fix or move the file by hand; dev-team-agents will not overwrite it.",
        )
    schema = data.get("schema")
    if isinstance(schema, int) and schema > SCHEMA:
        raise EnvError(
            "registry schema {} is newer than this CLI understands (max {})".format(
                schema, SCHEMA
            ),
            hint="Update dev-team-agents.",
        )
    return data


def save(data):
    jsonio.write_json_atomic(paths.registry_file(), data)
    return data


def entries():
    """``{project_id: entry}`` for every bound project."""
    return dict(load().get("projects", {}))


def get(project_id):
    return entries().get(project_id)


def find_by_path(path):
    """``(project_id, entry)`` for a bound path, or ``(None, None)``."""
    target = str(Path(path).resolve())
    for pid, entry in entries().items():
        if entry.get("path") == target:
            return pid, entry
    return None, None


def upsert(project_id, path, providers, mode, pin=None, extra=None):
    """Create or update an entry, refusing a second path for the same identity.

    The refusal is the fork guard: two checkouts of the same repository carry the
    same committed ``project_id``, and silently re-pointing the entry would make
    them share one memory directory.
    """
    if mode not in VALID_MODES:
        raise EnvError("unknown bind mode: {}".format(mode))
    resolved = str(Path(path).resolve())
    with store_lock("registry"):
        data = load()
        projects = data.setdefault("projects", {})
        existing = projects.get(project_id)
        if existing and existing.get("path") != resolved:
            other = Path(existing["path"])
            if other.exists():
                raise ConflictError(
                    "project_id {} is already bound to {}".format(project_id, other),
                    hint=(
                        "Two checkouts share one identity. Run `devteam doctor "
                        "--reassign-identity` in the copy that should get a new one."
                    ),
                    details={"project_id": project_id, "bound_path": str(other), "new_path": resolved},
                )
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry = dict(existing or {})
        entry.update(
            {
                "path": resolved,
                "providers": sorted(set(providers)),
                "mode": mode,
                "pin": pin,
                "last_sync": now,
            }
        )
        entry.setdefault("bound_at", now)
        if extra:
            entry.update(extra)
        projects[project_id] = entry
        data["schema"] = SCHEMA
        save(data)
        return entry


def set_pin(project_id, version):
    """Pin (or, with ``None``, release) a project's version."""
    with store_lock("registry"):
        data = load()
        entry = data.get("projects", {}).get(project_id)
        if entry is None:
            raise EnvError("project {} is not bound".format(project_id))
        entry["pin"] = version
        save(data)
        return entry


def touch_sync(project_id, version):
    with store_lock("registry"):
        data = load()
        entry = data.get("projects", {}).get(project_id)
        if entry is None:
            raise EnvError("project {} is not bound".format(project_id))
        entry["last_sync"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry["last_synced_version"] = version
        save(data)
        return entry


def relocate(project_id, new_path):
    """Point an existing identity at a new directory (``doctor`` reconciliation)."""
    with store_lock("registry"):
        data = load()
        entry = data.get("projects", {}).get(project_id)
        if entry is None:
            raise EnvError("project {} is not bound".format(project_id))
        previous = entry.get("path")
        entry["path"] = str(Path(new_path).resolve())
        save(data)
        return previous, entry["path"]


def remove(project_id):
    with store_lock("registry"):
        data = load()
        removed = data.get("projects", {}).pop(project_id, None)
        save(data)
        return removed
