"""The canvas graph: the task board joined with the execution trace, per session.

See ADR-0015 (CLI-derived reads), ADR-0041 (the trace) and ADR-0063 (this graph).

``devteam tasks graph --project <id> --json`` is the read the desktop app's canvas draws from. It is
derived here, in the CLI, from two read-only sources and writes nothing:

* the board record of each session (``tasks.session_view``) — titles, branches, PR marks, task text,
  worktrees and todos;
* the session's trace (``trace.build``) — every agent span, its nesting, model, duration, tokens
  and last-output excerpt (read back through the trace's own rule, never a second one here).

The two are joined on the spawn id: a board agent task's ``id`` is the trace span's ``id`` (the
provider's ``tool_use_id`` / ``callID``). The board view does not carry that id, so it is read from
the record here; the ``tasks list|watch`` shape is untouched.

Shape (schema 1, additive-only per ADR-0014): ``{schema, project_id, as_of, truncated, notices,
groups, nodes, edges}``; every array is sorted by ``(started_at | at, id)`` (edges by id), so two
reads of the same state print the same document. Every string shown to the user passes the board's
redaction and the trace's name rules again: both files are hand-editable JSON, read back as data.
"""

from __future__ import annotations

import os
import time

from . import tasks, trace

SCHEMA = 1
#: Most characters of a task text shown on a node, as the board's direct-work excerpt.
DESCRIPTION_MAX = 100
#: Most characters of a session's branch name shown on its frame.
BRANCH_MAX = 200
#: The trace's span statuses as a node shows them: a cancelled agent never finished its work.
_STATUS = {"running": "running", "completed": "completed", "failed": "failed",
           "interrupted": "interrupted", "cancelled": "interrupted"}
_SPAN_KINDS = ("agent", "review", "builtin")
#: The command a turn opens with that makes the main session the orchestrator (ADR-0062).
ORCHESTRATE = "orchestrate"


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _int(value):
    return int(value) if _number(value) else None


def _clean(value, limit):
    """``value`` as one redacted line of at most ``limit`` characters, else ``None``."""
    return tasks.clean_line(value, limit)


def _sort_key(item, fallback, *fields):
    """``(time, id)``; an item with no time of its own sorts at ``fallback`` (its session's start)."""
    for field in fields:
        if _number(item.get(field)):
            return (item[field], item["id"])
    return (fallback.get(item["id"], 0), item["id"])


def _edge(src, dst, kind="spawn"):
    return {"id": "e:{}>{}".format(src, dst), "from": src, "to": dst, "kind": kind}


def _todo(view):
    content = _clean(view.get("content"), DESCRIPTION_MAX)
    if content is None:
        return None
    return {"key": view["key"], "content": content, "status": view.get("status")}


def _node(**fields):
    node = {
        "id": None, "kind": None, "group": None, "label": None, "agent": None, "description": None,
        "persona": None, "persona_source": None, "status": None, "model": None,
        "started_at": None, "ended_at": None, "duration_s": 0, "tokens": 0, "subtree_tokens": 0,
        "usage_complete": False, "findings": None, "background": False, "last_output": None,
        "task_key": None, "worktree": None, "pr": None, "todos": [],
        "session_id": None, "record_id": None, "spawn_id": None,
    }
    node.update(fields)
    return node


def _group(**fields):
    group = {
        "id": None, "kind": None, "parent": None, "label": None, "provider": None, "status": None,
        "branch": None, "command": None, "at": None, "started_at": None, "ended_at": None,
        "prs": [], "tokens": 0, "usage_complete": False, "session_id": None,
    }
    group.update(fields)
    return group


def _board_status(view):
    if view.get("failed"):
        return "failed"
    if view.get("interrupted") or view.get("status") == "cancelled":
        return "interrupted"
    return {"in_progress": "running", "completed": "completed"}.get(view.get("status"))


# ── sources ──


class _Session:
    """One top session: its board record(s) and its trace, before they are drawn."""

    def __init__(self, session_id):
        self.session_id = session_id
        self.record = None          # the top session's own board record, if any
        self.view = None            # its board view (tasks.session_view), if any
        self.task_views = []        # board task views of the top session and its child sessions
        self.spawn_ids = {}         # board task key -> spawn id, per record (keys are per record)
        self.capped = False
        self.trace = None


