"""Bind, sync and unbind a project against the versioned core (ADR-0007).

A bind is fully reconstructible: the only authoritative files in the project are
``project.json`` and ``user-data/``. Everything else — provider links or copies,
ignore blocks — is regenerated from the store by ``devteam sync``.

Every artifact this module creates is recorded in a per-project manifest, and it
only ever removes paths that manifest claims, or symlinks pointing into the
store. A path it does not recognise is a conflict, never something to overwrite.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from . import gitignore, jsonio, paths, project, providers, quarantine, registry, versions
from .errors import ConflictError, EnvError, UsageError

MODES = ("auto", "link", "copy", "vendored")
MANIFEST_SCHEMA = 1

#: Ignored in the project's own ``.gitignore``: paths every developer on the
#: project needs ignored. ``project.json`` is deliberately absent — it is
#: committed (ADR-0008).
PROJECT_GITIGNORE_ENTRIES = (
    ".dev-team-agents/user-data/",
    "!.dev-team-agents/user-data/graphify.json",
    ".dev-team-agents/resolved/",
    ".dev-team-agents/VERSION",
    ".dev-team-agents/.worktree-session",
    ".dev-team-agents/.learn-last-run",
    ".worktrees/",
)


def manifest_file(project_id):
    return paths.project_data_dir(project_id) / "bind-manifest.json"


def read_manifest(project_id):
    return jsonio.read_json(manifest_file(project_id), default=None) or {}


def _local_exclude_file(project_root):
    """``.git/info/exclude`` for this checkout, when it is a git repository."""
    git_dir = Path(project_root) / ".git"
    if git_dir.is_file():
        # A linked worktree: .git is a file pointing at the real git dir.
        try:
            content = git_dir.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if content.startswith("gitdir:"):
            resolved = Path(content.split(":", 1)[1].strip())
            if not resolved.is_absolute():
                resolved = (Path(project_root) / resolved).resolve()
            common = resolved / "commondir"
            if common.is_file():
                try:
                    rel = common.read_text(encoding="utf-8").strip()
                    resolved = (resolved / rel).resolve()
                except OSError:
                    pass
            return resolved / "info" / "exclude"
        return None
    if git_dir.is_dir():
        return git_dir / "info" / "exclude"
    return None


def symlink_supported(project_root):
    """Probe, rather than guess from the platform name.

    Windows with Developer Mode on supports symlinks; Windows without it does
    not, and neither does a filesystem mounted without the capability. Only an
    attempt answers the question.
    """
    probe_root = Path(project_root) / project.PROJECT_DIR
    try:
        probe_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=str(probe_root)) as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            link = Path(tmp) / "link"
            os.symlink(str(target), str(link), target_is_directory=True)
            return link.is_symlink()
    except (OSError, NotImplementedError, AttributeError):
        return False


def resolve_mode(requested, project_root):
    """``(mode, reason)`` — reason is set only when ``auto`` had to fall back."""
    if requested not in MODES:
        raise UsageError("unknown mode {!r} (expected one of: {})".format(requested, ", ".join(MODES)))
    if requested == "vendored":
        return "vendored", None
    if requested == "copy":
        return "copy", None
    if requested == "link":
        if not symlink_supported(project_root):
            raise EnvError(
                "this filesystem cannot create symlinks, so --mode=link is impossible",
                hint="Use --mode=copy, or enable Developer Mode on Windows and retry.",
            )
        return "link", None
    if symlink_supported(project_root):
        return "link", None
    return "copy", "symlinks are unavailable here"


def _is_managed_path(rel, path, previous_paths, project_root):
    """True when ``path`` is something dev-team-agents created and may replace.

    Three cases count as managed: a path this project's own manifest claims, a
    symlink into the versioned core (a v3 artifact), and a symlink into the
    project's own ``.dev-team-agents/`` (a **v2** artifact — the relative links
    `install.sh` created). The third is what lets a v2 install be taken over
    without asking the user to delete anything by hand.
    """
    path = Path(path)
    if rel and rel in previous_paths:
        return True
    if not path.is_symlink():
        return False
    try:
        target = Path(os.readlink(str(path)))
    except OSError:
        return False
    if not target.is_absolute():
        target = path.parent / target
    roots = [paths.core_dir(), Path(project_root) / project.PROJECT_DIR]
    return any(_is_inside(target, root) for root in roots)


def _is_inside(candidate, root):
    """Containment by path components, on both sides fully resolved.

    ``realpath`` on both is what makes this correct on macOS, where ``/var`` is a
    symlink to ``/private/var``: comparing a resolved root against an unresolved
    target would report a path as foreign and refuse to replace an artifact
    dev-team-agents itself created. ``relative_to`` rather than ``startswith``
    compares whole components, so a sibling named ``core-backup`` is not read as
    living inside ``core``.
    """
    try:
        resolved_candidate = Path(os.path.realpath(str(candidate)))
        resolved_root = Path(os.path.realpath(str(root)))
        resolved_candidate.relative_to(resolved_root)
        return True
    except (ValueError, OSError):
        return False


def _remove_artifact(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(str(path))


def _materialize(source, dest, mode, previous_paths, rel, project_root):
    """Create one artifact, returning ``link`` or ``copy``."""
    source = Path(source)
    dest = Path(dest)
    if not source.exists():
        raise EnvError("core is missing {}".format(source))

    if dest.exists() or dest.is_symlink():
        if not _is_managed_path(rel, dest, previous_paths, project_root):
            raise ConflictError(
                "{} already exists and was not created by dev-team-agents".format(dest),
                hint="Move or remove it, then run `devteam sync` again.",
                details={"path": str(dest)},
            )
        _remove_artifact(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == "link":
        os.symlink(str(source), str(dest), target_is_directory=source.is_dir())
        return "link"
    if source.is_dir():
        shutil.copytree(str(source), str(dest), symlinks=False)
    else:
        shutil.copy2(str(source), str(dest))
    return "copy"


def _vendored_tree(version_dir, project_root, previous_paths):
    """v2 layout: the framework inside the project, with relative links."""
    install_dir = Path(project_root) / project.PROJECT_DIR
    created = []
    for name in versions.CORE_TREES:
        source = Path(version_dir) / name
        if not source.is_dir():
            continue
        dest = install_dir / name
        rel = str(Path(project.PROJECT_DIR) / name)
        if dest.exists() or dest.is_symlink():
            if rel not in previous_paths and not dest.is_symlink():
                # A v2 install being re-vendored: replacing the framework tree
                # with the same trees from the store is the documented update.
                shutil.rmtree(str(dest))
            else:
                _remove_artifact(dest)
        shutil.copytree(str(source), str(dest), symlinks=False)
        created.append({"path": rel, "kind": "copy"})

    for rel_path, source in providers.claude_artifacts(install_dir):
        dest = Path(project_root) / rel_path
        rel = str(rel_path)
        if dest.exists() or dest.is_symlink():
            _remove_artifact(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        depth = len(rel_path.parts) - 1
        relative_target = Path(*([".."] * depth)) / source.relative_to(Path(project_root))
        os.symlink(str(relative_target), str(dest), target_is_directory=True)
        created.append({"path": rel, "kind": "relative-link"})
    return created


def bind(root=None, provider_names=None, mode="auto", pin=None, emitter=None):
    """Bind ``root`` to the store. Idempotent, and safe to re-run."""
    project_root = project.resolve_root(root)
    if not project_root.is_dir():
        raise UsageError("not a directory: {}".format(project_root))

    version = versions.resolve(pin)
    version_dir = versions.require(version)

    requested = list(provider_names) if provider_names else providers.detect(project_root)
    unknown = [p for p in requested if p not in providers.ALL_PROVIDERS]
    if unknown:
        raise UsageError(
            "unknown provider(s): {} (expected: {})".format(
                ", ".join(unknown), ", ".join(providers.ALL_PROVIDERS)
            )
        )
    selected = [p for p in providers.ALL_PROVIDERS if p in set(requested)]

    resolved_mode, fallback_reason = resolve_mode(mode, project_root)
    if fallback_reason and emitter:
        emitter.warn("mode=copy: {}".format(fallback_reason))

    data, created_identity = project.ensure(project_root)
    project_id = data["project_id"]

    previous = read_manifest(project_id)
    previous_paths = {item.get("path") for item in previous.get("artifacts", [])}

    artifacts = []
    if resolved_mode == "vendored":
        artifacts.extend(_vendored_tree(version_dir, project_root, previous_paths))
    elif "claude" in selected:
        for rel_path, source in providers.claude_artifacts(version_dir):
            rel = str(rel_path)
            kind = _materialize(
                source,
                Path(project_root) / rel_path,
                resolved_mode,
                previous_paths,
                rel,
                project_root,
            )
            artifacts.append({"path": rel, "kind": kind})

    delegated = []
    if resolved_mode != "vendored":
        if "opencode" in selected:
            providers.install_opencode(version_dir, project_root)
            delegated.extend(providers.DELEGATED_ARTIFACTS["opencode"])
        if "codex" in selected:
            providers.install_codex(version_dir, project_root)
            delegated.extend(providers.DELEGATED_ARTIFACTS["codex"])

    stale = _prune_stale(
        project_root, previous, {item["path"] for item in artifacts}, project_id
    )

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "project_id": project_id,
        "path": str(project_root),
        "version": version,
        "mode": resolved_mode,
        "providers": selected,
        "artifacts": artifacts,
        "delegated": delegated,
    }
    jsonio.write_json_atomic(manifest_file(project_id), manifest)

    registry.upsert(
        project_id,
        project_root,
        selected,
        resolved_mode,
        pin=pin,
        extra={"last_synced_version": version},
    )

    ignore_changed, ignore_action = gitignore.apply_managed_block(
        Path(project_root) / ".gitignore", list(PROJECT_GITIGNORE_ENTRIES)
    )

    exclude_action = "skipped"
    exclude_file = _local_exclude_file(project_root)
    if exclude_file is not None and resolved_mode != "vendored":
        entries = sorted({item["path"] for item in artifacts} | set(delegated))
        _, exclude_action = gitignore.apply_managed_block(exclude_file, entries)

    return {
        "project_id": project_id,
        "path": str(project_root),
        "version": version,
        "mode": resolved_mode,
        "providers": selected,
        "artifacts": len(artifacts),
        "delegated": delegated,
        "identity_created": created_identity,
        "pruned": stale,
        "gitignore": ignore_action if ignore_changed else "unchanged",
        "git_exclude": exclude_action,
        "fallback_reason": fallback_reason,
    }


def _prune_stale(project_root, previous, current_paths, project_id):
    """Retire artifacts a previous bind made that this one no longer needs.

    A symlink is unlinked: it holds no content and ``sync`` recreates it. A real
    directory or file is **moved to quarantine**, never deleted — a previous bind
    in ``vendored`` mode produced real trees, and deleting them here would
    destroy the only copy before a migration could set it aside.
    """
    unlinked = []
    quarantined = []
    for item in previous.get("artifacts", []):
        rel = item.get("path")
        if not rel or rel in current_paths:
            continue
        candidate = Path(project_root) / rel
        if not (candidate.exists() or candidate.is_symlink()):
            continue
        try:
            if candidate.is_symlink():
                candidate.unlink()
                unlinked.append(rel)
            else:
                destination = quarantine.move(candidate, project_id, group="pruned")
                if destination is not None:
                    quarantined.append({"path": rel, "to": str(destination)})
        except OSError:
            continue
    return {"unlinked": unlinked, "quarantined": quarantined}


def sync_project(project_id, emitter=None):
    entry = registry.get(project_id)
    if entry is None:
        raise EnvError("project {} is not bound".format(project_id))
    root = Path(entry["path"])
    if not root.is_dir():
        raise EnvError(
            "bound path no longer exists: {}".format(root),
            hint="Run `devteam doctor` from the project's new location to reconcile it.",
        )
    result = bind(
        root,
        provider_names=entry.get("providers"),
        mode=entry.get("mode", "auto"),
        pin=entry.get("pin"),
        emitter=emitter,
    )
    registry.touch_sync(project_id, result["version"])
    return result


def sync_all(emitter=None):
    results = []
    problems = []
    for project_id in sorted(registry.entries()):
        try:
            results.append(sync_project(project_id, emitter=emitter))
        except (EnvError, ConflictError) as exc:
            problems.append({"project_id": project_id, "error": exc.message})
            if emitter:
                emitter.warn("{}: {}".format(project_id, exc.message))
    return {"synced": results, "problems": problems}


def unbind(root=None, project_id=None, keep_artifacts=False):
    """Remove bind artifacts and the registry entry.

    ``project.json`` and everything under ``user-data/`` stay: identity and
    memory are never collateral damage of an unbind.
    """
    if project_id is None:
        project_root = project.resolve_root(root)
        data = project.load(project_root)
        if data is None:
            raise UsageError("{} is not a bound project".format(project_root))
        project_id = data["project_id"]
    else:
        entry = registry.get(project_id)
        if entry is None:
            raise EnvError("project {} is not bound".format(project_id))
        project_root = Path(entry["path"])

    manifest = read_manifest(project_id)
    removed = []
    if not keep_artifacts:
        for item in manifest.get("artifacts", []):
            candidate = Path(project_root) / item.get("path", "")
            if candidate.exists() or candidate.is_symlink():
                try:
                    _remove_artifact(candidate)
                    removed.append(item["path"])
                except OSError:
                    continue
        exclude_file = _local_exclude_file(project_root)
        if exclude_file is not None:
            gitignore.apply_managed_block(exclude_file, [])

    registry.remove(project_id)
    return {
        "project_id": project_id,
        "path": str(project_root),
        "removed": removed,
        "kept": ["project.json", "user-data/"],
    }
