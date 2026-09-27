"""Atomic JSON reads and writes.

Every store mutation goes through here. A half-written ``registry.json`` would
orphan every bound project, so writes land in a sibling temporary file and are
promoted with ``os.replace``, which is atomic on POSIX and on Windows.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import EnvError


def read_json(path, default=None):
    """Parse ``path``; return ``default`` when it does not exist.

    A malformed file is an environment error, never a reason to overwrite: the
    caller is told which file to fix instead of losing its contents.
    """
    p = Path(path)
    if not p.exists():
        return default
    try:
        with p.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise EnvError(
            "{} is not valid JSON ({})".format(p, exc),
            hint="Fix the file by hand. dev-team-agents never rewrites a malformed file.",
        ) from exc
    except OSError as exc:
        raise EnvError("cannot read {}: {}".format(p, exc)) from exc


def write_json_atomic(path, data):
    """Write ``data`` as pretty JSON, atomically, creating parent directories."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=str(p.parent),
        prefix=p.name + ".",
        suffix=".tmp",
        delete=False,
    )
    tmp_name = handle.name
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, str(p))
    except OSError as exc:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise EnvError("cannot write {}: {}".format(p, exc)) from exc
    return p
