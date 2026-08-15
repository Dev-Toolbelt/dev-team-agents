# DevTeam Agents Usage Metrics — Last 20 Days

**Window:** 2026-07-25 22:07 → 2026-08-14 22:07, `America/Sao_Paulo` time (20 days)
**First event observed in window:** 2026-07-26 09:34 (`America/Sao_Paulo`)
**Generated:** 2026-08-14 22:07 (`America/Sao_Paulo`)
**Timezone used for time-based metrics:** `America/Sao_Paulo` (UTC−3)
**Total events in window:** 2,947 (agent metrics computed over 1,659 valid `agent_completed` — 3 manual test events `__manual_verification_test__` excluded from 1,662)
**PostHog project ID:** 430371

---

## 0. Event type distribution

**Conclusion:** `agent_completed` dominates with 1,662 events (56.4%); `command_invoked` accounts for only 11 (0.4%), matching the pattern seen in the previous report — work is driven by direct agent spawns, not the slash-command layer.

| Event | Occurrences | % |
|---|---:|---:|
| **`agent_completed`** | **1,662** | **56.4%** |
| `session_end` | 1,140 | 38.7% |
| `install` | 92 | 3.1% |
| `update` | 35 | 1.2% |
| `command_invoked` | 11 | 0.4% |
| `first_install` | 7 | 0.2% |
| `agent_spawned` | 0 | 0.0% |

> `agent_spawned` **never fired** in the window. All agent metrics use `agent_completed` as a proxy.

## 1. Most-called commands

**Conclusion:** `status` leads with 3 invocations out of only 11 total — too small a sample for a meaningful ranking, but the data point itself is the finding: 27 of 34 canonical commands recorded zero invocations (see section 14).

| Command | Calls |
|---|---:|
| **`status`** | **3** |
| `architect` | 2 |
| `review` | 2 |
| `install` | 1 |
| `pr` | 1 |
| `push` | 1 |
| `sync-rules` | 1 |

## 2. Most-invoked agents

**Conclusion:** `software-architect` leads with 325 completions (19.6% of 1,659), closely followed by `frontend-developer` (288) and `backend-developer` (232) — the three sum to 51.0% of all agent activity.

| Agent | Completions | % |
|---|---:|---:|
| **`software-architect`** | **325** | **19.6%** |
| `frontend-developer` | 288 | 17.4% |
| `backend-developer` | 232 | 14.0% |
| `devops-specialist` | 119 | 7.2% |
| `security-specialist` | 111 | 6.7% |
| `frontend-test-specialist` | 106 | 6.4% |
| `backend-test-specialist` | 93 | 5.6% |
| `nextjs-spa-specialist` ⚠️ | 66 | 4.0% |
| `qa-specialist` | 63 | 3.8% |
| `code-reviewer` | 60 | 3.6% |
| `test-author` ⚠️ | 45 | 2.7% |
| `database-specialist` | 41 | 2.5% |
| `product-analyst` | 40 | 2.4% |
| `technical-writer` | 21 | 1.3% |
| `laravel-specialist` ⚠️ | 15 | 0.9% |
| `Explore` ⚠️ | 12 | 0.7% |
| `frontend-reviewer` | 10 | 0.6% |
| `backend-reviewer` | 8 | 0.5% |
| `ui-ux-designer` | 2 | 0.1% |
| `unknown` ⚠️ | 2 | 0.1% |

> ⚠️ = name outside the canonical `agents/*.md` roster. `nextjs-spa-specialist`, `laravel-specialist` and `test-author` are project-local or legacy agent names; `Explore` is a native Claude Code subagent; `unknown` marks an event with an unresolved `agent_name`.

## 3. Model ranking, grouped by provider

**Conclusion:** 100% of completions came from the `claude` provider; `claude-sonnet-5` accounts for 62.4% of runs, and no `opencode` or `codex` event appeared in the window.

| Provider | Model | Runs | % |
|---|---|---:|---:|
| **`claude`** | **`claude-sonnet-5`** | **1,036** | **62.4%** |
| `claude` | `claude-opus-5[1m]` | 476 | 28.7% |
| `claude` | `claude-haiku-4-5-20251001` | 147 | 8.9% |

## 4. Token consumption ranking (total per agent)

