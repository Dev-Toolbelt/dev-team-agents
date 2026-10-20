"""The execution trace: one span per agent spawn, the tree derived on read (ADR-0041).

Spec: ``docs/specs/execution-trace.md``. The trace sits beside the task board (ADR-0018) and
never touches its record: ``<state-dir>/task-board/trace/<session-key>.json``, one file per
session, written only by :func:`capture` and :func:`settle` under a per-session lock, atomically,
and never deleted. The board lists only the top level of ``task-board/``, so this subdirectory
is invisible to it.

Unlike the board, every agent type is a span — review/QA agents and provider built-ins too —
because cost is the point. The tree (session → turn → span → nested span) is built by
:func:`build` on read; a span's parent is the span whose ``agent_id`` equals its ``owner``.

A hook calls :func:`capture` and :func:`settle`, so neither raises.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from . import command_usage, jsonio, lock, review_triggers, tasks, usage, versions
from .errors import DevteamError

SCHEMA = 1
TRACE_DIR = "trace"
#: Most spans one session's trace keeps: a runaway loop must not grow the file without bound.
MAX_SPANS = 500
#: Child-session aliases kept (opencode child sessions, Codex child threads).
MAX_ALIASES = 200

#: Most ended spans one Stop tries to read usage for, and how often one span is retried: a Stop
#: must stay bounded however many agents a session ran (each read is capped by ``usage.READ_CAP``).
SETTLE_READS = 20
USAGE_TRIES = 3
#: A span still running this long after it started is settled ``interrupted``: a background agent
#: whose hand-back never came, a Codex agent never waited on. Same age the board gives a review wait.
RUNNING_MAX_AGE = tasks.PENDING_MAX_AGE

ENDED = ("completed", "failed", "cancelled", "interrupted")
#: An agent name a span may carry; the same charset `insights` reads back (ADR-0042).
_AGENT_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_HANDBACK_FAILED = ("failed", "killed", "error")


def trace_dir(root, project_id):
    return tasks.tasks_dir(root, project_id) / TRACE_DIR


def trace_path(root, project_id, session_id):
    key = tasks.session_key(session_id)
    if key is None:
        return None
    return trace_dir(root, project_id) / "{}.json".format(key)


def _lock(path):
    return lock.Lock(str(path)[: -len(".json")] + ".lock", timeout=tasks.LOCK_TIMEOUT, stale_after=30.0)


def _load(path):
    try:
        data = jsonio.read_json(path)
    except (DevteamError, OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or not isinstance(data.get("spans"), list):
        return None
    if not all(isinstance(s, dict) and isinstance(s.get("agent"), str) for s in data["spans"]):
        return None
    return data


def _aliases_path(root, project_id):
    return trace_dir(root, project_id) / "aliases.json"


def _read_aliases(path):
    """The alias map, ``{}`` when absent, ``None`` when unreadable (never overwritten then)."""
    try:
        data = jsonio.read_json(path, default={})
    except (DevteamError, OSError, ValueError):
        return None
    found = data.get("aliases", {}) if isinstance(data, dict) else None
    return found if isinstance(found, dict) else None


def _root_session(root, project_id, session_id):
    """The top session a child session (opencode) or child thread (Codex) belongs to, else itself."""
    found = (_read_aliases(_aliases_path(root, project_id)) or {}).get(session_id)
    return (found, True) if isinstance(found, str) and found else (session_id, False)


def _write_alias(root, project_id, child, top):
    """Route ``child``'s later hook calls to ``top``'s trace. A bounded map: the oldest entry drops out."""
    if not child or child == top:
        return
    own = trace_path(root, project_id, child)
    if own is None or own.exists():
        return  # a session with a trace of its own is a top session, never someone's child
    path = _aliases_path(root, project_id)
    with _lock(path):
        aliases = _read_aliases(path)
        if aliases is None:
            return
        aliases.pop(child, None)
        aliases[child] = top
        while len(aliases) > MAX_ALIASES:
            aliases.pop(next(iter(aliases)))
        jsonio.write_json_atomic(path, {"schema": SCHEMA, "aliases": aliases})


def _provider_and_tool(payload):
    tool_name = payload.get("tool_name") if isinstance(payload.get("tool_name"), str) else ""
    bare_tool = payload.get("tool") if isinstance(payload.get("tool"), str) else ""
    bare = tool_name.split(".")[-1]
    if tool_name in tasks._CLAUDE_AGENT_TOOLS:
        return "claude", tool_name
    if bare in tasks._CODEX_AGENT_TOOLS:
        return "codex", bare
    if bare_tool.lower() == "task":
        return "opencode", "task"
    return None, None


def _kind(provider, name):
    if review_triggers.agent_name(name):
        return "review"
    if review_triggers.is_builtin(provider, name):
        return "builtin"
    return "agent"


def _response_fields(payload):
    """``(agent_id, model, duration_ms, tool_uses, async)`` from a Claude ``Agent`` result."""
    agent_id = model = duration = tools = None
    for found in tasks._json_objects(payload.get("tool_response") or payload.get("tool_output")):
        agent_id = agent_id or tasks._id_text(found.get("agentId"))
        model = model or (found.get("resolvedModel") if isinstance(found.get("resolvedModel"), str) else None)
        if duration is None and isinstance(found.get("totalDurationMs"), int):
            duration = found["totalDurationMs"]
        if tools is None and isinstance(found.get("totalToolUseCount"), int):
            tools = found["totalToolUseCount"]
    return agent_id, model, duration, tools, tasks._async_launch(payload)


def _findings(value):
    """A review's last ``<!-- review-result: findings=N -->`` in an agent's report, else ``None``.

    Read like the board reads it: the fields that echo the agent's prompt are dropped first, so a
    prompt that quotes a marker is never counted, and only the report's own last marker counts.
    """
    found = review_triggers.markers(tasks._output(value))
    return found[-1] if found else None


def _event(payload):
    """What an agent-tool payload stands for: ``(provider, op, body)``, else ``None``."""
    provider, tool = _provider_and_tool(payload)
    if provider is None:
        return None
    inp = tasks._dict(payload.get("tool_input")) or tasks._dict(payload.get("args"))
    event = tasks._text(payload.get("hook_event_name"))
    after = event in ("PostToolUse", "PostToolUseFailure") or any(
        k in payload for k in ("output", "tool_response", "tool_output")
    )
    use_id = tasks._first_text(payload, "tool_use_id", "toolUseId")
    if tool == "wait_agent":
        results = tasks._wait_results(payload.get("tool_response"))
        return (provider, "wait", results) if results else None
    if tool == "close_agent":
        ident = tasks._id_text(inp.get("target") or inp.get("id") or inp.get("agent_id"))
        return (provider, "wait", [(ident, "cancelled", False)]) if ident else None
    name = review_triggers.spawn_name(tasks._first_text(inp, "subagent_type", "agent_type"))
    if name is not None and not _AGENT_NAME.match(name):
        return None  # a name no agent carries: recorded before the provider checks it, so never trusted
    if not after:
        if not name or not use_id:
            return None
        return provider, "spawn", {
            "id": use_id, "agent": name, "kind": _kind(provider, name),
            "background": inp.get("run_in_background") is True,
        }
    if not use_id:
        return None
    if event == "PostToolUseFailure":
        return provider, "end", {"id": use_id, "status": "failed"}
    if tool == "spawn_agent":
        ref = tasks._spawned_agent_id(payload.get("tool_response"))
        if ref:
            return provider, "ref", {"id": use_id, "agent_id": ref}
        task_path = tasks._spawned_task_path(payload.get("tool_response"))
        if task_path:
            # Multi-agent v2: no agent id, only a task path; its end is the parent rollout's
            # FINAL_ANSWER, read by `settle`.
            return provider, "ref", {"id": use_id, "agent_path": task_path}
        return None  # no agent at all: the span stays as it is, and the Stop settles it
    findings = _findings(payload.get("tool_response") or payload.get("tool_output") or payload.get("output"))
    if provider == "opencode":
        return provider, "end", {
            "id": use_id, "status": "completed", "findings": findings,
            "agent_id": tasks._id_text(payload.get("agent_session_id")),
            "usage": usage.from_payload(payload.get("agent_usage")),
            "model": payload.get("agent_model") if isinstance(payload.get("agent_model"), str) else None,
        }
    agent_id, model, duration, tools, launched = _response_fields(payload)
    body = {"id": use_id, "agent_id": agent_id, "model": model, "duration_ms": duration, "tool_uses": tools}
    if launched:
        return provider, "background", body
    body["findings"] = findings
    return provider, "end", dict(body, status="completed")


def _turn_of(root, project_id, session_id, spans):
    """``(turn_at, command)`` of the session's current turn; the last span's when the turn was injected."""
    record = tasks.record_path(root, project_id, session_id)
    started, excerpt = tasks._turn(record) if record is not None else (None, "")
    if started is None:
        last = max((s for s in spans if s.get("turn_at")), key=lambda s: s["turn_at"], default=None)
        return (last["turn_at"], last.get("command")) if last else (None, None)
    match = command_usage._INVOCATION_RE.match(excerpt or "")
    return started, (match.group(1) if match else None)


#: The tree this module runs from; its version is the harness that produced the trace.
_TREE = Path(__file__).resolve().parents[3]


def _new_trace(session_id, provider, now):
    return {
        "schema": SCHEMA, "session_id": session_id, "provider": provider,
        # Lets the optimization loop compare cost before and after a harness change.
        "harness_version": versions.version_from_tree(_TREE),
        "created_at": now, "updated_at": now,
        "scan": {"opened_at": now, "tx_path": None, "tx_offset": None, "queue_ids": []},
        "spans": [],
    }


def _find(spans, ident):
    return next((s for s in spans if ident and ident in (s.get("id"), s.get("agent_id"))), None)


def _fill_usage(span, provider, transcript, session_id=None):
    """Read the ended span's usage from its provider's record, once. Returns True when it changed."""
    if span.get("usage") is not None or span.get("status") not in ENDED:
        return False
    if (span.get("usage_tries") or 0) >= USAGE_TRIES:
        return False
    span["usage_tries"] = (span.get("usage_tries") or 0) + 1
    found, model = None, None
    if provider == "claude":
        agent_id = span.get("agent_id") or usage.claude_agent_id_for(transcript, span.get("id"))
        if agent_id and not span.get("agent_id"):
            span["agent_id"] = agent_id
        found = usage.claude_transcript_usage(usage.claude_subagent_path(transcript, agent_id))
    elif provider == "codex" and span.get("agent_id"):
        found, model = usage.codex_rollout_usage(usage.codex_rollout(span["agent_id"], span.get("started_at")))
    elif provider == "codex" and span.get("agent_path"):
        # v2: the child's own rollout names its parent thread and its task path in its first line.
        parent = usage.codex_thread_id(span.get("rollout_path") or transcript) or session_id
        child = usage.codex_child_rollout(parent, span["agent_path"], span.get("started_at"))
        found, model = usage.codex_rollout_usage(child)
    if found is None:
        return False
    span["usage"] = found
    if model and not span.get("model"):
        span["model"] = model
    return True


def _is_v2(span):
    return span.get("status") == "running" and bool(span.get("agent_path"))


def _mark_rollout(span, transcript):
    """Where the parent rollout ends now; a v2 FINAL_ANSWER for ``span`` can only come after it."""
    if span.get("rollout_path") or not (transcript and os.path.isfile(transcript)):
        return
    span["rollout_offset"] = os.path.getsize(transcript)
    span["rollout_path"] = transcript


def _settle_v2(trace, transcript, now):
    """End v2 spans at their FINAL_ANSWER: the first one from their path after their own spawn mark.

    Same rule as the board (``tasks._scan_codex_v2``); a span with none is left to
    :data:`RUNNING_MAX_AGE`. Spans whose spawn wrote to another rollout (a nested spawn from a child
    thread, a resumed thread) are not read here.
    """
    readable = [s for s in trace["spans"] if _is_v2(s) and s.get("rollout_path") == transcript]
    if not readable or not transcript or not os.path.isfile(transcript):
        return
    scan = trace.get("codex_scan") if isinstance(trace.get("codex_scan"), dict) else {}
    # Resume where the last scan stopped, or at the oldest open mark when that is later (as the board).
    start = min(s.get("rollout_offset") or 0 for s in readable)
    if scan.get("tx_path") == transcript and isinstance(scan.get("tx_offset"), int):
        start = max(start, scan["tx_offset"])
    answers, offset = usage.codex_final_answers(transcript, start)
    trace["codex_scan"] = {"tx_path": transcript, "tx_offset": offset}
    for answer in answers:
        waiting = sorted(
            (s for s in readable if _is_v2(s) and s["agent_path"] == answer["author"]
             and (s.get("rollout_offset") or 0) <= answer["offset"]),
            key=lambda s: s["started_at"],
        )
        if waiting:
            span = waiting[0]
            _end(span, "completed", max(span["started_at"], min(now, answer["at"] or now)))
            span["findings"] = _findings(answer["text"])


def _end(span, status, now):
    if span.get("status") in ENDED:
        return False
    span["status"] = status
    span["ended_at"] = max(int(now), span.get("started_at") or 0)
    return True


def _apply(trace, provider, op, body, owner, turn, now, transcript):
    spans = trace["spans"]
    if op == "spawn":
        if _find(spans, body["id"]) is not None or len(spans) >= MAX_SPANS:
            return False
        if body["background"] and not any(s.get("background") and s.get("status") == "running" for s in spans):
            trace["scan"] = {"opened_at": now, "tx_path": None, "tx_offset": None, "queue_ids": []}
            if transcript and os.path.isfile(transcript):
                trace["scan"].update(tx_path=transcript, tx_offset=os.path.getsize(transcript))
        spans.append({
            "id": body["id"], "agent": body["agent"], "kind": body["kind"], "owner": owner,
            "agent_id": None, "background": body["background"],
            "turn_at": turn[0], "command": turn[1],
            "started_at": now, "ended_at": None, "status": "running",
            "model": None, "usage": None, "tool_uses": None, "duration_ms": None, "findings": None,
        })
        if provider == "codex":
            _mark_rollout(spans[-1], transcript)
        return True
    if op == "wait":
        changed = False
        for ident, status, failed in body:
            span = _find(spans, ident)
            if span is not None and _end(span, "failed" if failed else status, now):
                _fill_usage(span, provider, transcript)
                changed = True
        return changed
    span = _find(spans, body["id"])
    if span is None:
        return False
    for key in ("agent_id", "agent_path", "model", "duration_ms", "tool_uses", "usage", "findings"):
        if body.get(key) is not None:
            span[key] = body[key]
    if op == "ref" and body.get("agent_path"):
        _mark_rollout(span, transcript)  # only when the spawn carried no rollout
    if op == "background":
        span["background"] = True
        return True
    if op == "end":
        _end(span, body["status"], now)
        _fill_usage(span, provider, transcript)
    return True


def capture(root, payload, now=None):
    """Fold one agent-tool hook payload into its session's trace. Never raises."""
    result = {"recorded": False, "session": None}
    try:
        if not isinstance(payload, dict):
            return result
        found = _event(payload)
        if found is None:
            return result
        provider, op, body = found
        project_id = tasks._bound_id(root)
        session_id = tasks._first_text(payload, "session_id", "sessionID", "sessionId")
        if not project_id or not session_id:
            return result
        top, child = _root_session(root, project_id, session_id)
        parent = tasks._first_text(payload, "parent_id") if provider == "opencode" else ""
        own = trace_path(root, project_id, session_id)
        if not child and parent and parent != session_id and own is not None and not own.exists():
            # opencode names a child session's parent on every call: route it before its agent ends.
            top, child = _root_session(root, project_id, parent)[0], True
            _write_alias(root, project_id, session_id, top)
        path = trace_path(root, project_id, top)
        if path is None:
            return result
        now = int(time.time() if now is None else now)
        owner = tasks._first_text(payload, "agent_id") or (session_id if child else tasks.MAIN_OWNER)
        transcript = tasks._first_text(payload, "transcript_path") or None
        jsonio.ensure_dir(path.parent)
        with _lock(path):
            trace = _load(path)
            if trace is None:
                if path.exists() or op != "spawn":
                    return result
                trace = _new_trace(top, provider, now)
            turn = _turn_of(root, project_id, top, trace["spans"]) if op == "spawn" else (None, None)
            if not _apply(trace, provider, op, body, owner, turn, now, transcript):
                return result
            trace["updated_at"] = now
            if transcript and provider in ("claude", "codex") and not child:
                trace["transcript_path"] = transcript
            jsonio.write_json_atomic(path, trace)
            # A child session's or thread's own spawns belong to this trace (opencode, Codex). Inside
            # the trace lock, so the child's next call finds it; the alias lock is only ever taken
            # inside this one or alone, never around it.
            if provider in ("opencode", "codex") and op in ("end", "ref") and body.get("agent_id"):
                _write_alias(root, project_id, body["agent_id"], top)
        result.update(recorded=True, session=top)
    except (DevteamError, OSError, ValueError, TypeError, KeyError, AttributeError):
        result["recorded"] = False
    return result


