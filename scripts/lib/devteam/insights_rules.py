"""The optimization loop's rules: metrics in, evidence-backed suggestions out (ADR-0042).

Spec: ``docs/specs/optimization-loop.md`` § Rules. Pure: no I/O, so every rule is tested on
metrics alone. A rule fires only above its minimum sample; below it the subject is reported as
``insufficient``, never as a suggestion. A suggestion proposes; nothing here or anywhere in the
loop applies it.
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics

from . import versions

#: Minimum sample for an agent- or command-level rule.
MIN_SPANS = 10
MIN_SESSIONS = 3
MIN_RUNS = 5

NEVER_FINDS_RATE = 0.9
UNRELIABLE_RATE = 0.25
REGRESSION_GROWTH = 0.30
REGRESSION_COVERAGE = 0.8
NEEDLESS_ZERO_TOOL_SHARE = 0.5
BUILTIN_SHARE = 0.5
EFFORT_MAX_FAILURE = 0.05


_SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]{1,32})?$")


def _id(rule, subject):
    digest = hashlib.sha256(json.dumps([rule, subject], sort_keys=True).encode("utf-8")).hexdigest()
    return "{}:{}".format(rule, digest[:12])


def _suggest(rule, subject, title, action, evidence, spans, sessions, examples):
    return {
        "id": _id(rule, subject), "rule": rule, "subject": subject, "title": title, "action": action,
        "evidence": evidence, "sample": {"spans": spans, "sessions": sessions}, "examples": list(examples)[:3],
    }


def _enough(row):
    return row["spans"] >= MIN_SPANS and row["sessions"] >= MIN_SESSIONS


def _review_never_finds(agents, out, short):
    for row in agents:
        if row["kind"] != "review" or row.get("tier") == "repetitive":
            continue
        reviews = row["reviews"]
        rate = reviews["zero_findings_rate"]
        if rate is None or rate < NEVER_FINDS_RATE:
            continue
        subject = {"agent": row["agent"], "provider": row["provider"]}
        if reviews["count"] < MIN_SPANS or row["sessions"] < MIN_SESSIONS:
            short.append({"rule": "review-never-finds", "subject": subject,
                          "sample": {"spans": reviews["count"], "sessions": row["sessions"]}})
            continue
        out.append(_suggest(
            "review-never-finds", subject,
            "{} found nothing in {:.0%} of {} reviews".format(row["agent"], rate, reviews["count"]),
            "Consider a cheaper tier than `{}` or dropping it from default spawns — first check it is "
            "not missing real issues: zero findings is cheap, not necessarily good, and a QA pass that "
            "finds nothing against its criteria can simply be correct.".format(row.get("tier")),
            {"zero_findings_rate": rate, "reviews": reviews["count"], "tier": row.get("tier"),
             "tokens_mean": row["tokens_mean"]},
            reviews["count"], row["sessions"], row["examples"],
        ))


def _agent_unreliable(agents, out, short):
    for row in agents:
        rate = round(row["failed_rate"] + row["interrupted_rate"], 3)
        if rate < UNRELIABLE_RATE:
            continue
        subject = {"agent": row["agent"], "provider": row["provider"]}
        if not _enough(row):
            short.append({"rule": "agent-unreliable", "subject": subject,
                          "sample": {"spans": row["spans"], "sessions": row["sessions"]}})
            continue
        out.append(_suggest(
            "agent-unreliable", subject,
            "{} ends failed or interrupted in {:.0%} of {} runs".format(row["agent"], rate, row["spans"]),
            "Investigate its prompt, tools or timeouts; open the example sessions with `devteam tasks trace`.",
            {"failed_rate": row["failed_rate"], "interrupted_rate": row["interrupted_rate"]},
            row["spans"], row["sessions"], row["examples"],
        ))


def _command_cost_regression(versions_rows, out, short):
    groups = {}
    for row in versions_rows:
        if row["harness_version"] and _SEMVER.match(str(row["harness_version"])):
            groups.setdefault((row["command"], row["provider"]), []).append(row)
    for (command, provider), rows in groups.items():
        rows.sort(key=lambda r: versions.sort_key(r["harness_version"]))
        for before, after in zip(rows, rows[1:]):
            if not (before["tokens_per_run"] and after["tokens_per_run"]):
                continue
            growth = (after["tokens_per_run"] - before["tokens_per_run"]) / before["tokens_per_run"]
            if growth < REGRESSION_GROWTH:
                continue
            subject = {"command": command, "provider": provider,
                       "from": before["harness_version"], "to": after["harness_version"]}
            sample = before["runs"] + after["runs"]
            covered = min(before["usage_coverage"] or 0, after["usage_coverage"] or 0)
            if before["runs"] < MIN_RUNS or after["runs"] < MIN_RUNS or covered < REGRESSION_COVERAGE:
                short.append({"rule": "command-cost-regression", "subject": subject,
                              "sample": {"spans": sample, "sessions": None}})
                continue
            out.append(_suggest(
                "command-cost-regression", subject,
                "{} costs {:.0%} more tokens per run on {} than on {}".format(
                    "/devteam:{}".format(command) if command else "Turns with no command", growth,
                    after["harness_version"], before["harness_version"]),
                "Review what changed in this command, its agents and the skills they load between the two versions.",
                {"tokens_per_run": {before["harness_version"]: before["tokens_per_run"],
                                    after["harness_version"]: after["tokens_per_run"]},
                 "runs": {before["harness_version"]: before["runs"], after["harness_version"]: after["runs"]}},
                sample, None, list(after["examples"]) + list(before["examples"]),
            ))


def _needless_spawn(agents, out, short):
    for row in agents:
        if row["kind"] != "agent" or row["zero_tool_share"] is None or row["zero_tool_share"] < NEEDLESS_ZERO_TOOL_SHARE:
            continue
        subject = {"agent": row["agent"], "provider": row["provider"]}
        if row["tool_uses_known"] < MIN_SPANS or row["sessions"] < MIN_SESSIONS:
            short.append({"rule": "needless-spawn", "subject": subject,
                          "sample": {"spans": row["tool_uses_known"], "sessions": row["sessions"]}})
            continue
        out.append(_suggest(
            "needless-spawn", subject,
            "{} used no tool in {:.0%} of its runs".format(row["agent"], row["zero_tool_share"]),
            "Check the spawn-classifier triggers that start it (skills/shared/spawn-classifier/SKILL.md): "
            "a run with no tool call may not have needed the agent.",
            {"zero_tool_share": row["zero_tool_share"], "runs_with_known_tools": row["tool_uses_known"]},
            row["tool_uses_known"], row["sessions"], row["examples"],
        ))


def _builtin_heavy(commands, out, short):
    for row in commands:
        share = row["builtin_token_share"]
        if share is None or share < BUILTIN_SHARE:
            continue
        subject = {"command": row["command"], "provider": row["provider"]}
        if row["runs"] < MIN_RUNS:
            short.append({"rule": "builtin-heavy-command", "subject": subject,
                          "sample": {"spans": row["runs"], "sessions": row["sessions"]}})
            continue
        out.append(_suggest(
            "builtin-heavy-command", subject,
            "Built-in agents spend {:.0%} of the tokens of {}".format(
                share, "/devteam:{}".format(row["command"]) if row["command"] else "turns with no command"),
            "Look for the context those explorations rebuild every time — a skill or a project doc loaded "
            "up front may spare them.",
            {"builtin_token_share": share, "tokens_per_run": row["tokens_per_run"]},
            row["runs"], row["sessions"], row["examples"],
        ))


def _effort_candidate(agents, low, excluded, out, short):
    baseline = sorted(r["tokens_mean"] for r in agents if r["agent"] in low and r["tokens_mean"] is not None)
    if not baseline:
        return
    median = statistics.median(baseline)
    for row in agents:
        # Reviewers are out by kind. `reasoning` agents are out by this rule's own judgment
        # (ADR-0042 spec, effort-candidate row): planning and architecture work is open-ended,
        # so a low cost there says nothing about how much reasoning it needs. `excluded` comes
        # from the canonical `_why_not_<agent>` notes in tiers.json, never from a copy here.
        if (row["kind"] != "agent" or row.get("tier") == "reasoning" or row["agent"] in low
                or row["agent"] in excluded or row["tokens_mean"] is None or row["tokens_mean"] > median):
            continue
        if row["failed_rate"] + row["interrupted_rate"] >= EFFORT_MAX_FAILURE:
            continue
        subject = {"agent": row["agent"], "provider": row["provider"]}
        if not _enough(row):
            short.append({"rule": "effort-candidate", "subject": subject,
                          "sample": {"spans": row["spans"], "sessions": row["sessions"]}})
            continue
        out.append(_suggest(
            "effort-candidate", subject,
            "{} costs no more than the agents already on `low` effort".format(row["agent"]),
            "Evaluate a `low` entry in tiers.json `agent_effort` — only if the agent is handed what to check "
            "(tiers.json `_why_qa_specialist`); an agent whose job is to discover what to check must stay off it.",
            {"tokens_mean": row["tokens_mean"], "low_effort_median": median,
             "failed_or_interrupted": round(row["failed_rate"] + row["interrupted_rate"], 3)},
            row["spans"], row["sessions"], row["examples"],
        ))


def evaluate(metrics, low_effort_agents=(), effort_excluded=()):
    """``(suggestions, insufficient)`` for ``metrics`` (``insights.report``'s groups).

    ``low_effort_agents`` already carry a ``low`` override; ``effort_excluded`` must never get one.
    """
    out, short = [], []
    agents = metrics.get("agents", [])
    _review_never_finds(agents, out, short)
    _agent_unreliable(agents, out, short)
    _command_cost_regression(metrics.get("versions", []), out, short)
    _needless_spawn(agents, out, short)
    _builtin_heavy(metrics.get("commands", []), out, short)
    _effort_candidate(agents, set(low_effort_agents), set(effort_excluded), out, short)
    return out, short