**Conclusion:** `software-architect` consumed 11.18M tokens — 44.1% of the window's 25.35M total, more than the next three agents combined.

| Agent | Total tokens | % | Input | Output |
|---|---:|---:|---:|---:|
| **`software-architect`** | **11,179,267** | **44.1%** | 520,623 | 10,658,644 |
| `frontend-developer` | 3,171,037 | 12.5% | 950,606 | 2,220,431 |
| `backend-developer` | 2,511,268 | 9.9% | 50,570 | 2,460,698 |
| `nextjs-spa-specialist` | 1,467,016 | 5.8% | 75,966 | 1,391,050 |
| `test-author` | 1,139,704 | 4.5% | 47,292 | 1,092,412 |
| `security-specialist` | 939,014 | 3.7% | 16,685 | 922,329 |
| `frontend-test-specialist` | 931,701 | 3.7% | 43,332 | 888,369 |
| `backend-test-specialist` | 860,049 | 3.4% | 71,586 | 788,463 |
| `qa-specialist` | 660,552 | 2.6% | 74,319 | 586,233 |
| `devops-specialist` | 655,532 | 2.6% | 83,001 | 572,531 |
| `product-analyst` | 462,980 | 1.8% | 1,440 | 461,540 |
| `database-specialist` | 430,124 | 1.7% | 3,040 | 427,084 |
| `laravel-specialist` | 398,472 | 1.6% | 17,908 | 380,564 |
| `code-reviewer` | 242,239 | 1.0% | 22,877 | 219,362 |
| `technical-writer` | 110,639 | 0.4% | 23,616 | 87,023 |
| `ui-ux-designer` | 64,708 | 0.3% | 40,596 | 24,112 |
| `backend-reviewer` | 59,268 | 0.2% | 482 | 58,786 |
| `frontend-reviewer` | 36,596 | 0.1% | 372 | 36,224 |
| `Explore` | 26,140 | 0.1% | 204 | 25,936 |
| `unknown` | 2,940 | 0.0% | 24 | 2,916 |
| **Total** | **25,349,246** | **100%** | **2,044,539** | **23,304,707** |

> **Data anomaly:** output accounts for 91.9% of total tokens and input only 8.1% — inverted relative to the expected consumption of a coding agent (input typically dominates). See Observations.

## 5. Agents with the highest average token use (per invocation)

**Conclusion:** `software-architect` also leads on average, at 34,398 tokens per invocation — 2.3× the global average of 15,281 tokens/run.

| Agent | Avg tokens/run | Runs |
|---|---:|---:|
| **`software-architect`** | **34,398** | 325 |
| `ui-ux-designer` | 32,354 | 2 ⚠️ low sample |
| `laravel-specialist` | 26,565 | 15 |
| `test-author` | 25,327 | 45 |
| `nextjs-spa-specialist` | 22,227 | 66 |
| `product-analyst` | 11,575 | 40 |
| `frontend-developer` | 11,011 | 288 |
| `backend-developer` | 10,824 | 232 |
| `database-specialist` | 10,491 | 41 |
| `qa-specialist` | 10,485 | 63 |
| `backend-test-specialist` | 9,248 | 93 |
| `frontend-test-specialist` | 8,790 | 106 |
| `security-specialist` | 8,460 | 111 |
| `backend-reviewer` | 7,409 | 8 |
| `devops-specialist` | 5,509 | 119 |
| `technical-writer` | 5,269 | 21 |
| `code-reviewer` | 4,037 | 60 |
| `frontend-reviewer` | 3,660 | 10 |
| `Explore` | 2,178 | 12 |
| `unknown` | 1,470 | 2 |

> **Per command: not computable.** The `command_invoked` event carries no token counters, and there is no correlation key linking a `command_invoked` to the `agent_completed` events it spawned. Per-command averages stay unavailable until telemetry emits a shared session/run identifier.

## 6. Country, state and city ranking

**Conclusion:** 100% of events came from Brazil, and 99.4% from Fortaleza/CE — the install base active in this window is essentially a single operator, which limits any "adoption" reading of the other rankings.

### Country

| Country | Events | % |
|---|---:|---:|
| **Brazil** | **2,947** | **100.0%** |

### State

