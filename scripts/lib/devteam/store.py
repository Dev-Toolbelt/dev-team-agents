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

from . import jsonio, paths, project, quarantine, registry, update
from .lock import store_lock
from .errors import ConflictError, EnvError, UsageError

ARCHIVE_PREFIX = "devteam-data"
MANIFEST_NAME = "export-manifest.json"

#: Never archived, under either mode: a lock file names the pid that holds it, so
#: restoring one can only ever block a process that does not exist. Matched against
#: **every** path component, not just the first — locks live at
#: ``machines/<id>/locks/`` now, whose first component is ``machines``, so a
#: first-component test silently let a held lock into an ``--all`` archive.
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
    if destination:
        target = Path(destination)
    else:
        # Not `Path.cwd()`: that is the bound repository, where the archive is one
        # `git add -A` away from being committed. The path is printed either way.
        target = paths.cache_dir() / "exports" / "{}-{}.tar.gz".format(ARCHIVE_PREFIX, stamp)
    if target.is_dir():
        target = target / "{}-{}.tar.gz".format(ARCHIVE_PREFIX, stamp)
    if target.exists():
        raise ConflictError("{} already exists".format(target))

    skipped = set(NEVER_EXPORTED)
    if not include_machine:
        skipped.update(paths.MACHINE_LOCAL_STORE_ENTRIES)
        skipped.update(paths.LOCAL_ONLY_STORE_ENTRIES)

    manifest = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": paths.platform_key(),
        # Deliberately not the absolute data dir: it disclosed the OS username and
        # home layout to whoever received the archive.
        "portable_only": not include_machine,
        "machine_id": paths.machine_id() if include_machine else None,
        "excluded": sorted(skipped),
        "note": (
            "This archive carries the portable records only: preferences and per-project "
            "memory. It deliberately excludes this machine's registry and bind manifests, "
            "its locks, and the quarantine tree — quarantine holds retired machine-local "
            "records, including a pre-upgrade credentials file, so a portable archive must "
            "not carry it. On the receiving machine, run `devteam bind` in each project — "
            "its committed project.json reconnects it to its memory, and the registry and "
            "manifests are rebuilt locally."
            if not include_machine
            else "This archive is a complete backup of this machine: the registry and bind "
            "manifests (absolute paths), and the quarantine tree, which can hold a retired "
            "pre-upgrade memory directory including a plaintext credentials file. Treat the "
            "file as sensitive. Restore it only on a machine where those paths are valid; "
            "otherwise export without --all."
        ),
    }
    manifest_path = data / MANIFEST_NAME
    jsonio.write_json_atomic(manifest_path, manifest)

    def _excluded(relative):
        """The one predicate the filter and the count both use.

        They were two expressions before, and a review found the count could drift
        from what the archive holds without a test noticing.
        """
        parts = Path(relative).parts
        if not parts:
            return False
        if any(part in skipped for part in parts):
            return True
        if include_machine:
            # `--all` exists to carry this machine's records, so the basename rule below
            # must not strip the very files it is for. The component list above still
            # drops locks.
            return False
        # By basename at every depth, not by first component: `quarantine/` holds
        # whole retired memory directories, and a plaintext `credentials.local.json`
        # inside one was shipped by a **default** export until this check existed.
        return paths.path_is_machine_local(relative)

    def _select(info):
        # Drop the "data" arcname prefix to get the store-relative path.
        if _excluded(Path(*Path(info.name).parts[1:])):
            return None
        return info

    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(target), "w:gz") as tar:
        tar.add(str(data), arcname="data", filter=_select)
    try:
        # An archive of the data store may hold credential references and, from a
        # quarantined pre-upgrade memory directory, whatever the user had in it.
        os.chmod(str(target), 0o600)
    except OSError:
        pass

    files = sum(
        1
        for item in data.rglob("*")
        if item.is_file() and not _excluded(item.relative_to(data))
    )
    return {
        "archive": str(target),
        "bytes": target.stat().st_size,
        "files": files,
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


def _withhold_consent_keys(preferences_path):
    """Strip the consent keys from an incoming preferences layer.

    `telemetry` and `auto_update` are CONSENT_KEYS precisely because consent belongs
    to one installation, and the existing backfill only adds keys that are *missing* —
    so an imported file already saying `true` would have enabled telemetry on a
    machine whose owner was never asked. Removing them makes the cascade resolve both
    to `consent-withheld`, which is what "never asked" is supposed to look like.
    """
    from .prefs import CONSENT_KEYS

    data = jsonio.read_json(preferences_path, default=None)
    if not isinstance(data, dict):
        return []
    removed = sorted(key for key in CONSENT_KEYS if key in data)
    if not removed:
        return []
    for key in removed:
        data.pop(key, None)
    jsonio.write_json_atomic(preferences_path, data)
    return removed


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
        # `update.safe_members` is the floor, not `filter="data"`: the keyword does
        # not exist on the declared python floor (3.9), where `extractall`'s default
        # is `fully_trusted` — so on the interpreter this CLI is required to support,
        # the `except TypeError` fallback used to extract an archive unchecked. This
        # copy of the loop also never inspected `linkname`, which made a symlink or
        # hardlink member an arbitrary write and a read-any-file primitive.
        members = list(update.safe_members(tar))
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
    if incoming_machine.is_symlink() or (
        incoming_machine.exists() and not incoming_machine.is_dir()
    ):
        # `is_symlink()` first, and not only `exists()`: `Path.exists()` follows the
        # link and returns False for a **dangling** one, which is precisely the case this
        # guard was written for — the archive was then treated as portable, the live
        # identity was carried into it, the move failed, and the real registry was left
        # stranded. `devteam export` never produces a symlink here, so any is refused.
        shutil.rmtree(str(staging), ignore_errors=True)
        raise EnvError(
            "archive member data/{} is not a directory".format(paths.MACHINES_DIR),
            hint="The archive was not produced by `devteam export`; inspect it by hand.",
        )
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
        # `machines/` first and `machine-id` last: if the second move fails, the
        # identity is still where the records are, not orphaned from them. Anything
        # already carried goes back before the exception leaves this function.
        for name in (paths.MACHINES_DIR, paths.MACHINE_ID_FILE):
            local = data / name
            if not local.exists():
                continue
            try:
                shutil.move(str(local), str(extracted / name))
            except (OSError, shutil.Error) as exc:
                for done in carried:
                    try:
                        shutil.move(str(extracted / done), str(data / done))
                    except (OSError, shutil.Error):
                        pass
                shutil.rmtree(str(staging), ignore_errors=True)
                raise EnvError(
                    "cannot carry this machine's records across the import: {}".format(exc),
                    hint="Nothing was replaced. Inspect the archive and the data store.",
                ) from exc
            carried.append(name)

    withheld = _withhold_consent_keys(extracted / "preferences.json")

    replaced = None
    if data.is_dir():
        replaced = data.with_name("data.replaced-{}".format(int(time.time())))
        data.replace(replaced)
    extracted.replace(data)
    shutil.rmtree(str(staging), ignore_errors=True)
    # The store was replaced wholesale, so a resolved id from before it is stale.
    paths.reset_machine_id_cache()

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
        "consent_withheld": withheld,
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

    It then **rewrites each bound project's pointers**. Moving ``state.json`` out from
    under ``.dev-team-agents/state-dir`` without repointing it made ``state_get``
    return an empty string for every key — installed version, session id, health-check
    marker — with no error anywhere. A pointer is a regenerated projection that every
    ``bind`` and ``sync`` already rewrites, so refreshing it is not a memory move: the
    claim this relocation touches nothing inside a project was wrong, and the honest
    statement is that it moves no *content* there.
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

    return {
        "moved": moved,
        "quarantined": quarantined,
        "repointed": _repoint_bound_projects(),
        "machine_id": paths.machine_id(),
    }


def _repoint_bound_projects():
    """Refresh the pointers of every bound project whose state just moved.

    Reads the registry that was itself only just promoted, so it runs last. A project
    whose directory is gone, or whose ``project.json`` is unreadable, is skipped rather
    than failing the relocation — the records are already in place, and `devteam
    doctor` reports a stale pointer for anything missed here.
    """
    refreshed = []
    try:
        entries = registry.entries()
    except EnvError:
        return refreshed
    for project_id, entry in sorted(entries.items()):
        root = Path(entry.get("path", ""))
        if not root.is_dir():
            continue
        try:
            if project.layout(root) < project.LAYOUT_MEMORY_IN_STORE:
                continue
            project.write_pointers(root, project_id)
        except (EnvError, OSError):
            continue
        refreshed.append(str(root))
    return refreshed
