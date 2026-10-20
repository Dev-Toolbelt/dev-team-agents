"""Token usage of one finished agent, read from its provider's own record (ADR-0041).

One parser per provider, shared by the execution trace (:mod:`devteam.trace`) and the per-agent
telemetry (``scripts/hooks/lib/agent-usage.sh``), so the two never count differently.

Every function returns ``{"input", "output", "cache_read", "cache_write"}`` (tokens) or ``None``
when the record is missing or unreadable. ``input`` never includes cached input. Nothing here
raises: a hook calls it.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import time
from pathlib import Path

#: Bytes of one agent transcript or rollout read at most; past that the usage is partial.
READ_CAP = 64 * 1024 * 1024
#: Bytes of one subagent ``.meta.json`` read at most; a real one is a few hundred.
META_CAP = 64 * 1024

_KEYS = ("input", "output", "cache_read", "cache_write")


def empty():
    return dict.fromkeys(_KEYS, 0)


def total(usage):
    """Every token the usage names, cached ones included; ``0`` for ``None``."""
    if not isinstance(usage, dict):
        return 0
    return sum(n for n in (usage.get(k) for k in _KEYS) if isinstance(n, int) and not isinstance(n, bool))


def _int(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _lines(path):
    try:
        with open(str(path), "rb") as handle:
            data = handle.read(READ_CAP)
    except OSError:
        return
    for raw in data.decode("utf-8", errors="ignore").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if isinstance(entry, dict):
            yield entry


def claude_transcript_usage(path):
    """Usage summed over a Claude Code agent transcript, counting each message once.

    Claude Code writes several lines per assistant message while it streams, each carrying the
    message's usage so far; the last line of a ``message.id`` is the final count. A line with no
    id is its own message.
    """
    if not path or not os.path.isfile(str(path)):
        return None
    last = {}
    for index, entry in enumerate(_lines(path)):
        message = entry.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
            continue
        key = message.get("id") if isinstance(message.get("id"), str) and message.get("id") else index
        last[key] = message["usage"]
    if not last:
        return None  # nothing flushed yet: not readable, so a later read may still find it
    usage = empty()
    for found in last.values():
        usage["input"] += _int(found.get("input_tokens"))
        usage["output"] += _int(found.get("output_tokens"))
        usage["cache_read"] += _int(found.get("cache_read_input_tokens"))
        usage["cache_write"] += _int(found.get("cache_creation_input_tokens"))
    return usage


def claude_subagent_path(transcript_path, agent_id):
    """``<transcript dir>/<session>/subagents/agent-<agent_id>.jsonl`` beside the session's transcript."""
    if not transcript_path or not agent_id or "/" in agent_id or "\\" in agent_id or agent_id.startswith("."):
        return None
    base = Path(str(transcript_path))
    if base.suffix != ".jsonl":
        return None
    return base.with_suffix("") / "subagents" / "agent-{}.jsonl".format(agent_id)


def claude_agent_id_for(transcript_path, tool_use_id):
    """The runtime agent id whose ``.meta.json`` names ``tool_use_id``, else ``None``.

    The fallback when no hook carried the id (a background launch whose ack was not seen).
    """
    if not transcript_path or not tool_use_id:
        return None
    directory = Path(str(transcript_path)).with_suffix("") / "subagents"
    try:
        names = os.listdir(str(directory))
    except OSError:
        return None
    for name in names:
        if not (name.startswith("agent-") and name.endswith(".meta.json")):
            continue
        try:
            with open(str(directory / name), "r", encoding="utf-8") as handle:
                meta = json.loads(handle.read(META_CAP))
        except (OSError, ValueError):
            continue
        if isinstance(meta, dict) and meta.get("toolUseId") == tool_use_id:
            return name[len("agent-"): -len(".meta.json")]
    return None


def codex_home():
    return os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")


def codex_rollout(agent_id, started_at):
    """The rollout file of Codex thread ``agent_id``, looked up on its start day and the next."""
    if not agent_id or not all(c.isalnum() or c == "-" for c in agent_id):
        return None
    base = os.path.join(codex_home(), "sessions")
    days = []
    for offset in (-86400, 0, 86400):
        day = time.strftime("%Y/%m/%d", time.localtime((started_at or time.time()) + offset))
        if day not in days:
            days.append(day)
    for day in days:
        found = glob.glob(os.path.join(base, day, "rollout-*-{}.jsonl".format(agent_id)))
        if found:
            return found[0]
    return None


