"""The optimization loop's numbers: execution traces aggregated across bound projects (ADR-0042).

Spec: ``docs/specs/optimization-loop.md``. :func:`report` reads every bound project's traces
(ADR-0041) and the board's review windows, computes the metrics, and hands them to
:mod:`devteam.insights_rules` for suggestions. Everything here is read-only except
:func:`dismiss`, which writes the user's decision to ``data/insights-decisions.json`` — portable,
because it is something the user decided (ADR-0013) — under a lock and atomically.

Nothing in this module edits the harness: a suggestion is a proposal, never a change.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path

from . import catalog, insights_rules, jsonio, lock, paths, tasks, trace, usage
from .errors import DevteamError, UsageError

DECISIONS_FILE = "insights-decisions.json"
DECISIONS_SCHEMA = 1

_TREE = trace.TREE
_SUGGESTION_ID = re.compile(r"^[a-z-]+:[0-9a-f]{12}$")
#: What a trace may name, read back before it reaches a report, a suggestion title the model reads, or
#: a `devteam tasks trace <session>` the command hints at: anything else is crafted, and the trace or
#: span is skipped (the same charset `tasks.session_key` accepts for an id).
_SAFE_NAME = trace.SAFE_NAME
_SAFE_SESSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_VERSION = trace.SAFE_VERSION
#: A trace file larger than this is skipped unread: `trace.MAX_SPANS` keeps a real one far below it.
MAX_TRACE_BYTES = 4 * 1024 * 1024


def _percentile(values, fraction):
    """Nearest-rank percentile of ``values``; ``None`` for no values."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(max(1, math.ceil(fraction * len(ordered))), len(ordered)) - 1]


def _mean(values):
    return round(sum(values) / len(values), 1) if values else None


def _tiers():
    """``{agent name: tier}`` from the agents' own frontmatter in this tree."""
    found = {}
    directory = _TREE / "agents"
    try:
        names = os.listdir(str(directory))
    except OSError:
        return found
    for name in names:
        if not name.endswith(".md"):
            continue
        try:
            with open(str(directory / name), "r", encoding="utf-8") as handle:
                meta, _ = catalog.parse_frontmatter(handle.read())
        except (OSError, ValueError, DevteamError):
            continue
        if isinstance(meta, dict) and isinstance(meta.get("tier"), str):
            found[name[: -len(".md")]] = meta["tier"]
    return found