def _record_tasks(rec):
    """``key -> spawn id`` of the record's agent tasks (the id the board view does not show)."""
    found = {}
    for task in rec.get("tasks") or []:
        if isinstance(task, dict) and task.get("kind") == "agent" and isinstance(task.get("key"), str):
            ident = trace.safe_name(task.get("id"))
            if ident:
                found[task["key"]] = ident
    return found


def _read_aliases(root, project_id):
    """The child-session -> top-session map, read once per build (``{}`` when absent or unreadable)."""
    found = trace.read_aliases(trace.aliases_path(root, project_id)) or {}
    return {k: v for k, v in found.items() if isinstance(k, str) and isinstance(v, str) and v}


def _skippable(path, session, now, since):
    """Whether ``--since`` drops the session a trace file stands for whatever the file says.

    Decided without reading the file: a trace last written before ``since``, and longer ago than the
    ended-after window, has an ``updated_at`` that is both, so the session is ended and idle before
    ``since`` unless its board record says otherwise (``build``'s own rule is applied to that side).
    """
    if since is None:
        return False
    try:
        mtime = os.stat(str(path)).st_mtime
    except OSError:
        return False
    if mtime >= since or now - mtime <= tasks.DEFAULT_ENDED_AFTER:
        return False
    if session is None or (session.view is None and session.record is None):
        return True
    return _status(session, now) == "ended" and _activity(session) < since


def _sessions(root, project_id, now, since=None):
    """Every top session of the project with a board record or a trace, keyed by session id."""
    sessions = {}
    aliases = _read_aliases(root, project_id)
    records = tasks.project_records(root, project_id)
    context = tasks.view_context(root, records) if records else None
    for rec in records:
        top = aliases.get(rec["session_id"])
        aliased = top is not None
        top = top or rec["session_id"]
        try:
            view = tasks.session_view(rec, root, now, context=context)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        session = sessions.setdefault(top, _Session(top))
        if not aliased:
            session.record, session.view = rec, view
        if len(rec.get("tasks") or []) >= tasks.MAX_TASKS:
            session.capped = True
        if view is not None:
            ids = _record_tasks(rec)
            # Keys repeat across a top session and its child sessions: the spawn id and the record
            # a task came from are carried along, so neither the join nor a fallback id collides.
            session.task_views.extend(
                dict(t, _spawn_id=ids.get(t["key"]), _record=rec["session_id"]) for t in view["tasks"])
    directory = trace.trace_dir(root, project_id)
    by_path = {}
    for sid, session in sessions.items():
        path = trace.trace_path(root, project_id, sid)
        if path is not None:
            by_path[path] = session
    try:
        names = sorted(
            n for n in os.listdir(str(directory)) if n.endswith(".json") and not n.startswith("."))
    except OSError:
        names = []
    for name in names:
        if name == "aliases.json":
            continue
        path = directory / name
        if _skippable(path, by_path.get(path), now, since):
            continue  # an ended session outside the window: its trace is never loaded
        data = trace.load(path)
        sid = data.get("session_id") if isinstance(data, dict) else None
        if not isinstance(sid, str) or not sid:
            continue
        if trace.trace_path(root, project_id, sid) != path:
            continue  # a file whose content names another session: never trusted to stand for it
        sessions.setdefault(sid, _Session(sid)).trace = data
    return sessions


def _activity(session):
    times = []
    if session.view is not None:
        times.append(session.view.get("last_activity_at"))
    if session.record is not None:
        times.extend((session.record.get("updated_at"), session.record.get("last_seen_at")))
    if session.trace is not None:
        times.append(session.trace.get("updated_at"))
    return max((t for t in times if _number(t)), default=0)


def _status(session, now):
    if session.view is not None:
        return session.view["status"]
    if session.record is not None:
        return tasks.session_status(session.record, now, tasks.DEFAULT_ENDED_AFTER)
    updated = session.trace.get("updated_at") if session.trace else None
    return "active" if _number(updated) and now - updated <= tasks.DEFAULT_ENDED_AFTER else "ended"


# ── drawing ──


class _Canvas:
    def __init__(self):
        self.groups, self.nodes, self.edges = [], [], []
        self.notices = []
        self.truncated = False
        self.fallback = {}  # item id -> the session start an untimed group or node sorts at
        self._ids = set()

    def add_group(self, group):
        if group["id"] in self._ids:
            return False
        self._ids.add(group["id"])
        self.groups.append(group)
        return True

    def add_node(self, node):
        if node["id"] in self._ids:
            return False
        self._ids.add(node["id"])
        self.nodes.append(node)
        return True