def codex_rollout_usage(path):
    """``(usage, model)`` from a Codex rollout: its last cumulative ``token_count`` and model."""
    if not path or not os.path.isfile(str(path)):
        return None, None
    totals, model = None, None
    for entry in _lines(path):
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            continue
        if entry.get("type") == "turn_context" and isinstance(payload.get("model"), str):
            model = payload["model"]
        if payload.get("type") == "token_count":
            info = payload.get("info")
            if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                totals = info["total_token_usage"]
    if totals is None:
        return None, model
    cached = _int(totals.get("cached_input_tokens"))
    return {
        "input": max(_int(totals.get("input_tokens")) - cached, 0),
        "output": _int(totals.get("output_tokens")),
        "cache_read": cached,
        "cache_write": _int(totals.get("cache_write_input_tokens")),
    }, model


def from_payload(value):
    """A usage object a hook payload carries (the opencode plugin's ``agent_usage``), else ``None``."""
    if not isinstance(value, dict):
        return None
    usage = {k: _int(value.get(k)) for k in _KEYS}
    return usage if any(k in value for k in _KEYS) else None


#: Codex multi-agent v2: a child agent's final report reaches its parent's rollout as an
#: `agent_message` whose text opens with this line (seen in codex 0.163; no hook carries it).
FINAL_ANSWER = "Message Type: FINAL_ANSWER"
#: Bytes of a parent rollout read per chunk, and per call at most; the rest waits for the next call.
FINAL_SCAN_CHUNK = 8 * 1024 * 1024
FINAL_SCAN_CAP = 64 * 1024 * 1024
#: Bytes of a rollout's first line read at most to identify its thread.
HEADER_CAP = 1024 * 1024
#: Rollout files examined per day directory when looking for a child thread, newest first among
#: those written since the spawn.
CHILD_SCAN_FILES = 200


def _epoch(stamp):
    if not isinstance(stamp, str):
        return None
    try:
        return int(datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp())
    except ValueError:
        return None


def _final_answer(raw, at_offset):
    """The v2 answer one rollout line holds, else ``None``."""
    if FINAL_ANSWER not in raw:
        return None
    try:
        entry = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(entry, dict):
        return None
    payload = entry.get("payload")
    if entry.get("type") != "response_item" or not isinstance(payload, dict) or payload.get("type") != "agent_message":
        return None
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    text = next((c.get("text") for c in content if isinstance(c, dict) and isinstance(c.get("text"), str)), "")
    author = payload.get("author")
    if not text.startswith(FINAL_ANSWER) or not isinstance(author, str) or not author:
        return None
    # Codex writes the sender twice; both must agree before the line can end anyone's agent.
    if "\nSender: {}\n".format(author) not in text.split("Payload:\n", 1)[0]:
        return None
    return {"author": author, "at": _epoch(entry.get("timestamp")), "offset": at_offset,
            "text": text.split("Payload:\n", 1)[-1]}


def codex_final_answers(path, offset):
    """``(answers, new_offset)``: the v2 ``FINAL_ANSWER`` messages in a Codex rollout after ``offset``.

    Each answer is ``{"author", "at", "offset", "text"}``: ``author`` is the child's task path
    (``/root/<name>``), ``offset`` where its line starts, ``text`` the report after its header. Reads
    complete lines only, chunk by chunk up to :data:`FINAL_SCAN_CAP` per call. A line longer than a
    chunk is skipped, not waited on; a rollout that shrank (rotated) restarts at its current end.
    """
    answers = []
    try:
        size = os.path.getsize(str(path))
    except OSError:
        return answers, offset if isinstance(offset, int) else 0
    if not isinstance(offset, int) or offset < 0 or offset > size:
        return answers, size
    limit = offset + FINAL_SCAN_CAP
    try:
        with open(str(path), "rb") as handle:
            while offset < size and offset < limit:
                handle.seek(offset)
                chunk = handle.read(FINAL_SCAN_CHUNK)
                end = chunk.rfind(b"\n") + 1
                if end == 0:
                    if len(chunk) < FINAL_SCAN_CHUNK:
                        break  # a partial last line: the rest is still being written
                    offset = _skip_line(handle, offset + len(chunk), size)
                    continue
                position = offset
                for raw in chunk[:end].split(b"\n")[:-1]:
                    found = _final_answer(raw.decode("utf-8", errors="replace"), position)
                    if found is not None:
                        answers.append(found)
                    position += len(raw) + 1
                offset += end
    except OSError:
        pass
    return answers, offset


