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

import copy
import datetime
import hashlib
import html
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

from . import jsonio, lock, project, review_triggers
from .errors import DevteamError

SCHEMA = 1
TASKS_DIR = "task-board"
HISTORY_CAP = 50

PROVIDERS = ("claude", "codex", "opencode")
STATUSES = ("pending", "in_progress", "completed", "cancelled")
MAIN_OWNER = "main"

DEFAULT_STALE_AFTER = 3600
DEFAULT_ENDED_AFTER = 6 * 3600
#: A review window still waiting on an agent this long after its last activity is settled as
#: unread instead of being joined: a lost result must not wedge the column forever.
PENDING_MAX_AGE = 6 * 3600

#: Per-provider command that reopens a session; emitted as `resume_command` in the `tasks` JSON contract.
RESUME = {
    "claude": "claude --resume",
    "codex": "codex resume",
    "opencode": "opencode --session",
}

_CLAUDE_TOOLS = ("TodoWrite", "TaskCreate", "TaskUpdate")
_CLAUDE_AGENT_TOOLS = ("Agent", "Task")
_CODEX_AGENT_TOOLS = ("spawn_agent", "wait_agent", "close_agent")
#: Longest first line of a Codex spawn message kept as a task's description.
AGENT_TEXT = 120
PLAN_STEP_RE = re.compile(r"^Step \d+:")
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


#: Longest task text a record keeps — the bound the app already cuts to (`MAX_TASK_TEXT` in
#: `app/src/cli/operations.ts`), so nothing shown is lost, and every record on disk stays bounded.
MAX_TASK_TEXT = 2000


def _task_text(text):
    return text[:MAX_TASK_TEXT].rstrip() if text else text


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
        content = _task_text(_first_text(entry, *content_names))
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
        match = re.match(r"\s*Task #(\w+)", value) or re.search(r"\bTask #(\w+) created", value)
        return match.group(1) if match else None
    if isinstance(value, list):
        for entry in value[:5]:
            found = _find_id(entry, depth + 1)
            if found:
                return found
    return None


def _json_objects(value):
    """Dicts in ``value``: itself, or any string inside it that parses as a JSON object."""
    if isinstance(value, dict):
        yield value
    for text in review_triggers._strings(value):
        if text.lstrip().startswith("{"):
            try:
                found = json.loads(text)
            except ValueError:
                continue
            if isinstance(found, dict):
                yield found


def _spawned_agent_id(response):
    """The agent id a Codex ``spawn_agent`` answered with, else ``""``."""
    for found in _json_objects(response):
        ident = _id_text(found.get("agent_id") or found.get("agentId"))
        if ident:
            return ident
    return ""


#: Codex's final agent states (`AgentStatus`, snake_case) -> (task status, failed).
_WAIT_FINAL = {
    "completed": ("completed", False),
    "errored": ("cancelled", True),
    "not_found": ("cancelled", True),
    "shutdown": ("cancelled", False),
}


def _wait_results(response):
    """``[(agent id, status, failed)]`` for every agent a Codex ``wait_agent`` reports as finished."""
    out = []
    for found in _json_objects(response):
        statuses = found.get("status")
        if not isinstance(statuses, dict):
            continue
        for ident, state in statuses.items():
            if isinstance(state, str):
                word = state
            elif isinstance(state, dict) and len(state) == 1:
                word = next(iter(state))
            else:
                word = None
            if isinstance(word, str) and word in _WAIT_FINAL:
                out.append((str(ident),) + _WAIT_FINAL[word])
        if out:
            break
    return out


def _agent_text(provider, name, inp):
    """``<agent>: <description>``; the agent's name alone when the call has no description."""
    if provider == "codex":
        described = _text(inp.get("message")).splitlines()
        described = described[0].strip()[:AGENT_TEXT] if described else ""
    else:
        described = _text(inp.get("description"))
    return _task_text("{}: {}".format(name, described) if described else name)


def _agent_op(payload, provider, bare):
    """The op an agent spawn, its result, its failure or a Codex wait stands for, else ``None``.

    Review/QA agents and the provider's built-in agents are not tasks (their effect is the review
    window, or none). ``agent_wait`` carries no name: it settles whichever tasks it reports.
    """
    tool_input = _dict(payload.get("tool_input"))
    inp = tool_input or _dict(payload.get("args"))
    if bare == "wait_agent":
        results = _wait_results(payload.get("tool_response"))
        return ("agent_wait", results) if results else None
    if bare == "close_agent":
        # An agent the session closed ahead of its result will never report one.
        ident = _id_text(inp.get("target") or inp.get("id") or inp.get("agent_id"))
        return ("agent_wait", [(ident, "cancelled", False)]) if ident else None
    name = review_triggers.spawn_name(_first_text(inp, "subagent_type", "agent_type"))
    if not name or review_triggers.agent_name(name) or review_triggers.is_builtin(provider, name):
        return None
    use_id = _first_text(payload, "tool_use_id", "toolUseId")
    transcript = _first_text(payload, "transcript_path")
    event = _text(payload.get("hook_event_name"))
    failed = event == "PostToolUseFailure"
    after = failed or event == "PostToolUse" or any(k in payload for k in ("output", "tool_response", "tool_output"))
    background = inp.get("run_in_background") is True
    if not after:
        return ("agent_spawn", {
            "id": use_id, "agent": name, "content": _agent_text(provider, name, inp),
            "background": background, "transcript": transcript,
        })
    if failed:
        return ("agent_end", {"id": use_id, "agent": name, "status": "cancelled", "failed": True})
    if bare == "spawn_agent":
        ref = _spawned_agent_id(payload.get("tool_response"))
        if ref:
            return ("agent_ref", {"id": use_id, "ref": ref}) if use_id else None
        # The spawn answered with no agent id: no agent exists, and no wait can ever settle it.
        return ("agent_end", {"id": use_id, "agent": name, "status": "cancelled", "failed": True})
    if background or _async_launch(payload):
        return ("agent_bg", {"id": use_id, "agent": name, "transcript": transcript})
    return ("agent_end", {"id": use_id, "agent": name, "status": "completed", "failed": False})


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
    elif tool_name in _CLAUDE_AGENT_TOOLS:
        detected = "claude"
    elif tool_name.split(".")[-1] in _CODEX_AGENT_TOOLS:
        detected = "codex"
    elif bare_tool.lower() == "task":
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

    if tool_name in _CLAUDE_AGENT_TOOLS or tool_name.split(".")[-1] in _CODEX_AGENT_TOOLS or bare_tool.lower() == "task":
        call["op"] = _agent_op(payload, detected, tool_name.split(".")[-1])
    elif detected == "claude":
        tool_input = _dict(payload.get("tool_input"))
        if tool_name == "TodoWrite":
            items = _items(tool_input.get("todos"))
            call["op"] = ("replace", items) if items is not None else None
        elif tool_name == "TaskCreate":
            content = _task_text(_first_text(tool_input, "subject", "content", "description", "activeForm"))
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
                        "content": _task_text(_first_text(tool_input, "subject", "content")) or None,
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
    reviews = data.get("reviews", [])
    if not isinstance(reviews, list):
        return False
    for window in reviews:
        if not isinstance(window, dict) or not isinstance(window.get("id"), str):
            return False
        if not _number(window.get("opened_at")) or not isinstance(window.get("task_keys"), list):
            return False
        if not (_optional_number(window.get("result_at")) and _optional_number(window.get("resolved_at"))):
            return False
        if not (_optional_number(window.get("findings")) and _optional_number(window.get("fix_after"))):
            return False
        if not isinstance(window.get("pending", 0), int) or not isinstance(window.get("left", {}), dict):
            return False
        if not (isinstance(window.get("fg", []), list) and isinstance(window.get("bg", []), list)):
            return False
        if not _optional_number(window.get("last_at")):
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
    mine = [t for t in record["tasks"] if t["owner"] == call["owner"] and not _is_agent(t)]
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
        if task.get("id") == item["id"] and task["owner"] == call["owner"] and not _is_agent(task):
            # A replayed create names a task that exists: refresh its text only, so a
            # started or finished task is never pushed back to pending.
            if item.get("content"):
                task["content"] = item["content"]
            task["removed_at"] = None
            return
    _add_task(record, call, item, now)


