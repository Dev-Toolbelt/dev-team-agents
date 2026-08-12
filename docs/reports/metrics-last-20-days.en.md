# PostHog Usage Metrics — Last 20 Days

**Window:** 2026-07-23 18:17 UTC → 2026-08-12 15:44 UTC (20 days, `now() - INTERVAL 20 DAY`)
**Generated at:** 2026-08-12
**Timezone used for time-based metrics:** UTC (raw PostHog `timestamp`)
**Total events in window:** 1,484 (2 manual test events `__manual_verification_test__` and 1 malformed event with null `agent_name`/`model` excluded from 1,487 raw rows)
**Source:** PostHog project `430371` ("Default project"), `events` table via HogQL, generated per `docs/prompts/posthog-metrics-report.md`

> ⚠️ **Sample caveat:** this data reflects the local sessions of a single
> developer (the geographic distribution below shows why). It is **not**
> representative of the broader install base — `agent_spawned` and
> `command_invoked` in particular carry very low volume in this window and
> should not be read as an adoption signal yet.

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

## 2. Most-called agents

Ranked by `agent_completed` (no `agent_spawned` event appeared in this window, so completion counts are used as a proxy).

| Rank | Agent | Completions |
|---|---|---|
| 1 | **backend-developer** | 195 |
| 2 | frontend-developer | 152 |
| 3 | software-architect | 90 |
| 4 | security-specialist | 73 |
| 5 | devops-specialist | 71 |
| 6 | frontend-test-specialist | 61 |
| 7 | backend-test-specialist | 54 |
| 8 | test-author | 45 |
| 9 | qa-specialist | 13 |
| 9 | technical-writer | 13 |
| 11 | code-reviewer | 12 |
| 11 | product-analyst | 12 |
| 13 | backend-reviewer | 6 |
| 13 | frontend-reviewer | 6 |

**Takeaway:** `backend-developer` is the most-invoked agent (24.3% of all completions), followed by `frontend-developer` (18.9%) — together, 43.2% of all agent activity in the window.

---

## 3. Model usage ranking, grouped by provider

| Provider | Model | Calls |
|---|---|---|
| claude | **claude-sonnet-5** | 570 |
| claude | claude-opus-5[1m] | 175 |
| claude | claude-haiku-4-5-20251001 | 58 |

**Takeaway:** all recorded activity ran on Claude — 71.0% on Sonnet 5, 21.8% on Opus 5 (1M context), 7.2% on Haiku 4.5. No other provider appeared in the window. (The 2 manual `__manual_verification_test__` events, run on `claude-sonnet-4-5`, were excluded from this ranking — see the header note.)

---

## 4. Token consumption ranking

Total tokens (input + output + cache_creation + cache_read) per agent, descending.

| Rank | Agent | Total tokens | Calls |
|---|---|---|---|
| 1 | **backend-developer** | 693,294,212 | 195 |
| 2 | frontend-developer | 388,745,340 | 152 |
| 3 | test-author | 371,111,987 | 45 |
| 4 | software-architect | 300,079,305 | 90 |
| 5 | security-specialist | 179,515,358 | 73 |
| 6 | frontend-test-specialist | 153,399,264 | 61 |
| 7 | devops-specialist | 116,652,699 | 71 |
| 8 | backend-test-specialist | 53,496,496 | 54 |
| 9 | qa-specialist | 32,014,392 | 13 |
| 10 | backend-reviewer | 19,713,773 | 6 |
| 11 | frontend-reviewer | 17,017,787 | 6 |
| 12 | technical-writer | 15,180,739 | 13 |
| 13 | product-analyst | 14,784,210 | 12 |
| 14 | code-reviewer | 11,947,029 | 12 |

**Window totals:** input 959,983 · output 6,890,257 · cache creation 175,567,933 · **cache read 2,183,534,418**

**Takeaway:** `backend-developer` leads both in number of calls and total tokens. Cache-read tokens dominate the total by a wide margin across every agent (see § 12).

---

## 5. Agents with the highest average tokens per call

| Rank | Agent | Avg tokens/call | Calls |
|---|---|---|---|
| 1 | **test-author** | 8,246,933 | 45 |
| 2 | backend-developer | 3,555,354 | 195 |
| 3 | software-architect | 3,334,214 | 90 |
| 4 | backend-reviewer | 3,285,628 | 6 |
| 5 | frontend-reviewer | 2,836,297 | 6 |
| 6 | frontend-developer | 2,557,535 | 152 |
| 7 | frontend-test-specialist | 2,514,742 | 61 |
| 8 | qa-specialist | 2,462,645 | 13 |
| 9 | security-specialist | 2,459,114 | 73 |
| 10 | devops-specialist | 1,642,995 | 71 |
| 11 | product-analyst | 1,232,017 | 12 |
| 12 | technical-writer | 1,167,749 | 13 |
| 13 | code-reviewer | 995,585 | 12 |
| 14 | backend-test-specialist | 990,675 | 54 |

