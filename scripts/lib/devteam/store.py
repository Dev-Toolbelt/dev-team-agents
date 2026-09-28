"""Portability of the data store: export, import, and a purging uninstall.

``data/`` is what the user would be upset to lose. It is split by what a record
*says* (ADR-0013): the portable subtree holds what the user authored, and
``data/machines/<machine-id>/`` holds what this machine observed — the registry and
the bind manifests, which are absolute paths and nothing else.

So an export is portable **by default**: the receiving machine rebuilds its own
registry and manifests from each project's committed ``project.json``, instead of
inheriting paths that do not exist there. ``--all`` keeps the machine subtree for
the case that is genuinely a backup of this machine rather than a move to another.
"""

from __future__ import annotations

import os
import shutil
import tarfile
import time
from pathlib import Path

from . import jsonio, paths, quarantine
from .lock import store_lock
from .errors import ConflictError, EnvError, UsageError

ARCHIVE_PREFIX = "devteam-data"
MANIFEST_NAME = "export-manifest.json"

#: Never archived, under either mode: a lock file names the pid that holds it, so
#: restoring one can only ever block a process that does not exist.
NEVER_EXPORTED = ("locks",)


def export(destination=None, include_machine=False):
    """Archive the data store into one tarball.

    Portable by default: ``machine-id`` and ``data/machines/`` stay behind, because
    they describe the exporting machine and are rebuilt by a ``devteam bind`` on the
    receiving one. Pass ``include_machine`` to take them along.
    """
    data = paths.data_dir()
    if not data.is_dir():
        raise EnvError(
            "there is no data store at {}".format(data),
            hint="Nothing to export yet — bind a project first.",
        )
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = Path(destination) if destination else Path.cwd() / "{}-{}.tar.gz".format(
        ARCHIVE_PREFIX, stamp
    )
    if target.is_dir():
        target = target / "{}-{}.tar.gz".format(ARCHIVE_PREFIX, stamp)
    if target.exists():
        raise ConflictError("{} already exists".format(target))

    skipped = set(NEVER_EXPORTED)
    if not include_machine:
        skipped.update(paths.MACHINE_LOCAL_STORE_ENTRIES)

    manifest = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": paths.platform_key(),
        "data_dir": str(data),
        "portable_only": not include_machine,
        "machine_id": paths.machine_id() if include_machine else None,
        "excluded": sorted(skipped),
        "note": (
            "This archive carries the portable records only: preferences, per-project "
            "memory and quarantine. On the receiving machine, run `devteam bind` in each "
            "project — its committed project.json reconnects it to its memory, and the "
            "registry and manifests are rebuilt locally."
            if not include_machine
            else "This archive includes this machine's registry and bind manifests, which "
            "hold absolute paths. Restore it only on a machine where those paths are "
            "valid; otherwise export without --all."
        ),
    }
    manifest_path = data / MANIFEST_NAME
    jsonio.write_json_atomic(manifest_path, manifest)

    def _select(info):
        parts = Path(info.name).parts[1:]  # drop the "data" arcname prefix
        if parts and parts[0] in skipped:
            return None
        return info

    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(target), "w:gz") as tar:
        tar.add(str(data), arcname="data", filter=_select)

    files = sum(
        1
        for item in data.rglob("*")
        if item.is_file() and item.relative_to(data).parts[0] not in skipped
    )
    return {
        "archive": str(target),
        "bytes": target.stat().st_size,
        "files": files,
        "data_dir": str(data),
        "portable_only": not include_machine,
        "excluded": sorted(skipped),
    }


def portable_entries():
    """Top-level entries of ``data/`` that hold user records.

    "Is the store populated?" must not be answered by ``any(data.iterdir())``: a
    machine that has only run `devteam store install` already has `machine-id` and
    `machines/` in there, and counting those made `devteam import` refuse on exactly
    the fresh machine the documented restore flow targets.
    """
    data = paths.data_dir()
    if not data.is_dir():
        return []
    return [
        entry.name
        for entry in data.iterdir()
        if entry.name not in paths.MACHINE_LOCAL_STORE_ENTRIES and entry.name != MANIFEST_NAME
    ]


def registry_file_has_entries():
    """True when this machine's registry lists at least one project."""
    data = jsonio.read_json(paths.registry_file(), default=None)
    if not isinstance(data, dict):
        return False
    return bool(data.get("projects"))


