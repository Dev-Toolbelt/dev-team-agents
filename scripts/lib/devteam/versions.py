"""The versioned core: install, select, pin and garbage-collect (ADR-0007)."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import paths
from .errors import ConflictError, EnvError, UsageError
from .lock import store_lock

#: Trees copied into ``core/versions/<v>/``. Everything an agent, command or
#: script needs at runtime, and nothing that only matters in the repository.
#:
#: ``opencode`` carries the provider plugin that ``install-opencode.sh:88`` hard
#: requires — without it ``devteam bind --provider opencode`` could never succeed,
#: and `providers.detect` selects that provider automatically for any project with
#: an `.opencode/` directory. ``CLAUDE-md`` holds the companion sections that the
#: copied ``CLAUDE.md`` links to; without it every one of those links dangles.
CORE_TREES = ("agents", "commands", "skills", "scripts", "templates")
#: Required for a tree to be a valid source; ``OPTIONAL_TREES`` are copied when present.
OPTIONAL_TREES = ("opencode", "CLAUDE-md", "plugins")

_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")
_CHANGELOG_RE = re.compile(r"^##\s*\[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def parse_semver(version):
    match = _SEMVER_RE.match(version or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def sort_key(version):
    parsed = parse_semver(version)
    return parsed if parsed else (-1, -1, -1)


def installed():
    """Versions present in the core, newest last."""
    root = paths.versions_dir()
    if not root.is_dir():
        return []
    # Only semver directories are versions. A `<v>.incoming` staging directory
    # left by a killed install would otherwise be listed as installed, and
    # `set_current` would happily activate it.
    # `is_version_name` as well: a stray `1.2.3-` passes the looser semver test but would
    # be refused by `paths.version_dir`, and doctor iterates this list.
    found = [
        p.name
        for p in root.iterdir()
        if p.is_dir() and parse_semver(p.name) and paths.is_version_name(p.name)
    ]
    return sorted(found, key=sort_key)


def current():
    """The version named by ``core/current``, or ``None``."""
    marker = paths.current_file()
    if not marker.is_file():
        return None
    try:
        value = marker.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise EnvError("cannot read {}: {}".format(marker, exc)) from exc
    return value or None


def set_current(version):
    if version not in installed():
        raise EnvError(
            "version {} is not installed in the core".format(version),
            hint="Run `devteam store list` to see what is available.",
        )
    # A hand-made or half-copied directory used to be accepted here, after which
    # every bind failed with "core is missing .../agents". The install path
    # already validates a tree; activation has to apply the same test.
    missing = [name for name in CORE_TREES if not (version_dir(version) / name).is_dir()]
    if missing:
        raise EnvError(
            "version {} is incomplete (missing: {})".format(version, ", ".join(missing)),
            hint="Re-install it with `devteam store install --from <tree> --force`.",
        )
    marker = paths.current_file()
    marker.parent.mkdir(parents=True, exist_ok=True)
    tmp = marker.with_suffix(".tmp")
    tmp.write_text(version + "\n", encoding="utf-8")
    tmp.replace(marker)
    return version


def version_dir(version):
    return paths.version_dir(version)


def require(version):
    """The directory for ``version``, or an environment error."""
    target = version_dir(version)
    if not target.is_dir():
        raise EnvError(
            "version {} is not installed (looked in {})".format(version, target),
            hint="Run `devteam update` or `devteam store install --from <tree>`.",
        )
    return target


def resolve(pin=None):
    """A pin wins over ``current``; without either, the store is unusable."""
    if pin:
        require(pin)
        return pin
    active = current()
    if not active:
        raise EnvError(
            "no active version: {} is missing".format(paths.current_file()),
            hint="Run `devteam store install --from <tree>` or `devteam update`.",
        )
    require(active)
    return active


def version_from_tree(src):
    """Read the newest version from a source tree's ``CHANGELOG.md``."""
    changelog = Path(src) / "CHANGELOG.md"
    if not changelog.is_file():
        return None
    try:
        text = changelog.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _CHANGELOG_RE.search(text)
    return match.group(1) if match else None


