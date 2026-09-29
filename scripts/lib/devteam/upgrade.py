"""Move a project's memory into the data store, with the user's consent.

Nothing here runs automatically. `bind`, `sync` and `update` never relocate
memory — they report that an upgrade is available, and this module performs it
only when the user asks and passes ``--apply``. That keeps the layout fallback
scoped by an explicit recorded version instead of living forever in the readers,
which is the state-ownership defect a permanent dual path would have been.

Order is copy → verify → retire, never move-and-hope: the source is only given up
once every byte is confirmed present at the destination, and even then it goes to
quarantine rather than being deleted.

The v2 memory directory mixed the user's work with this machine's markers, so the
upgrade splits it (ADR-0013): ``session-summary.md`` and the project preferences go
to the portable subtree, ``state.json`` and the dot-markers to the machine subtree.
Names in ``paths.PROJECT_OWNED_RECORDS`` (``graphify.json``) go nowhere at all: they
are committed, shared project config rather than personal memory, so they are
excluded from the copy and the quarantine and left exactly where they are.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import gitignore, jsonio, paths, project, quarantine, registry
from .errors import ConflictError, EnvError, UsageError

#: Entries the managed `.gitignore` block no longer needs once memory has left
#: the project. Removed from the block, never from the rest of the file.
#: `graphify.json`'s own exception line is deliberately absent here: it names a
#: `paths.PROJECT_OWNED_RECORDS` entry that never leaves the project on upgrade, so
#: the line that keeps it tracked by git for every other developer must survive too.
RETIRED_GITIGNORE_ENTRIES = (
    ".dev-team-agents/user-data/",
)


def _digest(path):
    sha = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _inventory(root):
    """Every file under the legacy memory directory, with its digest."""
    source = project.legacy_memory_dir(root)
    if not source.is_dir():
        return {}
    found = {}
    for path in sorted(source.rglob("*")):
        if path.is_file() and not path.is_symlink():
            found[str(path.relative_to(source))] = _digest(path)
    return found


def _is_project_owned(rel):
    """True for a record that stays in the project instead of moving anywhere.

    `graphify.json` is committed, shared config: `scripts/graphify-refresh.sh` reads
    it at this in-project path, and every developer on the repository sees the same
    file through a deliberate `.gitignore` exception. Copying it into the per-user
    store like the rest of the legacy directory — and retiring the exception that
    keeps it tracked — would silently break graph refresh for everyone else the
    next time they pull.
    """
    return Path(rel).name in paths.PROJECT_OWNED_RECORDS


def _destination_for(rel, portable, machine):
    """Which subtree a file from the legacy memory directory belongs to.

    Tests every path component via `paths.path_is_machine_local`, not just the
    first one: a review found that checking only `Path(rel).parts[0]` sent
    `env/credentials.local.json` to the portable subtree, because `"env"` itself
    isn't a machine-local name — only its child is. A user who organised their
    memory into subdirectories had a secret classified portable, exactly what
    ADR-0013 exists to prevent.
    """
    return machine if paths.path_is_machine_local(rel) else portable


def _git_tracked(root, relative):
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", relative],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def plan(root=None):
    """Describe the upgrade. Reads only."""
    project_root = project.resolve_root(root)
    data = project.load(project_root)
    if data is None:
        raise UsageError(
            "{} is not a bound project".format(project_root),
            hint="Run `devteam bind` first.",
        )
    current = project.layout(project_root)
    if current >= project.CURRENT_LAYOUT:
        raise UsageError(
            "{} is already on layout {}".format(project_root, current),
            hint="Nothing to upgrade.",
        )

    project_id = data["project_id"]
    inventory = _inventory(project_root)
    retained = sorted(rel for rel in inventory if _is_project_owned(rel))
    transferable = {rel: digest for rel, digest in inventory.items() if rel not in set(retained)}
    source = project.legacy_memory_dir(project_root)
    destination = project.memory_dir_for_layout(project_root, project_id, project.CURRENT_LAYOUT)
    state_destination = project.state_dir_for_layout(
        project_root, project_id, project.CURRENT_LAYOUT
    )
    machine_local = sorted(
        rel
        for rel in transferable
        if _destination_for(rel, destination, state_destination) is state_destination
    )
    collisions = sorted(
        rel
        for rel in transferable
        if (_destination_for(rel, destination, state_destination) / rel).exists()
    )

    actions = [
        "copy {} portable file(s) from .dev-team-agents/{}/ to {}".format(
            len(transferable) - len(machine_local), project.LEGACY_MEMORY_DIR, destination
        ),
        "copy {} machine-local file(s) to {}".format(len(machine_local), state_destination),
        "verify every copied file by sha256",
        "move the original directory to the data-store quarantine",
        "set layout = {} in .dev-team-agents/project.json".format(project.CURRENT_LAYOUT),
        "rewrite the managed .gitignore block without the user-data entries",
    ]
    if retained:
        actions.append(
            "keep {} project-owned file(s) in .dev-team-agents/{}/: {}".format(
                len(retained), project.LEGACY_MEMORY_DIR, ", ".join(retained)
            )
        )
    if collisions:
        actions.insert(
            0,
            "REFUSE: {} file(s) already exist at the destination".format(len(collisions)),
        )

    return {
        "path": str(project_root),
        "project_id": project_id,
        "from_layout": current,
        "to_layout": project.CURRENT_LAYOUT,
        "files": len(inventory),
        "source": str(source),
        "destination": str(destination),
        "state_destination": str(state_destination),
        "machine_local": machine_local,
        "retained": retained,
        "collisions": collisions,
        "git_tracked": [
            rel
            for rel in (
                "{}/{}".format(project.PROJECT_DIR, project.LEGACY_MEMORY_DIR),
            )
            if _git_tracked(project_root, rel)
        ],
        "actions": actions,
    }


def apply(root=None, emitter=None):
    """Perform the upgrade described by :func:`plan`."""
    preview = plan(root)
    project_root = Path(preview["path"])
    project_id = preview["project_id"]

    if preview["collisions"]:
        raise ConflictError(
            "{} file(s) already exist in the data store for this project".format(
                len(preview["collisions"])
            ),
            hint=(
                "The destination is not empty. Inspect "
                + preview["destination"]
                + " and move or remove the conflicting files yourself."
            ),
            details={"collisions": preview["collisions"][:20]},
        )

    source = project.legacy_memory_dir(project_root)
    destination = Path(preview["destination"])
    state_destination = Path(preview["state_destination"])
    retained = set(preview["retained"])
    before = _inventory(project_root)

    copied = []
    if before:
        for rel in before:
            if rel in retained:
                continue
            target = _destination_for(rel, destination, state_destination) / rel
            jsonio.ensure_dir(target.parent)
            shutil.copy2(str(source / rel), str(target))
            try:
                # `shutil.copy2` preserves the source mode, which may be a checkout's
                # 0644 on a file that is now a copy of `credentials.local.json`.
                # Containment should not depend on every source file having already
                # been owner-only — force it here instead.
                target.chmod(jsonio.STORE_FILE_MODE)
            except OSError:
                # A filesystem that cannot chmod (e.g. some network shares) still
                # produced a correct, verified copy; don't fail the upgrade over it.
                pass
            copied.append(rel)

        # Verify before giving up the only copy. A mismatch leaves the source
        # exactly where it was.
        mismatched = [
            rel
            for rel, digest in before.items()
            if rel not in retained
            and (
                not _destination_for(rel, destination, state_destination).joinpath(rel).is_file()
                or _digest(_destination_for(rel, destination, state_destination) / rel) != digest
            )
        ]
        if mismatched:
            raise EnvError(
                "{} file(s) did not copy correctly; nothing was removed".format(len(mismatched)),
                hint="Check free space and permissions on the data store, then retry.",
                details={"mismatched": mismatched[:20]},
            )

    # `quarantine.move()` relocates the whole legacy directory in one shot, and a
    # project-owned record (graphify.json) must never leave the project. Stage it
    # aside before the move and put it back once the directory is gone, rather than
    # teaching quarantine.move() to pick and choose what it carries.
    staging = None
    if retained:
        staging = tempfile.mkdtemp(prefix="devteam-upgrade-retain-")
        for rel in retained:
            staged = Path(staging) / rel
            staged.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(source / rel), str(staged))

    quarantined = None
    if source.is_dir():
        quarantined = quarantine.move(source, project_id, group="pre-upgrade-memory")

    if staging is not None:
        try:
            for rel in retained:
                restored = source / rel
                restored.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(Path(staging) / rel), str(restored))
        except OSError as exc:
            # The staged copy is the only one outside quarantine at this point, so it
            # is kept and named rather than cleaned up: an unconditional `finally`
            # would delete it and leave the project's committed file recoverable only
            # from git or by digging through the quarantine tree.
            raise EnvError(
                "the upgrade completed but {} project-owned file(s) could not be put "
                "back: {}".format(len(retained), exc),
                hint=(
                    "They are intact at {} and in the quarantine copy. Move them back to "
                    "{}/{}/ by hand.".format(staging, project.PROJECT_DIR, project.LEGACY_MEMORY_DIR)
                ),
                details={"staged_at": staging, "files": sorted(retained)},
            ) from exc
        else:
            shutil.rmtree(staging, ignore_errors=True)

    project.set_layout(project_root, project.CURRENT_LAYOUT)
    pointers = project.write_pointers(project_root, project_id)

    gitignore_path = project_root / ".gitignore"
    kept = [
        entry
        for entry in gitignore.read_managed_entries(gitignore_path)
        if entry not in RETIRED_GITIGNORE_ENTRIES
    ]
    _, ignore_action = gitignore.apply_managed_block(gitignore_path, kept)

    # The two pointers `write_pointers` just created carry an absolute path into one
    # developer's store, so they can never be committed.
    #
    # **Usually they are already excluded and this step reports `unchanged`**: `bind`
    # rebuilds the local exclude block from its whole artifact set and the pointers are
    # artifacts, so any project bound in `link` or `copy` mode is covered before `upgrade`
    # runs. The narrower case this closes is a project whose block does **not** have them —
    # a `vendored` bind, where `bind` skips the exclude write entirely; a checkout that
    # became a git repository after it was bound, so `local_exclude_file` was `None` at
    # bind time; or a block someone edited. In those, `upgrade` wrote the pointers and
    # touched no ignore file, leaving two untracked entries in every `git status` until
    # some later `devteam sync` happened to rebuild the block.
    #
    # Unioned into the existing managed entries rather than written as the block: replacing
    # it would erase the 100+ artifact paths `bind` put there.
    exclude_file = gitignore.local_exclude_file(project_root)
    exclude_action = "skipped"
    if exclude_file is not None:
        pointer_paths = [pointer["path"] for pointer in pointers]
        existing = gitignore.read_managed_entries(exclude_file)
        merged = sorted(set(existing) | set(pointer_paths))
        if merged != sorted(set(existing)):
            _, exclude_action = gitignore.apply_managed_block(exclude_file, merged)
        else:
            exclude_action = "unchanged"

    if emitter is not None and preview["git_tracked"]:
        emitter.warn(
            "the old memory directory was tracked by git — commit its removal: "
            "git rm -r --cached {}".format(" ".join(preview["git_tracked"]))
        )

    return {
        "path": str(project_root),
        "project_id": project_id,
        "from_layout": preview["from_layout"],
        "to_layout": project.CURRENT_LAYOUT,
        "copied": len(copied),
        "retained": sorted(retained),
        "destination": str(destination),
        "state_destination": str(state_destination),
        "quarantined": str(quarantined) if quarantined else None,
        "state_pointer": pointers[0]["path"],
        "memory_pointer": pointers[1]["path"],
        "gitignore": ignore_action,
        "git_exclude": exclude_action,
        "git_tracked": preview["git_tracked"],
    }


def pending_projects():
    """Bound projects still on an older layout, for the banner and doctor."""
    stale = []
    for project_id, entry in sorted(registry.entries().items()):
        root = Path(entry.get("path", ""))
        if not root.is_dir():
            continue
        try:
            if project.upgrade_available(root):
                stale.append({"project_id": project_id, "path": str(root), "layout": project.layout(root)})
        except EnvError:
            continue
    return stale
