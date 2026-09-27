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
import subprocess
import tempfile
from pathlib import Path

from . import gitignore, hooks, jsonio, paths, prefs, project, providers, quarantine, registry, versions
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


def _resolved_location(path):
    """Where ``path`` lives, with its parents resolved but the leaf not followed."""
    path = Path(path)
    try:
        parent = Path(os.path.realpath(str(path.parent)))
    except OSError:
        parent = path.parent
    return parent / path.name


def require_inside(candidate, project_root, what="path"):
    """Refuse to touch anything that resolves outside the project.

    A repository can commit ``.dev-team-agents`` or ``.claude`` as a **symlink**
    — git tracks symlinks natively — and every write below used to follow it,
    because ``mkdir(parents=True)`` and ``rmtree`` traverse links. A clone of a
    hostile or merely careless repo could therefore have its bind land anywhere,
    and a vendored bind could delete a directory in the user's home.

    ``_is_inside`` already compared paths correctly and simply was not called on
    this question. This is that call.
    """
    # Resolve the PARENT, then re-attach the name. Resolving the artifact itself
    # would follow it: a bind artifact is a symlink into the store, so its
    # realpath is legitimately outside the project and every check would refuse
    # the very paths dev-team-agents created. Resolving the parent still catches
    # the case that matters — a symlinked `.claude` or `.dev-team-agents`
    # relocating the write out of the tree.
    # Compared directly rather than through `_is_inside`, which resolves the whole
    # candidate — and resolving a bind artifact follows it into the store.
    located = _resolved_location(candidate)
    try:
        root = Path(os.path.realpath(str(project_root)))
        located.relative_to(root)
        return Path(candidate)
    except (ValueError, OSError):
        pass
    raise ConflictError(
        "{} resolves outside the project: {}".format(what, candidate),
        hint=(
            "A path inside the project (or one of its parents) is a symlink pointing "
            "elsewhere. dev-team-agents will not write or delete through it."
        ),
        details={"path": str(candidate), "project_root": str(project_root)},
    )


def _mkdir_within(directory, project_root):
    """Create ``directory`` one component at a time, never through a symlink."""
    directory = Path(directory)
    require_inside(directory, project_root, what="artifact parent")
    root = Path(project_root).resolve()
    try:
        relative = directory.resolve().relative_to(root)
    except ValueError as exc:  # pragma: no cover - require_inside already checked
        raise ConflictError("cannot create {} outside the project".format(directory)) from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ConflictError(
                "{} is a symlink; refusing to create artifacts through it".format(current),
                hint="Remove or repoint that link, then run `devteam sync` again.",
            )
        if not current.exists():
            current.mkdir()
    return current


def _retire_artifact(path, project_id, project_root, group="replaced"):
    """Retire one artifact. Symlinks are unlinked; real content is quarantined.

    A symlink holds no content and ``sync`` recreates it, so unlinking is free.
    A real file or directory is the only copy of whatever is inside it — in
    ``copy`` and ``vendored`` modes that includes anything the user added — so it
    is **moved**, never deleted. Returns ``("unlinked", None)`` or
    ``("quarantined", destination)``.
    """
    path = Path(path)
    require_inside(path, project_root, what="artifact")
    if path.is_symlink():
        path.unlink()
        return "unlinked", None
    destination = quarantine.move(path, project_id, group=group)
    return "quarantined", destination