| State | Events | % |
|---|---:|---:|
| **Ceará** | **2,928** | **99.4%** |
| São Paulo | 19 | 0.6% |

### City

| City | Events | % |
|---|---:|---:|
| **Fortaleza** | **2,928** | **99.4%** |
| Bauru | 19 | 0.6% |

## 7. Version ranking for the period

**Conclusion:** `v2.44.0` and `v2.44.1` concentrate 63.6% of events — the active base is current, but 370 events (12.6%) reported `version: unknown`, an instrumentation gap.

| Version | Events | % |
|---|---:|---:|
| **`v2.44.0`** | **951** | **32.3%** |
| `v2.44.1` | 922 | 31.3% |
| `unknown` ⚠️ | 370 | 12.6% |
| `v2.44.2` | 228 | 7.7% |
| `v2.29.0` | 149 | 5.1% |
| `v2.39.2` | 133 | 4.5% |
| `v2.31.0` | 48 | 1.6% |
| `v2.17.3` | 20 | 0.7% |
| `v1.8.1` | 13 | 0.4% |
| `v2.15.1` | 10 | 0.3% |
| `v2.30.1` | 9 | 0.3% |
| `v1.8.2` | 8 | 0.3% |
| Other 42 versions | 86 | 2.9% |

## 8. Models used, grouped by agent

**Conclusion:** no agent invoked more than one model in the window — the tier → model mapping is consistent. The three agents on Haiku (`test-author`, `laravel-specialist`, `nextjs-spa-specialist`) are all names outside the canonical roster.

| Agent | Model(s) | Runs |
|---|---|---:|
| `software-architect` | `claude-opus-5[1m]` | 325 |
| `security-specialist` | `claude-opus-5[1m]` | 111 |
| `product-analyst` | `claude-opus-5[1m]` | 40 |
| `frontend-developer` | `claude-sonnet-5` | 288 |
| `backend-developer` | `claude-sonnet-5` | 232 |
| `devops-specialist` | `claude-sonnet-5` | 119 |
| `frontend-test-specialist` | `claude-sonnet-5` | 106 |
| `backend-test-specialist` | `claude-sonnet-5` | 93 |
| `qa-specialist` | `claude-sonnet-5` | 63 |
| `code-reviewer` | `claude-sonnet-5` | 60 |
| `database-specialist` | `claude-sonnet-5` | 41 |
| `Explore` | `claude-sonnet-5` | 12 |
| `frontend-reviewer` | `claude-sonnet-5` | 10 |
| `backend-reviewer` | `claude-sonnet-5` | 8 |
| `ui-ux-designer` | `claude-sonnet-5` | 2 |
| `unknown` | `claude-sonnet-5` | 2 |
| `nextjs-spa-specialist` ⚠️ | `claude-haiku-4-5-20251001` | 66 |
| `test-author` ⚠️ | `claude-haiku-4-5-20251001` | 45 |
| `technical-writer` | `claude-haiku-4-5-20251001` | 21 |
| `laravel-specialist` ⚠️ | `claude-haiku-4-5-20251001` | 15 |

## 9. Peak days and hours

**Conclusion:** usage is heavily concentrated on Wednesday and Thursday (73.4% of events) and peaks at 10:00; weekends are nearly idle (41 events, 1.4%).

### By day of week

| Day | Events | % |
|---|---:|---:|
| **Wednesday** | **1,130** | **38.3%** |
| Thursday | 1,033 | 35.1% |
| Friday | 375 | 12.7% |
| Tuesday | 322 | 10.9% |
| Monday | 46 | 1.6% |
| Sunday | 31 | 1.1% |
| Saturday | 10 | 0.3% |

### By hour of day (`America/Sao_Paulo`)

| Hour | Events | Hour | Events |
|---|---:|---|---:|
| **10h** | **376** | 18h | 100 |
| 12h | 313 | 13h | 99 |
| 15h | 256 | 23h | 97 |
| 14h | 240 | 20h | 72 |
| 17h | 224 | 21h | 69 |
| 22h | 221 | 00h | 36 |
| 07h | 188 | 08h | 29 |
| 11h | 187 | 01h | 17 |
| 16h | 166 | 04h | 14 |
| 19h | 122 | 03h | 9 |
| 09h | 111 | 02h | 1 |
| — | — | 05h–06h | 0 |

