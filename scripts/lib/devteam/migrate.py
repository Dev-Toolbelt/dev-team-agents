"""Migrate a v2 vendored install to a v3 bind.

Two rules govern this module, and both come from the No-Destruction Rule:

* The vendored framework trees are **moved** into a dated quarantine under the
  data store, never deleted. A wrong move is recoverable; a wrong delete is not.
* ``user-data/`` and ``docs/`` are not touched. Memory and project knowledge are
  the two things a migration must not be able to lose. Relocating memory into the
  data store is a later milestone with its own migration.

The vendored tree is tracked by git in a v2 install. This module reports every
path that has to leave the index, and removes them from it only when asked
(``untrack=True``, `devteam migrate --apply --untrack`): ``git rm -r --cached`` on
exactly the paths the plan listed, which touches the index and never the working
tree. Committing stays with the user.

Two v2 shapes are converted:

``root``
    The framework vendored at ``.dev-team-agents/`` (v2.1.0 and later).
``pre-root``
    The framework at ``.claude/dev-team-agents/``, memory at ``.claude/user-data/``
    and docs at ``.claude/docs/`` (before v2.1.0). The tree is quarantined like the
    root one; the memory is moved to ``.dev-team-agents/user-data/`` (layout 1, which
    `devteam upgrade` then takes into the store); the docs stay where they are and
    are added to ``context_paths``.
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
PRE_ROOT_DIR = Path(project.PRE_ROOT_DIR)

#: The two v2 shapes, by where the framework was vendored.
LAYOUT_ROOT = "root"
LAYOUT_PRE_ROOT = "pre-root"

#: Paths per `git rm` call: a Claude install commits ~155 links, and an argv has a
#: ceiling on every platform.
UNTRACK_BATCH = 100


def pre_root_install(project_root):
    """True when a pre-v2.1.0 install still sits at ``.claude/dev-team-agents/``.

    The single answer for `bind`, `migrate` and `doctor`. It passed `bind`'s v2
    refusal once, which only looked at the project root, and collided halfway
    through on the relative links it had committed.
    """
    return (Path(project_root) / PRE_ROOT_DIR).is_dir()


def pre_root_error(project_root):
    """`bind`'s refusal for a pre-root install, and `doctor`'s finding: migrate it."""
    root = Path(project_root)
    return ConflictError(
        "{} has a v2 install from before v2.1.0 at {}/ — binding would collide with the "
        "links it committed".format(root, PRE_ROOT_DIR.as_posix()),
        hint="Run `devteam migrate` — it shows a plan first, moves the old install into "
        "a dated quarantine, keeps its memory, and binds.",
        details={"path": str(root / PRE_ROOT_DIR)},
    )


def detect(project_root):
    """What a v2 install looks like on disk, as a plain report.

    ``layout`` is ``root`` or ``pre-root`` (see the module docstring) and
    ``install_dir`` the project-relative directory the framework was vendored in.
    A pre-root install is quarantined whole, so every child but its own
    ``user-data`` counts as vendored — the tree carried directories (``workflows``)
    no later version shipped.
    """
    root = Path(project_root)
    if pre_root_install(root):
        install_rel = PRE_ROOT_DIR.as_posix()
        install_dir = root / PRE_ROOT_DIR
        children = sorted(install_dir.iterdir(), key=lambda child: child.name)
        trees = [c.name for c in children if c.is_dir() and not c.is_symlink() and c.name not in PRESERVED]
        files = [c.name for c in children if not (c.is_dir() and not c.is_symlink()) and c.name not in PRESERVED]
        return {
            "is_v2": True,
            "layout": LAYOUT_PRE_ROOT,
            "install_dir": install_rel,
            "vendored_trees": trees,
            "vendored_files": files,
            "unrecognised": [],
            "has_user_data": (root / project.PRE_ROOT_MEMORY_DIR).is_dir()
            or (install_dir / "user-data").is_dir(),
            "already_bound": project.load(root) is not None,
        }
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
        "layout": LAYOUT_ROOT,
        "install_dir": project.PROJECT_DIR,
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
    if not found["is_v2"] or found["layout"] != LAYOUT_ROOT:
        return []
    identity = project.load(project_root)
    if identity is not None:
        entry = registry.get(identity["project_id"])
        if entry is not None and entry.get("mode") == "vendored":
            return []
    return found["vendored_trees"]


def _tracked_v2_links(project_root):
    """Tracked symlinks that point into a v2 install directory, either layout.

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
    install_dirs = [
        os.path.abspath(str(root / project.PROJECT_DIR)),
        os.path.abspath(str(root / PRE_ROOT_DIR)),
    ]
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
        for install_dir in install_dirs:
            try:
                if os.path.commonpath([install_dir, resolved]) == install_dir:
                    found.append(path)
                    break
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


