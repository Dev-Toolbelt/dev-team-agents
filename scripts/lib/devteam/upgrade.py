"""Move a project's memory into the data store, with the user's consent.

Nothing here runs automatically. `bind`, `sync` and `update` never relocate
memory — they report that an upgrade is available, and this module performs it
only when the user asks and passes ``--apply``. That keeps the layout fallback
scoped by an explicit recorded version instead of living forever in the readers,
which is the state-ownership defect a permanent dual path would have been.

Order is copy → verify → retire, never move-and-hope: the source is only given up
once every byte is confirmed present at the destination, and even then it goes to
quarantine rather than being deleted.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

from . import gitignore, jsonio, project, quarantine, registry
from .errors import ConflictError, EnvError, UsageError

#: Entries the managed `.gitignore` block no longer needs once memory has left
#: the project. Removed from the block, never from the rest of the file.
RETIRED_GITIGNORE_ENTRIES = (
    ".dev-team-agents/user-data/",
    "!.dev-team-agents/user-data/graphify.json",
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
    source = project.legacy_memory_dir(project_root)
    destination = project.memory_dir_for_layout(project_root, project_id, project.CURRENT_LAYOUT)
    collisions = sorted(
        rel for rel in inventory if (destination / rel).exists()
    )

    actions = [
        "copy {} file(s) from .dev-team-agents/{}/ to the data store".format(
            len(inventory), project.LEGACY_MEMORY_DIR
        ),
        "verify every copied file by sha256",
        "move the original directory to the data-store quarantine",
        "set layout = {} in .dev-team-agents/project.json".format(project.CURRENT_LAYOUT),
        "rewrite the managed .gitignore block without the user-data entries",
    ]
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
    before = _inventory(project_root)

    copied = []
    if before:
        jsonio.ensure_dir(destination)
        for rel in before:
            target = destination / rel
            jsonio.ensure_dir(target.parent)
            shutil.copy2(str(source / rel), str(target))
            copied.append(rel)

        # Verify before giving up the only copy. A mismatch leaves the source
        # exactly where it was.
        mismatched = [
            rel
            for rel, digest in before.items()
            if not (destination / rel).is_file() or _digest(destination / rel) != digest
        ]
        if mismatched:
            raise EnvError(
                "{} file(s) did not copy correctly; nothing was removed".format(len(mismatched)),
                hint="Check free space and permissions on the data store, then retry.",
                details={"mismatched": mismatched[:20]},
            )

    quarantined = None
    if source.is_dir():
        quarantined = quarantine.move(source, project_id, group="pre-upgrade-memory")

    project.set_layout(project_root, project.CURRENT_LAYOUT)
    pointer = project.write_state_pointer(project_root, project_id)

    gitignore_path = project_root / ".gitignore"
    kept = [
        entry
        for entry in gitignore.read_managed_entries(gitignore_path)
        if entry not in RETIRED_GITIGNORE_ENTRIES
    ]
    _, ignore_action = gitignore.apply_managed_block(gitignore_path, kept)

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
        "destination": str(destination),
        "quarantined": str(quarantined) if quarantined else None,
        "state_pointer": pointer["path"],
        "gitignore": ignore_action,
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