def _effort_map():
    """``(low, excluded)`` from ``tiers.json`` ``agent_effort``: agents with a ``low`` override, and
    agents a ``_why_not_<agent>`` note keeps off one (the note is the rule's only home)."""
    try:
        with open(str(_TREE / "scripts" / "lib" / "tiers.json"), "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return set(), set()
    overrides = data.get("agent_effort") if isinstance(data, dict) else None
    if not isinstance(overrides, dict):
        return set(), set()
    low = {
        name for name, entry in overrides.items()
        if not name.startswith("_") and isinstance(entry, dict) and "low" in entry.values()
    }
    excluded = {name[len("_why_not_"):].replace("_", "-") for name in overrides if name.startswith("_why_not_")}
    return low, excluded


def _int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _tokens(value):
    """A span's token total, or ``None`` when its usage is unknown: no usage object, or one that
    carries no integer count at all (``{}``). A usage whose counts are all zero is a real 0."""
    if not isinstance(value, dict) or not any(_int(value.get(k)) for k in ("input", "output", "cache_read", "cache_write")):
        return None
    return usage.total(value)


def _spans(project_ids, since):
    """Every span of every trace in scope, flattened with its session's context."""
    out = []
    for project_id, root in tasks.bound_projects(project_ids):
        directory = trace.trace_dir(root, project_id)
        try:
            names = sorted(n for n in os.listdir(str(directory)) if n.endswith(".json") and n != "aliases.json")
        except OSError:
            continue
        for name in names:
            try:
                if os.path.getsize(str(directory / name)) > MAX_TRACE_BYTES:
                    continue
            except OSError:
                continue
            data = trace.load(directory / name)
            if data is None or not _SAFE_SESSION.match(str(data.get("session_id"))):
                continue
            updated = data.get("updated_at")
            if since is not None and not (_int(updated) and updated >= since):
                continue
            provider = data.get("provider") if data.get("provider") in tasks.PROVIDERS else None
            version = data.get("harness_version")
            version = version if isinstance(version, str) and _SAFE_VERSION.match(version) else None
            for span in data["spans"][: trace.MAX_SPANS]:
                if not _SAFE_NAME.match(str(span.get("agent"))):
                    continue
                start, end = span.get("started_at"), span.get("ended_at")
                command = span.get("command")
                out.append({
                    "project_id": project_id,
                    "session_id": data.get("session_id"),
                    "provider": provider,
                    "harness_version": version,
                    "agent": span["agent"],
                    "kind": span.get("kind") if span.get("kind") in ("agent", "review", "builtin") else "agent",
                    "status": span.get("status") if isinstance(span.get("status"), str) else None,
                    "model": span.get("model") if isinstance(span.get("model"), str) and _SAFE_NAME.match(span["model"]) else None,
                    "turn_at": span.get("turn_at") if _int(span.get("turn_at")) else None,
                    "command": command if isinstance(command, str) and _SAFE_NAME.match(command) else None,
                    "tokens": _tokens(span.get("usage")),
                    "duration_s": (end - start) if _int(start) and _int(end) else None,
                    "tool_uses": span.get("tool_uses") if _int(span.get("tool_uses")) else None,
                    "findings": span.get("findings") if _int(span.get("findings")) else None,
                })
    return out


def _review_windows(project_ids, since):
    """The board's review windows in scope, per provider: ``{provider: {windows, unread_rate,
    findings_mean, fixed_after_findings}}``.

    Kept apart per provider because a provider's capture gap must not read as a reliability signal
    of every provider: Codex multi-agent v2 reviewer windows are always settled unread today
    (task-board spec, Out of Scope).
    """
    groups = {}
    for project_id, root in tasks.bound_projects(project_ids):
        for rec in tasks.project_records(root, project_id):
            updated = rec.get("updated_at")
            if since is not None and not (_int(updated) and updated >= since):
                continue
            provider = rec.get("provider") if rec.get("provider") in tasks.PROVIDERS else None
            group = groups.setdefault(provider, {"windows": 0, "unread": 0, "fixed": 0, "findings": []})
            for window in rec.get("reviews") or []:
                if not isinstance(window, dict) or window.get("result_at") is None:
                    continue
                group["windows"] += 1
                count = window.get("findings")
                if _int(count):
                    group["findings"].append(count)
                    if count > 0 and window.get("resolution") == "fixed":
                        group["fixed"] += 1
                else:
                    group["unread"] += 1
    return {
        str(provider): {
            "windows": g["windows"],
            "unread_rate": round(g["unread"] / g["windows"], 3) if g["windows"] else None,
            "findings_mean": _mean(g["findings"]),
            "fixed_after_findings": g["fixed"],
        }
        for provider, g in sorted(groups.items(), key=lambda kv: str(kv[0])) if g["windows"]
    }


def _agents(spans, tiers):
    groups = {}
    for span in spans:
        groups.setdefault((span["agent"], span["provider"]), []).append(span)
    out = []
    for (agent, provider), members in sorted(groups.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        tokens = [s["tokens"] for s in members if s["tokens"] is not None]
        durations = [s["duration_s"] for s in members if s["duration_s"] is not None]
        reviews = [s["findings"] for s in members if s["kind"] == "review" and s["findings"] is not None]
        models = {}
        for s in members:
            if s["model"]:
                models[s["model"]] = models.get(s["model"], 0) + 1
        known_tools = [s["tool_uses"] for s in members if s["tool_uses"] is not None]
        out.append({
            "agent": agent, "provider": provider, "kind": members[0]["kind"], "tier": tiers.get(agent),
            "spans": len(members),
            "sessions": len({s["session_id"] for s in members}),
            "failed_rate": round(sum(s["status"] == "failed" for s in members) / len(members), 3),
            "interrupted_rate": round(sum(s["status"] == "interrupted" for s in members) / len(members), 3),
            "duration_p50": _percentile(durations, 0.5), "duration_p90": _percentile(durations, 0.9),
            "tokens_mean": _mean(tokens), "tokens_p90": _percentile(tokens, 0.9),
            "usage_coverage": round(len(tokens) / len(members), 3),
            "tool_uses_known": len(known_tools),
            "zero_tool_share": round(sum(n == 0 for n in known_tools) / len(known_tools), 3) if known_tools else None,
            "models": models,
            "reviews": {
                "count": len(reviews),
                "zero_findings_rate": round(sum(n == 0 for n in reviews) / len(reviews), 3) if reviews else None,
                "findings_mean": _mean(reviews),
            },
            "examples": sorted({s["session_id"] for s in members})[:3],
        })
    return out


def _runs(spans, key):
    """``{group: {run: [spans]}}``: a run is one session's turn, grouped by ``key(span)``."""
    groups = {}
    for span in spans:
        run = (span["project_id"], span["session_id"], span["turn_at"])
        groups.setdefault(key(span), {}).setdefault(run, []).append(span)
    return groups


def _run_stats(runs):
    """Per-run token totals over the runs whose every span has usage, and their coverage."""
    complete = [members for members in runs.values() if all(s["tokens"] is not None for s in members)]
    totals = [sum(s["tokens"] for s in members) for members in complete]
    return totals, round(len(complete) / len(runs), 3) if runs else None


def _commands(spans):
    out = []
    for (command, provider), runs in sorted(_runs(spans, lambda s: (s["command"], s["provider"])).items(),
                                            key=lambda kv: (str(kv[0][0]), str(kv[0][1]))):
        totals, coverage = _run_stats(runs)
        members = [s for m in runs.values() for s in m]
        known = [s for s in members if s["tokens"] is not None]
        builtin = sum(s["tokens"] for s in known if s["kind"] == "builtin")
        out.append({
            "command": command, "provider": provider, "runs": len(runs),
            "sessions": len({run[1] for run in runs}),
            "tokens_per_run": _mean(totals),
            "agents_per_run": _mean([len(m) for m in runs.values()]),
            "builtin_token_share": round(builtin / sum(s["tokens"] for s in known), 3) if known and sum(s["tokens"] for s in known) else None,
            "usage_coverage": coverage,
            "examples": sorted({run[1] for run in runs})[:3],
        })
    return out


def _versions(spans):
    out = []
    groups = _runs(spans, lambda s: (s["harness_version"], s["command"], s["provider"]))
    for (version, command, provider), runs in sorted(groups.items(), key=lambda kv: tuple(str(k) for k in kv[0])):
        totals, coverage = _run_stats(runs)
        out.append({
            "harness_version": version, "command": command, "provider": provider, "runs": len(runs),
            "tokens_per_run": _mean(totals), "usage_coverage": coverage,
            "examples": sorted({run[1] for run in runs})[:3],
        })
    return out


def decisions_path():
    return Path(paths.data_dir()) / DECISIONS_FILE


def _decisions():
    try:
        data = jsonio.read_json(decisions_path(), default={})
    except (DevteamError, OSError, ValueError):
        return {}  # a damaged record hides nothing, and is never rewritten by a read
    found = data.get("dismissed") if isinstance(data, dict) else None
    return found if isinstance(found, dict) else {}


def report(project_ids=None, since=None, include_dismissed=False, now=None):
    """Metrics and suggestions for every bound project in scope."""
    now = int(time.time() if now is None else now)
    spans = _spans(project_ids, since)
    metrics = {
        "agents": _agents(spans, _tiers()),
        "commands": _commands(spans),
        "versions": _versions(spans),
        "reviews": _review_windows(project_ids, since),
    }
    low, excluded = _effort_map()
    found, insufficient = insights_rules.evaluate(metrics, low, excluded)
    dismissed = _decisions()
    suggestions = []
    for suggestion in found:
        decision = dismissed.get(suggestion["id"])
        baseline = decision.get("sample_spans") if isinstance(decision, dict) else None
        hidden = _int(baseline) and suggestion["sample"]["spans"] < 2 * baseline
        if hidden and not include_dismissed:
            continue
        suggestions.append(dict(suggestion, dismissed=hidden))
    return dict(
        metrics,
        generated_at=now, since=since,
        sample={"spans": len(spans), "sessions": len({(s["project_id"], s["session_id"]) for s in spans}),
                "projects": len({s["project_id"] for s in spans})},
        suggestions=suggestions, insufficient=insufficient,
    )


def dismiss(suggestion_id, now=None):
    """Record the user's dismissal of a current suggestion; it returns once its sample doubles.

    Always measured over every bound project: a suggestion's id does not depend on scope, so a
    baseline taken from a narrower report would make it reappear in the first wider one. Dismissing
    a hidden suggestion again resets its baseline to the current sample.
    """
    if not isinstance(suggestion_id, str) or not _SUGGESTION_ID.match(suggestion_id):
        raise UsageError("not a suggestion id: {}".format(suggestion_id), hint="Copy the id from `devteam insights report`.")
    now = int(time.time() if now is None else now)
    current = {s["id"]: s for s in report(include_dismissed=True, now=now)["suggestions"]}
    if suggestion_id not in current:
        raise UsageError(
            "no current suggestion has id {}".format(suggestion_id),
            hint="Run `devteam insights report` and copy an id from its suggestions.",
        )
    path = decisions_path()
    jsonio.ensure_dir(path.parent)
    # A lock names a pid, so it is machine-local (the store's `locks/`), never beside the portable record.
    with lock.store_lock("insights-decisions"):
        data = jsonio.read_json(path, default={"schema": DECISIONS_SCHEMA, "dismissed": {}})
        if not isinstance(data, dict) or not isinstance(data.get("dismissed", {}), dict):
            raise UsageError("{} is not a decisions record".format(path), hint="Fix or move the file by hand.")
        data.setdefault("schema", DECISIONS_SCHEMA)
        data.setdefault("dismissed", {})[suggestion_id] = {
            "dismissed_at": now, "sample_spans": current[suggestion_id]["sample"]["spans"],
        }
        jsonio.write_json_atomic(path, data)
    return {"dismissed": suggestion_id, "sample_spans": current[suggestion_id]["sample"]["spans"]}