def _materialize(source, dest, mode, previous_paths, rel, project_root, project_id, retired):
    """Create one artifact, returning ``link`` or ``copy``.

    ``retired`` collects anything moved to quarantine, so a caller can report it.
    """
    source = Path(source)
    dest = Path(dest)
    if not source.exists():
        raise EnvError("core is missing {}".format(source))

    require_inside(dest, project_root, what="artifact")

    if dest.exists() or dest.is_symlink():
        if not _is_managed_path(rel, dest, previous_paths, project_root):
            raise ConflictError(
                "{} already exists and was not created by dev-team-agents".format(dest),
                hint="Move or remove it, then run `devteam sync` again.",
                details={"path": str(dest)},
            )
        action, destination = _retire_artifact(dest, project_id, project_root)
        if action == "quarantined":
            retired.append({"path": rel, "to": str(destination)})

    _mkdir_within(dest.parent, project_root)
    try:
        if mode == "link":
            os.symlink(str(source), str(dest), target_is_directory=source.is_dir())
            return "link"
        if source.is_dir():
            shutil.copytree(str(source), str(dest), symlinks=False)
        else:
            shutil.copy2(str(source), str(dest))
    except OSError as exc:
        raise EnvError(
            "cannot create {}: {}".format(dest, exc),
            hint="Check permissions on the project directory.",
        ) from exc
    return "copy"


def _vendored_tree(version_dir, project_root, previous_paths, project_id, retired):
    """v2 layout: the framework inside the project, with relative links.

    Every existing tree is **quarantined**, never deleted. The previous code had
    a delete branch justified as "a v2 install being re-vendored is the
    documented update" — which is exactly the judgment call the No-Destruction
    Rule says not to make: a hand-written agent sitting in that directory is
    indistinguishable from a framework file, and it was destroyed.
    """
    install_dir = Path(project_root) / project.PROJECT_DIR
    require_inside(install_dir, project_root, what="install directory")
    created = []
    for name in versions.CORE_TREES:
        source = Path(version_dir) / name
        if not source.is_dir():
            continue
        dest = install_dir / name
        rel = str(Path(project.PROJECT_DIR) / name)
        if dest.exists() or dest.is_symlink():
            action, destination = _retire_artifact(
                dest, project_id, project_root, group="revendored"
            )
            if action == "quarantined":
                retired.append({"path": rel, "to": str(destination)})
        _mkdir_within(dest.parent, project_root)
        shutil.copytree(str(source), str(dest), symlinks=False)
        created.append({"path": rel, "kind": "copy"})

    for rel_path, source in providers.claude_artifacts(install_dir):
        dest = Path(project_root) / rel_path
        rel = str(rel_path)
        require_inside(dest, project_root, what="artifact")
        if dest.exists() or dest.is_symlink():
            action, destination = _retire_artifact(dest, project_id, project_root)
            if action == "quarantined":
                retired.append({"path": rel, "to": str(destination)})
        _mkdir_within(dest.parent, project_root)
        depth = len(rel_path.parts) - 1
        relative_target = Path(*([".."] * depth)) / source.relative_to(Path(project_root))
        os.symlink(str(relative_target), str(dest), target_is_directory=True)
        created.append({"path": rel, "kind": "relative-link"})
    return created


def _stamp_installed_version(project_root, project_id, version):
    """Record the resolved version where the v2 readers already look.

    `/devteam:version`, the session banner and telemetry all read
    `installed_version` from `state.json`, and no v3 path wrote it — so a migrated
    project reported its v2 number forever. Retiring the key and repointing those
    four readers is a later decision; stamping it is what makes them truthful now.
    """
    state_file = project.memory_dir(project_root, project_id) / "state.json"
    state = jsonio.read_json(state_file, default=None)
    if state is None:
        state = {}
    if not isinstance(state, dict):
        return None
    if state.get("installed_version") == version:
        return state_file
    state["installed_version"] = version
    jsonio.write_json_atomic(state_file, state)
    return state_file


def _other_checkouts_bound(project_id, project_root):
    """True when another live checkout of the same repository is still bound."""
    entry = registry.get(project_id) or {}
    candidates = [entry.get("path")] + list(entry.get("worktrees", []))
    target = str(Path(project_root).resolve())
    for candidate in candidates:
        if not candidate or candidate == target:
            continue
        if Path(candidate).is_dir():
            return True
    return False