def settle(root, payload, now=None):
    """What a finished turn settles in the trace. Never raises.

    Background hand-backs in the transcript end their spans (at the hand-back's time); a
    foreground span still running cannot be, so it is ``interrupted``; ended spans whose usage
    was not readable yet are read again.
    """
    result = {"settled": False}
    try:
        project_id = tasks._bound_id(root)
        session_id = tasks._first_text(payload, "session_id", "sessionID", "sessionId") if isinstance(payload, dict) else ""
        if not project_id or not session_id:
            return result
        top, child = _root_session(root, project_id, session_id)
        path = trace_path(root, project_id, top)
        if child or path is None or not path.is_file():
            return result
        now = int(time.time() if now is None else now)
        transcript = tasks._first_text(payload, "transcript_path") or None
        with _lock(path):
            trace = _load(path)
            if trace is None:
                return result
            before = json.dumps(trace, sort_keys=True)
            provider = trace.get("provider")
            transcript = transcript or trace.get("transcript_path")
            spans = trace["spans"]
            pending = {}
            for span in spans:
                if span.get("background") and span.get("status") == "running":
                    # A hand-back names the spawn's id, or only the runtime agent id (`task-id`).
                    for ident in (span.get("id"), span.get("agent_id")):
                        if ident:
                            pending[ident] = span
            if pending and provider == "claude" and transcript and os.path.isfile(transcript):
                scan = trace.setdefault("scan", {"opened_at": now, "tx_path": None, "tx_offset": None, "queue_ids": []})
                scan["opened_at"] = min(s["started_at"] for s in pending.values())
                for report in tasks._background_reports(scan, transcript):
                    span = pending.get(report["id"])
                    if span is not None and span["status"] == "running":
                        status = "failed" if report["status"] in _HANDBACK_FAILED else "completed"
                        _end(span, status, max(span["started_at"], min(now, report["at"])))
                        if report.get("markers"):
                            span["findings"] = report["markers"][-1]
            if provider == "codex":
                _settle_v2(trace, transcript, now)
            reads = 0
            for span in spans:
                if span.get("status") == "running" and (
                    now - (span.get("started_at") or now) > RUNNING_MAX_AGE
                    or (not span.get("background")
                        and not (provider == "codex" and (span.get("agent_id") or span.get("agent_path"))))
                ):
                    _end(span, "interrupted", now)
                if reads < SETTLE_READS and span.get("usage") is None and span.get("status") in ENDED \
                        and (span.get("usage_tries") or 0) < USAGE_TRIES:
                    reads += 1
                    _fill_usage(span, provider, transcript, trace.get("session_id"))
            if json.dumps(trace, sort_keys=True) == before:
                result["settled"] = True
                return result
            trace["updated_at"] = now
            jsonio.write_json_atomic(path, trace)
        result["settled"] = True
    except (DevteamError, OSError, ValueError, TypeError, KeyError, AttributeError):
        result["settled"] = False
    return result


