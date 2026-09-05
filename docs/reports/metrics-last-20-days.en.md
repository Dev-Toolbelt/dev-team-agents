# PostHog Usage Metrics — Last 20 Days

**Window:** 2026-08-15 22:07 → 2026-09-04 22:07, `America/Sao_Paulo` time (20 days)  
**First event in window:** 2026-08-15 22:51  
**Last event in window:** 2026-09-04 16:48  
**Generated:** 2026-09-04 22:07 (`America/Sao_Paulo`)  
**Timezone used for all time-based metrics:** `America/Sao_Paulo` (UTC−3)  
**Total events in window:** 5,563  
**Distinct installs (anonymous IDs):** 6  
**PostHog project ID:** 430371

> **Coverage notice:** the geography section (country/state/city) **could not be computed**
> in this run — the environment executing the report blocked queries against the `$geoip_*`
> properties. Every other metric in the prompt was computed normally. See § 6.

---

## 0. Event type distribution

**Conclusion:** `session_end` dominates with 3,460 events (62.2%), followed by `agent_completed` with 2,051 (36.9%); `command_invoked` accounts for only 11 events (0.2%) — work is still driven by direct agent spawns, not the slash-command layer.

| Event | Occurrences | % | Distinct installs |
|---|---:|---:|---:|
| **`session_end`** | **3,460** | **62.2%** | 6 |
| `agent_completed` | 2,051 | 36.9% | 2 |
| `install` | 28 | 0.5% | 4 |
| `update` | 13 | 0.2% | 3 |
| `command_invoked` | 11 | 0.2% | 2 |
| **Total** | **5,563** | **100.0%** | 6 |

> `agent_spawned` and `first_install` **did not occur** in this window — both exist in the
> project history (26 `first_install` over the last 120 days). The "most-invoked agents" metric
> is therefore derived exclusively from `agent_completed` (§ 2).

---

## 1. Most-invoked commands

