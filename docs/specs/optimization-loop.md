---
status: approved
touches: [backend]
depends_on: [execution-trace.md]
---

## Spec — Optimization loop

### User Story
As a developer tuning the harness, I want a report that turns the execution traces of all my bound projects into concrete, evidence-backed suggestions, such as tier, effort, spawn and cost regressions, so that I can change the harness on numbers instead of guesses, and decide each change myself.

### Context
The execution trace (`execution-trace.md`, ADR-0041) records every agent spawn with cost and outcome. This spec reads it across sessions. Decision record: [ADR-0042](../development/adrs/0042-optimization-loop-suggests-harness-changes-from-execution-traces-and-never-applies-them.md).

#### Metrics — `devteam insights report [--project <id>…] [--since <epoch>] [--all] [--json]`

Read-only. The command walks every bound project (or `--project`), and every trace whose last update is at or after `--since`.

| Group | Key | Fields |
|---|---|---|
| `agents` | agent, provider | `kind`, `tier`, `spans`, `sessions`, `failed_rate`, `interrupted_rate`, `duration_p50`, `duration_p90` (s), `tokens_mean`, `tokens_p90` (spans with usage only), `usage_coverage`, `models` (model → spans), `reviews` (`count`, `zero_findings_rate`, `findings_mean`; review spans with a known `findings` only) |
| `commands` | command, provider | `runs` (distinct session + turn), `tokens_per_run`, `agents_per_run`, `builtin_token_share`, `usage_coverage` |
| `versions` | harness_version, command, provider | `runs`, `tokens_per_run`, `usage_coverage` |
| `reviews` | provider | `windows`, `unread_rate`, `findings_mean`, `fixed_after_findings` (from the board's review windows; per provider, so one provider's capture gap, such as Codex v2 reviewer windows settled unread, is not read as every provider's reliability) |

A turn with no command counts under command `null`. Percentiles are nearest-rank.

#### Rules — evidence-backed suggestions

| Rule id | Fires when | Suggests |
|---|---|---|
| `review-never-finds` | a review agent on a non-`repetitive` tier, ≥ 10 reviews with known findings across ≥ 3 sessions, `zero_findings_rate` ≥ 0.9 | a cheaper tier, or dropping it from default spawns, after checking it is not missing real issues |
| `agent-unreliable` | ≥ 10 spans across ≥ 3 sessions, (`failed` + `interrupted`) / spans ≥ 0.25 | investigating the agent's prompt, tools or timeouts |
| `command-cost-regression` | two consecutive harness versions for one command and provider, each with ≥ 5 runs and usage coverage ≥ 0.8, and `tokens_per_run` grew ≥ 30% | reviewing what changed in that command between the two versions |
| `needless-spawn` | a non-review, non-built-in agent with ≥ 10 spans with a known `tool_uses` across ≥ 3 sessions, ≥ 50% of them with zero tool uses | checking the spawn-classifier triggers that start it |
| `builtin-heavy-command` | a command with ≥ 5 runs whose `builtin_token_share` ≥ 0.5 | a skill or context load that spares the built-in exploration |
| `effort-candidate` | a non-review agent outside the `reasoning` tier and not named by a `tiers.json` `_why_not_<agent>` note (today `security-specialist`), with no `agent_effort` override, ≥ 10 spans across ≥ 3 sessions, failure rate < 0.05, and `tokens_mean` ≤ the median `tokens_mean` of the agents that do have `low` | evaluating a `low` effort override; the suggestion quotes `tiers.json` `_why_qa_specialist` (is the agent handed what to check?) |

A suggestion is `{id, rule, subject, title, action, evidence, sample: {spans, sessions}, examples: [session ids ≤ 3]}`. Its `id` is stable for the same rule and subject. Below a rule's minimum sample, the subject appears in `insufficient` as `{rule, subject, sample}`, never as a suggestion.

#### Decisions — `data/insights-decisions.json`

`devteam insights dismiss <id>` (always measured over every bound project; the id does not depend on scope) records `{id: {"dismissed_at", "sample_spans"}}` at the top of the data store (portable, ADR-0013), under a lock and atomically. A dismissed suggestion is omitted, unless `--all` is passed (then it is flagged `dismissed: true`), until its sample has at least doubled. Dismissing a hidden suggestion again resets its baseline to the current sample.

Only well-formed traces are read: a file over 4 MiB, a session id outside the `session_key` charset, or an agent, model or command name outside `[A-Za-z0-9_.:-]{1,64}` is skipped, so text recorded by a hook can never become a suggestion title or a shell argument. A usage object with no counts is unknown usage, not zero tokens. The `effort-candidate` median is the statistical median.

#### Command — `/devteam:insights`

Runs `devteam --json insights report` and presents the metrics and suggestions. For each suggestion, it asks one `AskUserQuestion`: **Plan the change**, **Dismiss**, or **Later**. **Plan the change** hands off to the plan-mode flow with the evidence. In a bound project that plan targets a project-level override, or drafts upstream feedback for a tier or effort; it edits the canonical files only inside the dev-team-agents repository. **Dismiss** runs `devteam insights dismiss`. The command never edits a file itself.

### Acceptance Criteria

**Scenario S1: metrics across projects**
- Given traces in two bound projects
- When `devteam insights report --json` runs
- Then `agents`, `commands` and `versions` aggregate spans from both, keyed by agent, command, harness version and provider

**Scenario S2: no suggestion below the sample**
- Given an agent that matches a rule's condition but has fewer spans or sessions than the rule's minimum
- When the report runs
- Then no suggestion is emitted for it, and it is listed under `insufficient`

**Scenario S3: every rule fires on its evidence**
- Given traces that satisfy one rule's condition above its sample
- When the report runs
- Then a suggestion with that rule id, its subject, its sample and up to three example sessions is emitted, and the same id is produced on the next run

**Scenario S4: cost regression across harness versions**
- Given one command whose runs under version B cost ≥ 30% more tokens than under the previous version A, each with ≥ 5 runs
- When the report runs
- Then a `command-cost-regression` suggestion names both versions and their `tokens_per_run`

**Scenario S5: dismiss until the evidence doubles**
- Given a suggestion the user dismissed at a sample of N spans
- When the report runs again with fewer than 2N spans, and later with 2N or more
- Then it is omitted the first time (shown with `dismissed: true` under `--all`), and shown again the second time

**Scenario S6: the command never applies a change**
- Given suggestions in the report
- When the user runs `/devteam:insights` and chooses any option
- Then no file of the harness is edited by the command; **Plan the change** opens a plan, and **Dismiss** only writes the decision record

**Scenario S7: unknown usage is not counted as zero**
- Given spans with `usage: null`
- When token metrics are computed
- Then those spans are excluded from token means and percentiles, and `usage_coverage` reports the share that had usage

### Out of Scope
- Applying any change automatically
- Judging answer quality (LLM-as-judge)
- A desktop-app view; it can consume `--json` later
- Sending metrics off the machine

### Dependencies
- **Depends on**: `execution-trace.md`
- **Blocks**: none

### Amendment Log
- 2026-10-19 | main conversation | Review windows grouped per provider; accepted suggestions land in a project override or upstream feedback in a bound project; the dismissal lock is machine-local | Branch review findings (architect A1, A2, A6)