def _memory_moves(project_root, found):
    """Where a pre-root install's memory goes: ``.dev-team-agents/user-data/``.

    Moved, never quarantined — memory is one of the two things a migration must not
    be able to lose — and to the layout-1 location rather than into the store, so
    `devteam upgrade` (reviewed, confirmed) stays the one path memory takes there.
    Refused when two candidates exist or the target is taken: merging two memory
    directories is a judgement this module does not make.
    """
    if found["layout"] != LAYOUT_PRE_ROOT:
        return []
    root = Path(project_root)
    target = "{}/{}".format(project.PROJECT_DIR, project.LEGACY_MEMORY_DIR)
    candidates = [
        rel
        for rel in (project.PRE_ROOT_MEMORY_DIR, "{}/user-data".format(PRE_ROOT_DIR.as_posix()))
        if (root / rel).is_dir() and not (root / rel).is_symlink()
    ]
    if not candidates:
        return []
    if len(candidates) > 1 or (root / target).exists():
        taken = candidates[1:] if len(candidates) > 1 else [target]
        raise ConflictError(
            "{}: memory would move from {} to {}, but {} already holds memory".format(
                root, candidates[0], target, taken[0]
            ),
            hint="Merge the two directories by hand, keep one, then run `devteam migrate` again.",
            details={"from": candidates, "to": target},
        )
    return [{"from": candidates[0], "to": target}]


def _context_paths_added(project_root, found):
    """A pre-root install's docs, left where they are and made visible to agents."""
    if found["layout"] != LAYOUT_PRE_ROOT or not (Path(project_root) / project.PRE_ROOT_DOCS_DIR).is_dir():
        return []
    identity = project.load(project_root)
    current = identity.get("context_paths", []) if identity else project.DEFAULT_CONTEXT_PATHS
    return [] if project.PRE_ROOT_DOCS_DIR in current else [project.PRE_ROOT_DOCS_DIR]


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
    entry = registry.get(identity["project_id"]) if identity is not None else None
    if entry is not None and entry.get("mode") == "vendored" and found["layout"] == LAYOUT_ROOT:
        raise UsageError(
            "{} is already bound in vendored mode, not a v2 install".format(project_root),
            hint=(
                "Nothing to migrate. To change modes run "
                "`devteam bind --mode link` (or --mode copy) instead."
            ),
        )

    selected = list(provider_names) if provider_names else providers.detect(project_root)
    install_rel = found["install_dir"]
    memory = _memory_moves(project_root, found)
    added = _context_paths_added(project_root, found)
    tracked = [
        "{}/{}".format(install_rel, name)
        for name in found["vendored_trees"] + found["vendored_files"]
        if _git_tracked(project_root, "{}/{}".format(install_rel, name))
    ]
    # Memory that git tracks leaves the index with the rest: its new home is
    # machine-local and excluded, so the old path would only ever show as deleted.
    tracked += [move["from"] for move in memory if _git_tracked(project_root, move["from"])]
    # An identity with no registry entry is ours but unbound — typically what an
    # earlier bind attempt left before it was refused. Adopted, not replaced: the id
    # may already be committed.
    adopts = identity is not None and entry is None

    actions = []
    if identity is None:
        actions.append("create {}/project.json with a new project_id".format(project.PROJECT_DIR))
    elif adopts:
        actions.append(
            "adopt the existing {}/project.json — it is not registered, so an earlier "
            "bind attempt left it".format(project.PROJECT_DIR)
        )
    for move in memory:
        actions.append(
            "move the memory in {} to {} (kept, not quarantined; `devteam upgrade` then "
            "takes it into the store)".format(move["from"], move["to"])
        )
    for path in added:
        actions.append("add {} to context_paths (the docs stay where they are)".format(path))
    for name in found["vendored_trees"] + found["vendored_files"]:
        actions.append("move {}/{} into the data-store quarantine".format(install_rel, name))
    actions.append("bind providers: {} (mode={})".format(", ".join(selected), mode))
    if found["layout"] == LAYOUT_PRE_ROOT:
        actions.append(
            "repoint the hooks in .claude/settings.json and replace the links into {}/".format(
                install_rel
            )
        )
    actions.append("write the managed .gitignore block")
    tracked_links = tracked_artifacts(project_root)
    if tracked or tracked_links:
        actions.append(
            "{} path(s) are tracked by git: `--untrack` removes them from the index "
            "(the files stay on disk); otherwise commit a `git rm -r --cached`".format(
                len(tracked) + len(tracked_links)
            )
        )

    return {
        "path": str(project_root),
        "layout": found["layout"],
        "install_dir": install_rel,
        "detected": found,
        "providers": selected,
        "mode": mode,
        "actions": actions,
        "adopts_identity": adopts,
        "memory_moves": memory,
        "context_paths_added": added,
        "git_tracked": tracked,
        "git_tracked_artifacts": tracked_links,
        "preserved": list(PRESERVED),
    }


