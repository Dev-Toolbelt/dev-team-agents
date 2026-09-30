"""The task board: per-session records hooks write and the CLI derives state from.

Why this exists (ADR-0018). Agents keep a todo list through their provider's native tool
(Claude Code `TodoWrite` / `TaskCreate` / `TaskUpdate`, Codex `update_plan`, opencode
`todowrite`). A hook captures every call into one record per session, so the desktop app
can show what is pending, in progress and done across every bound project.

One file per session, ``<state-dir>/task-board/<session-key>.json``, in the project's
machine-local state directory (ADR-0013). Per session, not per project, so two sessions
never contend for one lock. Written only by :func:`record` and :func:`mark`, under a
per-session lock and atomically; **never deleted** by anything here (No-Destruction Rule).

Everything a reader wants beyond the raw record — the session's status, a task's column,
stale/abandoned flags, time per status — is **derived on read**, never stored: a stored
"stale" would be wrong the moment the clock moved.

The hook payload shapes of `TodoWrite` and `Task*` are not publicly documented, so every
normalizer is defensive: unknown keys are ignored, and a payload that cannot be read is a
no-op, never an error.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import jsonio, lock, project
from .errors import DevteamError

SCHEMA = 1
TASKS_DIR = "task-board"
HISTORY_CAP = 50

PROVIDERS = ("claude", "codex", "opencode")
STATUSES = ("pending", "in_progress", "completed", "cancelled")
MAIN_OWNER = "main"

DEFAULT_STALE_AFTER = 3600
DEFAULT_ENDED_AFTER = 6 * 3600

#: Per-provider command that reopens a session, for the board's "Copy resume command".
RESUME = {
    "claude": "claude --resume",
    "codex": "codex resume",
    "opencode": "opencode --session",
}

_CLAUDE_TOOLS = ("TodoWrite", "TaskCreate", "TaskUpdate")
_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


# ── session key ──────────────────────────────────────────────────────────────


def session_key(session_id):
    """A filename for ``session_id``, or ``None`` when the id must be refused.

    Path separators, NUL and dot-only names are refused outright — the id comes from a
    hook payload and becomes a path. Any other odd character is replaced and a digest
    appended, so two different ids never share a file.
    """
    if not isinstance(session_id, str) or not session_id or len(session_id) > 256:
        return None
    if "/" in session_id or "\\" in session_id or "\0" in session_id:
        return None
    if session_id in (".", ".."):
        return None
    if _SAFE_KEY.match(session_id):
        return session_id
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", session_id).lstrip(".-_") or "session"
    digest = hashlib.sha1(session_id.encode("utf-8", "replace")).hexdigest()[:12]
    return "{}-{}".format(cleaned[:64], digest)


def tasks_dir(root, project_id=None):
    return Path(project.state_dir(root, project_id)) / TASKS_DIR


def record_path(root, project_id, session_id):
    key = session_key(session_id)
    if key is None:
        return None
    return tasks_dir(root, project_id) / "{}.json".format(key)


# ── payload normalizers ──────────────────────────────────────────────────────


def _text(value):
    return value.strip() if isinstance(value, str) else ""


def norm_content(text):
    """Identity of a task with no provider id: trimmed, whitespace-collapsed, case-folded."""
    return " ".join(str(text).split()).casefold()


def norm_status(value):
    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    if text in ("inprogress", "in_progress", "active", "running"):
        return "in_progress"
    if text in ("completed", "complete", "done"):
        return "completed"
    if text in ("cancelled", "canceled"):
        return "cancelled"
    return "pending"


def _dict(value):
    return value if isinstance(value, dict) else {}


def _first_text(mapping, *names):
    for name in names:
        value = _text(mapping.get(name))
        if value:
            return value
    return ""


def _id_text(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _items(raw, id_name=None, content_names=("content",)):
    """Normalized ``{id, content, status}`` items from a list, or ``None`` if unreadable."""
    if not isinstance(raw, list):
        return None
    if not raw:
        return []
    items = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        content = _first_text(entry, *content_names)
        if not content:
            continue
        items.append(
            {
                "id": _id_text(entry.get(id_name)) if id_name else None,
                "content": content,
                "status": norm_status(entry.get("status")),
            }
        )
    # A non-empty list with nothing readable is a payload we misunderstood, not the
    # owner clearing their list: returning [] would mark every task removed.
    return items or None


def _created_id(payload):
    """The id a `TaskCreate` reported, from ``tool_response`` or ``tool_output``.

    Either may be an object (``{"task": {"id": "3"}}``, ``{"id": 3}``) or a string
    (``Task #3 created successfully: …``); both spellings are looked up, in that order.
    """
    for name in ("tool_response", "tool_output"):
        found = _find_id(payload.get(name), 0)
        if found:
            return found
    return None


def _find_id(value, depth):
    if depth > 3:
        return None
    if isinstance(value, dict):
        for name in ("id", "taskId", "task_id"):
            found = _id_text(value.get(name))
            if found:
                return found
        for name in ("task", "result", "data", "output"):
            found = _find_id(value.get(name), depth + 1)
            if found:
                return found
        return None
    if isinstance(value, str):
        match = re.search(r"#(\w+)", value) or re.search(r"\bid\W{0,3}(\w+)", value, re.IGNORECASE)
        return match.group(1) if match else None
    if isinstance(value, list):
        for entry in value[:5]:
            found = _find_id(entry, depth + 1)
            if found:
                return found
    return None


def normalize(payload, provider="auto"):
    """Turn a hook payload into ``{provider, session_id, cwd, owner, agent_type, op}``.

    ``op`` is ``("replace", items)``, ``("create", item)`` or ``("update", item)``.
    Returns ``None`` for anything that is not a todo-tool call this module can read.
    """
    if not isinstance(payload, dict):
        return None
    tool_name = payload.get("tool_name")
    tool_name = tool_name if isinstance(tool_name, str) else ""
    bare_tool = payload.get("tool")
    bare_tool = bare_tool if isinstance(bare_tool, str) else ""

    detected = None
    if tool_name in _CLAUDE_TOOLS:
        detected = "claude"
    elif tool_name.split(".")[-1] == "update_plan":
        detected = "codex"
    elif bare_tool.lower() == "todowrite":
        detected = "opencode"
    if detected is None or provider not in ("auto", detected):
        return None

    session_id = _first_text(payload, "session_id", "sessionID", "sessionId")
    agent_id = _first_text(payload, "agent_id")
    call = {
        "provider": detected,
        "session_id": session_id,
        "cwd": _first_text(payload, "cwd"),
        "owner": agent_id or MAIN_OWNER,
        "agent_type": _first_text(payload, "agent_type") or None,
        "op": None,
    }

    if detected == "claude":
        tool_input = _dict(payload.get("tool_input"))
        if tool_name == "TodoWrite":
            items = _items(tool_input.get("todos"))
            call["op"] = ("replace", items) if items is not None else None
        elif tool_name == "TaskCreate":
            content = _first_text(tool_input, "subject", "content", "description", "activeForm")
            if content:
                call["op"] = (
                    "create",
                    {"id": _created_id(payload), "content": content, "status": "pending"},
                )
        else:
            task_id = _id_text(tool_input.get("taskId") or tool_input.get("task_id"))
            if task_id:
                raw_status = _text(tool_input.get("status")).lower()
                call["op"] = (
                    "update",
                    {
                        "id": task_id,
                        "content": _first_text(tool_input, "subject", "content") or None,
                        "status": "deleted" if raw_status == "deleted" else (
                            norm_status(raw_status) if raw_status else None
                        ),
                    },
                )
    elif detected == "codex":
        items = _items(_dict(payload.get("tool_input")).get("plan"), content_names=("step", "content"))
        call["op"] = ("replace", items) if items is not None else None
    else:
        items = _items(_dict(payload.get("args")).get("todos"), id_name="id")
        call["op"] = ("replace", items) if items is not None else None

    if call["op"] is None or not call["session_id"]:
        return None
    return call


# ── the record ───────────────────────────────────────────────────────────────


def _new_record(call, project_id, now):
    return {
        "schema": SCHEMA,
        "session_id": call["session_id"],
        "project_id": project_id,
        "provider": call["provider"],
        "cwd": call["cwd"],
        "branch": None,
        "created_at": now,
        "updated_at": now,
        "last_seen_at": now,
        "idle_at": None,
        "ended_at": None,
        "tasks": [],
    }


def _load(path):
    """The record at ``path``, or ``None`` if absent, unreadable or of another schema."""
    try:
        with open(str(path), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("tasks"), list):
        return None
    if not _valid_record(data):
        return None
    return data


def _optional_number(value):
    return value is None or _number(value)


def _valid_record(data):
    """Structural check, so one damaged file is refused instead of poisoning every reader."""
    if not isinstance(data.get("session_id"), str):
        return False
    for name in ("created_at", "updated_at", "last_seen_at"):
        if not _number(data.get(name)):
            return False
    if not (_optional_number(data.get("idle_at")) and _optional_number(data.get("ended_at"))):
        return False
    for task in data["tasks"]:
        if not isinstance(task, dict):
            return False
        for name in ("key", "content", "status", "owner"):
            if not isinstance(task.get(name), str):
                return False
        if not _number(task.get("created_at")) or "removed_at" not in task:
            return False
        if not _optional_number(task["removed_at"]) or not isinstance(task.get("history", []), list):
            return False
    return True


def _push(task, status, now):
    task["status"] = status
    task["history"].append({"status": status, "at": now})
    if len(task["history"]) > HISTORY_CAP:
        del task["history"][: len(task["history"]) - HISTORY_CAP]


def _add_task(record, call, item, now):
    task = {
        "key": "t{}".format(len(record["tasks"]) + 1),
        "id": item.get("id"),
        "owner": call["owner"],
        "agent_type": call["agent_type"],
        "content": item["content"],
        "status": item["status"],
        "created_at": now,
        "removed_at": None,
        "history": [{"status": item["status"], "at": now}],
    }
    record["tasks"].append(task)
    return task


def _revive(task, item, now):
    """Bring a matched task in line with what the call says it is now."""
    task["removed_at"] = None
    if item.get("id") and item.get("content"):
        task["content"] = item["content"]
    if item["status"] != task["status"]:
        _push(task, item["status"], now)


def _identity_matches(task, item):
    if item.get("id") and task.get("id"):
        return item["id"] == task["id"]
    if item.get("id") or task.get("id"):
        return False
    return norm_content(task["content"]) == norm_content(item["content"])


def _apply_replace(record, call, items, now):
    """Diff ``items`` against the tasks of this call's owner only.

    A subagent's list never overwrites the main list, and vice versa: a task belonging to
    another owner is not even a candidate. A task absent from the new list is marked
    removed, not deleted. Duplicates are paired in order, live before removed.
    """
    mine = [t for t in record["tasks"] if t["owner"] == call["owner"]]
    # A task removed after it finished is history: a new item that reads the same is a
    # new task, not that one coming back to life as pending.
    revivable = [t for t in mine if t["removed_at"] is not None and t["status"] not in ("completed", "cancelled")]
    candidates = [t for t in mine if t["removed_at"] is None] + revivable
    matched = set()
    for item in items:
        found = None
        for task in candidates:
            if id(task) not in matched and _identity_matches(task, item):
                found = task
                break
        if found is None:
            matched.add(id(_add_task(record, call, item, now)))
        else:
            matched.add(id(found))
            _revive(found, item, now)
    for task in mine:
        if id(task) not in matched and task["removed_at"] is None:
            task["removed_at"] = now


def _next_sequential_id(record):
    # Session-wide on purpose: Claude numbers TaskCreate calls across the whole session,
    # main agent and subagents alike, so the next id is the max over every owner.
    numbers = [int(t["id"]) for t in record["tasks"] if isinstance(t.get("id"), str) and t["id"].isdigit()]
    return str(max(numbers) + 1) if numbers else "1"


def _apply_create(record, call, item, now):
    if not item.get("id"):
        # The tool output named no id: assume the session assigned the next integer.
        item = dict(item, id=_next_sequential_id(record))
    for task in record["tasks"]:
        if task.get("id") == item["id"] and task["owner"] == call["owner"]:
            _revive(task, dict(item, id=None), now)
            return
    _add_task(record, call, item, now)


def _apply_update(record, call, item, now):
    same_id = [t for t in record["tasks"] if t.get("id") == item["id"]]
    # Same owner first; another owner's task only when this owner has none with that id
    # (Claude's task ids are shared by a session's main agent and its subagents).
    found = next((t for t in same_id if t["owner"] == call["owner"]), None) or (same_id[0] if same_id else None)
    if found is None:
        # Created before the hook existed (or its output was unreadable): keep the update.
        if item["status"] == "deleted":
            return
        _add_task(
            record,
            call,
            {
                "id": item["id"],
                "content": item["content"] or "Task {}".format(item["id"]),
                "status": item["status"] or "pending",
            },
            now,
        )
        return
    if item["content"]:
        found["content"] = item["content"]
    if item["status"] == "deleted":
        if found["removed_at"] is None:
            found["removed_at"] = now
    elif item["status"] and item["status"] != found["status"]:
        _push(found, item["status"], now)


def _apply(record, call, now):
    kind, body = call["op"]
    if kind == "replace":
        _apply_replace(record, call, body, now)
    elif kind == "create":
        _apply_create(record, call, body, now)
    else:
        _apply_update(record, call, body, now)


def _shown(task):
    """A removed task that never completed is not part of the board."""
    return task["removed_at"] is None or task["status"] == "completed"


def _column(status):
    return {"pending": "todo", "in_progress": "in_progress"}.get(status, "done")


def _open_count(record):
    return sum(1 for t in record["tasks"] if _shown(t) and _column(t["status"]) != "done")


def _all_done(record):
    shown = [t for t in record["tasks"] if _shown(t)]
    return bool(shown) and all(_column(t["status"]) == "done" for t in shown)


def _git_branch(cwd):
    if not cwd or not os.path.isdir(cwd):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    branch = result.stdout.decode("utf-8", "replace").strip()
    return branch if result.returncode == 0 and branch else None


#: Long enough to outlast a concurrent hook's whole critical section (a read, a diff and an
#: atomic write, all local) yet well inside a hook's budget: a lock timeout loses the call.
LOCK_TIMEOUT = 10.0


def _session_lock(path):
    return lock.Lock(str(path)[: -len(".json")] + ".lock", timeout=LOCK_TIMEOUT, stale_after=30.0)


def _bound_id(root):
    data = project.load(root)
    if isinstance(data, dict) and data.get("project_id"):
        return data["project_id"]
    return None


def record(root, payload, provider="auto", now=None):
    """Fold one hook payload into its session record. Never raises.

    Returns ``{"recorded", "session", "all_done", "became_all_done"}``.
    """
    result = {"recorded": False, "session": None, "all_done": False, "became_all_done": False}
    try:
        call = normalize(payload, provider)
        if call is None:
            return result
        project_id = _bound_id(root)
        path = record_path(root, project_id, call["session_id"]) if project_id else None
        if path is None:
            return result
        now = int(time.time() if now is None else now)
        # Resolved before the lock: `git` can take seconds, and holding the lock across it
        # made a concurrent hook time out and its call vanish for good.
        stored = _load(path)
        branch = _git_branch(call["cwd"] or (stored or {}).get("cwd"))
        with _session_lock(path):
            rec = _load(path)
            if rec is None:
                if path.exists():
                    # Present but unreadable, or a schema this build does not know: never
                    # overwrite what we cannot read.
                    return result
                rec = _new_record(call, project_id, now)
            was_open = _open_count(rec) > 0
            _apply(rec, call, now)
            rec["provider"] = call["provider"]
            if call["cwd"]:
                rec["cwd"] = call["cwd"]
            rec["branch"] = branch or rec.get("branch")
            rec["updated_at"] = now
            # Activity after the last idle mark means the session is working again; without
            # this a same-second tie kept showing it idle.
            rec["idle_at"] = None
            rec["last_seen_at"] = now
            # A call proves the session is alive, even one resumed after `SessionEnd`.
            rec["ended_at"] = None
            jsonio.write_json_atomic(path, rec)
        done = _all_done(rec)
        result.update(recorded=True, session=call["session_id"], all_done=done, became_all_done=done and was_open)
    except (DevteamError, OSError, ValueError, TypeError, KeyError, AttributeError):
        result["recorded"] = False
    return result


def mark(root, payload, state, now=None):
    """Mark a session ``idle`` or ``ended``. No-op when it has no record. Never raises."""
    result = {"marked": False, "open": 0}
    try:
        if state not in ("idle", "ended") or not isinstance(payload, dict):
            return result
        session_id = _first_text(payload, "session_id", "sessionID", "sessionId")
        project_id = _bound_id(root)
        path = record_path(root, project_id, session_id) if project_id else None
        if path is None or not path.is_file():
            return result
        now = int(time.time() if now is None else now)
        with _session_lock(path):
            rec = _load(path)
            if rec is None:
                return result
            rec["last_seen_at"] = now
            if state == "idle":
                rec["idle_at"] = now
                rec["ended_at"] = None
            else:
                rec["ended_at"] = now
            jsonio.write_json_atomic(path, rec)
        result.update(marked=True, open=_open_count(rec))
    except (DevteamError, OSError, ValueError, TypeError, KeyError, AttributeError):
        result["marked"] = False
    return result


# ── derived state ────────────────────────────────────────────────────────────


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _session_status(rec, now, ended_after):
    if rec.get("ended_at") or now - rec.get("last_seen_at", 0) > ended_after:
        return "ended"
    idle_at = rec.get("idle_at")
    if _number(idle_at) and idle_at >= rec.get("updated_at", 0):
        return "idle"
    return "active"


def _durations(history, until):
    totals = {"pending": 0, "in_progress": 0, "completed": 0}
    for index, entry in enumerate(history):
        end = history[index + 1]["at"] if index + 1 < len(history) else until
        seconds = max(0, int(end - entry["at"]))
        totals[entry["status"]] = totals.get(entry["status"], 0) + seconds
    return totals


def _task_view(task, session_status, now, stale_after, until):
    history = [h for h in task.get("history", []) if isinstance(h, dict) and _number(h.get("at"))]
    if not history:
        history = [{"status": task["status"], "at": task["created_at"]}]
    since = history[-1]["at"]
    column = _column(task["status"])
    completed_at = None
    if task["status"] == "completed":
        completed_at = since
    return {
        "key": task["key"],
        "content": task["content"],
        "owner": task["owner"],
        "agent_type": task.get("agent_type"),
        "status": task["status"],
        "column": column,
        "created_at": task["created_at"],
        "status_since": since,
        "completed_at": completed_at,
        "durations": _durations(history, until),
        "stale": task["status"] == "in_progress"
        and session_status != "ended"
        and now - since > stale_after,
        "abandoned": column != "done" and session_status == "ended",
    }


def _task_order(task):
    """Creation time, then creation sequence: ``t2`` before ``t10``, not after it."""
    match = re.search(r"(\d+)$", str(task.get("key", "")))
    return (task.get("created_at", 0), int(match.group(1)) if match else 0)


def resume_command(root, provider, session_id, cwd=None):
    """One line that reopens the session where it was started.

    Providers look a session up by working directory, so a session begun in a linked
    worktree or a subdirectory only resumes from there; the project root is the fallback
    when the recorded directory is gone or was never recorded.
    """
    base = RESUME.get(provider)
    if not base:
        return None
    where = cwd if isinstance(cwd, str) and cwd and os.path.isdir(cwd) else root
    return "cd {} && {} {}".format(shlex.quote(str(where)), base, shlex.quote(session_id))


def _counts(views):
    counts = {"todo": 0, "in_progress": 0, "done": 0}
    for view in views:
        counts[view["column"]] += 1
    counts["total"] = len(views)
    return counts


def session_view(rec, root, now, stale_after=DEFAULT_STALE_AFTER, ended_after=DEFAULT_ENDED_AFTER):
    """One session as the board shows it, or ``None`` when it has no task to show."""
    status = _session_status(rec, now, ended_after)
    until = now
    if status == "ended":
        until = rec.get("ended_at") or rec.get("last_seen_at") or now
    views = [
        _task_view(task, status, now, stale_after, until)
        for task in sorted(rec["tasks"], key=_task_order)
        if isinstance(task, dict) and _shown(task)
    ]
    if not views:
        return None
    activity = max(v for v in (rec.get("updated_at"), rec.get("last_seen_at"), 0) if _number(v))
    return {
        "session_id": rec["session_id"],
        "provider": rec.get("provider"),
        "branch": rec.get("branch"),
        "cwd": rec.get("cwd"),
        "status": status,
        "created_at": rec.get("created_at"),
        "last_activity_at": activity,
        "ended_at": rec.get("ended_at"),
        "resume_command": resume_command(root, rec.get("provider"), rec["session_id"], rec.get("cwd")),
        "counts": _counts(views),
        "tasks": views,
    }


def _project_records(root, project_id):
    directory = tasks_dir(root, project_id)
    try:
        names = sorted(n for n in os.listdir(str(directory)) if n.endswith(".json") and not n.startswith("."))
    except OSError:
        return []
    records = []
    for name in names:
        rec = _load(directory / name)
        if rec is not None and isinstance(rec.get("session_id"), str):
            records.append(rec)
    return records


def project_view(root, project_id, now, since=None, stale_after=DEFAULT_STALE_AFTER, ended_after=DEFAULT_ENDED_AFTER):
    """One project as the board shows it, or ``None`` when no session has a task."""
    sessions = []
    for rec in _project_records(root, project_id):
        try:
            view = session_view(rec, root, now, stale_after, ended_after)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if view is None:
            continue
        if since is not None and view["last_activity_at"] < since:
            continue
        sessions.append(view)
    if not sessions:
        return None
    sessions.sort(key=lambda s: (-s["last_activity_at"], s["session_id"]))
    all_tasks = [t for s in sessions for t in s["tasks"]]
    return {
        "project_id": project_id,
        "root": str(root),
        "providers": sorted({s["provider"] for s in sessions if s["provider"]}),
        # A session is "active" for the card while it is still open — active or idle.
        "sessions_total": len(sessions),
        "sessions_active": sum(1 for s in sessions if s["status"] != "ended"),
        "counts": _counts(all_tasks),
        "stale": sum(1 for t in all_tasks if t["stale"]),
        "abandoned": sum(1 for t in all_tasks if t["abandoned"]),
        "last_activity_at": sessions[0]["last_activity_at"],
        "sessions": sessions,
    }


def _bound(project_ids):
    from . import notifications

    return notifications._bound_projects(project_ids)


def collect(project_ids=None, since=None, stale_after=DEFAULT_STALE_AFTER, ended_after=DEFAULT_ENDED_AFTER, now=None):
    """The board: every bound project with at least one task, most recent first."""
    now = int(time.time() if now is None else now)
    projects = []
    for project_id, root in _bound(project_ids):
        try:
            view = project_view(root, project_id, now, since, stale_after, ended_after)
        except DevteamError:
            continue
        if view is not None:
            projects.append(view)
    projects.sort(key=lambda p: (-p["last_activity_at"], p["project_id"]))
    return {"generated_at": now, "stale_after": stale_after, "ended_after": ended_after, "projects": projects}


# ── watch ────────────────────────────────────────────────────────────────────


class _Stop:
    def __init__(self):
        self.event = threading.Event()
        self.reason = None

    def set(self, reason):
        if self.reason is None:
            self.reason = reason
        self.event.set()


def _watch_stdin(stop):
    # EOF means the app is gone; an Electron crash sends no SIGTERM, and a watcher that
    # outlives its reader would poll the disk forever for nobody.
    try:
        while sys.stdin.read(4096):
            pass
    except (OSError, ValueError):
        pass
    stop.set("stdin-closed")


def _stamp(root, project_id):
    try:
        directory = tasks_dir(root, project_id)
        stamp = []
        for name in sorted(os.listdir(str(directory))):
            if name.endswith(".json") and not name.startswith("."):
                stat = os.stat(str(directory / name))
                stamp.append((name, stat.st_mtime_ns, stat.st_size))
        return tuple(stamp)
    except (OSError, DevteamError):
        return None


def watch(
    emit,
    project_ids=None,
    since=None,
    stale_after=DEFAULT_STALE_AFTER,
    ended_after=DEFAULT_ENDED_AFTER,
    interval=1.0,
    heartbeat=30.0,
    rescan=10.0,
    refresh=30.0,
    stop=None,
    watch_stdin=True,
    clock=time.time,
):
    """Stream ``snapshot`` events per changed project until told to stop.

    Events: a ``snapshot`` for every project that already has tasks, ``ready`` once that
    backlog is out, then a ``snapshot`` whenever a project's view changes (or
    ``{"project_id", "removed": true}`` when it no longer has tasks), ``heartbeat`` every
    ``heartbeat`` seconds and ``end`` last — the lifecycle of `notifications.watch`.

    A file's mtime only says the *record* changed. "Stale" and "abandoned" move with the
    clock, so every ``refresh`` seconds each project is recomputed too, and a snapshot is
    emitted only when the view actually differs from the last one sent.
    """
    stop = stop or _Stop()
    if watch_stdin:
        threading.Thread(target=_watch_stdin, args=(stop,), daemon=True).start()
    previous = None
    if threading.current_thread() is threading.main_thread():
        previous = signal.signal(signal.SIGTERM, lambda *_: stop.set("sigterm"))

    stamps = {}
    last_view = {}  # project id -> serialized view last emitted, or None once removed
    refreshed = {}
    projects = []
    last_rescan = -rescan
    last_beat = clock()

    def scan(project_id, root):
        now = clock()
        stamp = _stamp(root, project_id)
        if stamps.get(project_id, "unset") == stamp and now - refreshed.get(project_id, 0) < refresh:
            return
        stamps[project_id] = stamp
        refreshed[project_id] = now
        try:
            view = project_view(root, project_id, int(now), since, stale_after, ended_after)
        except DevteamError:
            return
        serialized = json.dumps(view, sort_keys=True) if view is not None else None
        if project_id in last_view:
            if last_view[project_id] == serialized:
                return
        elif view is None:
            last_view[project_id] = None
            return
        last_view[project_id] = serialized
        if view is not None:
            emit({"event": "snapshot", "project": view})
        else:
            emit({"event": "snapshot", "project": {"project_id": project_id, "removed": True}})

    try:
        first = True
        while not stop.event.is_set():
            now = clock()
            if now - last_rescan >= rescan:
                projects = _bound(project_ids)
                last_rescan = now
            for project_id, root in projects:
                scan(project_id, root)
            if first:
                emit({"event": "ready"})
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