def _apply_update(record, call, item, now):
    same_id = [t for t in record["tasks"] if t.get("id") == item["id"] and not _is_agent(t)]
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


def _is_agent(task):
    return task.get("kind") == "agent"


def _find_agent(record, item, statuses=("in_progress", "pending")):
    """The open agent task a result belongs to: by spawn id, by Codex agent id, else the oldest of its kind.

    The oldest-open fallback is for a result that names no spawn id; it needs the same owner
    and agent so two agents running side by side are not swapped.
    """
    agents = [t for t in record["tasks"] if _is_agent(t) and t["status"] in statuses]
    ident = item.get("id")
    if ident:
        for task in agents:
            if ident in (task.get("id"), task.get("agent_ref")):
                return task
        return None
    return next((t for t in agents if t.get("agent_type") == item.get("agent") and t["owner"] == item.get("owner")), None)


def _agent_scan(record, path, opened_at):
    """The record's transcript cursor for background agents' hand-backs, created on demand.

    It is shaped like a review window so :func:`_background_reports` reads both the same way.
    """
    scan = record.get("agent_scan")
    if not isinstance(scan, dict):
        scan = {"opened_at": opened_at, "tx_path": None, "tx_offset": None, "queue_ids": []}
        record["agent_scan"] = scan
    if scan.get("tx_path") is None and isinstance(path, str) and path and os.path.isfile(path):
        try:
            scan["tx_offset"] = os.path.getsize(path)
            scan["tx_path"] = path
        except OSError:
            pass
    return scan


def _follow_background(record, task, path, opened_at):
    """Start the background hand-back cursor for ``task`` where the transcript ends now.

    The cursor is shared by every background agent of the record. While another one is still
    running it keeps its place (its hand-back may sit anywhere after it); with none running it
    is stale, so it restarts at the transcript's end — a hand-back cannot precede the launch.
    """
    others = any(
        t is not task and _is_agent(t) and t.get("background") and t["status"] == "in_progress"
        for t in record["tasks"]
    )
    scan = _agent_scan(record, path, opened_at)
    if others or not (isinstance(path, str) and path and os.path.isfile(path)):
        return
    try:
        scan["tx_offset"] = os.path.getsize(path)
        scan["tx_path"] = path
        scan["opened_at"] = opened_at
    except OSError:
        pass


def _end_agent(task, status, failed, now):
    if failed:
        task["failed"] = True
    _push(task, status, now)


def _apply_agent(record, call, now):
    """Fold an agent event into the record. Returns True when it changed something."""
    kind, body = call["op"]
    if kind == "agent_spawn":
        if body["id"]:
            replayed = any(_is_agent(t) and t.get("id") == body["id"] for t in record["tasks"])
        else:
            # No id to match: a replay is the same agent, text and owner still open without one.
            replayed = any(
                _is_agent(t) and not t.get("id") and t["status"] == "in_progress" and t["owner"] == call["owner"]
                and t.get("agent_type") == body["agent"] and t["content"] == body["content"]
                for t in record["tasks"]
            )
        if replayed:
            return False  # a replayed spawn names a task that exists
        task = _add_task(
            record, call, {"id": body["id"] or None, "content": body["content"], "status": "in_progress"}, now
        )
        task.update(kind="agent", agent_type=body["agent"], background=bool(body["background"]), failed=False)
        if body["background"]:
            _follow_background(record, task, body.get("transcript"), now)
        return True
    if kind == "agent_wait":
        changed = False
        for ident, status, failed in body:
            task = _find_agent(record, {"id": ident})
            if task is not None:
                _end_agent(task, status, failed, now)
                changed = True
        return changed
    item = dict(body, owner=call["owner"])
    task = _find_agent(record, item)
    if task is None:
        return False
    if kind == "agent_ref":
        task["agent_ref"] = body["ref"]
        return True
    if kind == "agent_bg":
        task["background"] = True
        _follow_background(record, task, body.get("transcript"), now)
        return True
    _end_agent(task, body["status"], body["failed"], now)
    return True


def _apply(record, call, now):
    kind, body = call["op"]
    if kind.startswith("agent_"):
        return _apply_agent(record, call, now)
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


def _task_column(task, members):
    """The board column: a task inside an unresolved review window is In Review."""
    return "in_review" if task["key"] in members else _column(task["status"])


def _hidden_keys(record):
    """Keys of the agent tasks the board leaves out: their owner also keeps a mirrored plan.

    The plan's ``Step N:`` tasks are the better grain; the agent tasks stay in the record.
    """
    owners = {
        t["owner"] for t in record["tasks"]
        if not _is_agent(t) and _shown(t) and PLAN_STEP_RE.match(t["content"])
    }
    if not owners:
        return set()
    return {t["key"] for t in record["tasks"] if _is_agent(t) and t["owner"] in owners}


def _visible(record):
    hidden = _hidden_keys(record)
    return [t for t in record["tasks"] if _shown(t) and t["key"] not in hidden]


def _open_keys(record, members):
    return {t["key"] for t in _visible(record) if _task_column(t, members) != "done"}


def _open_count(record):
    return len(_open_keys(record, _review_members(record)))


def _all_done(record, members):
    shown = _visible(record)
    return bool(shown) and all(_task_column(t, members) == "done" for t in shown)


def _cleanly_done(record, members):
    """``_all_done`` with no task that failed or was cut off: those are not a finished session."""
    return _all_done(record, members) and not any(
        t.get("failed") or t.get("interrupted") for t in _visible(record)
    )


# ── review windows (In Review column) ────────────────────────────────────────


def _windows(record):
    return record.get("reviews") or []


def _completed_at(task):
    """When the task last entered ``completed``, or ``None`` if it is not completed."""
    if task["status"] != "completed":
        return None
    for entry in reversed(task.get("history") or []):
        if isinstance(entry, dict) and entry.get("status") == "completed" and _number(entry.get("at")):
            return entry["at"]
    return task["created_at"]