def _span_node(sid, built, board, group, todos_by_owner):
    view = board.get(built["id"])
    agent_id = built.get("agent_id")
    findings = built["findings"]
    return _node(
        id="span:{}:{}".format(sid, built["id"]),
        kind=built["kind"] or "agent",
        group=group,
        label=built["agent"],
        agent=built["agent"],
        description=_clean(view.get("content"), DESCRIPTION_MAX) if view else None,
        status=_STATUS.get(built["status"]),
        model=built["model"],
        started_at=_int(built["started_at"]),
        ended_at=_int(built["ended_at"]),
        duration_s=built["duration_s"],
        tokens=built["tokens"],
        subtree_tokens=built["subtree_tokens"],
        usage_complete=built["usage_complete"],
        findings=findings if _number(findings) and isinstance(findings, int) else None,
        background=built["background"],
        last_output=built["last_output"],
        task_key=view["key"] if view else None,
        worktree=view.get("worktree") if view else None,
        pr=view.get("pr") if view else None,
        todos=list(todos_by_owner.get(agent_id, ())) if agent_id else [],
        session_id=sid, spawn_id=built["id"],
        record_id=view.get("_record") if view else None,
    )


def _board_node(sid, view, group, now):
    ended = view.get("completed_at") if view.get("status") == "completed" else None
    if view.get("status") == "cancelled":
        ended = view.get("status_since")
    start = _int(view.get("created_at"))
    end = _int(ended)
    agent = trace.safe_name(view.get("agent_type"))
    # A task with no spawn id is named by the record it came from too: keys repeat across a top
    # session and its child sessions.
    ident = view.get("_spawn_id") or "{}:{}".format(view.get("_record") or sid, view["key"])
    return _node(
        id="span:{}:{}".format(sid, ident),
        kind="agent", group=group, label=agent, agent=agent,
        description=_clean(view.get("content"), DESCRIPTION_MAX),
        status=_board_status(view),
        started_at=start, ended_at=end,
        duration_s=max(0, (end if end is not None else int(now)) - start) if start is not None else 0,
        task_key=view["key"], worktree=view.get("worktree"), pr=view.get("pr"),
        session_id=sid, spawn_id=view.get("_spawn_id"), record_id=view.get("_record") or sid,
    )