def _skip_line(handle, offset, size):
    """The offset just past the line that runs on from ``offset``, read in chunks, never held whole."""
    handle.seek(offset)
    while offset < size:
        chunk = handle.read(FINAL_SCAN_CHUNK)
        if not chunk:
            return size
        cut = chunk.find(b"\n")
        if cut != -1:
            return offset + cut + 1
        offset += len(chunk)
    return size


def codex_thread_id(rollout_path):
    """The thread id a rollout file is named after (``rollout-<stamp>-<thread id>.jsonl``), else ``None``."""
    name = os.path.basename(str(rollout_path or ""))
    if not (name.startswith("rollout-") and name.endswith(".jsonl")):
        return None
    tail = name[: -len(".jsonl")].split("-")
    ident = "-".join(tail[-5:]) if len(tail) >= 6 else ""
    return ident if len(ident) == 36 and all(c.isalnum() or c == "-" for c in ident) else None


def _first_line(path):
    """A file's first line, read up to :data:`HEADER_CAP` bytes; ``None`` past that or on error."""
    data = b""
    try:
        with open(path, "rb") as handle:
            while len(data) < HEADER_CAP:
                chunk = handle.read(64 * 1024)
                if not chunk:
                    return None
                cut = chunk.find(b"\n")
                if cut != -1:
                    return data + chunk[:cut]
                data += chunk
    except OSError:
        return None
    return None


def codex_child_rollout(parent_thread_id, agent_path, started_at):
    """The rollout of the v2 child ``agent_path`` spawned by ``parent_thread_id`` at ``started_at``.

    Found by its first line (``session_meta``: ``source.subagent.thread_spawn``) among regular
    ``rollout-*`` files of the spawn's day and the next that were written since the spawn, examining at
    most :data:`CHILD_SCAN_FILES` a day. When the same task path was spawned more than once, the
    child whose own start is the first at or after ``started_at`` wins. ``None`` when none matches.
    """
    if not parent_thread_id or not isinstance(agent_path, str) or not agent_path:
        return None
    since = (started_at or time.time()) - 60
    base = os.path.join(codex_home(), "sessions")
    best = None
    for offset in (0, 86400):
        day = os.path.join(base, time.strftime("%Y/%m/%d", time.localtime((started_at or time.time()) + offset)))
        try:
            names = [n for n in os.listdir(day) if n.startswith("rollout-") and n.endswith(".jsonl")]
        except OSError:
            continue
        candidates = []
        for name in names:
            path = os.path.join(day, name)
            try:
                if os.path.isfile(path) and os.path.getmtime(path) >= since:
                    candidates.append(path)
            except OSError:
                continue
        for path in sorted(candidates)[:CHILD_SCAN_FILES]:
            line = _first_line(path)
            try:
                meta = json.loads(line.decode("utf-8", errors="replace")) if line else None
            except ValueError:
                continue
            payload = meta.get("payload") if isinstance(meta, dict) else None
            source = payload.get("source") if isinstance(payload, dict) else None
            sub = source.get("subagent") if isinstance(source, dict) else None
            spawn = sub.get("thread_spawn") if isinstance(sub, dict) else None
            if not (isinstance(spawn, dict) and spawn.get("parent_thread_id") == parent_thread_id
                    and spawn.get("agent_path") == agent_path):
                continue
            began = _epoch(payload.get("timestamp"))
            if began is None:
                try:
                    began = int(os.path.getmtime(path))
                except OSError:
                    continue
            if began >= since and (best is None or began < best[0]):
                best = (began, path)
    return best[1] if best else None