*(`command_invoked` carries no token data, so a per-command average cannot be computed from this event.)*

**Takeaway:** `test-author` has by far the highest average per call (2.3× the runner-up) despite a middling call volume — each invocation does an unusually large amount of context work relative to its peers.

---

## 6. Country, state, and city ranking

| Country | Events |
|---|---|
| **Brazil** | 1,483 |
| France | 1 |

| State/Region | Events |
|---|---|
| **Ceará** | 1,460 |
| São Paulo | 23 |
| Île-de-France | 1 |

| City | Events |
|---|---|
| **Fortaleza** | 1,460 |
| Bauru | 23 |
| Aulnay-sous-Bois | 1 |

**Takeaway:** this confirms the opening sample caveat — 98% of events originate from a single city (Fortaleza, CE), i.e. this is dogfood/dev-machine telemetry, not yet a distributed user base.

> 🔒 **Privacy note (out of scope for this report, already resolved):** the `anonymize_ips` fix on the PostHog project is not retroactive — most events in this 20-day window were ingested **before** the fix and still retain the raw `$ip` property stored in PostHog (identified in this report's previous run, on 2026-08-12). Only events captured after activation stop retaining the IP. The 20-day window needs to "roll" past the fix date for this note to disappear from future runs of this report.

---

## 7. Version ranking used in the period

| Rank | Version | Events |
|---|---|---|
| 1 | **v2.44.0** | 891 |
| 2 | v2.29.0 | 149 |
| 3 | v1.8.2 | 111 |
| 4 | v2.39.2 | 99 |
| 5 | v1.8.1 | 46 |
| 5 | *unknown* | 46 |
| 7 | v2.31.0 | 19 |
| 8 | v1.11.0 | 16 |
| 9 | v2.15.1 | 10 |
| 10 | v2.30.1 | 9 |
| *(+40 other versions with ≤5 events each)* | | |

**Takeaway:** `v2.44.0` (the current tip) dominates with 59.9% of events, expected since most of the volume comes from today's session. The long tail of older versions (v1.8.x, v2.7–v2.41.x) reflects historical events retained within the 20-day window, not concurrent installs. `unknown` (46 events, 3.1%) comes from `install`/`update`/`agent_completed` events captured before the version was resolved — see the "Observations" section.

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

| Day | Events |
|---|---|
| **Wednesday** | 1,032 |
| Thursday | 151 |
| Friday | 137 |
| Saturday | 47 |
| Tuesday | 47 |
| Monday | 43 |
| Sunday | 30 |

**By hour of day (UTC):**

| Hour | Events | | Hour | Events |
|---|---|---|---|---|
| 00 | 49 | | 12 | 11 |
| 01 | 231 | | 13 | 298 |
| 02 | 93 | | 14 | 134 |
| 03 | 28 | | 15 | 117 |
| 04 | 17 | | 16 | 18 |
| 05 | 1 | | 17 | 25 |
| 06 | 9 | | 18 | 40 |
| 07 | 14 | | 19 | 49 |
| 08 | 0 | | 20 | 41 |
| 09 | 0 | | 21 | 25 |
| 10 | 188 | | 22 | 52 |
| 11 | 14 | | 23 | 33 |

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

Cross-referencing the observed `agent_completed` names against the agent roster in `agents/*.md` (18 agents total):

**Agents with zero completions in this window:** `database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist`, `setup-assistant` (5 of 18 — no invocation recorded in 20 days).

Cross-referencing observed `command_invoked` names against the `scripts/lib/commands.json` roster (`/devteam:*` commands) is not reliable here — only 6 of ~25 documented commands fired in the window (`architect`, `push`, `status`, `sync-rules`, `pr`, `review`), which would mean ~19 commands with zero usage. Given § 1's caveat that `command_invoked` volume is suspiciously low relative to `agent_completed`, this table is **not** yet a reliable adoption signal and was not detailed further — flagged as a possible instrumentation gap (see Observations).

---

## Observations

- **This is dogfood data from a single developer, not user-base telemetry.** 98% of geolocated events point to a single city; treat every ranking above as "how this repo's own maintainer used it," not adoption at scale.
- **`command_invoked` under-fires relative to `agent_completed`** (7 vs. 803 in the same 20-day window, even though commands routinely spawn multiple agents). Worth checking whether command-name detection in `scripts/hooks/pre-tool-use/02b-telemetry.sh` is missing invocation paths (e.g. commands run without the expected trigger phrase).
- **`version: "unknown"` on 46 events** — the version isn't always resolved at capture time; worth checking whether `state.json` is read before or after the write being reported.
- **Zero cross-model agents**: every agent used exactly one model for its entire tier in this window, matching `tiers.json` with no observed drift — a good consistency signal for the tier→model contract described in `CLAUDE.md`.
- **Very high cache efficiency** (~2,275:1 cache-read to input) — the prompt-cache system is carrying nearly all context reuse, intended behavior, not a red flag.
- **5 agents with zero activity** in the window (`database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist`, `setup-assistant`) — expected if no corresponding work (schema, mobile, design, SEO, new-project onboarding) occurred in 20 days, not necessarily a defect.
- **2 manual test events (`__manual_verification_test__`, model `claude-sonnet-4-5`) and 1 malformed event (null `agent_name`/`model`)** were excluded from all agent/model/token metrics above so they wouldn't skew the rankings — see the adjusted total in the header.

---

## Machine-readable summary for LLMs

Dense, prose-free block optimized for parsing/ingestion by another agent or LLM. All
values mirror the tables above; no new data is introduced here.

```yaml
report:
  title: "PostHog usage metrics — dev-team-agents"
  window:
    start_utc: "2026-07-23T18:17:25Z"
    end_utc: "2026-08-12T15:44:41Z"
    days: 20
  generated_at: "2026-08-12"
  source:
    posthog_project_id: 430371
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
    - {agent: "backend-developer", calls: 195}
    - {agent: "frontend-developer", calls: 152}
    - {agent: "software-architect", calls: 90}
    - {agent: "security-specialist", calls: 73}
    - {agent: "devops-specialist", calls: 71}
    - {agent: "frontend-test-specialist", calls: 61}
    - {agent: "backend-test-specialist", calls: 54}
    - {agent: "test-author", calls: 45}
    - {agent: "qa-specialist", calls: 13}
    - {agent: "technical-writer", calls: 13}
    - {agent: "code-reviewer", calls: 12}
    - {agent: "product-analyst", calls: 12}
    - {agent: "backend-reviewer", calls: 6}
    - {agent: "frontend-reviewer", calls: 6}

  models_by_provider:
    claude:
      - {model: "claude-sonnet-5", calls: 570}
      - {model: "claude-opus-5[1m]", calls: 175}
      - {model: "claude-haiku-4-5-20251001", calls: 58}

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

  tokens_by_agent_total_desc:
    - {agent: "backend-developer", total: 693294212, calls: 195}
    - {agent: "frontend-developer", total: 388745340, calls: 152}
    - {agent: "test-author", total: 371111987, calls: 45}
    - {agent: "software-architect", total: 300079305, calls: 90}
    - {agent: "security-specialist", total: 179515358, calls: 73}
    - {agent: "frontend-test-specialist", total: 153399264, calls: 61}
    - {agent: "devops-specialist", total: 116652699, calls: 71}
    - {agent: "backend-test-specialist", total: 53496496, calls: 54}
    - {agent: "qa-specialist", total: 32014392, calls: 13}
    - {agent: "backend-reviewer", total: 19713773, calls: 6}
    - {agent: "frontend-reviewer", total: 17017787, calls: 6}
    - {agent: "technical-writer", total: 15180739, calls: 13}
    - {agent: "product-analyst", total: 14784210, calls: 12}
    - {agent: "code-reviewer", total: 11947029, calls: 12}

  tokens_by_agent_avg_desc:
    - {agent: "test-author", avg: 8246933}
    - {agent: "backend-developer", avg: 3555354}
    - {agent: "software-architect", avg: 3334214}
    - {agent: "backend-reviewer", avg: 3285628}
    - {agent: "frontend-reviewer", avg: 2836297}
    - {agent: "frontend-developer", avg: 2557535}
    - {agent: "frontend-test-specialist", avg: 2514742}
    - {agent: "qa-specialist", avg: 2462645}
    - {agent: "security-specialist", avg: 2459114}
    - {agent: "devops-specialist", avg: 1642995}
    - {agent: "product-analyst", avg: 1232017}
    - {agent: "technical-writer", avg: 1167749}
    - {agent: "code-reviewer", avg: 995585}
    - {agent: "backend-test-specialist", avg: 990675}

  geography:
    countries: [{name: "Brazil", events: 1483}, {name: "France", events: 1}]
    states: [{name: "Ceara", events: 1460}, {name: "Sao Paulo", events: 23}, {name: "Ile-de-France", events: 1}]
    cities: [{name: "Fortaleza", events: 1460}, {name: "Bauru", events: 23}, {name: "Aulnay-sous-Bois", events: 1}]

  top_versions:
    - {version: "v2.44.0", events: 891}
    - {version: "v2.29.0", events: 149}
    - {version: "v1.8.2", events: 111}
    - {version: "v2.39.2", events: 99}
    - {version: "v1.8.1", events: 46}
    - {version: "unknown", events: 46}
    - {version: "v2.31.0", events: 19}

  usage_by_weekday_utc:
    wednesday: 1032
    thursday: 151
    friday: 137
    saturday: 47
    tuesday: 47
    monday: 43
    sunday: 30

  peak_usage_by_hour_utc:
    - {hour: 13, events: 298}
    - {hour: 1, events: 231}
    - {hour: 10, events: 188}
    - {hour: 14, events: 134}
    - {hour: 15, events: 117}

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
