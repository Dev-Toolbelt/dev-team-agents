"""Portability of the data store: export, import, and a purging uninstall.

``data/`` is what the user would be upset to lose, and ADR-0007 states plainly
that its registry and manifests hold absolute paths — so moving a machine is an
export/import, not a file copy that happens to work.
"""

from __future__ import annotations

import shutil
import tarfile
import time
from pathlib import Path

from . import jsonio, paths
from .errors import ConflictError, EnvError, UsageError

ARCHIVE_PREFIX = "devteam-data"
MANIFEST_NAME = "export-manifest.json"


def export(destination=None):
    """Archive the whole data store, including quarantine, into one tarball."""
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

    manifest = {
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "platform": paths.platform_key(),
        "data_dir": str(data),
        "note": (
            "registry.json and bind-manifest.json hold absolute paths from the exporting "
            "machine. After importing, run `devteam doctor` in each project and "
            "`devteam sync --all` to rebuild artifacts."
        ),
    }
    manifest_path = data / MANIFEST_NAME
    jsonio.write_json_atomic(manifest_path, manifest)

    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(target), "w:gz") as tar:
        tar.add(str(data), arcname="data")

    files = sum(1 for _ in data.rglob("*") if _.is_file())
    return {
        "archive": str(target),
        "bytes": target.stat().st_size,
        "files": files,
        "data_dir": str(data),
    }


def import_archive(archive, force=False):
    """Restore an exported store. Refuses to overwrite a populated one."""
    source = Path(archive)
    if not source.is_file():
        raise UsageError("no such archive: {}".format(source))
    data = paths.data_dir()
    if data.is_dir() and any(data.iterdir()) and not force:
        raise ConflictError(
            "the data store at {} is not empty".format(data),
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

    replaced = None
    if data.is_dir():
        replaced = data.with_name("data.replaced-{}".format(int(time.time())))
        data.replace(replaced)
    extracted.replace(data)
    shutil.rmtree(str(staging), ignore_errors=True)

    return {
        "archive": str(source),
        "data_dir": str(data),
        "previous_kept_at": str(replaced) if replaced else None,
        "next": "run `devteam doctor` per project, then `devteam sync --all`",
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
