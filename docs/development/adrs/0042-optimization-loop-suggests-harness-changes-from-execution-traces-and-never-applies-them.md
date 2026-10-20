# ADR-0042: Optimization loop suggests harness changes from execution traces and never applies them

**Date:** 2026-10-19  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/insights.py`, `scripts/lib/devteam/insights_rules.py`, `commands/insights.md`  
**Relates to:** [ADR-0041](0041-execution-trace-kept-beside-the-task-board-record-as-one-span-per-agent-spawn.md) (execution trace), [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (portable vs machine-local), [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (`--json` contract)

## Context

The execution trace (ADR-0041) records, per agent spawn, its status, duration, tokens, model, review findings, the `/devteam:*` command of its turn and the harness version. Nothing reads it across sessions. Decisions such as which tier an agent runs on, which agents get the `low` effort override, or which agents the spawn-classifier starts were all made by judgment, with no cost or reliability data behind them. The `tiers.json` notes on `security-specialist` and `qa-specialist` show what such a decision costs when it is made by pattern-matching.

## Decision

1. **Three layers, each testable on its own.**
   - `devteam insights report` aggregates traces and the board's review windows from every bound project into metrics, deterministically.
   - `insights_rules.py` turns those metrics into suggestions. It is pure: metrics in, suggestions out.
   - `/devteam:insights` presents the suggestions and asks the user about each one.
2. **Suggest, never apply.** No layer edits `tiers.json`, an agent, a skill or the classifier. A suggestion the user accepts enters the normal plan-mode flow and is reviewed like any other change.
3. **Every suggestion carries its evidence:** the rule id, the threshold, the sample (spans and sessions) and up to three example session ids. A rule fires only above a minimum sample, and below it the report says "insufficient data". Metrics are grouped by `harness_version`, so a cost regression is only claimed between two consecutive versions that each have a sample.
4. **Dismissals are user decisions, so they are portable.** They live in `data/insights-decisions.json` at the top of the data store (ADR-0013), written under a lock and atomically. A dismissed suggestion comes back only once its sample has at least doubled. Traces stay machine-local; only the user's decision travels.
5. **Local only.** Nothing the loop computes is sent off the machine.

## Consequences

### Positive
- Tier, effort and spawn decisions can be argued from numbers the harness already collects, per provider.
- A cost regression after an update shows up as a named rule with two versions and their figures.

### Negative
- Rules are heuristics over mechanical signals (cost, failures, findings); they say nothing about answer quality. A cheap reviewer that misses bugs looks good to the "never finds" rule. The rule text says so, and the decision stays human.
- Sessions recorded before ADR-0041 have no trace, so early reports are mostly "insufficient data".

### Neutral
- The decision record is project-independent, because suggestions are about agents and commands, which are the same in every bound project.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Ask an LLM to read raw traces and propose improvements | Costly, not reproducible, and its claims carry no evidence the user can check |
| Apply low-risk suggestions automatically (e.g. effort `low`) | Effort overrides the session's level and changes cost and quality for every user (CLAUDE.md, Effort is deliberately sparse); it must stay a reviewed change |
| Store dismissals per project, machine-local | A dismissal is a user decision about a shared agent; it would reappear on every other machine and project |
