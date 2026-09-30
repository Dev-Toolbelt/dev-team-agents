"""Notifications: the queue hooks append to, and the three ways a client reads it.

Why this exists. The framework's notifications used to be boxed text a hook printed
to stdout. A provider shows none of that to the user: SessionStart stdout is model
context and Stop stdout is not displayed. The triggers were right; the channel was
dead. Now a hook appends one JSON line to a per-project queue
(`scripts/hooks/lib/notify.sh`) and the desktop app surfaces it as a native
notification — through this module, because ADR-0015 makes the CLI the app's only
way into the store.

Two files per project, both in its machine-local state directory (ADR-0013):

``notifications.jsonl``
    Append-only, written by hooks only. The CLI **never rewrites it** — a rewrite
    racing a hook's append would drop the line being written. Its size is bounded by
    the writer (`notify.sh` keeps the newest 200 lines).
``notifications-seen.json``
    ``{"schema": 1, "seen": {<id>: <epoch seen>}}``, written by the CLI only, under a
    lock and atomically. Separate from the queue for the same reason.

A notification whose ``expires_at`` has passed is not reported: a context-window
warning from yesterday's session is not something to show when the app opens.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

from . import jsonio, lock, project, registry
from .errors import UsageError

QUEUE_FILE = "notifications.jsonl"
SEEN_FILE = "notifications-seen.json"
SEEN_SCHEMA = 1

LEVELS = ("info", "warning", "critical")

#: The record a hook writes, key for key — `notify.sh` is the other half of this
#: contract. `seen` is added by this module when it reports a record.
RECORD_KEYS = (
    "id",
    "ts",
    "project_id",
    "session_id",
    "level",
    "code",
    "message",
    "dedupe_key",
    "expires_at",
)

#: A seen mark older than this, whose record the writer has already trimmed away, is
#: dropped on the next ack — the seen file stays as small as the queue.
SEEN_RETENTION_SECONDS = 7 * 24 * 3600


def queue_path(root, project_id):
    return Path(project.state_dir(root, project_id)) / QUEUE_FILE


def seen_path(root, project_id):
    return Path(project.state_dir(root, project_id)) / SEEN_FILE


def _number(value):
    # `bool` is an `int` subclass; `true` is not a timestamp.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _valid(record):
    """Whether ``record`` has every key, each of a type the readers can rely on.

    Typed, not just present: one record with ``"ts": null`` made the sort in
    :func:`collect` raise, and every command reading the queue — `list`, `ack`,
    `watch` — failed until 200 newer lines pushed it out.
    """
    if not isinstance(record, dict):
        return False
    if any(key not in record for key in RECORD_KEYS):
        return False
    if not (isinstance(record["id"], str) and record["id"] != ""):
        return False
    if record["level"] not in LEVELS or not _number(record["ts"]):
        return False
    if not (record["expires_at"] is None or _number(record["expires_at"])):
        return False
    return all(
        isinstance(record[key], str) for key in ("project_id", "session_id", "code", "message", "dedupe_key")
    )


def read_queue(path):
    """Every well-formed record in ``path``, oldest first.

    A malformed line — a hook killed mid-write, a hand edit — is skipped, never fatal:
    one bad line must not hide every notification after it.
    """
    path = Path(path)
    if not path.is_file():
        return []
    records = []
    with open(str(path), "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if _valid(record):
                records.append({key: record[key] for key in RECORD_KEYS})
    return records


def load_seen(path):
    data = jsonio.read_json(Path(path), default=None)
    if not isinstance(data, dict) or not isinstance(data.get("seen"), dict):
        return {}
    return {str(k): v for k, v in data["seen"].items() if isinstance(v, (int, float))}


def _expired(record, now):
    expires = record.get("expires_at")
    return isinstance(expires, (int, float)) and expires > 0 and expires <= now


def _bound_projects(project_ids=None):
    """``(project_id, root)`` for every registered project whose directory exists."""
    selected = []
    for project_id, entry in sorted(registry.entries().items()):
        if project_ids is not None and project_id not in project_ids:
            continue
        root = Path(entry.get("path", ""))
        if root.is_dir():
            selected.append((project_id, root))
    return selected


def collect(project_ids=None, unseen_only=False, now=None):
    """Live notifications across bound projects, oldest first."""
    now = time.time() if now is None else now
    result = []
    for project_id, root in _bound_projects(project_ids):
        seen = load_seen(seen_path(root, project_id))
        for record in read_queue(queue_path(root, project_id)):
            if _expired(record, now):
                continue
            # The queue lives in THIS project's state dir, so the project is known
            # even if a hook wrote an empty id (a project bound before the hook knew
            # how to read project.json).
            record["project_id"] = record["project_id"] or project_id
            record["seen"] = record["id"] in seen
            if unseen_only and record["seen"]:
                continue
            result.append(record)
    result.sort(key=lambda r: (r["ts"], r["id"]))
    return result


def ack(ids=None, all_=False, project_ids=None, now=None):
    """Mark notifications seen. Returns the ids newly marked.

    Holds one store lock for the whole call: two app windows acking at once must not
    each read the seen file, add their own id and write back — the second write would
    erase the first.
    """
    if not all_ and not ids:
        raise UsageError(
            "nothing to acknowledge",
            hint="Pass one or more notification ids, or --all.",
        )
    now = time.time() if now is None else now
    wanted = set(ids or [])
    marked = []
    with lock.store_lock("notifications"):
        for project_id, root in _bound_projects(project_ids):
            queue = read_queue(queue_path(root, project_id))
            live_ids = {record["id"] for record in queue}
            path = seen_path(root, project_id)
            seen = load_seen(path)
            changed = False
            for record in queue:
                if record["id"] in seen:
                    continue
                if all_ or record["id"] in wanted:
                    seen[record["id"]] = now
                    marked.append(record["id"])
                    changed = True
            # Drop marks for records the writer has trimmed, once they are old enough
            # that no reader can still be holding the id.
            for stale in [
                key
                for key, when in seen.items()
                if key not in live_ids and now - when > SEEN_RETENTION_SECONDS
            ]:
                del seen[stale]
                changed = True
            if changed:
                jsonio.write_json_atomic(path, {"schema": SEEN_SCHEMA, "seen": seen})
    return sorted(marked)


class _Stop:
    """Why `watch` ended: SIGTERM, a closed stdin (the parent died), or the caller."""

    def __init__(self):
        self.event = threading.Event()
        self.reason = None

    def set(self, reason):
        if self.reason is None:
            self.reason = reason
        self.event.set()


def _watch_stdin(stop):
    # The app keeps our stdin open for as long as it wants the stream. EOF means the
    # parent is gone — an Electron crash leaves no one to send SIGTERM, and a watcher
    # that outlives its reader is a process polling the disk forever for nobody.
    try:
        while sys.stdin.read(4096):
            pass
    except (OSError, ValueError):
        pass
    stop.set("stdin-closed")


def watch(emit, interval=1.0, heartbeat=30.0, rescan=10.0, stop=None, watch_stdin=True, clock=time.time):
    """Stream new notifications as events until told to stop.

    ``emit`` receives one event dict at a time. Events, in order:

    - ``{"event": "notification", "notification": {...}}`` for every unseen, live
      record already queued (the backlog);
    - ``{"event": "ready", "projects": N}`` once, when that backlog is out;
    - ``{"event": "notification", ...}`` again for each record appended after that;
    - ``{"event": "heartbeat", "ts": ...}`` every ``heartbeat`` seconds, so a reader
      can tell a quiet watcher from a hung one;
    - ``{"event": "end", "reason": ...}`` last.

    Change detection is ``stat`` (mtime and size) per queue per tick — no file is
    opened until one changed. The project set is re-read every ``rescan`` seconds so
    a project bound while the app runs is picked up.
    """
    stop = stop or _Stop()
    if watch_stdin:
        threading.Thread(target=_watch_stdin, args=(stop,), daemon=True).start()
    previous = None
    if threading.current_thread() is threading.main_thread():
        previous = signal.signal(signal.SIGTERM, lambda *_: stop.set("sigterm"))

    emitted = set()
    owned = {}  # project id -> the ids of its records last seen unseen and live
    stamps = {}
    projects = []
    last_rescan = -rescan
    last_beat = clock()

    def scan(project_id, root):
        path = queue_path(root, project_id)
        try:
            stat = os.stat(str(path))
            stamp = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            stamp = None
        if stamps.get(project_id) == stamp:
            return
        stamps[project_id] = stamp
        if stamp is None:
            return
        records = collect([project_id], unseen_only=True, now=clock())
        for record in records:
            if record["id"] in emitted:
                continue
            emitted.add(record["id"])
            emit({"event": "notification", "notification": record})
        # Forget ids this project no longer reports — acknowledged, expired or trimmed —
        # so the set is bounded by the queues rather than by how long `watch` has run.
        # An id comes back only if a record reappears, which no writer does.
        live = {record["id"] for record in records}
        gone = owned.get(project_id, set()) - live
        emitted.difference_update(gone)
        owned[project_id] = live

    try:
        first = True
        while not stop.event.is_set():
            now = clock()
            if now - last_rescan >= rescan:
                projects = _bound_projects()
                last_rescan = now
            for project_id, root in projects:
                scan(project_id, root)
            if first:
                emit({"event": "ready", "projects": len(projects)})
                first = False
            if now - last_beat >= heartbeat:
                emit({"event": "heartbeat", "ts": now})
                last_beat = now
            stop.event.wait(interval)
    except KeyboardInterrupt:
        stop.set("interrupted")
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)
    emit({"event": "end", "reason": stop.reason or "stopped"})
    return stop.reason