def _ended_at(task):
    """When the task last entered its current status: its last history entry, else its creation."""
    for entry in reversed(task.get("history") or []):
        if isinstance(entry, dict) and entry.get("status") == task["status"] and _number(entry.get("at")):
            return entry["at"]
    return task["created_at"]


def _window_state(window):
    """``pending`` | ``findings`` | ``unread``: what a task held by an unresolved window shows.

    A window with a zero result is resolved as ``passed`` the moment it arrives and holds nothing,
    so ``passed`` is never a state a task in review can show.
    """
    if window.get("result_at") is None:
        return "pending"
    findings = window.get("findings")
    if findings is None:
        return "unread"
    return "findings" if findings > 0 else "unread"


def _review_members(record):
    """``{task key: {"state", "findings", "since"}}`` for every task inside an unresolved window.

    A later window wins over an earlier one for the same task. A task leaves when the agent
    reopens it (``left``), when it is removed unfinished, or when it is no longer in progress or
    completed.
    """
    windows = _windows(record)
    if not windows:
        return {}
    by_key = {t["key"]: t for t in record["tasks"] if isinstance(t, dict)}
    members = {}
    for window in windows:
        if window.get("resolved_at") is not None:
            continue
        if window.get("result_at") is not None and window.get("findings") == 0:
            # A zero result that a record left unresolved (hand-edited, or written mid-update)
            # is a pass: it holds nothing.
            continue
        left = window.get("left") or {}
        for key in window["task_keys"]:
            task = by_key.get(key)
            if key in left or task is None or not _shown(task) or task["status"] not in ("in_progress", "completed"):
                continue
            members[key] = {
                "state": _window_state(window),
                "findings": window.get("findings"),
                "since": window["opened_at"],
            }
    return members


def _review_spans(record, until):
    """``{task key: [(start, end), ...]}`` inside a review window, overlapping windows merged."""
    spans = {}
    for window in _windows(record):
        end_of_window = window.get("resolved_at")
        left = window.get("left") or {}
        for key in window["task_keys"]:
            end = min(x for x in (left.get(key), end_of_window, until) if x is not None)
            if end > window["opened_at"]:
                spans.setdefault(key, []).append((window["opened_at"], end))
    merged = {}
    for key, items in spans.items():
        out = []
        for start, end in sorted(items):
            if out and start <= out[-1][1]:
                if end > out[-1][1]:
                    out[-1] = (out[-1][0], end)
            else:
                out.append((start, end))
        merged[key] = out
    return merged


def _review_seconds(record, until):
    """Seconds each task spent inside a review window, overlapping windows merged."""
    return {key: int(sum(end - start for start, end in items)) for key, items in _review_spans(record, until).items()}


def _resolve(window, now, resolution):
    window["resolved_at"] = now
    window["resolution"] = resolution


def _sweep_reviews(record, now):
    """Apply the fix rule to every recorded-but-unresolved window. Returns True on a change.

    The re-review rule lives in :func:`_finalize`, at the moment a zero result arrives; the fix
    rule depends on task state, so it is evaluated on every record and every view.
    """
    changed = False
    for window in _windows(record):
        if window.get("resolved_at") is not None or window.get("result_at") is None:
            continue
        fix_after = window.get("fix_after")
        if fix_after is None:
            continue
        # A fix task is one created at or after the result. Tasks that existed when the result
        # arrived (`known_keys`, else the window's own members) can never be fixes.
        excluded = set(window.get("known_keys") or window["task_keys"]) | set(window["task_keys"])
        fixes = [t for t in _visible(record) if t["key"] not in excluded and t["created_at"] >= fix_after]
        if fixes and all(_column(t["status"]) == "done" for t in fixes):
            # Never before the last fix finished: a result dated at its (earlier) hand-back would
            # otherwise close the window before work that was still being done when it arrived.
            # `_ended_at`, not `_completed_at`: a cancelled fix also counts as done, and also ends.
            _resolve(window, max([now] + [_ended_at(t) for t in fixes]), "fixed")
            changed = True
    return changed


def _strong(window):
    """True when an agent or a review command (not only a prompt keyword) is in the window."""
    return bool(window.get("strong", window.get("trigger") != "prompt"))


def _finalize(record, window, now, observed=None):
    """Record the result of a window whose sources have all answered."""
    if window.get("markers", 0) == 0:
        findings = None
    elif window.get("unread", 0) and window.get("found", 0) == 0:
        findings = None
    else:
        findings = window.get("found", 0)
    window["findings"] = findings
    window["result_at"] = now
    if findings == 0:
        _resolve(window, now, "passed")
        for earlier in _windows(record):
            if earlier is window:
                break
            if earlier.get("resolved_at") is None:
                _resolve(earlier, now, "fixed")
    elif findings is None and not _strong(window):
        # A keyword-only window that closed unread proves nothing about the work: nothing is held.
        _resolve(window, now, "unread-dismissed")
    else:
        window["fix_after"] = now
        # Tasks that existed when the result arrived. A background report read at a later Stop
        # (`observed`) is dated at its hand-back, so a task created after that is a fix candidate;
        # a live result keeps every task it can see, whatever a parallel hook stamped it.
        backdated = observed is not None and now < observed
        window["known_keys"] = [
            t["key"] for t in record["tasks"] if not backdated or (t.get("created_at") or 0) <= now
        ]
    _sweep_reviews(record, now)


def _reopen(record, before, now):
    """A task the agent moves out of the review leaves every window it is in.

    Out means: a completed task set back to work, or any task leaving ``in_progress`` /
    ``completed`` (to ``pending``, cancelled) or dropped while unfinished.
    """
    for window in _windows(record):
        if window.get("resolved_at") is not None:
            continue
        left = window.setdefault("left", {})
        for task in record["tasks"]:
            was = before.get(task["key"])
            if task["key"] not in window["task_keys"] or task["key"] in left:
                continue
            out = was in ("in_progress", "completed") and (
                task["status"] not in ("in_progress", "completed") or not _shown(task)
            )
            if out or (was == "completed" and task["status"] == "in_progress"):
                left[task["key"]] = now


def _tokens(window):
    """The window's outstanding work as ``(foreground ids, background ids)``, created on demand.

    A record written before tokens were tracked by kind only has ``pending``: each of its
    agent slots becomes a foreground token, which the next ``Stop`` retires as unread.
    """
    if "fg" not in window:
        window["fg"] = ["legacy:{}".format(i) for i in range(max(0, window.get("pending", 0) - (1 if window.get("scan") else 0)))]
        window.setdefault("bg", [])
    window.setdefault("bg", [])
    return window["fg"], window["bg"]


def _sync_pending(window):
    """``pending`` mirrors the tokens: foreground launches + background launches + the scan flag."""
    fg, bg = _tokens(window)
    window["pending"] = len(fg) + len(bg) + (1 if window.get("scan") else 0)


def _synthetic(ident):
    return not ident or ident.startswith(("anon:", "off:", "legacy:"))


