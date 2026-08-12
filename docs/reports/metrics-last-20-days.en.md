# DevTeam Agents Usage Metrics — Last 20 Days

**Window:** 2026-07-23 18:17 UTC → 2026-08-12 15:44 UTC (20 days)
**Generated at:** 2026-08-12
**Timezone used for time-based metrics:** UTC
**Total events in window:** 1,484 (2 manual test events `__manual_verification_test__` and 1 malformed event with null `agent_name`/`model` excluded from 1,487 raw rows)

---

## 1. Most-called commands

Only 7 `command_invoked` events fell in the window — too small a sample for a meaningful ranking, listed for completeness.

| Command | Calls |
|---|---|
| `architect` | 2 |
| `push` | 1 |
| `status` | 1 |
| `sync-rules` | 1 |
| `pr` | 1 |
| `review` | 1 |

**Takeaway:** `command_invoked` volume (7) is far below `agent_completed` volume (803) in the same window — most of the period's work was driven directly through agent spawns rather than the `/devteam:*` slash-command layer, or the event is simply under-firing. Worth checking the command-name matcher in `scripts/hooks/pre-tool-use/02b-telemetry.sh` against real usage.

---

## 2. Most-invoked agents

Ranked by `agent_completed` (no `agent_spawned` event appeared in this window, so completion counts are used as a proxy). Top 10.

| Rank | Agent | Completions | % |
|---|---|---|---|
| 1 | **backend-developer** | 195 | 24.3% |
| 2 | frontend-developer | 152 | 18.9% |
| 3 | software-architect | 90 | 11.2% |
| 4 | security-specialist | 73 | 9.1% |
| 5 | devops-specialist | 71 | 8.8% |
| 6 | frontend-test-specialist | 61 | 7.6% |
| 7 | backend-test-specialist | 54 | 6.7% |
| 8 | test-author | 45 | 5.6% |
| 9 | qa-specialist | 13 | 1.6% |
| 9 | technical-writer | 13 | 1.6% |

**Takeaway:** `backend-developer` is the most-invoked agent (24.3% of all completions), followed by `frontend-developer` (18.9%) — together, 43.2% of all agent activity in the window.

---

## 3. Model ranking grouped by provider

| Provider | Model | Calls | % |
|---|---|---|---|
| claude | **claude-sonnet-5** | 570 | 71.0% |
| claude | claude-opus-5[1m] | 175 | 21.8% |
| claude | claude-haiku-4-5-20251001 | 58 | 7.2% |

**Takeaway:** all recorded activity ran on Claude — 71.0% on Sonnet 5, 21.8% on Opus 5 (1M context), 7.2% on Haiku 4.5. No other provider appeared in the window. (The 2 manual `__manual_verification_test__` events, run on `claude-sonnet-4-5`, were excluded from this ranking — see the header note.)

---

## 4. Token consumption ranking

Total tokens (input + output + cache_creation + cache_read) per agent, descending. Top 10.

| Rank | Agent | Total tokens | % | Calls |
|---|---|---|---|---|
| 1 | **backend-developer** | 693,294,212 | 29.3% | 195 |
| 2 | frontend-developer | 388,745,340 | 16.4% | 152 |
| 3 | test-author | 371,111,987 | 15.7% | 45 |
| 4 | software-architect | 300,079,305 | 12.7% | 90 |
| 5 | security-specialist | 179,515,358 | 7.6% | 73 |
| 6 | frontend-test-specialist | 153,399,264 | 6.5% | 61 |
| 7 | devops-specialist | 116,652,699 | 4.9% | 71 |
| 8 | backend-test-specialist | 53,496,496 | 2.3% | 54 |
| 9 | qa-specialist | 32,014,392 | 1.4% | 13 |
| 10 | backend-reviewer | 19,713,773 | 0.8% | 6 |

**Window totals:** input 959,983 · output 6,890,257 · cache creation 175,567,933 · **cache read 2,183,534,418**

**Takeaway:** `backend-developer` leads both in number of calls and total tokens. Cache-read tokens dominate the total by a wide margin across every agent (see § 12).

---

## 5. Agents with the highest average tokens per call

Top 10.