def _node(span, now):
    end = span.get("ended_at") or now
    own = usage.total(span.get("usage"))
    return {
        "id": span.get("id"), "agent": span.get("agent"), "kind": span.get("kind"),
        "agent_id": span.get("agent_id"), "status": span.get("status"),
        "background": bool(span.get("background")),
        "started_at": span.get("started_at"), "ended_at": span.get("ended_at"),
        "duration_s": max(0, int(end) - int(span.get("started_at") or end)),
        "duration_ms": span.get("duration_ms"), "tool_uses": span.get("tool_uses"),
        "model": span.get("model"), "usage": span.get("usage"), "findings": span.get("findings"),
        "tokens": own, "subtree_tokens": own, "usage_complete": span.get("usage") is not None, "children": [],
    }


def build(trace, now=None):
    """The session's trace as a tree: ``{session_id, provider, totals, turns}``."""
    now = int(time.time() if now is None else now)
    spans = [s for s in trace.get("spans", []) if isinstance(s, dict)]
    nodes = {id(s): _node(s, now) for s in spans}
    by_agent = {s["agent_id"]: s for s in spans if s.get("agent_id")}

    def parent_of(span):
        """The span's parent, unless the span sits on a cycle of owners: a cycle member hangs from
        its turn, and whatever hangs below it keeps its place."""
        parent = by_agent.get(span.get("owner"))
        seen = set()
        walk = parent
        while walk is not None and id(walk) not in seen:
            if walk is span:
                return None
            seen.add(id(walk))
            walk = by_agent.get(walk.get("owner"))
        return parent

    roots = []
    for span in spans:
        parent = parent_of(span)
        if parent is not None:
            nodes[id(parent)]["children"].append(nodes[id(span)])
        else:
            roots.append(span)

    def total(node):
        node["subtree_tokens"] = node["tokens"] + sum(total(c) for c in node["children"])
        node["usage_complete"] = node["usage"] is not None and all(c["usage_complete"] for c in node["children"])
        return node["subtree_tokens"]

    turns = {}
    for span in roots:
        key = span.get("turn_at")
        turn = turns.setdefault(key, {"turn_at": key, "command": span.get("command"), "spans": []})
        turn["command"] = turn["command"] or span.get("command")
        node = nodes[id(span)]
        total(node)
        turn["spans"].append(node)
    ordered = sorted(turns.values(), key=lambda t: (t["turn_at"] is None, t["turn_at"] or 0))
    for turn in ordered:
        turn["tokens"] = sum(n["subtree_tokens"] for n in turn["spans"])
        turn["usage_complete"] = all(n["usage_complete"] for n in turn["spans"])
    starts = [s.get("started_at") for s in spans if isinstance(s.get("started_at"), int)]
    ends = [s.get("ended_at") or now for s in spans]
    return {
        "session_id": trace.get("session_id"), "provider": trace.get("provider"),
        "harness_version": trace.get("harness_version"),
        "totals": {
            "spans": len(spans),
            "tokens": sum(usage.total(s.get("usage")) for s in spans),
            "duration_s": max(0, max(ends) - min(starts)) if starts else 0,
            "usage_complete": all(s.get("usage") is not None for s in spans),
        },
        "turns": ordered,
    }


def show(root, session_id, now=None):
    """The built trace of ``session_id`` in the project at ``root``, else ``None``."""
    project_id = tasks._bound_id(root)
    if not project_id:
        return None
    session_id = _root_session(root, project_id, session_id)[0]
    path = trace_path(root, project_id, session_id)
    trace = _load(path) if path is not None and path.is_file() else None
    return build(trace, now) if trace is not None else None