**Conclusion:** `/devteam:learn` and `/devteam:status` tie for the lead with 4 invocations each (36.4% of the window's 11 command invocations); absolute volume is very low — 11 invocations against 2,051 agent runs.

| # | Command | Invocations | % |
|---:|---|---:|---:|
| 1 | **`/devteam:learn`** | **4** | **36.4%** |
| 2 | **`/devteam:status`** | **4** | **36.4%** |
| 3 | `/devteam:commit` | 1 | 9.1% |
| 4 | `/devteam:review` | 1 | 9.1% |
| 5 | `/devteam:sync-rules` | 1 | 9.1% |
| | **Total** | **11** | **100.0%** |

---

## 2. Most-invoked agents

**Conclusion:** `software-architect` is by far the most-run agent, with 733 runs — 35.7% of all 2,051 runs in the window, more than triple the runner-up.

| # | Agent | Runs | % |
|---:|---|---:|---:|
| 1 | **`software-architect`** | **733** | **35.7%** |
| 2 | `backend-developer` | 210 | 10.2% |
| 3 | `qa-specialist` | 190 | 9.3% |
| 4 | `code-reviewer` | 185 | 9.0% |
| 5 | `security-specialist` | 183 | 8.9% |
| 6 | `Explore` | 104 | 5.1% |
| 7 | `frontend-developer` | 102 | 5.0% |
| 8 | `database-specialist` | 72 | 3.5% |
| 9 | `devops-specialist` | 71 | 3.5% |
| 10 | `technical-writer` | 59 | 2.9% |
| 11 | `laravel-specialist` | 44 | 2.1% |
| 12 | `backend-test-specialist` | 28 | 1.4% |
| 13 | `general-purpose` | 23 | 1.1% |
| 14 | `frontend-test-specialist` | 18 | 0.9% |
| 15 | `product-analyst` | 16 | 0.8% |
| 16 | `unknown` | 4 | 0.2% |
| 17 | `frontend-reviewer` | 4 | 0.2% |
| 18 | `nextjs-spa-specialist` | 4 | 0.2% |
| 19 | `devops-deploy` | 1 | 0.0% |
| | **Total** | **2,051** | **100.0%** |

> Names outside the dev-team-agents roster (`Explore`, `general-purpose`, `laravel-specialist`,
> `nextjs-spa-specialist`, `devops-deploy`, `unknown`) are Claude Code native agents or
> project-local agents on installs that report telemetry — see § 14.

---

## 3. Model ranking, grouped by provider

**Conclusion:** 100% of runs come from the `claude` provider; `claude-sonnet-5` leads with 1,009 runs (49.2%), closely followed by `claude-opus-5[1m]` with 907 (44.2%).

| # | Provider | Model | Runs | % |
|---:|---|---|---:|---:|
| 1 | `claude` | **`claude-sonnet-5`** | **1,009** | **49.2%** |
| 2 | `claude` | `claude-opus-5[1m]` | 907 | 44.2% |
| 3 | `claude` | `claude-haiku-4-5-20251001` | 110 | 5.4% |
| 4 | `claude` | `claude-opus-5` | 25 | 1.2% |

> `claude-opus-5[1m]` and `claude-opus-5` are the **same model**: the `[1m]` suffix marks the
> 1M-token context window. Combined, Opus accounts for 932 runs (45.4%).

---

## 4. Token consumption ranking (total per agent)

**Conclusion:** `software-architect` burns 3,838,820,406 tokens — 42.7% of the window's 8,980,194,025 tokens, more than the next four agents combined.

| # | Agent | Runs | Total tokens | % | Input | Output | Cache write | Cache read |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | **`software-architect`** | 733 | **3,838,820,406** | **42.7%** | 564,073 | 15,477,887 | 576,179,185 | 3,246,599,261 |
| 2 | `backend-developer` | 210 | 1,714,251,132 | 19.1% | 511,022 | 4,902,642 | 51,526,859 | 1,657,310,609 |
| 3 | `frontend-developer` | 102 | 977,907,232 | 10.9% | 88,216 | 1,802,198 | 28,097,664 | 947,919,154 |
| 4 | `qa-specialist` | 190 | 781,024,141 | 8.7% | 100,640 | 1,956,823 | 33,403,147 | 745,563,531 |
| 5 | `security-specialist` | 183 | 330,725,990 | 3.7% | 257,866 | 2,004,359 | 34,694,592 | 293,769,173 |
| 6 | `code-reviewer` | 185 | 305,923,830 | 3.4% | 113,243 | 1,543,237 | 33,840,160 | 270,427,190 |
| 7 | `laravel-specialist` | 44 | 253,823,909 | 2.8% | 37,754 | 731,683 | 10,868,882 | 242,185,590 |
| 8 | `devops-specialist` | 71 | 202,943,124 | 2.3% | 114,598 | 802,141 | 12,874,075 | 189,152,310 |
| 9 | `database-specialist` | 72 | 133,138,236 | 1.5% | 14,034 | 459,341 | 11,147,311 | 121,517,550 |
| 10 | `backend-test-specialist` | 28 | 117,356,533 | 1.3% | 39,448 | 397,519 | 5,716,385 | 111,203,181 |
| 11 | `frontend-test-specialist` | 18 | 83,340,498 | 0.9% | 2,006 | 246,611 | 3,423,837 | 79,668,044 |
| 12 | `technical-writer` | 59 | 81,611,998 | 0.9% | 35,614 | 365,922 | 9,695,633 | 71,514,829 |
| 13 | `Explore` | 104 | 75,546,199 | 0.8% | 219,576 | 517,225 | 10,527,654 | 64,281,744 |
| 14 | `nextjs-spa-specialist` | 4 | 38,872,022 | 0.4% | 4,528 | 86,964 | 2,596,931 | 36,183,599 |
| 15 | `product-analyst` | 16 | 17,672,756 | 0.2% | 524 | 92,060 | 2,711,468 | 14,868,704 |
| 16 | `frontend-reviewer` | 4 | 14,376,696 | 0.2% | 31,127 | 63,656 | 871,235 | 13,410,678 |
| 17 | `general-purpose` | 23 | 10,051,923 | 0.1% | 266 | 17,129 | 3,369,945 | 6,664,583 |
| 18 | `unknown` | 4 | 2,773,240 | 0.0% | 464 | 11,194 | 601,234 | 2,160,348 |
| 19 | `devops-deploy` | 1 | 34,160 | 0.0% | 20 | 6 | 34,134 | 0 |
| | **Total** | **2,051** | **8,980,194,025** | **100.0%** | **2,135,019** | **31,478,597** | **832,180,331** | **8,114,400,078** |

---

## 5. Agents with the highest average token cost per run

**Conclusion:** `nextjs-spa-specialist` has the highest average per run (9,718,006 tokens), but over only 4 runs; among agents with meaningful volume, `frontend-developer` (9,587,326 tokens over 102 runs) and `backend-developer` (8,163,101 over 210) are the most expensive per invocation.

| # | Agent | Runs | Total tokens | Avg per run |
|---:|---|---:|---:|---:|
| 1 | **`nextjs-spa-specialist`** | 4 | 38,872,022 | **9,718,006** |
| 2 | `frontend-developer` | 102 | 977,907,232 | 9,587,326 |
| 3 | `backend-developer` | 210 | 1,714,251,132 | 8,163,101 |
| 4 | `laravel-specialist` | 44 | 253,823,909 | 5,768,725 |
| 5 | `software-architect` | 733 | 3,838,820,406 | 5,237,136 |
| 6 | `frontend-test-specialist` | 18 | 83,340,498 | 4,630,028 |
| 7 | `backend-test-specialist` | 28 | 117,356,533 | 4,191,305 |
| 8 | `qa-specialist` | 190 | 781,024,141 | 4,110,653 |
| 9 | `frontend-reviewer` | 4 | 14,376,696 | 3,594,174 |
| 10 | `devops-specialist` | 71 | 202,943,124 | 2,858,354 |
| 11 | `database-specialist` | 72 | 133,138,236 | 1,849,142 |
| 12 | `security-specialist` | 183 | 330,725,990 | 1,807,246 |
| 13 | `code-reviewer` | 185 | 305,923,830 | 1,653,642 |
| 14 | `technical-writer` | 59 | 81,611,998 | 1,383,254 |
| 15 | `product-analyst` | 16 | 17,672,756 | 1,104,547 |
| 16 | `Explore` | 104 | 75,546,199 | 726,406 |
| 17 | `unknown` | 4 | 2,773,240 | 693,310 |
| 18 | `general-purpose` | 23 | 10,051,923 | 437,040 |
| 19 | `devops-deploy` | 1 | 34,160 | 34,160 |
| | **Overall average** | **2,051** | **8,980,194,025** | **4,378,447** |

> **Per command:** token consumption per command cannot be derived. The `command_invoked`
> event carries no token counters and `agent_completed` carries no originating command — there
> is no join key between the two. Reported as non-computable.

---

## 6. Country, state and city ranking

**Conclusion:** metric **not computed in this run**. The `$geoip_*` properties are present and populated on events (confirmed by schema inspection — see § 15), but the environment running this report blocked the queries that read them. No geography data was collected, and nothing was estimated or inferred to fill the gap.

| Dimension | Property | Status |
|---|---|---|
| Country | `$geoip_country_name` | Not computed — query blocked |
| State / region | `$geoip_subdivision_1_name` | Not computed — query blocked |
| City | `$geoip_city_name` | Not computed — query blocked |

> To obtain this section, run the three `$geoip_*` aggregation queries in an environment
> without that restriction. The previous report (Aug 14) holds the historical geography series.

---

## 7. Version ranking for the period

**Conclusion:** `v2.47.2` leads with 2,314 events (41.6%); the whole `v2.47.x` line sums to 3,874 events (69.6%), showing fast adoption of the current release — but 962 events still come from the `v2.44.x` line.

| # | Version | Events | % |
|---:|---|---:|---:|
| 1 | **`v2.47.2`** | **2,314** | **41.6%** |
| 2 | `v2.47.0` | 1,055 | 19.0% |
| 3 | `v2.44.7` | 573 | 10.3% |
| 4 | `v2.47.1` | 505 | 9.1% |
| 5 | `v2.44.4` | 389 | 7.0% |
| 6 | `v2.46.0` | 341 | 6.1% |
| 7 | `v2.45.0` | 273 | 4.9% |
| 8 | `unknown` | 69 | 1.2% |
| 9 | `v1.9.2` | 39 | 0.7% |
| 10 | `main` | 4 | 0.1% |
| 11 | `v1.10.0` | 1 | 0.0% |
| | **Total** | **5,563** | **100.0%** |

---

## 8. Models used, grouped by agent

**Conclusion:** the tier → model mapping is **consistent** — `software-architect`, `security-specialist` and `product-analyst` on Opus (`reasoning`), executors on Sonnet, `technical-writer` on Haiku (`repetitive`). The only anomaly is `unknown`, which appears under two models because it is a bucket for agents not identified in the transcript.

| Agent | Model | Runs |
|---|---|---:|
| `Explore` | `claude-sonnet-5` | 104 |
| `backend-developer` | `claude-sonnet-5` | 210 |
| `backend-test-specialist` | `claude-sonnet-5` | 28 |
| `code-reviewer` | `claude-sonnet-5` | 185 |
| `database-specialist` | `claude-sonnet-5` | 72 |
| `devops-deploy` | `claude-haiku-4-5-20251001` | 1 |
| `devops-specialist` | `claude-sonnet-5` | 71 |
| `frontend-developer` | `claude-sonnet-5` | 102 |
| `frontend-reviewer` | `claude-sonnet-5` | 4 |
| `frontend-test-specialist` | `claude-sonnet-5` | 18 |
| `general-purpose` | `claude-sonnet-5` | 23 |
| `laravel-specialist` | `claude-haiku-4-5-20251001` | 44 |
| `nextjs-spa-specialist` | `claude-haiku-4-5-20251001` | 4 |
| `product-analyst` | `claude-opus-5[1m]` | 16 |
| `qa-specialist` | `claude-sonnet-5` | 190 |
| `security-specialist` | `claude-opus-5[1m]` | 171 |
|  | `claude-opus-5` | 12 |
| `software-architect` | `claude-opus-5[1m]` | 720 |
|  | `claude-opus-5` | 13 |
| `technical-writer` | `claude-haiku-4-5-20251001` | 59 |
| `unknown` | `claude-sonnet-5` | 2 |
|  | `claude-haiku-4-5-20251001` | 2 |

> Agents that invoked more than one model: `security-specialist`, `software-architect`, `unknown`. For
> `software-architect` and `security-specialist` this is only the `[1m]` variant of the same Opus.

---

## 9. Peak days and hours

**Conclusion:** usage is concentrated on weekdays — Monday leads with 1,204 events (21.6%) and Saturday is near-zero (19 events); the hourly peak is **16:00** (742 events), with the 15:00–18:00 block holding 40.1% of volume.

### 9.1 By day of week

| # | Day | Events | % |
|---:|---|---:|---:|
| 1 | **Monday** | **1,204** | **21.6%** |
| 2 | Tuesday | 1,092 | 19.6% |
| 3 | Wednesday | 1,032 | 18.6% |
| 4 | Sunday | 875 | 15.7% |
| 5 | Friday | 725 | 13.0% |
| 6 | Thursday | 616 | 11.1% |
| 7 | Saturday | 19 | 0.3% |

### 9.2 By hour of day

| Hour | Events | % |
|---|---:|---:|
| 00:00 | 210 | 3.8% |
| 01:00 | 56 | 1.0% |
| 02:00 | 4 | 0.1% |
| 07:00 | 66 | 1.2% |
| 08:00 | 57 | 1.0% |
| 09:00 | 167 | 3.0% |
| 10:00 | 459 | 8.3% |
| 11:00 | 276 | 5.0% |
| 12:00 | 227 | 4.1% |
| 13:00 | 180 | 3.2% |
| 14:00 | 219 | 3.9% |
| 15:00 | 403 | 7.2% |
| **16:00** | **742** | **13.3%** |
| 17:00 | 688 | 12.4% |
| 18:00 | 399 | 7.2% |
| 19:00 | 145 | 2.6% |
| 20:00 | 418 | 7.5% |
| 21:00 | 237 | 4.3% |
| 22:00 | 271 | 4.9% |
| 23:00 | 339 | 6.1% |

> Hours with no events in the window: 03, 04, 05, 06h — the 03:00–06:00 band is the only
> fully inactive block.

---

## 10. New installs vs updates rate

**Conclusion:** **no `first_install`** in the window — all 28 `install` events are reinstalls/repairs over existing installations, against 13 `update`. The install:update ratio is 2.15:1, and 100% of updates were `mode=manual` — no auto-update fired in the period.

| Event type | Occurrences | Distinct installs |
|---|---:|---:|
| `first_install` | **0** | 0 |
| **`install`** | **28** | 4 |
| `update` | 13 | 3 |

### 10.1 Update paths (`from_version` → `to_version`)

| From | To | Occurrences |
|---|---|---:|
| **`v2.47.2`** | **`v2.47.2`** | **2** |
| **`unknown`** | **`v2.47.2`** | **2** |
| `v2.47.1` | `v2.47.2` | 1 |
| `v2.45.0` | `v2.47.0` | 1 |
| `v1.10.0` | `v1.10.0` | 1 |
| `v2.45.0` | `v2.45.0` | 1 |
| `v2.39.2` | `v2.45.0` | 1 |
| `v2.47.0` | `v2.47.1` | 1 |
| `unknown` | `v2.47.0` | 1 |
| `v2.47.0` | `v2.47.2` | 1 |
| `v2.32.0` | `v2.46.0` | 1 |

> Four updates have `from_version == to_version` (re-runs of `update.sh` with no version
> change) and three start from `unknown` — cases where `state.json` had no `installed_version`
> before the update. Two long jumps appear: `v2.32.0 → v2.46.0` and `v2.39.2 → v2.45.0`.

---

## 11. Daily event volume

**Conclusion:** the peak was **2026-08-16** with 875 events (15.7% of the window); the distribution is heavily uneven — 9 days hold 89.3% of volume, and 3 days recorded no events at all.

| Date | Events | % |
|---|---:|---:|
| 2026-08-15 | 7 | 0.1% |
| **2026-08-16** | **875** | **15.7%** |
| 2026-08-17 | 164 | 2.9% |
| 2026-08-18 | 682 | 12.3% |
| 2026-08-19 | 633 | 11.4% |
| 2026-08-20 | 524 | 9.4% |
| 2026-08-21 | 526 | 9.5% |
| 2026-08-22 | 12 | 0.2% |
| 2026-08-24 | 700 | 12.6% |
| 2026-08-25 | 36 | 0.6% |
| 2026-08-26 | 86 | 1.5% |
| 2026-08-27 | 36 | 0.6% |
| 2026-08-28 | 174 | 3.1% |
| 2026-08-31 | 340 | 6.1% |
| 2026-09-01 | 374 | 6.7% |
| 2026-09-02 | 313 | 5.6% |
| 2026-09-03 | 56 | 1.0% |
| 2026-09-04 | 25 | 0.4% |
| **Total** | **5,563** | **100.0%** |

> Days with no events in the window: 2026-08-23, 2026-08-29, 2026-08-30.

---

## 12. Cache efficiency

**Conclusion:** cache carries virtually the entire context load — 8,114,400,078 `cache_read` tokens are 90.4% of the total, against only 2,135,019 non-cached input tokens (0.0%). The aggregate `cache_read / input` ratio is **3,801:1**, indicating extremely high context reuse.

| Component | Tokens | % of total |
|---|---:|---:|
| **Cache read** | **8,114,400,078** | **90.4%** |
| Cache write (creation) | 832,180,331 | 9.3% |
| Output | 31,478,597 | 0.4% |
| Input (non-cached) | 2,135,019 | 0.0% |

### 12.1 Per agent (top 10 by `cache_read`)

| # | Agent | Cache read | % of agent's tokens | cache_read / input ratio |
|---:|---|---:|---:|---:|
| 1 | **`software-architect`** | **3,246,599,261** | **84.6%** | **5,756:1** |
| 2 | `backend-developer` | 1,657,310,609 | 96.7% | 3,243:1 |
| 3 | `frontend-developer` | 947,919,154 | 96.9% | 10,745:1 |
| 4 | `qa-specialist` | 745,563,531 | 95.5% | 7,408:1 |
| 5 | `security-specialist` | 293,769,173 | 88.8% | 1,139:1 |
| 6 | `code-reviewer` | 270,427,190 | 88.4% | 2,388:1 |
| 7 | `laravel-specialist` | 242,185,590 | 95.4% | 6,415:1 |
| 8 | `devops-specialist` | 189,152,310 | 93.2% | 1,651:1 |
| 9 | `database-specialist` | 121,517,550 | 91.3% | 8,659:1 |
| 10 | `backend-test-specialist` | 111,203,181 | 94.8% | 2,819:1 |

> `devops-deploy` is the only agent with `cache_read = 0` (a single run, no reuse possible).

---

## 13. Session-end distribution

**Conclusion:** 95.8% of the 3,460 `session_end` events have `stop_hook_active=false` — the `Stop` hook fired in normal mode in the overwhelming majority of sessions; only 146 (4.2%) were re-entries with the hook already active.

| `stop_hook_active` | Occurrences | % |
|---|---:|---:|
| **`false`** | **3,314** | **95.8%** |
| `true` | 146 | 4.2% |
| **Total** | **3,460** | **100.0%** |

---

## 14. Commands and agents never used in the period

**Conclusion:** 30 of the 35 canonical commands (85.7%) had **zero** invocations in the window, including the core `/devteam:plan`, `/devteam:backend` and `/devteam:frontend` flows — the coverage gap is in the command layer, not the agents, of which 13 out of 18 were exercised.

### 14.1 Commands with zero usage

| Commands with no invocation in the window |
|---|
| `/devteam:adr`, `/devteam:architect`, `/devteam:audit`, `/devteam:backend`, `/devteam:dba` |
| `/devteam:design`, `/devteam:devops`, `/devteam:docs`, `/devteam:explain`, `/devteam:fix` |
| `/devteam:frontend`, `/devteam:fullstack`, `/devteam:health-check`, `/devteam:install`, `/devteam:merge` |
| `/devteam:mobile`, `/devteam:plan`, `/devteam:pr`, `/devteam:push`, `/devteam:qa` |
| `/devteam:refactor`, `/devteam:relayout`, `/devteam:rule`, `/devteam:security`, `/devteam:seo` |
| `/devteam:setup`, `/devteam:symlinks`, `/devteam:tester`, `/devteam:update`, `/devteam:version` |

> Used in the window (5): `/devteam:learn`, `/devteam:status`, `/devteam:commit`, `/devteam:review`, `/devteam:sync-rules`.

### 14.2 Roster agents with zero usage

| Agent | Role |
|---|---|
| `backend-reviewer` | Backend reviewer (only reached via `/devteam:review` routing) |
| `mobile-developer` | Mobile implementation |
| `seo-specialist` | SEO quality gate |
| `setup-assistant` | Project onboarding |
| `ui-ux-designer` | Design system and UX flows |

### 14.3 Agent names outside the canonical roster

| Observed name | Likely origin |
|---|---|
| `Explore` | Claude Code native agent |
| `devops-deploy` | Project-local agent |
| `general-purpose` | Claude Code native agent |
| `laravel-specialist` | Project-local agent |
| `nextjs-spa-specialist` | Project-local agent |
| `unknown` | Fallback bucket — name not resolved in the transcript |

> These 6 names sum to 180 runs (8.8% of the window) — a meaningful volume that is **not** from the dev-team-agents roster and should not be read as harness usage.

---

## 15. Privacy finding — persisted geolocation properties

**Conclusion:** schema inspection shows PostHog's GeoIP enrichment persists **latitude, longitude, postal code and accuracy radius** on events, on top of country/state/city. `PRIVACY.md` documents only that the IP is discarded — it does not mention that coordinates and postal code are stored on the event.

| Persisted property | Documented in `PRIVACY.md`? |
|---|---|
| `$geoip_country_name` | Yes |
| `$geoip_subdivision_1_name` | Yes |
| `$geoip_city_name` | Yes |
| `$geoip_latitude` | **No** |
| `$geoip_longitude` | **No** |
| `$geoip_postal_code` | **No** |
| `$geoip_accuracy_radius` | **No** |
| `$geoip_time_zone` | **No** |

> **Recommendation:** either disable the coordinate/postal-code properties in the PostHog
> project's GeoIP transformation, or declare them explicitly in `PRIVACY.md`. The "What we do NOT
> collect" section currently states no personal identifier is collected, and a latitude/longitude
> pair with a postal code is substantially more precise than "country/state/city" suggests.

---

## 16. Operating system distribution

**Conclusion:** `darwin` (macOS) leads with 3,396 events (61.0%), but Windows via MSYS/Git Bash already accounts for 2,166 (38.9%) — a Windows base large enough to make the symlink path (`/devteam:symlinks`) a real operational risk.

| # | OS | Events | % |
|---:|---|---:|---:|
| 1 | **`darwin`** | **3,396** | **61.0%** |
| 2 | `mingw64_nt-10.0-26200` | 2,166 | 38.9% |
| 3 | `linux` | 1 | 0.0% |

---

## Observations

- **The slash-command layer is essentially unused.** 11 `command_invoked` events against 2,051 agent runs — a 1:186 ratio. 30 of 35 commands were never called, including `/devteam:plan`, `/devteam:backend`, `/devteam:frontend` and `/devteam:fullstack`. Agents are being spawned directly, bypassing the orchestration wrappers that carry the gates (plan gate, scope-lock, spec sync).
- **`software-architect` dominates both runs and cost.** 733 runs (35.7%) and 3,838,820,406 tokens (42.7% of total). Running on Opus in the `reasoning` tier, it is simultaneously the most expensive per token and the most frequent — the combination that weighs most on the bill.
- **Cache is doing nearly all the context work.** 90.4% of tokens are `cache_read` and only 0.0% are non-cached input — an aggregate 3,801:1 ratio. A healthy reuse signal, but it also means the harness's real cost is dominated by context re-reading, not new work.
- **8.8% of runs are not from the roster.** 180 of 2,051 runs come from names outside `agents/` (`Explore`, `general-purpose`, `laravel-specialist`, `nextjs-spa-specialist`, `devops-deploy`, `unknown`). Any reading of "dev-team-agents usage" from raw `agent_completed` is inflated by that proportion.
- **No new installations in the window.** Zero `first_install` against 28 `install` and 13 `update`, all `mode=manual`, across 6 anonymous IDs. The period's telemetry reflects recurring internal use, not adoption — and no auto-update fired.
- **Privacy finding (§ 15).** GeoIP enrichment persists latitude, longitude and postal code on events; `PRIVACY.md` does not declare those three properties. Requires either a fix in the PostHog project transformation or a documentation update.
- **Data gap in this run.** The geography section could not be computed (§ 6) because the environment blocked `$geoip_*` queries. No value was estimated in its place.

---

## Structured summary for LLM consumption

```yaml
janela:
  inicio: "2026-08-15 22:07"
  fim: "2026-09-04 22:07"
  primeiro_evento: "2026-08-15 22:51"
  ultimo_evento: "2026-09-04 16:48"
  timezone: "America/Sao_Paulo"
  dias: 20
  projeto_posthog: 430371
total_eventos: 5563
instalacoes_distintas: 6
eventos_por_tipo:
  session_end: 3460
  agent_completed: 2051
  install: 28
  update: 13
  command_invoked: 11
  first_install: 0
  agent_spawned: 0
top_comandos_por_invocacoes:
  - {comando: "learn", invocacoes: 4}
  - {comando: "status", invocacoes: 4}
  - {comando: "commit", invocacoes: 1}
  - {comando: "review", invocacoes: 1}
  - {comando: "sync-rules", invocacoes: 1}
total_invocacoes_comando: 11
top_agentes_por_execucoes:
  - {agente: "software-architect", execucoes: 733}
  - {agente: "backend-developer", execucoes: 210}
  - {agente: "qa-specialist", execucoes: 190}
  - {agente: "code-reviewer", execucoes: 185}
  - {agente: "security-specialist", execucoes: 183}
  - {agente: "Explore", execucoes: 104}
  - {agente: "frontend-developer", execucoes: 102}
  - {agente: "database-specialist", execucoes: 72}
  - {agente: "devops-specialist", execucoes: 71}
  - {agente: "technical-writer", execucoes: 59}
  - {agente: "laravel-specialist", execucoes: 44}
  - {agente: "backend-test-specialist", execucoes: 28}
  - {agente: "general-purpose", execucoes: 23}
  - {agente: "frontend-test-specialist", execucoes: 18}
  - {agente: "product-analyst", execucoes: 16}
  - {agente: "unknown", execucoes: 4}
  - {agente: "frontend-reviewer", execucoes: 4}
  - {agente: "nextjs-spa-specialist", execucoes: 4}
  - {agente: "devops-deploy", execucoes: 1}
total_execucoes_agente: 2051
modelos_por_provider:
  - {provider: "claude", modelo: "claude-sonnet-5", execucoes: 1009}
  - {provider: "claude", modelo: "claude-opus-5[1m]", execucoes: 907}
  - {provider: "claude", modelo: "claude-haiku-4-5-20251001", execucoes: 110}
  - {provider: "claude", modelo: "claude-opus-5", execucoes: 25}
tokens_totais:
  total: 8980194025
  input: 2135019
  output: 31478597
  cache_creation: 832180331
  cache_read: 8114400078
tokens_por_agente_total_desc:
  - {agente: "software-architect", execucoes: 733, total: 3838820406, input: 564073, output: 15477887, cache_creation: 576179185, cache_read: 3246599261}
  - {agente: "backend-developer", execucoes: 210, total: 1714251132, input: 511022, output: 4902642, cache_creation: 51526859, cache_read: 1657310609}
  - {agente: "frontend-developer", execucoes: 102, total: 977907232, input: 88216, output: 1802198, cache_creation: 28097664, cache_read: 947919154}
  - {agente: "qa-specialist", execucoes: 190, total: 781024141, input: 100640, output: 1956823, cache_creation: 33403147, cache_read: 745563531}
  - {agente: "security-specialist", execucoes: 183, total: 330725990, input: 257866, output: 2004359, cache_creation: 34694592, cache_read: 293769173}
  - {agente: "code-reviewer", execucoes: 185, total: 305923830, input: 113243, output: 1543237, cache_creation: 33840160, cache_read: 270427190}
  - {agente: "laravel-specialist", execucoes: 44, total: 253823909, input: 37754, output: 731683, cache_creation: 10868882, cache_read: 242185590}
  - {agente: "devops-specialist", execucoes: 71, total: 202943124, input: 114598, output: 802141, cache_creation: 12874075, cache_read: 189152310}
  - {agente: "database-specialist", execucoes: 72, total: 133138236, input: 14034, output: 459341, cache_creation: 11147311, cache_read: 121517550}
  - {agente: "backend-test-specialist", execucoes: 28, total: 117356533, input: 39448, output: 397519, cache_creation: 5716385, cache_read: 111203181}
  - {agente: "frontend-test-specialist", execucoes: 18, total: 83340498, input: 2006, output: 246611, cache_creation: 3423837, cache_read: 79668044}
  - {agente: "technical-writer", execucoes: 59, total: 81611998, input: 35614, output: 365922, cache_creation: 9695633, cache_read: 71514829}
  - {agente: "Explore", execucoes: 104, total: 75546199, input: 219576, output: 517225, cache_creation: 10527654, cache_read: 64281744}
  - {agente: "nextjs-spa-specialist", execucoes: 4, total: 38872022, input: 4528, output: 86964, cache_creation: 2596931, cache_read: 36183599}
  - {agente: "product-analyst", execucoes: 16, total: 17672756, input: 524, output: 92060, cache_creation: 2711468, cache_read: 14868704}
  - {agente: "frontend-reviewer", execucoes: 4, total: 14376696, input: 31127, output: 63656, cache_creation: 871235, cache_read: 13410678}
  - {agente: "general-purpose", execucoes: 23, total: 10051923, input: 266, output: 17129, cache_creation: 3369945, cache_read: 6664583}
  - {agente: "unknown", execucoes: 4, total: 2773240, input: 464, output: 11194, cache_creation: 601234, cache_read: 2160348}
  - {agente: "devops-deploy", execucoes: 1, total: 34160, input: 20, output: 6, cache_creation: 34134, cache_read: 0}
media_tokens_por_execucao_desc:
  - {agente: "nextjs-spa-specialist", execucoes: 4, media: 9718006}
  - {agente: "frontend-developer", execucoes: 102, media: 9587326}
  - {agente: "backend-developer", execucoes: 210, media: 8163101}
  - {agente: "laravel-specialist", execucoes: 44, media: 5768725}
  - {agente: "software-architect", execucoes: 733, media: 5237136}
  - {agente: "frontend-test-specialist", execucoes: 18, media: 4630028}
  - {agente: "backend-test-specialist", execucoes: 28, media: 4191305}
  - {agente: "qa-specialist", execucoes: 190, media: 4110653}
  - {agente: "frontend-reviewer", execucoes: 4, media: 3594174}
  - {agente: "devops-specialist", execucoes: 71, media: 2858354}
  - {agente: "database-specialist", execucoes: 72, media: 1849142}
  - {agente: "security-specialist", execucoes: 183, media: 1807246}
  - {agente: "code-reviewer", execucoes: 185, media: 1653642}
  - {agente: "technical-writer", execucoes: 59, media: 1383254}
  - {agente: "product-analyst", execucoes: 16, media: 1104547}
  - {agente: "Explore", execucoes: 104, media: 726406}
  - {agente: "unknown", execucoes: 4, media: 693310}
  - {agente: "general-purpose", execucoes: 23, media: 437040}
  - {agente: "devops-deploy", execucoes: 1, media: 34160}
media_tokens_geral: 4378447
media_tokens_por_comando: nao_computavel  # command_invoked nao carrega contadores de token
geografia:
  status: nao_computado
  motivo: "ambiente bloqueou consultas as propriedades $geoip_*"
  pais: null
  estado: null
  cidade: null
versoes_por_eventos_desc:
  - {versao: "v2.47.2", eventos: 2314}
  - {versao: "v2.47.0", eventos: 1055}
  - {versao: "v2.44.7", eventos: 573}
  - {versao: "v2.47.1", eventos: 505}
  - {versao: "v2.44.4", eventos: 389}
  - {versao: "v2.46.0", eventos: 341}
  - {versao: "v2.45.0", eventos: 273}
  - {versao: "unknown", eventos: 69}
  - {versao: "v1.9.2", eventos: 39}
  - {versao: "main", eventos: 4}
  - {versao: "v1.10.0", eventos: 1}
modelos_por_agente:
  Explore:
    - {modelo: "claude-sonnet-5", execucoes: 104}
  backend-developer:
    - {modelo: "claude-sonnet-5", execucoes: 210}
  backend-test-specialist:
    - {modelo: "claude-sonnet-5", execucoes: 28}
  code-reviewer:
    - {modelo: "claude-sonnet-5", execucoes: 185}
  database-specialist:
    - {modelo: "claude-sonnet-5", execucoes: 72}
  devops-deploy:
    - {modelo: "claude-haiku-4-5-20251001", execucoes: 1}
  devops-specialist:
    - {modelo: "claude-sonnet-5", execucoes: 71}
  frontend-developer:
    - {modelo: "claude-sonnet-5", execucoes: 102}
  frontend-reviewer:
    - {modelo: "claude-sonnet-5", execucoes: 4}
  frontend-test-specialist:
    - {modelo: "claude-sonnet-5", execucoes: 18}
  general-purpose:
    - {modelo: "claude-sonnet-5", execucoes: 23}
  laravel-specialist:
    - {modelo: "claude-haiku-4-5-20251001", execucoes: 44}
  nextjs-spa-specialist:
    - {modelo: "claude-haiku-4-5-20251001", execucoes: 4}
  product-analyst:
    - {modelo: "claude-opus-5[1m]", execucoes: 16}
  qa-specialist:
    - {modelo: "claude-sonnet-5", execucoes: 190}
  security-specialist:
    - {modelo: "claude-opus-5[1m]", execucoes: 171}
    - {modelo: "claude-opus-5", execucoes: 12}
  software-architect:
    - {modelo: "claude-opus-5[1m]", execucoes: 720}
    - {modelo: "claude-opus-5", execucoes: 13}
  technical-writer:
    - {modelo: "claude-haiku-4-5-20251001", execucoes: 59}
  unknown:
    - {modelo: "claude-sonnet-5", execucoes: 2}
    - {modelo: "claude-haiku-4-5-20251001", execucoes: 2}
uso_por_dia_da_semana:
  segunda: 1204
  terca: 1092
  quarta: 1032
  quinta: 616
  sexta: 725
  sabado: 19
  domingo: 875
uso_por_hora:
  "00": 210
  "01": 56
  "02": 4
  "07": 66
  "08": 57
  "09": 167
  "10": 459
  "11": 276
  "12": 227
  "13": 180
  "14": 219
  "15": 403
  "16": 742
  "17": 688
  "18": 399
  "19": 145
  "20": 418
  "21": 237
  "22": 271
  "23": 339
volume_por_dia:
  "2026-08-15": 7
  "2026-08-16": 875
  "2026-08-17": 164
  "2026-08-18": 682
  "2026-08-19": 633
  "2026-08-20": 524
  "2026-08-21": 526
  "2026-08-22": 12
  "2026-08-24": 700
  "2026-08-25": 36
  "2026-08-26": 86
  "2026-08-27": 36
  "2026-08-28": 174
  "2026-08-31": 340
  "2026-09-01": 374
  "2026-09-02": 313
  "2026-09-03": 56
  "2026-09-04": 25
  dias_sem_eventos: ["2026-08-23", "2026-08-29", "2026-08-30"]
instalacoes_vs_atualizacoes:
  first_install: 0
  install: 28
  update: 13
  update_modes: {manual: 13}
  caminhos_update:
    - {de: "v2.47.2", para: "v2.47.2", ocorrencias: 2}
    - {de: "unknown", para: "v2.47.2", ocorrencias: 2}
    - {de: "v2.47.1", para: "v2.47.2", ocorrencias: 1}
    - {de: "v2.45.0", para: "v2.47.0", ocorrencias: 1}
    - {de: "v1.10.0", para: "v1.10.0", ocorrencias: 1}
    - {de: "v2.45.0", para: "v2.45.0", ocorrencias: 1}
    - {de: "v2.39.2", para: "v2.45.0", ocorrencias: 1}
    - {de: "v2.47.0", para: "v2.47.1", ocorrencias: 1}
    - {de: "unknown", para: "v2.47.0", ocorrencias: 1}
    - {de: "v2.47.0", para: "v2.47.2", ocorrencias: 1}
    - {de: "v2.32.0", para: "v2.46.0", ocorrencias: 1}
eficiencia_cache:
  cache_read_pct_do_total: 90.36
  input_pct_do_total: 0.0238
  razao_cache_read_por_input: 3801
  por_agente_top10:
    - {agente: "software-architect", cache_read: 3246599261, pct_dos_tokens_do_agente: 84.57, razao_cache_read_por_input: 5756}
    - {agente: "backend-developer", cache_read: 1657310609, pct_dos_tokens_do_agente: 96.68, razao_cache_read_por_input: 3243}
    - {agente: "frontend-developer", cache_read: 947919154, pct_dos_tokens_do_agente: 96.93, razao_cache_read_por_input: 10745}
    - {agente: "qa-specialist", cache_read: 745563531, pct_dos_tokens_do_agente: 95.46, razao_cache_read_por_input: 7408}
    - {agente: "security-specialist", cache_read: 293769173, pct_dos_tokens_do_agente: 88.83, razao_cache_read_por_input: 1139}
    - {agente: "code-reviewer", cache_read: 270427190, pct_dos_tokens_do_agente: 88.4, razao_cache_read_por_input: 2388}
    - {agente: "laravel-specialist", cache_read: 242185590, pct_dos_tokens_do_agente: 95.41, razao_cache_read_por_input: 6415}
    - {agente: "devops-specialist", cache_read: 189152310, pct_dos_tokens_do_agente: 93.2, razao_cache_read_por_input: 1651}
    - {agente: "database-specialist", cache_read: 121517550, pct_dos_tokens_do_agente: 91.27, razao_cache_read_por_input: 8659}
    - {agente: "backend-test-specialist", cache_read: 111203181, pct_dos_tokens_do_agente: 94.76, razao_cache_read_por_input: 2819}
fim_de_sessao:
  stop_hook_active_false: 3314
  stop_hook_active_true: 146
cobertura_zero_uso:
  comandos_canonicos_total: 35
  comandos_sem_uso_total: 30
  comandos_sem_uso: ["adr", "architect", "audit", "backend", "dba", "design", "devops", "docs", "explain", "fix", "frontend", "fullstack", "health-check", "install", "merge", "mobile", "plan", "pr", "push", "qa", "refactor", "relayout", "rule", "security", "seo", "setup", "symlinks", "tester", "update", "version"]
  comandos_usados: ["learn", "status", "commit", "review", "sync-rules"]
  agentes_roster_total: 18
  agentes_roster_sem_uso: ["backend-reviewer", "mobile-developer", "seo-specialist", "setup-assistant", "ui-ux-designer"]
  agentes_fora_do_roster: ["Explore", "devops-deploy", "general-purpose", "laravel-specialist", "nextjs-spa-specialist", "unknown"]
  execucoes_fora_do_roster: 180
  execucoes_fora_do_roster_pct: 8.78
sistema_operacional:
  "darwin": 3396
  "mingw64_nt-10.0-26200": 2166
  "linux": 1
achado_seguranca_privacidade:
  tipo: geolocalizacao_persistida_nao_documentada
  propriedades_nao_documentadas: ["$geoip_latitude", "$geoip_longitude", "$geoip_postal_code", "$geoip_accuracy_radius", "$geoip_time_zone"]
  documento_afetado: "PRIVACY.md"
  severidade: media
  acao_recomendada: "desabilitar coordenadas/CEP na transformacao GeoIP do projeto PostHog ou declara-las em PRIVACY.md"
```