def _git_common_dir(path):
    """The shared git directory for ``path``, or ``None`` outside a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(path),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.decode("utf-8", "replace").strip()
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path(path) / candidate
    try:
        return Path(os.path.realpath(str(candidate)))
    except OSError:
        return None


def _same_git_repository(path_a, path_b):
    """True when both paths are checkouts of one repository (a linked worktree).

    A worktree of a bound repository carries the **committed** ``project.json``,
    so it presents the same ``project_id`` at a second path — which is exactly the
    shape of the fork collision. Telling the two apart matters because this
    repository's own CLAUDE.md mandates worktrees: treating one as a fork told the
    user to reassign an identity in a tracked file on a feature branch, which on
    merge would rename the main checkout's identity and orphan its memory.
    """
    common_a = _git_common_dir(path_a)
    common_b = _git_common_dir(path_b)
    return common_a is not None and common_a == common_b


def _runtime_root(version_dir, project_root, mode, previous_paths, project_id, retired):
    """Give the project an in-tree path to the resolved core version.

    116 shipped references — `.dev-team-agents/scripts/...` in 6 commands and 14
    skills, `.dev-team-agents/templates/...` in 13 places, and `CLAUDE.md`'s own
    `bash .dev-team-agents/scripts/new-adr.sh` — assume the framework is reachable
    from inside the project. A link-mode bind left `.dev-team-agents/` holding
    `project.json` alone, so every one of them broke.

    One pointer fixes all of them without a copy, and it is the same path the bash
    installers' `ensure_claude_framework` was faking by vendoring 2.3 MB back in.
    """
    rel_path = Path(project.PROJECT_DIR) / "core"
    rel = str(rel_path)
    dest = Path(project_root) / rel_path
    kind = _materialize(
        Path(version_dir),
        dest,
        "link" if mode != "copy" else "copy",
        previous_paths,
        rel,
        project_root,
        project_id,
        retired,
    )
    return [{"path": rel, "kind": kind}]


def bind(root=None, provider_names=None, mode="auto", pin=None, emitter=None):
    """Bind ``root`` to the store. Idempotent, and safe to re-run."""
    project_root = project.resolve_root(root)
    if not project_root.is_dir():
        raise UsageError("not a directory: {}".format(project_root))

    requested = list(provider_names) if provider_names else providers.detect(project_root)
    unknown = [p for p in requested if p not in providers.ALL_PROVIDERS]
    if unknown:
        raise UsageError(
            "unknown provider(s): {} (expected: {})".format(
                ", ".join(unknown), ", ".join(providers.ALL_PROVIDERS)
            )
        )
    selected = [p for p in providers.ALL_PROVIDERS if p in set(requested)]

    # Everything that can refuse the bind runs BEFORE the first write. A missing
    # `jq` used to surface from inside the opencode installer, after 154 Claude
    # symlinks already existed and before the manifest, registry entry or exclude
    # block recorded them — leaving artifacts nothing could clean up and nothing
    # kept out of git.
    for provider_name in selected:
        providers.require_tools(provider_name)

    resolved_mode, fallback_reason = resolve_mode(mode, project_root)
    if fallback_reason and emitter:
        emitter.warn("mode=copy: {}".format(fallback_reason))

    data, created_identity = project.ensure(project_root)
    project_id = data["project_id"]

    # `pin=None` means "leave the pin alone", not "clear it". Reading the stored
    # pin here is what stops a bare `devteam bind` from silently moving a pinned
    # project to `current` — the spec calls bind idempotent, and it is the one
    # command a user re-runs casually.
    existing = registry.get(project_id)
    effective_pin = pin if pin is not None else (existing or {}).get("pin")

    # The registry collision check must also precede the writes, so a refused
    # bind (a fork inheriting an identity) leaves nothing behind.
    is_worktree_of_bound = False
    if existing and existing.get("path") != str(project_root.resolve()):
        other = Path(existing["path"])
        if other.exists():
            if _same_git_repository(other, project_root):
                # A linked worktree of an already-bound repository. It carries the
                # same committed project_id, which used to be read as a fork
                # collision — and following that advice would have written a new
                # identity into a tracked file on a feature branch, renaming the
                # main checkout's identity on merge.
                is_worktree_of_bound = True
            else:
                raise ConflictError(
                    "project_id {} is already bound to {}".format(project_id, other),
                    hint=(
                        "Two checkouts share one identity. Run `devteam doctor "
                        "--reassign-identity` in the copy that should get a new one."
                    ),
                    details={"project_id": project_id, "bound_path": str(other)},
                )

    version = versions.resolve(effective_pin)
    version_dir = versions.require(version)

    previous = read_manifest(project_id)
    previous_paths = {item.get("path") for item in previous.get("artifacts", [])}

    artifacts = []
    retired = []
    merged = []
    if resolved_mode == "vendored":
        artifacts.extend(
            _vendored_tree(version_dir, project_root, previous_paths, project_id, retired)
        )
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
                project_id,
                retired,
            )
            artifacts.append({"path": rel, "kind": kind})

    if "claude" in selected or resolved_mode == "vendored":
        artifacts.extend(
            _runtime_root(version_dir, project_root, resolved_mode, previous_paths, project_id, retired)
        )
        artifacts.extend(hooks.wire(project_root, emitter=emitter))

    # Resolved preferences and the state pointer are written on every bind and
    # every sync: both are projections of state that lives elsewhere, so a stale
    # one is a bug rather than a user edit to preserve.
    artifacts.append(prefs.materialize(project_root, project_id, version))
    artifacts.append(project.write_state_pointer(project_root, project_id))
    _stamp_installed_version(project_root, project_id, version)

    if project.upgrade_available(project_root) and emitter is not None:
        emitter.warn(
            "this project still keeps its memory in {}/{} — run `devteam upgrade` to move it "
            "into the store and leave the project clean".format(
                project.PROJECT_DIR, project.LEGACY_MEMORY_DIR
            )
        )

    if resolved_mode != "vendored":
        if "opencode" in selected:
            providers.install_opencode(version_dir, project_root)
            artifacts.extend(providers.delegated_artifacts("opencode", project_root))
            merged.extend(providers.merged_project_files("opencode", project_root))
        if "codex" in selected:
            providers.install_codex(version_dir, project_root)
            artifacts.extend(providers.delegated_artifacts("codex", project_root))
            merged.extend(providers.merged_project_files("codex", project_root))

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
    }
    jsonio.write_json_atomic(manifest_file(project_id), manifest)

    if is_worktree_of_bound:
        registry.add_worktree(project_id, project_root, version)
    else:
        registry.upsert(
            project_id,
            project_root,
            selected,
            resolved_mode,
            pin=effective_pin,
            extra={"last_synced_version": version},
        )

    ignore_changed, ignore_action = gitignore.apply_managed_block(
        Path(project_root) / ".gitignore", list(PROJECT_GITIGNORE_ENTRIES)
    )

    exclude_action = "skipped"
    exclude_file = _local_exclude_file(project_root)
    if exclude_file is not None and resolved_mode != "vendored":
        entries = sorted({item["path"] for item in artifacts})
        _, exclude_action = gitignore.apply_managed_block(exclude_file, entries)
    elif exclude_file is None and emitter:
        emitter.warn(
            "not a git repository: bind artifacts were not added to any ignore file"
        )

    return {
        "project_id": project_id,
        "path": str(project_root),
        "version": version,
        "mode": resolved_mode,
        "providers": selected,
        "artifacts": len(artifacts),
        "retired": retired,
        "merged_project_files": sorted(set(merged)),
        "pin": effective_pin,
        "identity_created": created_identity,
        "pruned": stale,
        "gitignore": ignore_action if ignore_changed else "unchanged",
        "git_exclude": exclude_action,
        "fallback_reason": fallback_reason,
    }


def _prune_stale(project_root, previous, current_paths, project_id):
    """Retire artifacts a previous bind made that this one no longer needs."""
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
            action, destination = _retire_artifact(
                candidate, project_id, project_root, group="pruned"
            )
        except (OSError, ConflictError):
            continue
        if action == "unlinked":
            unlinked.append(rel)
        elif destination is not None:
            quarantined.append({"path": rel, "to": str(destination)})
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
    # Linked worktrees of the same repository carry their own artifacts and are
    # refreshed alongside the checkout that owns the registry entry.
    refreshed = []
    for worktree in entry.get("worktrees", []):
        if not Path(worktree).is_dir():
            continue
        bind(
            worktree,
            provider_names=entry.get("providers"),
            mode=entry.get("mode", "auto"),
            pin=entry.get("pin"),
            emitter=emitter,
        )
        refreshed.append(worktree)
    result["worktrees"] = refreshed
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
        except OSError as exc:
            # A read-only mount, an unmounted volume or a permission change is the
            # likeliest failure across many projects. Escaping as a traceback
            # aborted every project after this one and emitted zero bytes on
            # stdout, breaking the --json contract.
            message = "{}: {}".format(type(exc).__name__, exc)
            problems.append({"project_id": project_id, "error": message})
            if emitter:
                emitter.warn("{}: {}".format(project_id, message))
    return {"synced": results, "problems": problems}


def unbind(root=None, project_id=None, keep_artifacts=False):
    """Remove bind artifacts and the registry entry.

    ``project.json`` and everything under ``user-data/`` stay: identity and
    memory are never collateral damage of an unbind. Real directories — which in
    ``copy`` and ``vendored`` modes may contain files the user added — are moved
    to quarantine rather than deleted.
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
        bound_path = entry.get("path")
        if not bound_path:
            raise EnvError(
                "registry entry for {} has no path".format(project_id),
                hint="Remove the entry by hand, or re-bind the project.",
            )
        project_root = Path(bound_path)

    manifest = read_manifest(project_id)
    unlinked = []
    quarantined = []
    problems = []
    if not keep_artifacts:
        for item in manifest.get("artifacts", []):
            rel = item.get("path")
            # An entry with no path used to become `Path(project_root) / ""`,
            # which IS the project root — and the removal helper then deleted the
            # whole project, source code included, before crashing on the missing
            # key. `_prune_stale` already guarded this; unbind did not.
            if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
                problems.append({"path": rel, "error": "not a relative artifact path"})
                continue
            if item.get("kind") in ("resolved", "pointer"):
                # Generated projections: unlink and move on. They carry no state
                # of their own — the layers they project from are untouched.
                candidate = Path(project_root) / rel
                if candidate.exists():
                    try:
                        candidate.unlink()
                        unlinked.append(rel)
                    except OSError as exc:
                        problems.append({"path": rel, "error": str(exc)})
                continue
            if item.get("kind") == "settings":
                # `.claude/settings.json` belongs to the project and may be
                # committed. Remove only the hook entries we registered.
                try:
                    events = hooks.unwire(project_root)
                except (OSError, EnvError) as exc:
                    problems.append({"path": rel, "error": str(exc)})
                else:
                    if events:
                        unlinked.append("{} (hooks: {})".format(rel, ", ".join(events)))
                continue
            candidate = Path(project_root) / rel
            if not (candidate.exists() or candidate.is_symlink()):
                continue
            try:
                action, destination = _retire_artifact(
                    candidate, project_id, project_root, group="unbound"
                )
            except (OSError, ConflictError) as exc:
                problems.append({"path": rel, "error": str(exc)})
                continue
            if action == "unlinked":
                unlinked.append(rel)
            elif destination is not None:
                quarantined.append({"path": rel, "to": str(destination)})
        exclude_file = _local_exclude_file(project_root)
        if exclude_file is not None and not _other_checkouts_bound(project_id, project_root):
            # git reads only $GIT_COMMON_DIR/info/exclude for a linked worktree —
            # verified, the per-worktree file is ignored — so the block is shared
            # by every checkout of the repository. Clearing it while another
            # worktree is still bound would un-ignore that worktree's artifacts.
            gitignore.apply_managed_block(exclude_file, [])

    registry.remove(project_id)
    return {
        "project_id": project_id,
        "path": str(project_root),
        "unlinked": unlinked,
        "quarantined": quarantined,
        "problems": problems,
        "kept": ["project.json", "user-data/"],
    }