def _retire_pre_root_links(project_root):
    """Unlink what still points into the quarantined pre-root tree, after the bind.

    The bind replaced every link it recreates; these are the rest — a skill renamed
    or removed since v2.0 — now dangling. A symlink holds no content, which is why
    unlinking one is not a destruction (the same rule `bind._retire_artifact` uses).
    """
    root = Path(project_root)
    install_dir = os.path.abspath(str(root / PRE_ROOT_DIR))
    retired = []
    for folder in ("agents", "commands", "skills"):
        base = root / ".claude" / folder
        if not base.is_dir() or base.is_symlink():
            continue
        for child in sorted(base.iterdir(), key=lambda item: item.name):
            if not child.is_symlink():
                continue
            target = Path(os.readlink(str(child)))
            if not target.is_absolute():
                target = child.parent / target
            resolved = os.path.normpath(os.path.abspath(str(target)))
            try:
                inside = os.path.commonpath([install_dir, resolved]) == install_dir
            except ValueError:
                inside = False
            if inside:
                child.unlink()
                retired.append(child.relative_to(root).as_posix())
    return retired


def _in_git_work_tree(project_root):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == b"true"


def untrack(project_root, relatives):
    """``git rm -r --cached`` on exactly ``relatives``. Returns ``(done, problem)``.

    The one git command this CLI runs on a user's repository, and only when asked:
    ``--cached`` removes index entries and never touches a file on disk, nothing is
    committed, and no path outside the plan's own list is ever named. A failure is
    reported, not raised — the migration itself already succeeded.
    """
    relatives = sorted(set(relatives))
    if not relatives:
        return [], None
    if not _in_git_work_tree(project_root):
        return [], "{} is not inside a git work tree; nothing to untrack".format(project_root)
    done = []
    for start in range(0, len(relatives), UNTRACK_BATCH):
        batch = relatives[start : start + UNTRACK_BATCH]
        try:
            result = subprocess.run(
                ["git", "rm", "-r", "--cached", "--quiet", "--ignore-unmatch", "--", *batch],
                cwd=str(project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
        except OSError as exc:
            return done, "git could not run: {}".format(exc)
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            return done, "git rm --cached failed: {}".format(detail[-1] if detail else result.returncode)
        done.extend(batch)
    return done, None


def apply(root=None, provider_names=None, mode="auto", pin=None, emitter=None, untrack_paths=False):
    """Perform the migration described by :func:`plan`.

    ``untrack_paths`` also removes from git's index every path the plan reported as
    tracked (see :func:`untrack`); without it they are only reported.
    """
    preview = plan(root, provider_names=provider_names, mode=mode)
    project_root = Path(preview["path"])
    found = preview["detected"]

    # Memory before identity: `project.ensure` picks layout 1 because memory is at
    # `.dev-team-agents/user-data/`, which is what makes `devteam upgrade` offer the
    # move into the store afterwards.
    for move in preview["memory_moves"]:
        target = project_root / move["to"]
        target.parent.mkdir(parents=True, exist_ok=True)
        os.rename(str(project_root / move["from"]), str(target))

    # Identity next: quarantine is keyed by project_id, and the vendored trees
    # move before the bind runs. Binding first would let the bind's own stale
    # pruning claim those trees, which is the wrong owner for them and would
    # report them under the wrong heading.
    context_paths = (
        project.DEFAULT_CONTEXT_PATHS + preview["context_paths_added"]
        if preview["context_paths_added"]
        else None
    )
    identity, _created = project.ensure(project_root, context_paths=context_paths)
    project_id = identity["project_id"]
    if (
        preview["memory_moves"]
        and preview["adopts_identity"]
        and identity.get("layout") != project.LAYOUT_MEMORY_IN_PROJECT
    ):
        # The adopted identity was born on layout 2 because, when the failed bind
        # wrote it, the project had no memory at `.dev-team-agents/user-data/`. It
        # has now, and a layout-2 project reads memory from the store only: left
        # alone, the memory just moved would be invisible, and `devteam upgrade`
        # would never offer to take it there.
        project.set_layout(project_root, project.LAYOUT_MEMORY_IN_PROJECT)

    install_dir = project_root / preview["install_dir"]
    stamp = time.strftime("%Y-%m-%d")
    quarantined = []
    for name in found["vendored_trees"] + found["vendored_files"]:
        destination = quarantine.move(
            install_dir / name, project_id, group="v2-install", stamp=stamp
        )
        if destination is not None:
            quarantined.append(
                {"from": "{}/{}".format(preview["install_dir"], name), "to": str(destination)}
            )
    if preview["layout"] == LAYOUT_PRE_ROOT:
        try:
            install_dir.rmdir()  # emptied above; a leftover keeps it, and is reported
        except OSError:
            pass

    bind_result = bind_module.bind(
        project_root,
        provider_names=preview["providers"],
        mode=mode,
        pin=pin,
        emitter=emitter,
    )
    retired_links = (
        _retire_pre_root_links(project_root) if preview["layout"] == LAYOUT_PRE_ROOT else []
    )

    # Recomputed from the manifest the bind just wrote: that is the authoritative
    # list, and it can differ from the plan's git-derived guess.
    tracked_links = tracked_artifacts(project_root)
    untracked, untrack_problem = [], None
    if untrack_paths:
        untracked, untrack_problem = untrack(
            project_root, preview["git_tracked"] + tracked_links + retired_links
        )

    return {
        "path": str(project_root),
        "layout": preview["layout"],
        "project_id": bind_result["project_id"],
        "version": bind_result["version"],
        "mode": bind_result["mode"],
        "providers": bind_result["providers"],
        "adopted_identity": preview["adopts_identity"],
        "memory_moved": preview["memory_moves"],
        "context_paths_added": preview["context_paths_added"],
        "quarantined": quarantined,
        "quarantine_dir": str(quarantine.target_dir(project_id, "v2-install", stamp))
        if quarantined
        else None,
        "retired_links": retired_links,
        "git_tracked": preview["git_tracked"],
        "git_tracked_artifacts": tracked_links,
        "untracked": untracked,
        "untrack_problem": untrack_problem,
        "preserved": list(PRESERVED),
        "unrecognised": found["unrecognised"],
    }