## 10. New installs vs updates

**Conclusion:** only 7 of the 134 install-family events (5.2%) were `first_install` — the window is dominated by reinstalls and updates of the existing base, not new acquisition.

| Event | Occurrences | % of family |
|---|---:|---:|
| **`install`** | **92** | **68.7%** |
| `update` | 35 | 26.1% |
| `first_install` | 7 | 5.2% |

All 35 `update` events reported `mode: manual` — **the auto-update path never fired in the window.**

## 11. Daily event volume

**Conclusion:** 2,614 of 2,947 events (88.7%) fall in just 4 days (Aug 11–14); the first 16 days of the window total 333 events.

| Date | Events | Date | Events |
|---|---:|---|---:|
| 2026-07-26 | 18 | 2026-08-05 | 47 |
| 2026-07-27 | 5 | 2026-08-06 | 136 |
| 2026-07-28 | 22 | 2026-08-07 | 22 |
| 2026-07-29 | 4 | 2026-08-08 | 6 |
| 2026-07-30 | 2 | 2026-08-09 | 4 |
| 2026-07-31 | 7 | 2026-08-10 | 7 |
| 2026-08-01 | 4 | 2026-08-11 | 294 |
| 2026-08-02 | 9 | **2026-08-12** | **1,079** |
| 2026-08-03 | 34 | 2026-08-13 | 895 |
| 2026-08-04 | 6 | 2026-08-14 | 346 |

## 12. Cache efficiency

**Conclusion: not computable in this window.** The `cache_creation_tokens` and `cache_read_tokens` fields are **null on 100% of the 1,662 `agent_completed` events** — no event reported a cache value, zero or otherwise.

| Metric | Value |
|---|---:|
| `agent_completed` events with cache fields populated | 0 of 1,662 |
| Aggregate `cache_read_tokens` | — (unavailable) |
| Aggregate `cache_creation_tokens` | — (unavailable) |
| `cache_read` / `input` ratio | — (unavailable) |

## 13. Session-end distribution

**Conclusion:** 97.7% of `session_end` events reported `stop_hook_active=false` — the stop hook is rarely active at the moment of termination.

| `stop_hook_active` | Events | % |
|---|---:|---:|
| **`false`** | **1,114** | **97.7%** |
| `true` | 26 | 2.3% |

## 14. Commands and agents never used in the period

**Conclusion:** 27 of 34 canonical commands (79.4%) and 3 of 18 canonical agents recorded not a single invocation in the window — command-surface coverage is the project's largest usage gap.

### Commands with zero invocations (27 of 34)

`adr` · `audit` · `backend` · `commit` · `dba` · `design` · `devops` · `docs` · `explain` · `fix` · `frontend` · `fullstack` · `health-check` · `learn` · `mobile` · `plan` · `qa` · `refactor` · `relayout` · `rule` · `security` · `seo` · `setup` · `symlinks` · `tester` · `update` · `version`

### Canonical agents with zero runs (3 of 18)

`mobile-developer` · `seo-specialist` · `setup-assistant`

### Names observed outside the canonical roster (5)

| Name | Runs | Likely nature |
|---|---:|---|
| `nextjs-spa-specialist` | 66 | project-local agent |
| `test-author` | 45 | legacy name (agent removed from roster) |
| `laravel-specialist` | 15 | project-local agent |
| `Explore` | 12 | native Claude Code subagent |
| `unknown` | 2 | `agent_name` unresolved at emission |

## Operating system (supplementary)

| OS | Events | % |
|---|---:|---:|
| **`darwin`** | **2,735** | **92.8%** |
| `mingw64_nt-10.0-26200` | 191 | 6.5% |
| `linux` | 21 | 0.7% |

---

## Observations