def _take_slot(window, ident, kind):
    """Retire the launch ``ident``. True if one was.

    A missing or synthetic id (``anon:``, ``off:``) falls back to the oldest token of ``kind``;
    a real id the window never launched retires nothing.
    """
    fg, bg = _tokens(window)
    for tokens in (fg, bg):
        if ident and ident in tokens:
            tokens.remove(ident)
            return True
    if not _synthetic(ident):
        return False
    tokens = fg if kind == "fg" else bg
    if tokens:
        tokens.pop(0)
        return True
    return False


def _wait_base(window):
    """When the window's wait for its agents started: its last activity, else its opening."""
    last = window.get("last_at")
    return window["opened_at"] if last is None else last


def _expire(rec, now):
    """Settle every window that has waited too long for an agent. Returns every outcome."""
    outcomes = []
    for window in _windows(rec):
        if window.get("resolved_at") is not None or window.get("result_at") is not None:
            continue
        if now - _wait_base(window) <= PENDING_MAX_AGE:
            continue
        fg, bg = _tokens(window)
        window["unread"] = window.get("unread", 0) + len(fg) + len(bg)
        del fg[:], bg[:]
        window["scan"] = False
        outcomes.append(_finish(rec, window, now))
    return outcomes


def _open_window(record):
    for window in reversed(_windows(record)):
        if window.get("resolved_at") is None and window.get("result_at") is None:
            return window
    return None


def _alive(rec, now):
    """Clear ``ended_at``; when the session had ended, this is a resume: remember when."""
    if rec.get("ended_at"):
        rec["resumed_at"] = now
    rec["ended_at"] = None


def _entering_keys(record):
    resolved = [w["resolved_at"] for w in _windows(record) if _number(w.get("resolved_at"))]
    since = max(resolved) if resolved else None
    # With no earlier window, what counts as "completed since the last review" starts at the
    # session's own beginning: its creation, or its latest resume (`resumed_at`), whichever is later.
    floor = max(record.get("created_at") or 0, record.get("resumed_at") or 0)
    keys = []
    hidden = _hidden_keys(record)
    for task in sorted(record["tasks"], key=_task_order):
        if task["removed_at"] is not None or task["key"] in hidden:
            continue
        if task["status"] == "in_progress":
            keys.append(task["key"])
        elif task["status"] == "completed":
            done_at = _completed_at(task)
            if done_at is None:
                continue
            if (done_at > since) if since is not None else (done_at >= floor):
                keys.append(task["key"])
    return keys


def _async_launch(payload):
    """True when the tool response is a background launch ack, not a report."""
    for key in ("tool_response", "tool_output"):
        response = payload.get(key)
        if isinstance(response, dict) and (response.get("isAsync") is True or response.get("status") == "async_launched"):
            return True
    return False


#: Keys of a tool response that echo what the agent was asked, not what it answered.
_ECHO_KEYS = ("prompt", "description", "input", "tool_input", "instructions")


def _output(value):
    """An agent's answer without the fields that echo its input (Claude's ``Agent`` response)."""
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if k not in _ECHO_KEYS}
    return value


def review_call(payload):
    """Normalize a hook payload into a review event, or ``None``.

    Returns ``{"kind": "open"|"result", "session_id", "cwd", "trigger", "source", "markers",
    "agent"}``. ``open`` comes from a review/QA agent spawn or a prompt; ``result`` from a
    finished agent (Claude ``PostToolUse`` on ``Agent``/``Task``, Codex ``wait_agent``, the
    opencode plugin's ``task`` output).
    """
    if not isinstance(payload, dict):
        return None
    session_id = _first_text(payload, "session_id", "sessionID", "sessionId")
    if not session_id:
        return None
    tool_name = payload.get("tool_name") if isinstance(payload.get("tool_name"), str) else ""
    bare = tool_name.split(".")[-1]
    tool = payload.get("tool") if isinstance(payload.get("tool"), str) else ""
    tool_input = _dict(payload.get("tool_input"))
    args = _dict(payload.get("args"))
    event = _text(payload.get("hook_event_name"))
    call = {
        "session_id": session_id,
        "cwd": _first_text(payload, "cwd"),
        "kind": None,
        "trigger": None,
        "source": None,
        "markers": [],
        "agent": False,
        "background": False,
        "tool_use_id": _first_text(payload, "tool_use_id", "toolUseId"),
        "transcript_path": _first_text(payload, "transcript_path"),
    }

    if bare in ("Agent", "Task", "spawn_agent") or tool.lower() == "task":
        name = review_triggers.agent_name(
            _first_text(tool_input, "subagent_type", "agent_type") or _first_text(args, "subagent_type", "agent_type")
        )
        failed = event == "PostToolUseFailure"
        after = failed or event == "PostToolUse" or any(k in payload for k in ("output", "tool_response", "tool_output"))
        background = tool_input.get("run_in_background") is True or args.get("run_in_background") is True
        if after:
            if failed:
                # The launch died before it reported: retire it as unread, whatever its kind.
                if not name:
                    return None
                call.update(kind="result", markers=[], agent=True, source=name)
                return call
            # `spawn_agent` answers with an agent id, not a report; a background agent's
            # launch answers before it has run. Neither can carry a result.
            if bare == "spawn_agent" or background:
                return None
            if _async_launch(payload):
                # A foreground launch the tool then ran in the background (no
                # `run_in_background` in its input): its token moves from fg to bg.
                if name and call["tool_use_id"]:
                    call.update(kind="backgrounded", agent=True, source=name)
                    return call
                return None
            found = review_triggers.markers(
                [_output(payload.get("tool_response")), _output(payload.get("tool_output")), payload.get("output")]
            )
            # Only a known review agent's answer is a result: a `general-purpose` agent that
            # quotes the marker (in a report about it, a diff, a doc) must change nothing. The
            # marker-only shortcut is Codex's `wait_agent`, which does not name its agent.
            if not name:
                return None
            call.update(kind="result", markers=found, agent=True, source=name)
            return call
        if not name:
            return None
        call.update(kind="open", trigger="agent", source=name, background=background)
        return call

    if bare == "wait_agent":
        found = review_triggers.markers(_output(payload.get("tool_response")))
        if not found:
            return None
        # One wait can return several agents' reports: one slot and one marker each. Its own
        # tool-use id names the wait, not a launch, so it retires no launch token by id.
        call.update(kind="result", markers=found, per_marker=True, slot_id=None)
        return call

    prompt = payload.get("prompt")
    if isinstance(prompt, str) and not tool_name and not tool:
        hit = review_triggers.prompt_trigger(prompt)
        if hit is None:
            return None
        call.update(kind="open", trigger=hit[0], source=hit[1])
        return call
    return None