| Rank | Agent | Avg tokens/call | % | Calls |
|---|---|---|---|---|
| 1 | **test-author** | 8,246,933 | 22.1% | 45 |
| 2 | backend-developer | 3,555,354 | 9.5% | 195 |
| 3 | software-architect | 3,334,214 | 8.9% | 90 |
| 4 | backend-reviewer | 3,285,628 | 8.8% | 6 |
| 5 | frontend-reviewer | 2,836,297 | 7.6% | 6 |
| 6 | frontend-developer | 2,557,535 | 6.9% | 152 |
| 7 | frontend-test-specialist | 2,514,742 | 6.7% | 61 |
| 8 | qa-specialist | 2,462,645 | 6.6% | 13 |
| 9 | security-specialist | 2,459,114 | 6.6% | 73 |
| 10 | devops-specialist | 1,642,995 | 4.4% | 71 |

*(`command_invoked` carries no token data, so a per-command average cannot be computed from this event. `%` is each agent's share of the sum of all agents' averages.)*

**Takeaway:** `test-author` has by far the highest average per call (2.3× the runner-up) despite a middling call volume — each invocation does an unusually large amount of context work relative to its peers.

---

## 6. Country, state, and city ranking

| Country | Events | % |
|---|---|---|
| **Brazil** | 1,483 | 99.9% |
| France | 1 | 0.1% |

| State/Region | Events | % |
|---|---|---|
| **Ceará** | 1,460 | 98.4% |
| São Paulo | 23 | 1.5% |
| Île-de-France | 1 | 0.1% |

| City | Events | % |
|---|---|---|
| **Fortaleza** | 1,460 | 98.4% |
| Bauru | 23 | 1.5% |
| Aulnay-sous-Bois | 1 | 0.1% |