def _draw(canvas, session, now):
    sid = session.session_id
    rec, view = session.record or {}, session.view or {}
    built = None
    if session.trace is not None:
        try:
            built = trace.build(session.trace, now)
        except (TypeError, ValueError, KeyError, AttributeError, RecursionError):
            # A hand-edited trace the tree cannot be built from: the board alone is drawn.
            canvas.notices.append("bad_trace:" + sid)
    turns = built["turns"] if built else []
    totals = built["totals"] if built else {"tokens": 0, "usage_complete": False}
    session_group = "session:" + sid
    provider = (built or {}).get("provider") or rec.get("provider")
    started = _int(rec.get("created_at")) or _int((session.trace or {}).get("created_at"))
    canvas.add_group(_group(
        id=session_group, kind="session",
        label=_clean(view.get("title"), DESCRIPTION_MAX) or sid,
        provider=provider if provider in tasks.PROVIDERS else None,
        status=_status(session, now),
        branch=_clean(rec.get("branch"), BRANCH_MAX),
        at=started, started_at=started, ended_at=_int(rec.get("ended_at")),
        prs=list(view.get("prs") or []),
        tokens=totals["tokens"], usage_complete=totals["usage_complete"], session_id=sid,
    ))

    agents = [t for t in session.task_views if t.get("kind") == "agent"]
    board = {t["_spawn_id"]: t for t in agents if t.get("_spawn_id")}
    todos_by_owner = {}
    for task in session.task_views:
        if task.get("kind") == "todo":
            item = _todo(task)
            if item is not None:
                todos_by_owner.setdefault(task.get("owner"), []).append(item)

    orchestrated = any(t.get("command") == ORCHESTRATE for t in turns)
    status = _status(session, now)
    main_id = "main:" + sid
    canvas.add_node(_node(
        id=main_id, kind="main", group=session_group,
        label="Orchestrator" if orchestrated else "Main session",
        persona="orchestrator" if orchestrated else None,
        persona_source="command" if orchestrated else None,
        status={"active": "running", "idle": "idle", "ended": "completed"}.get(status),
        started_at=started, ended_at=_int(rec.get("ended_at")),
        tokens=0, subtree_tokens=totals["tokens"], usage_complete=totals["usage_complete"],
        todos=list(todos_by_owner.get(tasks.MAIN_OWNER, ())),
        session_id=sid, record_id=sid if session.record is not None else None,
    ))

    if built is not None:
        spans = session.trace.get("spans")
        # Conservative: capture stops adding spans at MAX_SPANS, so a trace holding that many may
        # have dropped more. A trace at exactly the cap is reported truncated though nothing was.
        if isinstance(spans, list) and sum(isinstance(s, dict) for s in spans) >= trace.MAX_SPANS:
            canvas.truncated = True
    drawn = set()
    budget = [trace.MAX_SPANS]

    def walk(node, parent, group, seen):
        if id(node) in seen:
            return  # a cycle in a hand-edited tree: never walked twice
        seen.add(id(node))
        here = parent
        if node["id"] is not None:
            if budget[0] <= 0:
                canvas.truncated = True
                return
            drawn_node = _span_node(sid, node, board, group, todos_by_owner)
            canvas.fallback[drawn_node["id"]] = started or 0
            if canvas.add_node(drawn_node):
                budget[0] -= 1
                drawn.add(node["id"])
                canvas.edges.append(_edge(parent, drawn_node["id"]))
                here = drawn_node["id"]
        for child in node["children"]:
            walk(child, here, group, seen)

    seen = set()
    for turn in turns:
        at = turn["turn_at"] if _number(turn["turn_at"]) else None
        turn_group = "turn:{}:{}".format(sid, int(at) if at is not None else "none")
        command = turn["command"]
        canvas.fallback[turn_group] = started or 0
        canvas.add_group(_group(
            id=turn_group, kind="turn", parent=session_group,
            label="/devteam:{}".format(command) if command else "Prompt",
            command=command, at=_int(at), started_at=_int(at),
            tokens=turn["tokens"], usage_complete=turn["usage_complete"], session_id=sid,
        ))
        for node in turn["spans"]:
            walk(node, main_id, turn_group, seen)

    # Board agents the trace has no span for — every one of them when the session has no trace. A
    # span the budget cut is still the trace's: its board task is not drawn again, flat under main.
    known = set(drawn)

    def collect(node, seen_ids):
        if id(node) in seen_ids:
            return
        seen_ids.add(id(node))
        if node["id"] is not None:
            known.add(node["id"])
        for child in node["children"]:
            collect(child, seen_ids)

    collected = set()
    for turn in turns:
        for node in turn["spans"]:
            collect(node, collected)
    left = [t for t in agents if not t.get("_spawn_id") or t["_spawn_id"] not in known]
    if session.trace is None and left:
        canvas.notices.append("no_trace:" + sid)
    for count, task in enumerate(sorted(left, key=lambda t: (t.get("created_at") or 0, t["key"]))):
        if count >= tasks.MAX_TASKS:
            canvas.truncated = True
            break
        node = _board_node(sid, task, session_group, now)
        if canvas.add_node(node):
            canvas.edges.append(_edge(main_id, node["id"]))
    if session.capped:
        canvas.truncated = True


def build(root, project_id, now=None, since=None):
    """The project's canvas graph (see the module docstring)."""
    now = int(time.time() if now is None else now)
    canvas = _Canvas()
    sessions = _sessions(root, project_id, now, since)
    for sid in sorted(sessions):
        session = sessions[sid]
        if session.view is None and session.trace is None and not session.task_views:
            continue  # a record with nothing to show, as the board drops it
        if since is not None and _status(session, now) == "ended" and _activity(session) < since:
            continue
        _draw(canvas, session, now)
    return {
        "schema": SCHEMA,
        "project_id": project_id,
        "as_of": now,
        "truncated": canvas.truncated,
        "notices": sorted(set(canvas.notices)),
        "groups": sorted(canvas.groups, key=lambda g: _sort_key(g, canvas.fallback, "started_at", "at")),
        "nodes": sorted(canvas.nodes, key=lambda n: _sort_key(n, canvas.fallback, "started_at")),
        "edges": sorted(canvas.edges, key=lambda e: e["id"]),
    }


def project_root(project_id):
    """The bound root of ``project_id``, else ``None``."""
    for found, root in tasks.bound_projects([project_id]):
        if found == project_id:
            return root
    return None