def _review_store(root, payload, now, apply):
    """Run ``apply(record, call, now)`` on the session record under its lock. Never raises."""
    try:
        call = review_call(payload)
        if call is None:
            return None
        project_id = _bound_id(root)
        path = record_path(root, project_id, call["session_id"]) if project_id else None
        if path is None or not path.is_file():
            return None
        now = int(time.time() if now is None else now)
        with _session_lock(path):
            rec = _load(path)
            if rec is None:
                return None
            outcome = apply(rec, call, now)
            if outcome is None:
                return None
            rec["updated_at"] = max(rec["updated_at"], now)
            rec["last_seen_at"] = now
            rec["idle_at"] = None
            _alive(rec, now)
            jsonio.write_json_atomic(path, rec)
        outcome["session"] = call["session_id"]
        return outcome
    except (DevteamError, OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def review_open(root, payload, now=None):
    """Open a review window for the payload's session, or join the one already open.

    Returns ``{"recorded", "session", "window", "joined"}``. Nothing is recorded when the payload
    is not a review trigger, the session has no record, or no task would enter the window.
    """
    def apply(rec, call, at):
        if call["kind"] != "open":
            return None
        _expire(rec, at)
        window = _open_window(rec)
        joined = window is not None
        if window is None:
            keys = _entering_keys(rec)
            if not keys:
                return None
            window = {
                "id": "r{}".format(len(_windows(rec)) + 1),
                "trigger": call["trigger"],
                "source": call["source"],
                "opened_at": at,
                "last_at": at,
                "pending": 0,
                "fg": [],
                "bg": [],
                "scan": False,
                "markers": 0,
                "unread": 0,
                "found": 0,
                "result_at": None,
                "findings": None,
                "resolved_at": None,
                "resolution": None,
                "task_keys": keys,
                "left": {},
                "fix_after": None,
                "strong": False,
            }
            rec.setdefault("reviews", []).append(window)
        fg, bg = _tokens(window)
        if call["trigger"] in ("agent", "command"):
            window["strong"] = True
        elif "strong" not in window:
            window["strong"] = window.get("trigger") != "prompt"
        if call["trigger"] != "agent":
            # One flag, not a counter: every prompt/command in the window shares one final
            # message, and `Stop` retires the flag once.
            window["scan"] = True
        else:
            window["anon"] = window.get("anon", 0) + 1
            ident = call.get("tool_use_id") or "anon:{}".format(window["anon"])
            if ident not in fg and ident not in bg:
                (bg if call.get("background") else fg).append(ident)
        window["last_at"] = at
        _sync_pending(window)
        _remember_transcript(window, call)
        return {"recorded": True, "window": window["id"], "joined": joined}

    result = {"recorded": False, "session": None, "window": None, "joined": False}
    result.update(_review_store(root, payload, now, apply) or {})
    return result


def _remember_transcript(window, call):
    """Start the window's background scan where the transcript ends when the window opens."""
    path = call.get("transcript_path")
    if window.get("tx_offset") is not None or not path or not os.path.isfile(path):
        return
    try:
        window["tx_offset"] = os.path.getsize(path)
        window["tx_path"] = path
    except OSError:
        pass


def _apply_result(rec, call, now, observed=None):
    """Fold one report into the open window: one report retires one slot and carries one marker.

    A report that carries several markers (an orchestrator's summary) counts its LAST one;
    only distinct reports add up. A Codex ``wait_agent`` (``per_marker``) returns several agents'
    reports at once: each marker is a report, so each takes a slot and adds up.
    """
    window = _open_window(rec)
    late = False
    if window is None:
        # A Codex `wait_agent` can return after `Stop` already retired its launch as unread.
        window = _late_window(rec, now) if call.get("per_marker") and call["markers"] else None
        if window is None:
            return None
        late = True
    launch = call.get("tool_use_id")
    if launch:
        if launch in window.get("consumed", []):
            return None
        window.setdefault("consumed", []).append(launch)
    markers = call["markers"]
    slot = False
    if late:
        return _reread(rec, window, markers, now)
    if call.get("per_marker"):
        for _ in markers:
            _take_slot(window, None, "fg")
        window["markers"] = window.get("markers", 0) + len(markers)
        window["found"] = window.get("found", 0) + sum(markers)
        window["last_at"] = now
        return _finish(rec, window, now)
    if markers or call["agent"]:
        slot = _take_slot(window, call.get("slot_id") or launch, call.get("slot_kind", "fg"))
    if markers:
        window["markers"] = window.get("markers", 0) + 1
        window["found"] = window.get("found", 0) + markers[-1]
    elif slot:
        window["unread"] = window.get("unread", 0) + 1
    window["last_at"] = now
    return _finish(rec, window, now, observed)


def _late_window(rec, now):
    """The one window a late report may reattach to, else ``None``.

    The most recent window that is unresolved and closed unread (``findings`` null), and only
    while it is younger than :data:`PENDING_MAX_AGE`; an older window is never reopened.
    """
    for window in reversed(_windows(rec)):
        if window.get("resolved_at") is None and window.get("result_at") is not None and window.get("findings") is None:
            return window if now - window["result_at"] <= PENDING_MAX_AGE else None
    return None


def _reread(rec, window, markers, now):
    """Recompute an unread window from markers that arrived after it closed."""
    window["markers"] = window.get("markers", 0) + len(markers)
    window["found"] = window.get("found", 0) + sum(markers)
    window["unread"] = max(0, window.get("unread", 0) - len(markers))
    window["last_at"] = now
    before = (window.get("result_at"), window.get("fix_after"), window.get("known_keys"))
    _finalize(rec, window, now)
    if window.get("findings") is None:
        window["result_at"], window["fix_after"] = before[0], before[1]
        if before[2] is None:
            window.pop("known_keys", None)
        else:
            window["known_keys"] = before[2]
    return {
        "recorded": True,
        "window": window["id"],
        "result": window.get("findings") is not None,
        "findings": window.get("findings"),
        "resolved": window.get("resolved_at") is not None,
        "_all_done_now": _all_done(rec, _review_members(rec)),
    }


def _apply_backgrounded(rec, call, now):
    """A foreground launch turned out to run in the background: move its token fg -> bg.

    Stop then leaves it alone and its later transcript hand-back resolves it by id.
    """
    window = _open_window(rec)
    if window is None:
        return None
    fg, bg = _tokens(window)
    launch = call["tool_use_id"]
    if launch not in fg:
        return None
    fg.remove(launch)
    bg.append(launch)
    window["last_at"] = now
    _sync_pending(window)
    done = _all_done(rec, _review_members(rec))
    return {
        "recorded": True, "window": window["id"], "result": False, "findings": None,
        "resolved": False, "all_done": done, "became_all_done": False,
    }


def _finish(rec, window, now, observed=None):
    _sync_pending(window)
    complete = window["pending"] <= 0
    if complete:
        window["pending"] = 0
        _finalize(rec, window, now, observed)
    return {
        "recorded": True,
        "window": window["id"],
        "result": complete,
        "findings": window.get("findings") if complete else None,
        "resolved": window.get("resolved_at") is not None,
        "_all_done_now": _all_done(rec, _review_members(rec)),
    }


def review_result(root, payload, now=None):
    """Fold a finished review agent's output into the open window.

    Returns ``{"recorded", "session", "window", "result", "findings", "resolved",
    "all_done", "became_all_done"}``; ``result`` is true when this call completed the window.
    """
    def apply(rec, call, at):
        if call["kind"] == "backgrounded":
            return _apply_backgrounded(rec, call, at)
        if call["kind"] != "result":
            return None
        was_done = _all_done(rec, _review_members(rec))
        outcome = _apply_result(rec, call, at)
        if outcome is None:
            return None
        done = outcome.pop("_all_done_now")
        outcome.update(all_done=done, became_all_done=done and not was_done and _cleanly_done(rec, _review_members(rec)))
        return outcome

    result = {
        "recorded": False, "session": None, "window": None, "result": False,
        "findings": None, "resolved": False, "all_done": False, "became_all_done": False,
    }
    result.update(_review_store(root, payload, now, apply) or {})
    return result


# ── the Stop scan: a finished turn settles what it can ────────────────────────


def _content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
        )
    return ""