- **Inverted input/output ratio.** Output accounts for 23.3M of the 25.35M tokens (91.9%) against 2.04M input (8.1%). A real coding agent reads far more than it writes — this ratio suggests `input_tokens` is undercounted (or `output_tokens` is aggregating the total) in `scripts/helpers/telemetry-send.sh`. Until that is verified, all absolute token figures should be read as order-of-magnitude, not actual cost.
- **Cache telemetry entirely absent.** `cache_creation_tokens` and `cache_read_tokens` arrived null on 1,662 of 1,662 events. The cache-efficiency metric — the most direct signal of context reuse — has been blind since instrumentation, not for lack of cache usage.
- **The slash-command layer is nearly invisible in telemetry.** 11 `command_invoked` against 1,662 `agent_completed` (0.66%), and `agent_spawned` at zero events. Either the commands genuinely aren't used, or `command_invoked`/`agent_spawned` under-fire. The two hypotheses have very different consequences and the current data does not separate them.
- **Extreme concentration in origin and time.** 99.4% of events come from a single city and 88.7% from just 4 consecutive days (Aug 11–14). The rankings in this report describe one operator's work pattern during an intense sprint — not product adoption.
- **Off-roster names totalled 138 runs (8.3%).** `test-author` (45) still fires despite no longer existing in `agents/*.md`, and `nextjs-spa-specialist`/`laravel-specialist` (81) are project-local agents. The `agent_name` field does not distinguish framework agents from project agents, which pollutes every per-agent ranking.
- **`version: unknown` on 12.6% of events** and 100% of updates in `mode: manual` — the auto-update path produced not a single event in the window.

---

## Structured summary for LLM consumption

