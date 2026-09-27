"""Migrate a v2 vendored install to a v3 bind.

Two rules govern this module, and both come from the No-Destruction Rule:

* The vendored framework trees are **moved** into a dated quarantine under the
  data store, never deleted. A wrong move is recoverable; a wrong delete is not.
* ``user-data/`` and ``docs/`` are not touched. Memory and project knowledge are
  the two things a migration must not be able to lose. Relocating memory into the
  data store is a later milestone with its own migration.

The vendored tree is tracked by git in a v2 install, so removing it from the
index is an explicit commit the user makes — this module reports it and stops
short of rewriting their history.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from . import bind as bind_module
from . import project, providers, quarantine, registry, versions
from .errors import UsageError

#: Everything a v2 install placed under ``.dev-team-agents/`` that a bind
#: replaces. Anything else found there is reported and left alone.
VENDORED_TREES = versions.CORE_TREES + ("CLAUDE-md",)
VENDORED_FILES = ("VERSION", "CHANGELOG.md", "CLAUDE.md", "README.md")

#: Never quarantined, never rewritten.
PRESERVED = ("user-data", "project.json", ".worktree-session", ".learn-last-run")


def detect(project_root):
    """What a v2 install looks like on disk, as a plain report."""
    root = Path(project_root)
    install_dir = root / project.PROJECT_DIR
    trees = [
        name
        for name in VENDORED_TREES
        if (install_dir / name).is_dir() and not (install_dir / name).is_symlink()
    ]
    files = [name for name in VENDORED_FILES if (install_dir / name).is_file()]
    unknown = []
    if install_dir.is_dir():
        known = set(VENDORED_TREES) | set(VENDORED_FILES) | set(PRESERVED) | {"resolved"}
        for child in sorted(install_dir.iterdir()):
            if child.name not in known:
                unknown.append(child.name)
    return {
        "is_v2": bool(trees),
        "vendored_trees": trees,
        "vendored_files": files,
        "unrecognised": unknown,
        "has_user_data": (install_dir / "user-data").is_dir(),
        "already_bound": project.load(root) is not None,
    }


def _git_tracked(project_root, relative):
    """Whether git has ``relative`` in the index — decides the advisory."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=str(project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def plan(root=None, provider_names=None, mode="auto"):
    """Describe what a migration would do. Reads only."""
    project_root = project.resolve_root(root)
    found = detect(project_root)
    if not found["is_v2"]:
        raise UsageError(
            "{} has no vendored v2 install to migrate".format(project_root),
            hint="Use `devteam bind` for a project that was never installed.",
        )

    # A v3 `--mode=vendored` bind looks exactly like a v2 install on disk: the
    # same trees in the same place. Without this check, migrating one silently
    # reversed the mode the user chose — and `vendored` exists precisely for CI,
    # containers and air-gapped repos where `link` into a per-developer absolute
    # path does not work.
    identity = project.load(project_root)
    if identity is not None:
        entry = registry.get(identity["project_id"])
        if entry is not None and entry.get("mode") == "vendored":
            raise UsageError(
                "{} is already bound in vendored mode, not a v2 install".format(project_root),
                hint=(
                    "Nothing to migrate. To change modes run "
                    "`devteam bind --mode link` (or --mode copy) instead."
                ),
            )

    selected = list(provider_names) if provider_names else providers.detect(project_root)
    tracked = [
        "{}/{}".format(project.PROJECT_DIR, name)
        for name in found["vendored_trees"] + found["vendored_files"]
        if _git_tracked(project_root, "{}/{}".format(project.PROJECT_DIR, name))
    ]

    actions = []
    if not found["already_bound"]:
        actions.append("create .dev-team-agents/project.json with a new project_id")
    actions.append("bind providers: {} (mode={})".format(", ".join(selected), mode))
    for name in found["vendored_trees"] + found["vendored_files"]:
        actions.append(
            "move .dev-team-agents/{} into the data-store quarantine".format(name)
        )
    actions.append("write the managed .gitignore block")
    if tracked:
        actions.append(
            "REPORT ONLY: {} path(s) are tracked by git and need an explicit "
            "`git rm -r --cached` commit".format(len(tracked))
        )

    return {
        "path": str(project_root),
        "detected": found,
        "providers": selected,
        "mode": mode,
        "actions": actions,
        "git_tracked": tracked,
        "preserved": list(PRESERVED),
    }


def apply(root=None, provider_names=None, mode="auto", pin=None, emitter=None):
    """Perform the migration described by :func:`plan`."""
    preview = plan(root, provider_names=provider_names, mode=mode)
    project_root = Path(preview["path"])

    # Identity first: quarantine is keyed by project_id, and the vendored trees
    # move before the bind runs. Binding first would let the bind's own stale
    # pruning claim those trees, which is the wrong owner for them and would
    # report them under the wrong heading.
    identity, _created = project.ensure(project_root)
    project_id = identity["project_id"]

    install_dir = project_root / project.PROJECT_DIR
    stamp = time.strftime("%Y-%m-%d")
    quarantined = []
    for name in preview["detected"]["vendored_trees"] + preview["detected"]["vendored_files"]:
        destination = quarantine.move(
            install_dir / name, project_id, group="v2-install", stamp=stamp
        )
        if destination is not None:
            quarantined.append(
                {"from": "{}/{}".format(project.PROJECT_DIR, name), "to": str(destination)}
            )

    bind_result = bind_module.bind(
        project_root,
        provider_names=preview["providers"],
        mode=mode,
        pin=pin,
        emitter=emitter,
    )

    return {
        "path": str(project_root),
        "project_id": bind_result["project_id"],
        "version": bind_result["version"],
        "mode": bind_result["mode"],
        "providers": bind_result["providers"],
        "quarantined": quarantined,
        "quarantine_dir": str(quarantine.target_dir(project_id, "v2-install", stamp))
        if quarantined
        else None,
        "git_tracked": preview["git_tracked"],
        "preserved": list(PRESERVED),
        "unrecognised": preview["detected"]["unrecognised"],
    }