def import_archive(archive, force=False):
    """Restore an exported store. Refuses to overwrite one that holds user records."""
    source = Path(archive)
    if not source.is_file():
        raise UsageError("no such archive: {}".format(source))
    data = paths.data_dir()
    occupied = portable_entries()
    if occupied and not force:
        raise ConflictError(
            "the data store at {} already holds records: {}".format(
                data, ", ".join(sorted(occupied))
            ),
            hint="Export it first, then pass --force to replace it.",
        )

    staging = data.parent / "data.incoming"
    if staging.exists():
        shutil.rmtree(str(staging))
    jsonio.ensure_dir(staging)
    with tarfile.open(str(source), "r:gz") as tar:
        members = []
        for member in tar.getmembers():
            name = Path(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise EnvError("refusing unsafe archive member: {}".format(member.name))
            if member.isdev() or member.isfifo():
                raise EnvError("refusing device/fifo member: {}".format(member.name))
            members.append(member)
        try:
            tar.extractall(str(staging), members=members, filter="data")
        except TypeError:
            tar.extractall(str(staging), members=members)

    extracted = staging / "data"
    if not extracted.is_dir():
        shutil.rmtree(str(staging), ignore_errors=True)
        raise EnvError("archive does not contain a data/ directory")

    # A portable archive carries no machine subtree. Promoting it as-is would take
    # this machine's registry out of the active store — not deleted, but every bound
    # project would silently look unbound — so the local machine records are carried
    # across into the incoming tree before it is promoted.
    incoming_machine = extracted / paths.MACHINES_DIR
    portable_only = not incoming_machine.exists()
    carried = []
    had_binds = registry_file_has_entries()
    if not portable_only and not force and had_binds:
        # An --all archive brings its own registry. Promoting it would put this
        # machine's live bind state aside — recoverable, but every bound project
        # would stop resolving until it was restored by hand.
        shutil.rmtree(str(staging), ignore_errors=True)
        raise ConflictError(
            "{} already has bound projects and the archive carries its own registry".format(
                paths.machine_dir()
            ),
            hint="Export this machine first, then pass --force. Or import without --all.",
        )
    if portable_only:
        for name in (paths.MACHINE_ID_FILE, paths.MACHINES_DIR):
            local = data / name
            if local.exists():
                shutil.move(str(local), str(extracted / name))
                carried.append(name)

    replaced = None
    if data.is_dir():
        replaced = data.with_name("data.replaced-{}".format(int(time.time())))
        data.replace(replaced)
    extracted.replace(data)
    shutil.rmtree(str(staging), ignore_errors=True)

    if portable_only:
        # What decides the next step is whether THIS machine already knows the
        # projects, not whether its records were carried across: a freshly installed
        # machine carries a machine-id and an empty registry, and still needs a bind.
        next_step = (
            "run `devteam doctor` per project, then `devteam sync --all`"
            if had_binds
            else "run `devteam bind` in each project — its committed project.json "
            "reconnects it to the memory that just arrived"
        )
    else:
        next_step = (
            "the archive carried another machine's absolute paths: run `devteam doctor` "
            "per project, then `devteam sync --all`"
        )

    return {
        "archive": str(source),
        "data_dir": str(data),
        "previous_kept_at": str(replaced) if replaced else None,
        "portable_only": portable_only,
        "machine_records_kept": carried,
        "next": next_step,
    }


def uninstall(purge=False):
    """Remove the core. The data store goes only with an explicit ``--purge``."""
    core = paths.core_dir()
    cache = paths.cache_dir()
    removed = []
    for path in (core, cache):
        if path.is_dir():
            shutil.rmtree(str(path))
            removed.append(str(path))

    data = paths.data_dir()
    if purge and data.is_dir():
        shutil.rmtree(str(data))
        removed.append(str(data))

    return {
        "removed": removed,
        "data_kept": None if purge else (str(data) if data.is_dir() else None),
        "purged": bool(purge),
    }


# ── one-time relocation into the machine subtree ──────────────────────────────


def machine_layout_pending():
    """True when the store still keeps machine-local records at the portable paths.

    Cheap enough to call on every invocation: one ``is_file`` on the legacy registry,
    and a directory scan only for a store that has per-project records at all.
    """
    data = paths.data_dir()
    if not data.is_dir():
        return False
    if (data / "registry.json").is_file():
        return True
    projects = paths.projects_dir()
    if not projects.is_dir():
        return False
    for project_dir in projects.iterdir():
        if not project_dir.is_dir():
            continue
        for item in project_dir.iterdir():
            if item.is_file() and paths.is_machine_local_record(item.name):
                return True
    return False


def adopt_machine_layout():
    """Move machine-local records under ``data/machines/<machine-id>/`` (ADR-0013).

    Idempotent, and a no-op for a store that was already written in the split shape.
    Each file is promoted with ``os.replace``, which is atomic within a filesystem —
    the record is either at the old path or the new one, never neither. A legacy file
    whose destination is already occupied goes to quarantine instead of overwriting
    it, because only one of the two can be current and this function cannot tell which.

    ``data/locks`` is deliberately left where it is rather than moved: a lock file may
    be held right now by a running process that will look for it at the old path.
    Locks are regenerated, so the stale directory costs nothing.
    """
    if not machine_layout_pending():
        return {"moved": [], "quarantined": [], "machine_id": None}

    data = paths.data_dir()
    machine = paths.machine_dir()
    moved = []
    quarantined = []

    def _promote(origin, target, label):
        jsonio.ensure_dir(target.parent)
        if target.exists():
            destination = quarantine.move(origin, None, group="pre-machine-split")
            if destination is not None:
                quarantined.append({"path": label, "to": str(destination)})
            return
        try:
            os.replace(str(origin), str(target))
        except FileNotFoundError:
            # A concurrent invocation promoted this record between the scan and here.
            # Its work is ours; there is nothing left to do for this file.
            return
        moved.append(label)

    with store_lock("registry"):
        # Re-checked under the lock: two invocations can both pass the scan above.
        if not machine_layout_pending():
            return {"moved": [], "quarantined": [], "machine_id": paths.machine_id()}

        legacy_registry = data / "registry.json"
        if legacy_registry.is_file():
            _promote(legacy_registry, machine / "registry.json", "registry.json")

        projects = paths.projects_dir()
        if projects.is_dir():
            for project_dir in sorted(projects.iterdir()):
                if not project_dir.is_dir():
                    continue
                project_id = project_dir.name
                for item in sorted(project_dir.iterdir()):
                    if not item.is_file() or not paths.is_machine_local_record(item.name):
                        continue
                    _promote(
                        item,
                        paths.machine_project_dir(project_id) / item.name,
                        "projects/{}/{}".format(project_id, item.name),
                    )

    return {"moved": moved, "quarantined": quarantined, "machine_id": paths.machine_id()}
