"""Move content aside instead of deleting it (No-Destruction Rule).

Anything dev-team-agents would otherwise remove, and that is not trivially
regenerable, lands in a dated directory under the data store. A symlink into the
core is regenerable and is simply unlinked; a real directory of files never is,
because nothing guarantees the caller knows what is inside it.

Nothing empties this tree — not sync, not update, not uninstall without
``--purge``.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

from . import paths


def target_dir(project_id, group="pruned", stamp=None):
    day = stamp or time.strftime("%Y-%m-%d")
    return paths.quarantine_dir(day) / (project_id or "store") / group


def move(source, project_id, group="pruned", stamp=None):
    """Move ``source`` into quarantine; return the destination, or ``None``."""
    src = Path(source)
    if not (src.exists() or src.is_symlink()):
        return None
    destination_dir = target_dir(project_id, group=group, stamp=stamp)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / src.name
    if destination.exists() or destination.is_symlink():
        # Two moves of the same name on the same day: keep both.
        destination = destination_dir / "{}.{}".format(src.name, int(time.time() * 1000))
    shutil.move(str(src), str(destination))
    return destination
