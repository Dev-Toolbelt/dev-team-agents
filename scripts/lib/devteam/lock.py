"""Cross-platform advisory lock for store mutations.

Directory creation is the primitive: ``os.mkdir`` is atomic on every platform we
target, needs no extra module, and leaves a visible artifact a user can inspect
or delete. ``fcntl`` would not work on Windows and ``msvcrt`` would not work
anywhere else.

Concurrency is real here, not theoretical: two Claude sessions in two bound
projects can both mutate ``registry.json``.
"""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

from .errors import ConflictError

DEFAULT_TIMEOUT = 15.0
#: A lock older than this is treated as abandoned by a killed process.
DEFAULT_STALE_AFTER = 300.0


class Lock:
    """Context manager holding ``<name>.lock`` under the data store."""

    def __init__(self, path, timeout=DEFAULT_TIMEOUT, stale_after=DEFAULT_STALE_AFTER):
        self.path = Path(path)
        self.timeout = timeout
        self.stale_after = stale_after
        self._held = False
        self.stolen_from = None

    @property
    def _owner_file(self):
        return self.path / "owner.json"

    def _write_owner(self):
        body = {
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "acquired_at": time.time(),
        }
        try:
            with self._owner_file.open("w", encoding="utf-8") as handle:
                json.dump(body, handle)
        except OSError:
            # The lock itself is held; losing the descriptive file is harmless.
            pass

    def _owner_age(self):
        """Seconds since the holder recorded itself, or ``None`` if unknown."""
        try:
            with self._owner_file.open("r", encoding="utf-8") as handle:
                acquired = json.load(handle).get("acquired_at")
        except (OSError, ValueError):
            # No readable owner file — fall back to the directory's own mtime so
            # a crash between mkdir and the owner write still ages out.
            try:
                acquired = self.path.stat().st_mtime
            except OSError:
                return None
        if not isinstance(acquired, (int, float)):
            return None
        return max(0.0, time.time() - acquired)

    def _break_if_stale(self):
        age = self._owner_age()
        if age is None or age < self.stale_after:
            return False
        try:
            if self._owner_file.exists():
                self._owner_file.unlink()
            self.path.rmdir()
        except OSError:
            return False
        self.stolen_from = age
        return True

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                self.path.mkdir()
            except FileExistsError:
                if self._break_if_stale():
                    continue
                if time.monotonic() >= deadline:
                    raise ConflictError(
                        "timed out after {:.0f}s waiting for {}".format(
                            self.timeout, self.path
                        ),
                        hint=(
                            "Another dev-team-agents process is writing to the store. "
                            "If none is running, remove that directory."
                        ),
                    )
                time.sleep(0.05)
                continue
            except OSError as exc:
                raise ConflictError(
                    "cannot create lock {}: {}".format(self.path, exc)
                ) from exc
            self._held = True
            self._write_owner()
            return self

    def release(self):
        if not self._held:
            return
        try:
            if self._owner_file.exists():
                self._owner_file.unlink()
            self.path.rmdir()
        except OSError:
            pass
        self._held = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


def store_lock(name, timeout=DEFAULT_TIMEOUT):
    """Named lock under the data store's ``locks/`` directory."""
    from . import paths

    return Lock(paths.locks_dir() / "{}.lock".format(name), timeout=timeout)