> 🔒 **Privacy note (out of scope for this report, already resolved):** the IP-anonymization fix on the telemetry backend is not retroactive — most events in this 20-day window were ingested **before** the fix and still retain the raw `$ip` property stored (identified in this report's previous run, on 2026-08-12). Only events captured after activation stop retaining the IP. The 20-day window needs to "roll" past the fix date for this note to disappear from future runs of this report.

---

## 7. Version ranking used in the period

Top 10.

| Rank | Version | Events | % |
|---|---|---|---|
| 1 | **v2.44.0** | 891 | 60.0% |
| 2 | v2.29.0 | 149 | 10.0% |
| 3 | v1.8.2 | 111 | 7.5% |
| 4 | v2.39.2 | 99 | 6.7% |
| 5 | v1.8.1 | 46 | 3.1% |
| 5 | *unknown* | 46 | 3.1% |
| 7 | v2.31.0 | 19 | 1.3% |
| 8 | v1.11.0 | 16 | 1.1% |
| 9 | v2.15.1 | 10 | 0.7% |
| 10 | v2.30.1 | 9 | 0.6% |

**Takeaway:** `v2.44.0` (the current tip) dominates with 60.0% of events, expected since most of the volume comes from today's session. The long tail of older versions (v1.8.x, v2.7–v2.41.x) reflects historical events retained within the 20-day window, not concurrent installs. `unknown` (46 events, 3.1%) comes from `install`/`update`/`agent_completed` events captured before the version was resolved.

---

## 8. Models used, grouped by agent

| Agent | Model(s) used | Note |
|---|---|---|
| backend-developer | claude-sonnet-5 (195) | single model |
| frontend-developer | claude-sonnet-5 (152) | single model |
| software-architect | claude-opus-5[1m] (90) | single model |
| security-specialist | claude-opus-5[1m] (73) | single model |
| devops-specialist | claude-sonnet-5 (71) | single model |
| frontend-test-specialist | claude-sonnet-5 (61) | single model |
| backend-test-specialist | claude-sonnet-5 (54) | single model |
| test-author | claude-haiku-4-5-20251001 (45) | single model |
| qa-specialist | claude-sonnet-5 (13) | single model |
| technical-writer | claude-haiku-4-5-20251001 (13) | single model |
| code-reviewer | claude-sonnet-5 (12) | single model |
| product-analyst | claude-opus-5[1m] (12) | single model |
| backend-reviewer | claude-sonnet-5 (6) | single model |
| frontend-reviewer | claude-sonnet-5 (6) | single model |

**Takeaway:** every agent in this window called **exactly one** model — no agent split across multiple models or providers. This matches `tiers.json`'s tier→model mapping in `CLAUDE.md` (`reasoning`→opus, `backend-exec`/`frontend`→sonnet, `repetitive`→haiku), with no observed drift between the configured tier and the resolved model.

---

## 9. Busiest days and hours (UTC)

**By day of week:**

| Day | Events | % |
|---|---|---|
| **Wednesday** | 1,032 | 69.5% |
| Thursday | 151 | 10.2% |
| Friday | 137 | 9.2% |
| Saturday | 47 | 3.2% |
| Tuesday | 47 | 3.2% |
| Monday | 43 | 2.9% |
| Sunday | 30 | 2.0% |

**By hour of day (UTC):**

| Hour | Events | % |
|---|---|---|
| **13** | **298** | **20.1%** |
| **01** | **231** | **15.6%** |
| **10** | **188** | **12.7%** |
| 14 | 134 | 9.0% |
| 15 | 117 | 7.9% |
| 02 | 93 | 6.3% |
| 22 | 52 | 3.5% |
| 00 | 49 | 3.3% |
| 19 | 49 | 3.3% |
| 20 | 41 | 2.8% |
| 18 | 40 | 2.7% |
| 23 | 33 | 2.2% |
| 03 | 28 | 1.9% |
| 17 | 25 | 1.7% |
| 21 | 25 | 1.7% |
| 04 | 17 | 1.1% |
| 16 | 18 | 1.2% |
| 07 | 14 | 0.9% |
| 11 | 14 | 0.9% |
| 12 | 11 | 0.7% |
| 06 | 9 | 0.6% |
| 05 | 1 | 0.1% |
| 08 | 0 | 0.0% |
| 09 | 0 | 0.0% |

**Takeaway:** ⚠️ heavily skewed by today (2026-08-12, a Wednesday, contributed 996 of 1,484 events — see the daily trend in § 11). The peak hours, 13h and 01h UTC, correspond to roughly 10am and 10pm in `America/Fortaleza` (UTC-3, the dominant geography from § 6) — consistent with a late-night and mid-morning work pattern for this single contributor. Treat the day-of-week ranking as unreliable until volume is more spread across weeks.

---

## 10. New installs vs. updates rate

| Event | Count |
|---|---|
| `first_install` | 10 |
| `install` (reinstall/update via the installer) | 76 |
| `update` (manual update via `update.sh`) | 34 |

**Takeaway:** reinstalls/updates outnumber fresh installs ~11:1 in this window — expected for a local copy under active development, reinstalled/updated repeatedly during testing, not organic new-user growth.

---

## 11. Daily event volume

| Date | Events |
|---|---|
| 2026-07-23 | 28 |
| 2026-07-24 | 93 |
| 2026-07-25 | 37 |
| 2026-07-26 | 19 |
| 2026-07-27 | 6 |
| 2026-07-28 | 22 |
| 2026-07-29 | 2 |
| 2026-07-30 | 4 |
| 2026-07-31 | 7 |
| 2026-08-01 | 4 |
| 2026-08-02 | 8 |
| 2026-08-03 | 30 |
| 2026-08-04 | 11 |
| 2026-08-05 | 31 |
| 2026-08-06 | 119 |
| 2026-08-07 | 37 |
| 2026-08-08 | 6 |
| 2026-08-09 | 3 |
| 2026-08-10 | 7 |
| 2026-08-11 | 14 |
| **2026-08-12** | **996** |

**Takeaway:** the window is dominated by today (67.1% of total volume) — consistent with this report being generated mid-session on 2026-08-12. Excluding today, 2026-08-06 (119) and 2026-07-24 (93) were the next highest-volume days.

---

## 12. Cache efficiency

| Metric | Value |
|---|---|
| Total input tokens | 959,983 |
| Total cache-read tokens | 2,183,534,418 |
| Total cache-creation tokens | 175,567,933 |
| **Cache-read : input ratio** | **~2,275 : 1** |

**Takeaway:** cache-reads vastly outnumber fresh input tokens across the whole window — the prompt-cache system is doing the overwhelming majority of context delivery, expected behavior for repeated agent invocations sharing a cached system/skill context within the 1-hour TTL. This is a strong efficiency signal, not a concern.

---

## 13. Session-end distribution

| `stop_hook_active` | Sessions |
|---|---|
| `false` | 532 |
| `true` | 22 |

**Takeaway:** 96.0% of sessions ended with the stop hook inactive (i.e. a clean, unblocked close) — only 4.0% hit an active stop-hook condition (mandatory session summary, lint failures, etc.) at session end.

---

## 14. Commands/agents never used in the period

Cross-referencing the observed `agent_completed` names against the agent roster in `agents/*.md` (18 agents total).

**Agents with zero activity in this window:**

| Agent | Completions |
|---|---|
| database-specialist | 0 |
| mobile-developer | 0 |
| ui-ux-designer | 0 |
| seo-specialist | 0 |
| setup-assistant | 0 |

**Command coverage:**

| Metric | Value |
|---|---|
| Documented commands (`scripts/lib/commands.json`) | ~25 |
| Commands observed in the window | 6 (`architect`, `push`, `status`, `sync-rules`, `pr`, `review`) |
| Reliable sample to infer coverage | No — `command_invoked` volume (7 events) is suspiciously low relative to `agent_completed` (803), see § 1 |

---

## Machine-readable summary for LLMs

```yaml
report:
  title: "DevTeam Agents usage metrics — last 20 days"
  window:
    start_utc: "2026-07-23T18:17:25Z"
    end_utc: "2026-08-12T15:44:41Z"
    days: 20
  generated_at: "2026-08-12"
  total_events: 1484
  excluded_events:
    manual_test: 2
    malformed: 1

  caveats:
    - "Single developer/machine sample — not representative of the user base."
    - "command_invoked has very low volume (7) vs agent_completed (803) — possible instrumentation gap."
    - "67% of total volume concentrated on the report's generation day (2026-08-12)."
    - "Day-of-week ranking unreliable due to today's spike."

  event_type_counts:
    agent_completed: 803
    session_end: 554
    install: 76
    update: 34
    first_install: 10
    command_invoked: 7

  top_commands:
    - {command: "architect", calls: 2}
    - {command: "push", calls: 1}
    - {command: "status", calls: 1}
    - {command: "sync-rules", calls: 1}
    - {command: "pr", calls: 1}
    - {command: "review", calls: 1}

  top_agents_by_calls:
    - {agent: "backend-developer", calls: 195, percentage: 24.3}
    - {agent: "frontend-developer", calls: 152, percentage: 18.9}
    - {agent: "software-architect", calls: 90, percentage: 11.2}
    - {agent: "security-specialist", calls: 73, percentage: 9.1}
    - {agent: "devops-specialist", calls: 71, percentage: 8.8}
    - {agent: "frontend-test-specialist", calls: 61, percentage: 7.6}
    - {agent: "backend-test-specialist", calls: 54, percentage: 6.7}
    - {agent: "test-author", calls: 45, percentage: 5.6}
    - {agent: "qa-specialist", calls: 13, percentage: 1.6}
    - {agent: "technical-writer", calls: 13, percentage: 1.6}

  models_by_provider:
    claude:
      - {model: "claude-sonnet-5", calls: 570, percentage: 71.0}
      - {model: "claude-opus-5[1m]", calls: 175, percentage: 21.8}
      - {model: "claude-haiku-4-5-20251001", calls: 58, percentage: 7.2}

  model_by_agent:
    backend-developer: "claude-sonnet-5"
    frontend-developer: "claude-sonnet-5"
    software-architect: "claude-opus-5[1m]"
    security-specialist: "claude-opus-5[1m]"
    devops-specialist: "claude-sonnet-5"
    frontend-test-specialist: "claude-sonnet-5"
    backend-test-specialist: "claude-sonnet-5"
    test-author: "claude-haiku-4-5-20251001"
    qa-specialist: "claude-sonnet-5"
    technical-writer: "claude-haiku-4-5-20251001"
    code-reviewer: "claude-sonnet-5"
    product-analyst: "claude-opus-5[1m]"
    backend-reviewer: "claude-sonnet-5"
    frontend-reviewer: "claude-sonnet-5"
    note: "No agent used more than one model in the window — no drift from tiers.json mapping."

  window_total_tokens:
    input: 959983
    output: 6890257
    cache_creation: 175567933
    cache_read: 2183534418
    cache_read_to_input_ratio: "~2275:1"

  tokens_by_agent_total_desc_top10:
    - {agent: "backend-developer", total: 693294212, percentage: 29.3, calls: 195}
    - {agent: "frontend-developer", total: 388745340, percentage: 16.4, calls: 152}
    - {agent: "test-author", total: 371111987, percentage: 15.7, calls: 45}
    - {agent: "software-architect", total: 300079305, percentage: 12.7, calls: 90}
    - {agent: "security-specialist", total: 179515358, percentage: 7.6, calls: 73}
    - {agent: "frontend-test-specialist", total: 153399264, percentage: 6.5, calls: 61}
    - {agent: "devops-specialist", total: 116652699, percentage: 4.9, calls: 71}
    - {agent: "backend-test-specialist", total: 53496496, percentage: 2.3, calls: 54}
    - {agent: "qa-specialist", total: 32014392, percentage: 1.4, calls: 13}
    - {agent: "backend-reviewer", total: 19713773, percentage: 0.8, calls: 6}

  tokens_by_agent_avg_desc_top10:
    - {agent: "test-author", avg: 8246933, percentage: 22.1}
    - {agent: "backend-developer", avg: 3555354, percentage: 9.5}
    - {agent: "software-architect", avg: 3334214, percentage: 8.9}
    - {agent: "backend-reviewer", avg: 3285628, percentage: 8.8}
    - {agent: "frontend-reviewer", avg: 2836297, percentage: 7.6}
    - {agent: "frontend-developer", avg: 2557535, percentage: 6.9}
    - {agent: "frontend-test-specialist", avg: 2514742, percentage: 6.7}
    - {agent: "qa-specialist", avg: 2462645, percentage: 6.6}
    - {agent: "security-specialist", avg: 2459114, percentage: 6.6}
    - {agent: "devops-specialist", avg: 1642995, percentage: 4.4}

  geography:
    countries: [{name: "Brazil", events: 1483, percentage: 99.9}, {name: "France", events: 1, percentage: 0.1}]
    states: [{name: "Ceara", events: 1460, percentage: 98.4}, {name: "Sao Paulo", events: 23, percentage: 1.5}, {name: "Ile-de-France", events: 1, percentage: 0.1}]
    cities: [{name: "Fortaleza", events: 1460, percentage: 98.4}, {name: "Bauru", events: 23, percentage: 1.5}, {name: "Aulnay-sous-Bois", events: 1, percentage: 0.1}]

  top_versions_top10:
    - {version: "v2.44.0", events: 891, percentage: 60.0}
    - {version: "v2.29.0", events: 149, percentage: 10.0}
    - {version: "v1.8.2", events: 111, percentage: 7.5}
    - {version: "v2.39.2", events: 99, percentage: 6.7}
    - {version: "v1.8.1", events: 46, percentage: 3.1}
    - {version: "unknown", events: 46, percentage: 3.1}
    - {version: "v2.31.0", events: 19, percentage: 1.3}
    - {version: "v1.11.0", events: 16, percentage: 1.1}
    - {version: "v2.15.1", events: 10, percentage: 0.7}
    - {version: "v2.30.1", events: 9, percentage: 0.6}

  usage_by_weekday_utc:
    wednesday: {events: 1032, percentage: 69.5}
    thursday: {events: 151, percentage: 10.2}
    friday: {events: 137, percentage: 9.2}
    saturday: {events: 47, percentage: 3.2}
    tuesday: {events: 47, percentage: 3.2}
    monday: {events: 43, percentage: 2.9}
    sunday: {events: 30, percentage: 2.0}

  peak_usage_by_hour_utc_top3:
    - {hour: 13, events: 298, percentage: 20.1}
    - {hour: 1, events: 231, percentage: 15.6}
    - {hour: 10, events: 188, percentage: 12.7}

  installs:
    first_install: 10
    install: 76
    update: 34
    reinstall_to_new_ratio: "~11:1"

  cache_efficiency:
    cache_read_to_input_ratio: "~2275:1"
    interpretation: "positive — high context reuse via prompt cache"

  session_end:
    stop_hook_active_false: 532
    stop_hook_active_true: 22
    clean_percentage: "96%"

  zero_usage_coverage:
    agents_no_activity:
      - "database-specialist"
      - "mobile-developer"
      - "ui-ux-designer"
      - "seo-specialist"
      - "setup-assistant"
    commands_no_activity_reliable: false
    reason: "command_invoked sample too small (7 events) to infer coverage"

  open_questions_for_next_window:
    - "Does command_invoked keep under-firing relative to agent_completed?"
    - "Does version: unknown still appear after reviewing state.json read/write ordering?"
    - "Does geography reflect real users beyond the dev machine yet?"
```