```yaml
window:
  start: "2026-07-25T22:07:00-03:00"
  end: "2026-08-14T22:07:00-03:00"
  first_event_observed: "2026-07-26T09:34:00-03:00"
  days: 20
  timezone: "America/Sao_Paulo"
  posthog_project: 430371
  total_events: 2947
  valid_agent_completed: 1659
  excluded_manual_test: 3

events_by_type:
  agent_completed: 1662
  session_end: 1140
  install: 92
  update: 35
  command_invoked: 11
  first_install: 7
  agent_spawned: 0

top_commands_by_calls:
  status: 3
  architect: 2
  review: 2
  install: 1
  pr: 1
  push: 1
  sync-rules: 1

top_agents_by_calls:
  software-architect: 325
  frontend-developer: 288
  backend-developer: 232
  devops-specialist: 119
  security-specialist: 111
  frontend-test-specialist: 106
  backend-test-specialist: 93
  nextjs-spa-specialist: 66
  qa-specialist: 63
  code-reviewer: 60
  test-author: 45
  database-specialist: 41
  product-analyst: 40
  technical-writer: 21
  laravel-specialist: 15
  Explore: 12
  frontend-reviewer: 10
  backend-reviewer: 8
  ui-ux-designer: 2
  unknown: 2

models_by_provider:
  claude:
    claude-sonnet-5: 1036
    claude-opus-5[1m]: 476
    claude-haiku-4-5-20251001: 147

total_tokens:
  total: 25349246
  input: 2044539
  output: 23304707
  cache_creation: null
  cache_read: null
  avg_per_run: 15281

tokens_by_agent_total_desc:
  software-architect: 11179267
  frontend-developer: 3171037
  backend-developer: 2511268
  nextjs-spa-specialist: 1467016
  test-author: 1139704
  security-specialist: 939014
  frontend-test-specialist: 931701
  backend-test-specialist: 860049
  qa-specialist: 660552
  devops-specialist: 655532
  product-analyst: 462980
  database-specialist: 430124
  laravel-specialist: 398472
  code-reviewer: 242239
  technical-writer: 110639
  ui-ux-designer: 64708
  backend-reviewer: 59268
  frontend-reviewer: 36596
  Explore: 26140
  unknown: 2940

avg_tokens_per_run_desc:
  software-architect: 34398
  ui-ux-designer: 32354
  laravel-specialist: 26565
  test-author: 25327
  nextjs-spa-specialist: 22227
  product-analyst: 11575
  frontend-developer: 11011
  backend-developer: 10824
  database-specialist: 10491
  qa-specialist: 10485
  backend-test-specialist: 9248
  frontend-test-specialist: 8790
  security-specialist: 8460
  backend-reviewer: 7409
  devops-specialist: 5509
  technical-writer: 5269
  code-reviewer: 4037
  frontend-reviewer: 3660
  Explore: 2178
  unknown: 1470

avg_tokens_per_command: not_computable_no_correlation_key

geography:
  countries:
    Brazil: 2947
  states:
    Ceara: 2928
    Sao Paulo: 19
  cities:
    Fortaleza: 2928
    Bauru: 19

versions_desc:
  v2.44.0: 951
  v2.44.1: 922
  unknown: 370
  v2.44.2: 228
  v2.29.0: 149
  v2.39.2: 133
  v2.31.0: 48
  v2.17.3: 20
  v1.8.1: 13
  v2.15.1: 10
  v2.30.1: 9
  v1.8.2: 8
  other_42_versions: 86

models_by_agent:
  software-architect: [claude-opus-5[1m]]
  security-specialist: [claude-opus-5[1m]]
  product-analyst: [claude-opus-5[1m]]
  frontend-developer: [claude-sonnet-5]
  backend-developer: [claude-sonnet-5]
  devops-specialist: [claude-sonnet-5]
  frontend-test-specialist: [claude-sonnet-5]
  backend-test-specialist: [claude-sonnet-5]
  qa-specialist: [claude-sonnet-5]
  code-reviewer: [claude-sonnet-5]
  database-specialist: [claude-sonnet-5]
  Explore: [claude-sonnet-5]
  frontend-reviewer: [claude-sonnet-5]
  backend-reviewer: [claude-sonnet-5]
  ui-ux-designer: [claude-sonnet-5]
  unknown: [claude-sonnet-5]
  nextjs-spa-specialist: [claude-haiku-4-5-20251001]
  test-author: [claude-haiku-4-5-20251001]
  technical-writer: [claude-haiku-4-5-20251001]
  laravel-specialist: [claude-haiku-4-5-20251001]

usage_by_weekday:
  wednesday: 1130
  thursday: 1033
  friday: 375
  tuesday: 322
  monday: 46
  sunday: 31
  saturday: 10

usage_by_local_hour:
  "10": 376
  "12": 313
  "15": 256
  "14": 240
  "17": 224
  "22": 221
  "07": 188
  "11": 187
  "16": 166
  "19": 122
  "09": 111
  "18": 100
  "13": 99
  "23": 97
  "20": 72
  "21": 69
  "00": 36
  "08": 29
  "01": 17
  "04": 14
  "03": 9
  "02": 1
  "05": 0
  "06": 0

volume_by_day:
  "2026-07-26": 18
  "2026-07-27": 5
  "2026-07-28": 22
  "2026-07-29": 4
  "2026-07-30": 2
  "2026-07-31": 7
  "2026-08-01": 4
  "2026-08-02": 9
  "2026-08-03": 34
  "2026-08-04": 6
  "2026-08-05": 47
  "2026-08-06": 136
  "2026-08-07": 22
  "2026-08-08": 6
  "2026-08-09": 4
  "2026-08-10": 7
  "2026-08-11": 294
  "2026-08-12": 1079
  "2026-08-13": 895
  "2026-08-14": 346

installs_vs_updates:
  install: 92
  update: 35
  first_install: 7
  new_install_rate: 0.052
  update_modes:
    manual: 35
    auto: 0

cache_efficiency: not_computable_fields_null_on_1662_of_1662_events

session_end:
  stop_hook_active_false: 1114
  stop_hook_active_true: 26

operating_system:
  darwin: 2735
  mingw64_nt-10.0-26200: 191
  linux: 21

coverage:
  canonical_commands: 34
  commands_used: 7
  commands_unused: [adr, audit, backend, commit, dba, design, devops, docs, explain, fix, frontend, fullstack, health-check, learn, mobile, plan, qa, refactor, relayout, rule, security, seo, setup, symlinks, tester, update, version]
  canonical_agents: 18
  agents_used: 15
  agents_unused: [mobile-developer, seo-specialist, setup-assistant]
  off_roster_names:
    nextjs-spa-specialist: 66
    test-author: 45
    laravel-specialist: 15
    Explore: 12
    unknown: 2

data_anomalies:
  - inverted_output_input_ratio: {output_pct: 0.919, input_pct: 0.081}
  - missing_cache_tokens: {affected_events: 1662, total: 1662}
  - command_invoked_suspected_underfire: {command_invoked: 11, agent_completed: 1662}
  - agent_spawned_zero_events: true
  - version_unknown: {events: 370, pct: 0.126}
```