TRANSCRIPT_TAIL = 512 * 1024


def last_assistant_text(payload):
    """The final assistant message of the turn that just ended, or ``""``.

    Codex and the opencode plugin hand it over as ``last_assistant_message``; Claude Code's
    ``Stop`` gives a ``transcript_path`` (JSONL) whose last text-bearing assistant entry, after
    the last real user prompt, is the final text.
    """
    direct = payload.get("last_assistant_message")
    if isinstance(direct, str) and direct:
        return direct
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not path or not os.path.isfile(path):
        return ""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as handle:
            handle.seek(max(0, size - TRANSCRIPT_TAIL))
            lines = handle.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
        role = message.get("role") or entry.get("type")
        if role == "assistant":
            text = _content_text(message.get("content", entry.get("content")))
            if text.strip():
                return text
        elif role == "user":
            content = message.get("content", entry.get("content"))
            if isinstance(content, str) or (
                isinstance(content, list)
                and any(isinstance(b, dict) and b.get("type") != "tool_result" for b in content)
            ):
                return ""
    return ""


#: Bytes of transcript read per `Stop` for background hand-backs; the rest waits for the next one.
BACKGROUND_SCAN_BYTES = 2 * 1024 * 1024
#: One Stop reads this much of the transcript at most (in chunks of ``BACKGROUND_SCAN_BYTES``), so a
#: long gap is caught up in one go and a runaway transcript still cannot stall the hook.
BACKGROUND_SCAN_CAP = 64 * 1024 * 1024

_TAG_RE = {
    name: re.compile(r"<{0}>(.*?)</{0}>".format(name), re.DOTALL)
    for name in ("tool-use-id", "task-id", "status")
}
#: The agent's own answer: from the first ``<result>`` to the last ``</result>``. A notification
#: with no such section (a Bash background task reports a ``<summary>``) carries no report.
_RESULT_RE = re.compile(r"<result>(.*)</result>", re.DOTALL)


def _result_text(section):
    """The agent's answer as it wrote it. Claude Code HTML-escapes the ``<result>`` of a
    notification, so its closing ``<!-- review-result: findings=N -->`` arrives as
    ``&lt;!-- … --&gt;``; unescaped here, it is read by the same last-line rule as any report."""
    return html.unescape(section)


#: Task ids of the queue entries seen, kept per window so a later user entry can mirror one.
QUEUE_IDS_KEPT = 64


def _notification_ids(text):
    found = {name: (rx.search(text).group(1).strip() if rx.search(text) else "") for name, rx in _TAG_RE.items()}
    return found["tool-use-id"], found["task-id"]


def _notification_status(text):
    """The hand-back's own ``<status>`` word, lowercased, else ``""``."""
    found = _TAG_RE["status"].search(text)
    return found.group(1).strip().lower() if found else ""


def _entry_text(entry, queued=()):
    """Text of a transcript entry that is a harness-injected task notification, else ``""``.

    Two forms count: a ``queue-operation`` entry (top-level ``content``), and the ``user``-role
    entry that mirrors a queue entry with the same task id. A user entry that stands alone (typed
    or pasted by the user, a tool output, a file quoted back) is not a hand-back, and neither is a
    notification that does not open the entry's text. An assistant message that merely quotes the
    tag is never one.
    """
    kind = entry.get("type")
    message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
    if kind == "queue-operation":
        content = entry.get("content")
        mirrored = True
    elif kind == "user" or message.get("role") == "user":
        content = message.get("content", entry.get("content"))
        if not isinstance(content, str):
            content = _content_text(content)
        mirrored = False
    else:
        return ""
    if not isinstance(content, str) or not content.lstrip().startswith("<task-notification>"):
        return ""
    if not mirrored:
        use_id, task_id = _notification_ids(content)
        if not ((task_id and task_id in queued) or (use_id and use_id in queued)):
            return ""
    return content