def install_from_tree(src, version=None, force=False, make_current=None):
    """Copy a canonical source tree into ``core/versions/<version>``.

    Used by the installer, by ``devteam update`` after a download, and by the
    test suite. A version already installed is left alone unless ``force``.
    """
    source = Path(src).resolve()
    if not source.is_dir():
        raise UsageError("source tree does not exist: {}".format(source))
    missing = [name for name in CORE_TREES if not (source / name).is_dir()]
    if missing:
        raise UsageError(
            "{} does not look like a dev-team-agents tree (missing: {})".format(
                source, ", ".join(missing)
            )
        )

    resolved_version = version or version_from_tree(source)
    if not resolved_version:
        raise UsageError(
            "cannot determine the version to install",
            hint="Pass --version X.Y.Z, or point --from at a tree with a CHANGELOG.md.",
        )
    if parse_semver(resolved_version) is None or not paths.is_version_name(resolved_version):
        raise UsageError("version must be X.Y.Z, got: {}".format(resolved_version))

    with store_lock("core"):
        target = version_dir(resolved_version)
        if target.exists() and not force:
            raise ConflictError(
                "version {} is already installed".format(resolved_version),
                hint="Pass --force to replace it.",
                details={"version": resolved_version, "path": str(target)},
            )

        # Staging is built BEFORE the old tree is touched. Removing it up front
        # meant a failed copy left `current` pointing at a version that no longer
        # existed on disk.
        staging = target.with_name(target.name + ".incoming")
        if staging.exists():
            shutil.rmtree(str(staging))
        staging.mkdir(parents=True)
        try:
            for name in CORE_TREES:
                # symlinks=False: a symlink inside a downloaded archive would be
                # preserved into the store, and `providers` executes scripts from
                # there. Copy content, never links.
                shutil.copytree(str(source / name), str(staging / name), symlinks=False)
            for name in OPTIONAL_TREES:
                if (source / name).is_dir():
                    shutil.copytree(str(source / name), str(staging / name), symlinks=False)
            for name in ("CHANGELOG.md", "CLAUDE.md"):
                candidate = source / name
                if candidate.is_file():
                    shutil.copy2(str(candidate), str(staging / name))
            (staging / "VERSION").write_text(resolved_version + "\n", encoding="utf-8")
            # Only now is the tree complete: promote it in one move so a killed
            # copy never leaves a half-populated version for bind to resolve.
            if target.exists():
                shutil.rmtree(str(target))
            staging.replace(target)
        except Exception:
            if staging.exists():
                shutil.rmtree(str(staging), ignore_errors=True)
            raise

    if make_current or (make_current is None and current() is None):
        set_current(resolved_version)
    return resolved_version


def pinned_versions():
    """Every version some project pins, so GC cannot remove it."""
    from . import registry

    return {
        entry.get("pin")
        for entry in registry.entries().values()
        if entry.get("pin")
    }


def gc(dry_run=True):
    """Remove versions that are neither ``current`` nor pinned by any project.

    The keep-set is computed **inside** the locks that protect the state it reads.
    Computing it outside let a `devteam pin` land between the read and the
    `rmtree`, deleting the version a project had just pinned itself to — after
    which every `sync` for that project failed.

    Lock order is registry-then-core everywhere, which is what keeps this from
    deadlocking against a bind.
    """
    with store_lock("registry"):
        with store_lock("core"):
            keep = set(pinned_versions())
            active = current()
            if active:
                keep.add(active)
            removable = [v for v in installed() if v not in keep]
            if dry_run:
                return {"removed": [], "would_remove": removable, "kept": sorted(keep)}
            removed = []
            for version in removable:
                shutil.rmtree(str(version_dir(version)), ignore_errors=True)
                removed.append(version)
    return {"removed": removed, "would_remove": [], "kept": sorted(keep)}
