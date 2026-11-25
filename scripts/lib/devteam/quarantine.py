"""Move content aside instead of deleting it (No-Destruction Rule).

Anything dev-team-agents would otherwise remove, and that is not trivially
regenerable, lands in a dated directory under the data store. A symlink into the
core is regenerable and is simply unlinked; a real directory of files never is,
because nothing guarantees the caller knows what is inside it.

Nothing empties this tree — not sync, not update, not uninstall without
``--purge``.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from . import jsonio, paths


def target_dir(project_id, group="pruned", stamp=None):
    day = stamp or time.strftime("%Y-%m-%d")
    return paths.quarantine_dir(day) / (project_id or "store") / group


def _drop_inner_junctions(directory):
    """Remove junctions inside a directory about to be quarantined, without entering them.

    Across volumes `shutil.move` copies the tree, and `copytree` copies what a junction
    points to: a junction to the core store would put a copy of the store in quarantine.
    A junction holds no content, so removing it loses nothing.
    """
    for current, dirs, _files in os.walk(str(directory)):
        for name in list(dirs):
            child = os.path.join(current, name)
            if paths.is_junction(child):
                paths.remove_link(child)
                dirs.remove(name)


def move(source, project_id, group="pruned", stamp=None):
    """Move ``source`` into quarantine; return the destination, or ``None``."""
    src = Path(source)
    if not (src.exists() or paths.is_link(src)):
        return None
    if paths.is_junction(src):
        # Across volumes `shutil.move` copies a junction's target into quarantine and then
        # removes it: the store's files, not a link. A junction holds nothing; remove it.
        raise OSError("refusing to quarantine the junction {}: remove the link instead".format(src))
    if os.name == "nt" and src.is_dir():
        _drop_inner_junctions(src)
    destination_dir = target_dir(project_id, group=group, stamp=stamp)
    # A quarantined directory can hold exactly the secrets ADR-0013 keeps out of a
    # portable export (a retired v2 memory dir with `credentials.local.json` in it).
    # A bare `mkdir` left this tree at the platform default (0755) while every other
    # store directory is 0700, so containment rested entirely on `data/` itself never
    # being loosened — one `chmod` away from wrong. `jsonio.ensure_dir` gives it the
    # same 0700 as the rest of the store.
    jsonio.ensure_dir(destination_dir)
    destination = destination_dir / src.name
    if destination.exists() or paths.is_link(destination):
        # Two moves of the same name on the same day: keep both.
        destination = destination_dir / "{}.{}".format(src.name, int(time.time() * 1000))
    shutil.move(str(src), str(destination))
    return destination
