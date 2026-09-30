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

import os
import subprocess
import time
from pathlib import Path

from . import bind as bind_module
from . import project, providers, quarantine, registry, versions
from .errors import ConflictError, UsageError

#: Everything a v2 install placed under ``.dev-team-agents/`` that a bind
#: replaces. Anything else found there is reported and left alone.
VENDORED_TREES = versions.CORE_TREES + ("CLAUDE-md",)
VENDORED_FILES = ("VERSION", "CHANGELOG.md", "CLAUDE.md", "README.md")

#: Never quarantined, never rewritten.
PRESERVED = ("user-data", "project.json", ".worktree-session", ".learn-last-run")


#: Where a v2 install lived before v2.1.0 moved it to the project root.
PRE_ROOT_DIR = Path(".claude") / "dev-team-agents"


def pre_root_install(project_root):
    """True when a pre-v2.1.0 install still sits at ``.claude/dev-team-agents/``.

    The single answer for `bind`, `migrate` and `doctor`. `detect` looks only at the
    project root, so this shape passed `bind`'s v2 refusal and collided halfway through,
    on the relative links it had committed (`.claude/agents/dev-team ->
    ../dev-team-agents/agents`).
    """
    return (Path(project_root) / PRE_ROOT_DIR).is_dir()


def _migrate_to_root_script():
    # The copy in the active store version, which is the one this CLI ships with; a
    # pre-v2.1.0 install does not carry the script itself.
    try:
        script = versions.version_dir(versions.resolve()) / "scripts" / "migrate-to-root.sh"
    except Exception:  # noqa: BLE001 - a hint must never be the reason a refusal fails
        script = None
    return str(script) if script is not None and script.is_file() else "scripts/migrate-to-root.sh"


def pre_root_error(project_root):
    """The refusal for a pre-root install: move it first, then migrate."""
    root = Path(project_root)
    hint = (
        "Move it first: from {} run `bash \"{}\"`, commit the move, then run "
        "`devteam migrate`.".format(root, _migrate_to_root_script())
    )
    if (root / project.PROJECT_DIR).exists():
        # migrate-to-root.sh refuses to move onto an existing directory — typically
        # one an earlier, failed bind attempt left holding only project.json.
        hint += (
            " {}/ already exists here, and the script will not move onto it: move it "
            "aside first.".format(project.PROJECT_DIR)
        )
    return ConflictError(
        "{} has a v2 install from before v2.1.0 at {}/ — binding would collide with the "
        "links it committed".format(root, PRE_ROOT_DIR.as_posix()),
        hint=hint,
        details={"path": str(root / PRE_ROOT_DIR)},
    )


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


def leftover_trees(project_root):
    """The v2 trees still vendored under ``.dev-team-agents/``, or ``[]``.

    Empty for a project registered in vendored mode: a v3 `--mode vendored` bind puts
    the same trees in the same place on purpose, and reporting it as a leftover would
    tell the user to quarantine the one layout they chose. This is the single answer
    to "is there a v2 install here?" for `bind`'s refusal and `doctor`'s warning, so
    the two can never disagree about the same directory.
    """
    found = detect(project_root)
    if not found["is_v2"]:
        return []
    identity = project.load(project_root)
    if identity is not None:
        entry = registry.get(identity["project_id"])
        if entry is not None and entry.get("mode") == "vendored":
            return []
    return found["vendored_trees"]


def _tracked_v2_links(project_root):
    """Tracked symlinks that point into the project's own ``.dev-team-agents/``.

    What a v2 install committed, and what a bind replaces with links into this
    machine's store — before any bind has run there is no manifest to read, so the
    plan finds them from git's own record: mode 120000 entries whose target resolves
    inside the install directory.
    """
    root = Path(project_root)
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    links = []
    for record in result.stdout.decode("utf-8", "replace").split("\0"):
        meta, _, path = record.partition("\t")
        if path and meta.startswith("120000 "):
            links.append((path, meta.split()[1]))
    if not links:
        return []
    # The committed target, not the working tree's: after a bind the link on disk
    # already points into the store, and the plan must still name it. One
    # `cat-file --batch` for every blob — a Claude install commits ~155 links.
    try:
        shown = subprocess.run(
            ["git", "cat-file", "--batch"],
            cwd=str(root),
            input="".join(blob + "\n" for _, blob in links).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return []
    output = shown.stdout
    install_dir = os.path.abspath(str(root / project.PROJECT_DIR))
    found = []
    offset = 0
    for path, _blob in links:
        # Each answer is "<sha> <type> <size>\n<content>\n".
        header_end = output.index(b"\n", offset)
        size = int(output[offset:header_end].split()[2])
        start = header_end + 1
        target = Path(output[start : start + size].decode("utf-8", "replace"))
        offset = start + size + 1
        if not target.is_absolute():
            target = (root / path).parent / target
        resolved = os.path.normpath(os.path.abspath(str(target)))
        try:
            if os.path.commonpath([install_dir, resolved]) == install_dir:
                found.append(path)
        except ValueError:
            continue
    return sorted(found)


def tracked_artifacts(project_root):
    """Bind artifacts git tracks — from the manifest once bound, from git before."""
    identity = project.load(project_root)
    # Only a registered project's manifest is current: an unbind that kept its
    # artifacts leaves the last manifest behind, and trusting it would report what a
    # bind that no longer exists once wrote.
    if identity is not None and registry.get(identity["project_id"]) is not None:
        manifest = bind_module.read_manifest(identity["project_id"])
        if manifest.get("artifacts"):
            return bind_module.tracked_artifacts(project_root, manifest)
    return _tracked_v2_links(project_root)


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
    # Before `detect`, which would call this "nothing to migrate": the tree is one
    # directory deeper, and `migrate-to-root.sh` is what moves it (and its links).
    if pre_root_install(project_root):
        raise pre_root_error(project_root)
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
    tracked_links = tracked_artifacts(project_root)
    if tracked or tracked_links:
        actions.append(
            "REPORT ONLY: {} path(s) are tracked by git and need an explicit "
            "`git rm -r --cached` commit".format(len(tracked) + len(tracked_links))
        )

    return {
        "path": str(project_root),
        "detected": found,
        "providers": selected,
        "mode": mode,
        "actions": actions,
        "git_tracked": tracked,
        "git_tracked_artifacts": tracked_links,
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
        # Recomputed from the manifest the bind just wrote: that is the authoritative
        # list, and it can differ from the plan's git-derived guess.
        "git_tracked_artifacts": tracked_artifacts(project_root),
        "preserved": list(PRESERVED),
        "unrecognised": preview["detected"]["unrecognised"],
    }