def _entry_epoch(entry):
    stamp = entry.get("timestamp")
    if isinstance(stamp, str):
        try:
            return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def _background_reports(window, path):
    """New background hand-backs in the transcript since the window's offset.

    Yields ``{"id", "markers", "status"}`` per notification (``status`` is the hand-back's own
    ``<status>``, else ``""``), and advances ``window["tx_offset"]`` past the complete lines read,
    chunk by chunk up to ``BACKGROUND_SCAN_CAP``. The same notification appears as a queue entry
    and as a user entry, and a resumed agent may notify twice: the caller dedupes on ``id``. A
    notification with no ``tool-use-id`` and no ``task-id`` names nothing and is dropped. A line
    longer than the read cap is skipped, not waited for: the scan resumes at the next line.
    """
    reports = []
    for _ in range(max(1, BACKGROUND_SCAN_CAP // BACKGROUND_SCAN_BYTES)):
        found, more = _scan_chunk(window, path)
        reports.extend(found)
        if not more:
            break
    return reports


def _scan_chunk(window, path):
    """One read of at most ``BACKGROUND_SCAN_BYTES``: ``(reports, more)``, ``more`` when text remains."""
    try:
        size = os.path.getsize(path)
        offset = window.get("tx_offset")
        if window.get("tx_path") is None:
            offset = max(0, size - BACKGROUND_SCAN_BYTES)
            window["tx_path"] = path
        elif window["tx_path"] != path or not isinstance(offset, int) or offset > size:
            # A compacted or rotated transcript: what is there now is not ours to replay from
            # byte 0. Continue from its end; ids already consumed stay consumed.
            offset = size
            window["tx_path"] = path
        with open(path, "rb") as handle:
            handle.seek(offset)
            chunk = handle.read(BACKGROUND_SCAN_BYTES)
    except OSError:
        return [], False
    end = chunk.rfind(b"\n") + 1
    if end == 0 and len(chunk) < BACKGROUND_SCAN_BYTES:
        window["tx_offset"] = offset
        return [], False
    window["tx_offset"] = offset + (end or len(chunk))
    more = window["tx_offset"] < size
    queued = window.setdefault("queue_ids", [])
    reports = []
    for line in chunk[:end].decode("utf-8", "replace").splitlines():
        if "<task-notification>" not in line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        text = _entry_text(entry, queued)
        if not text:
            continue
        at = _entry_epoch(entry)
        if at is None or int(at) < window["opened_at"]:
            continue
        use_id, task_id = _notification_ids(text)
        if entry.get("type") == "queue-operation":
            for ident in (task_id, use_id):
                if ident and ident not in queued:
                    queued.append(ident)
            del queued[:-QUEUE_IDS_KEPT]
        if not (use_id or task_id):
            continue
        section = _RESULT_RE.search(text)
        reports.append({
            "id": use_id or task_id,
            "at": int(at),
            "markers": review_triggers.markers(_result_text(section.group(1)))[-1:] if section else [],
            "status": _notification_status(text),
        })
    return reports, more


def _scan_background(rec, payload, now):
    """Fold background review agents' hand-backs from the transcript into the open window.

    Only a hand-back whose id is a background token this window launched counts: a notification
    from any other task (a Bash job, another agent) never touches it, whatever it quotes.
    Returns every outcome that completed a window.
    """
    path = payload.get("transcript_path")
    if not isinstance(path, str) or not path or not os.path.isfile(path):
        return []
    outcomes = []
    window = _open_window(rec)
    if window is None or window["pending"] <= 0:
        return []
    for report in _background_reports(window, path):
        window = _open_window(rec)
        if window is None:
            break
        if report["id"] in window.get("consumed", []) or report["id"] not in _tokens(window)[1]:
            continue
        base = _wait_base(window)
        if report["at"] - base > PENDING_MAX_AGE:
            # Handed back after the window's wait ran out: `_expire` settles it as unread, the
            # same as if this Stop had come in time.
            continue
        window.setdefault("consumed", []).append(report["id"])
        # The result counts from when it was handed back, not from this Stop: a turn that sat on
        # a question for hours must not make the fixes started meanwhile look older than it. Never
        # before the window's last activity, so `last_at` only moves forward.
        at = max(base, min(now, report["at"]))
        applied = _apply_result(
            rec, {"markers": report["markers"], "agent": True, "slot_id": report["id"], "slot_kind": "bg"}, at, now
        )
        if applied is not None and applied["result"]:
            outcomes.append(applied)
    return outcomes


#: A hand-back ``<status>`` that means the background agent did not finish its work.
_HANDBACK_FAILED = ("failed", "killed", "error")


def _scan_agent_tasks(rec, payload, now):
    """Complete the background agent tasks whose hand-back is in the transcript. True when it looked.

    A hand-back counts only for a task this record launched in the background, matched by the
    spawn's id: a notification from any other task (a Bash job) never touches one. The cursor
    advances every time, so a mutated record is always written.
    """
    pending = {
        t["id"]: t for t in rec["tasks"]
        if _is_agent(t) and t.get("background") and t["status"] == "in_progress" and t.get("id")
    }
    path = payload.get("transcript_path")
    if not pending or not isinstance(path, str) or not path or not os.path.isfile(path):
        return False
    scan = _agent_scan(rec, path, min(t["created_at"] for t in pending.values()))
    for report in _background_reports(scan, path):
        task = pending.get(report["id"])
        if task is not None and task["status"] == "in_progress":
            # Ended when it handed back, not at this Stop, which may come hours later; never before
            # its own last event, so the history stays in order.
            last = task["history"][-1]["at"] if task.get("history") else task["created_at"]
            at = max(last, task["created_at"], min(now, report["at"]))
            if report["status"] in _HANDBACK_FAILED:
                _end_agent(task, "cancelled", True, at)
            else:
                _end_agent(task, "completed", False, at)
    return True


def _interrupt_agents(rec, now):
    """Settle the foreground agent tasks a finished turn left open as cancelled and ``interrupted``.

    A turn that ended cannot have a foreground agent running in front of it (the call was
    interrupted, or its end never reached a hook). A background agent survives, and so does a
    Codex agent whose spawn answered with an id: its ``wait_agent`` may come in a later turn.
    """
    changed = False
    for task in rec["tasks"]:
        if (
            _is_agent(task) and task["status"] == "in_progress"
            and not task.get("background") and not task.get("agent_ref")
        ):
            task["interrupted"] = True
            _push(task, "cancelled", now)
            changed = True
    return changed


def _retire_at_stop(rec, payload, now):
    """What a finished turn settles in every open window. Returns every outcome.

    * the prompt/command scan flag is read against the final message and cleared;
    * foreground agent launches still outstanding are retired as unread — a turn that ended
      cannot have an agent still running in front of it, so its result was lost (a failed
      launch, an interrupted turn, a wait that never returned it);
    * background launches survive: their hand-back arrives in a later turn.
    """
    outcomes = []
    text = None
    for window in _windows(rec):
        if window.get("resolved_at") is not None or window.get("result_at") is not None:
            continue
        fg, _ = _tokens(window)
        if not fg and not window.get("scan"):
            continue
        if window.get("scan"):
            if text is None:
                text = review_triggers.markers(last_assistant_text(payload))[-1:]
            if window.get("markers", 0) == 0 and text:
                window["markers"] = 1
                window["found"] = window.get("found", 0) + text[0]
            window["scan"] = False
        if fg:
            window["unread"] = window.get("unread", 0) + len(fg)
            del fg[:]
        outcomes.append(_finish(rec, window, now))
    return outcomes


def _git_location(cwd):
    """``(branch, worktree)`` for a working directory, from one ``git`` call.

    ``worktree`` is ``{"path", "branch"}`` when ``cwd`` is inside a linked worktree (its git dir is
    not the repository's common dir), else ``None``. ``path`` is the worktree's root relative to
    the main checkout when it lives under it (``.worktrees/feat/x``), else absolute.
    """
    if not cwd or not os.path.isdir(cwd):
        return None, None
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD", "--git-dir", "--git-common-dir", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    lines = result.stdout.decode("utf-8", "replace").splitlines()
    if result.returncode != 0 or len(lines) < 4:
        return None, None
    branch, git_dir, common_dir, toplevel = (line.strip() for line in lines[:4])
    branch = branch or None
    # `--git-dir`/`--git-common-dir` are relative to `cwd` outside a worktree.
    git_dir = os.path.realpath(os.path.join(cwd, git_dir))
    common_dir = os.path.realpath(os.path.join(cwd, common_dir))
    if git_dir == common_dir or not toplevel:
        return branch, None
    main = os.path.dirname(common_dir)
    top = os.path.realpath(toplevel)
    path = os.path.relpath(top, main) if top.startswith(main + os.sep) else top
    return branch, {"path": path.replace(os.sep, "/"), "branch": branch}


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
        branch, worktree = _git_location(call["cwd"] or (stored or {}).get("cwd"))
        with _session_lock(path):
            rec = _load(path)
            if rec is None:
                if path.exists():
                    # Present but unreadable, or a schema this build does not know: never
                    # overwrite what we cannot read.
                    return result
                if call["op"][0] != "agent_spawn" and call["op"][0].startswith("agent_"):
                    # A result for a spawn this session never recorded: nothing to settle, no record to start.
                    return result
                rec = _new_record(call, project_id, now)
            open_before = _open_keys(rec, _review_members(rec))
            before = {t["key"]: t["status"] for t in rec["tasks"]}
            changed = _apply(rec, call, now)
            if changed is False:
                # An agent event that matched no task (a replayed spawn, a result nobody launched):
                # the record is not touched, so a stray call cannot keep a session looking alive.
                return result
            _reopen(rec, before, now)
            # Where a task was started is fixed at its creation: the session may `cd` on later.
            for task in rec["tasks"]:
                if task["key"] not in before and worktree is not None:
                    task["worktree"] = dict(worktree)
            _sweep_reviews(rec, now)
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
            _alive(rec, now)
            members = _review_members(rec)
            done = _all_done(rec, members)
            # Dropping an unfinished task is abandonment, not completion: the transition counts
            # only when a task that was open is now actually completed or cancelled.
            finished = any(
                t["key"] in open_before and _shown(t) and _task_column(t, members) == "done" for t in rec["tasks"]
            )
            clean = _cleanly_done(rec, members)
            # An agent's end is raised at `Stop` (`mark`), never mid-turn: more agents may follow
            # it. The debt is kept on the record for that Stop to pay.
            mid_turn = call["op"][0].startswith("agent_")
            if not done:
                rec["done_pending"] = False
            elif finished and mid_turn and clean:
                rec["done_pending"] = True
            jsonio.write_json_atomic(path, rec)
        result.update(
            recorded=True, session=call["session_id"], all_done=done,
            became_all_done=done and finished and not mid_turn and clean,
        )
    except (DevteamError, OSError, ValueError, TypeError, KeyError, AttributeError):
        result["recorded"] = False
    return result


def mark(root, payload, state, now=None):
    """Mark a session ``idle`` or ``ended``. No-op when it has no record. Never raises."""
    result = {
        "marked": False, "open": 0,
        "review_result": False, "review_window": None, "review_findings": None,
        "review_results": [], "became_all_done": False,
    }
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
            done = []
            if state == "idle":
                rec["idle_at"] = now
                _alive(rec, now)
                was_done = _all_done(rec, _review_members(rec)) and not rec.get("done_pending")
                # Hand-backs first: one that arrived within the window's wait counts even when this
                # Stop comes hours later (the turn sat on a question), and only then does the wait
                # expire what is still missing.
                for outcomes in (_scan_background(rec, payload, now), _expire(rec, now), _retire_at_stop(rec, payload, now)):
                    done.extend(o for o in outcomes if o["result"])
                _scan_agent_tasks(rec, payload, now)
                _interrupt_agents(rec, now)
                done_now = _cleanly_done(rec, _review_members(rec))
                rec["done_pending"] = False
            else:
                rec["ended_at"] = now
            jsonio.write_json_atomic(path, rec)
        result.update(marked=True, open=_open_count(rec))
        if state == "idle" and done_now and not was_done:
            # A background agent's hand-back can finish the last task with no review window involved.
            result["became_all_done"] = True
        if done:
            # One entry per window that closed in this Stop; the flat keys mirror the last one.
            result.update(
                review_result=True,
                review_window=done[-1]["window"],
                review_findings=done[-1]["findings"],
                review_results=[{"window": o["window"], "findings": o["findings"]} for o in done],
                became_all_done=done_now and not was_done,
            )
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


def _durations(history, until, review_spans=()):
    """Seconds per provider status. Time inside a review window belongs to ``in_review`` only,
    so the columns partition the task's life instead of overlapping."""
    totals = {"pending": 0, "in_progress": 0, "completed": 0}
    for index, entry in enumerate(history):
        end = history[index + 1]["at"] if index + 1 < len(history) else until
        inside = sum(max(0, min(end, b) - max(entry["at"], a)) for a, b in review_spans)
        seconds = max(0, int(end - entry["at"] - inside))
        totals[entry["status"]] = totals.get(entry["status"], 0) + seconds
    return totals


def _worktree_view(value):
    """A stored worktree as the JSON contract shows it; anything malformed is null."""
    if not isinstance(value, dict) or not isinstance(value.get("path"), str) or not value["path"]:
        return None
    branch = value.get("branch")
    return {"path": value["path"], "branch": branch if isinstance(branch, str) and branch else None}


def _task_view(task, session_status, now, stale_after, until, member=None, review_spans=()):
    history = [h for h in task.get("history", []) if isinstance(h, dict) and _number(h.get("at"))]
    if not history:
        history = [{"status": task["status"], "at": task["created_at"]}]
    since = history[-1]["at"]
    column = "in_review" if member else _column(task["status"])
    completed_at = None
    if task["status"] == "completed":
        completed_at = since
    return {
        "key": task["key"],
        "content": task["content"],
        "owner": task["owner"],
        "agent_type": task.get("agent_type"),
        "kind": "agent" if _is_agent(task) else "todo",
        "failed": bool(task.get("failed")),
        "interrupted": bool(task.get("interrupted")),
        # Additive: the linked worktree the task was started in (`{"path", "branch"}`), else null.
        "worktree": _worktree_view(task.get("worktree")),
        "status": task["status"],
        "column": column,
        "created_at": task["created_at"],
        "status_since": since,
        "completed_at": completed_at,
        "durations": dict(
            _durations(history, until, review_spans),
            in_review=int(sum(end - start for start, end in review_spans)),
        ),
        "review": dict(member) if member else None,
        "stale": task["status"] == "in_progress"
        and not member
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
    if not isinstance(session_id, str) or session_id.startswith("-") or not _SAFE_KEY.match(session_id):
        return None
    where = cwd if isinstance(cwd, str) and cwd and os.path.isdir(cwd) else root
    return "cd {} && {} {}".format(shlex.quote(str(where)), base, shlex.quote(session_id))


def _counts(views):
    counts = {"todo": 0, "in_progress": 0, "done": 0, "in_review": 0}
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
    # The fix rule depends on task state, so it is re-evaluated here on a copy; the stored
    # record only ever changes through a hook call.
    rec = copy.deepcopy(rec)
    _expire(rec, now)
    _sweep_reviews(rec, rec.get("updated_at") or now)
    members = _review_members(rec)
    spans = _review_spans(rec, until)
    shown = {t["key"] for t in _visible(rec)}
    views = [
        _task_view(task, status, now, stale_after, until, members.get(task["key"]), spans.get(task["key"], ()))
        for task in sorted(rec["tasks"], key=_task_order)
        if isinstance(task, dict) and task["key"] in shown
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
        "with_findings": sum(1 for t in all_tasks if (t["review"] or {}).get("state") == "findings"),
        "stale": sum(1 for t in all_tasks if t["stale"]),
        "abandoned": sum(1 for t in all_tasks if t["abandoned"]),
        "last_activity_at": sessions[0]["last_activity_at"],
        # When this derived view was computed: the app renders live figures as
        # `durations[current] + (now - as_of)`.
        "as_of": now,
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
        # `as_of` moves on every computation; it is not a change.
        serialized = json.dumps({k: v for k, v in view.items() if k != "as_of"}, sort_keys=True) if view is not None else None
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
