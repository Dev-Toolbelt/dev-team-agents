# PostHog Usage Metrics — Last 20 Days

**Window:** 2026-07-23 18:17 UTC → 2026-08-12 14:01 UTC (20 days, `now() - INTERVAL 20 DAY`)
**Generated:** 2026-08-12
**Timezone used for time-based metrics:** UTC (raw PostHog `timestamp`)
**Total events in window:** 1,284 (2 manual test events and 1 malformed event excluded from 1,287 raw rows)
**Source:** PostHog project `430371` ("Default project"), HogQL `events` table, generated per `docs/prompts/posthog-metrics-report.md`

> ⚠️ **Sample caveat:** this data reflects a single developer's local sessions (the geo
> breakdown below shows why). It is **not** representative of the wider installed base —
> `agent_spawned` and `command_invoked` in particular have very low volume in this window
> and should not be read as adoption signals yet.

---

## 1. Comandos mais chamados

Only 5 `command_invoked` events landed in the window — too small a sample to rank meaningfully, but listed for completeness.

| Command | Invocations |
|---|---|
| `architect` | 1 |
| `review` | 1 |
| `pr` | 1 |
| `sync-rules` | 1 |
| `status` | 1 |

**Takeaway:** `command_invoked` volume (5) is far below `agent_completed` volume (664) in the same window — most work in this window was driven directly through agent spawns, not the `/devteam:*` slash-command layer, or the event simply under-fires. Worth checking `scripts/hooks/pre-tool-use/02b-telemetry.sh`'s command-name matcher against real usage.

---

## 2. Agentes mais chamados

Ranked by `agent_completed` (no `agent_spawned` events appeared in this window, so completion count is used as the proxy).

| Rank | Agent | Completions |
|---|---|---|
| 1 | **backend-developer** | 177 |
| 2 | frontend-developer | 133 |
| 3 | devops-specialist | 67 |
| 4 | security-specialist | 63 |
| 5 | backend-test-specialist | 50 |
| 5 | frontend-test-specialist | 50 |
| 7 | software-architect | 43 |
| 8 | test-author | 39 |
| 9 | technical-writer | 10 |
| 9 | product-analyst | 10 |
| 11 | code-reviewer | 6 |
| 11 | qa-specialist | 6 |
| 13 | backend-reviewer | 5 |
| 13 | frontend-reviewer | 5 |

**Takeaway:** `backend-developer` is the most-invoked agent (27% of all completions), followed by `frontend-developer` (20%) — together nearly half of all agent activity in the window.

---

## 3. Ranking de modelos utilizados, agrupado por provider

| Provider | Model | Invocations |
|---|---|---|
| claude | **claude-sonnet-5** | 499 |
| claude | claude-opus-5[1m] | 116 |
| claude | claude-haiku-4-5-20251001 | 49 |

**Takeaway:** all recorded activity ran on Claude — 75% on Sonnet 5, 17% on Opus 5 (1M context), 7% on Haiku 4.5. No other provider appeared in the window.

---

## 4. Ranking de consumo de tokens

Total tokens (input + output + cache_creation + cache_read) per agent, descending.

| Rank | Agent | Total tokens | Invocations |
|---|---|---|---|
| 1 | **backend-developer** | 586,179,566 | 177 |
| 2 | frontend-developer | 328,738,619 | 133 |
| 3 | test-author | 314,928,051 | 39 |
| 4 | security-specialist | 156,221,148 | 63 |
| 5 | software-architect | 146,726,525 | 43 |
| 6 | frontend-test-specialist | 120,737,348 | 50 |
| 7 | devops-specialist | 110,507,050 | 67 |
| 8 | backend-test-specialist | 52,021,265 | 50 |
| 9 | backend-reviewer | 15,857,617 | 5 |
| 10 | technical-writer | 14,793,236 | 10 |
| 11 | frontend-reviewer | 13,651,733 | 5 |
| 12 | qa-specialist | 13,397,030 | 6 |
| 13 | product-analyst | 12,320,175 | 10 |
| 14 | code-reviewer | 3,328,352 | 6 |

**Window totals:** input 843,081 · output 5,499,345 · cache creation 136,003,707 · **cache read 1,747,061,582**

**Takeaway:** `backend-developer` leads both by call count and by total tokens. Cache-read tokens dominate the total by a wide margin across every agent (see § 12).

---

## 5. Agentes que mais consomem tokens em média (por invocação)

| Rank | Agent | Avg tokens/call | Invocations |
|---|---|---|---|
| 1 | **test-author** | 8,075,078 | 39 |
| 2 | software-architect | 3,412,245 | 43 |
| 3 | backend-developer | 3,311,749 | 177 |
| 4 | backend-reviewer | 3,171,523 | 5 |
| 5 | frontend-reviewer | 2,730,347 | 5 |
| 6 | security-specialist | 2,479,701 | 63 |
| 7 | frontend-developer | 2,471,719 | 133 |
| 8 | frontend-test-specialist | 2,414,747 | 50 |
| 9 | qa-specialist | 2,232,838 | 6 |
| 10 | devops-specialist | 1,649,359 | 67 |
| 11 | technical-writer | 1,479,324 | 10 |
| 12 | product-analyst | 1,232,018 | 10 |
| 13 | backend-test-specialist | 1,040,425 | 50 |
| 14 | code-reviewer | 554,725 | 6 |

*(`command_invoked` carries no token data, so per-command average cannot be computed from this event.)*

**Takeaway:** `test-author` has by far the highest per-call average (2.4× the next agent) despite a mid-size call count — each invocation is doing unusually large context work relative to its peers.

---

## 6. Ranking de país, estado e cidade

| Country | Events |
|---|---|
| **Brazil** | 1,283 |
| France | 1 |

| State/Region | Events |
|---|---|
| **Ceará** | 1,260 |
| São Paulo | 23 |
| Île-de-France | 1 |

| City | Events |
|---|---|
| **Fortaleza** | 1,260 |
| Bauru | 23 |
| Aulnay-sous-Bois | 1 |

**Takeaway:** this confirms the sample-size caveat above — 98% of events originate from one city (Fortaleza, CE), i.e. this is dogfood/dev-machine telemetry, not a distributed user base yet.

> 🔒 **Privacy note (out of scope for this report, flagged for follow-up):** the geo values
> above come from PostHog's `$geoip_*` enrichment as expected, but every raw event
> inspected in this window also carries a **`$ip` property with the literal client IP
> address**. `PRIVACY.md` states "IP addresses (stripped at the PostHog ingestion
> layer)" — that claim does not match what was observed in the raw event payload. This
> is worth a dedicated look at the PostHog project's IP-anonymization / person-profile
> settings; not something this report should fix inline.

---

## 7. Ranking das versões usadas no período

| Rank | Version | Events |
|---|---|---|
| 1 | **v2.44.0** | 791 |
| 2 | v2.29.0 | 149 |
| 3 | v1.8.2 | 111 |
| 4 | v1.8.1 | 46 |
| 5 | *unknown* | 40 |
| 6 | v2.31.0 | 19 |
| 7 | v1.11.0 | 16 |
| 8 | v2.15.1 | 10 |
| 9 | v2.30.1 | 9 |
| 10 | v2.27.3 | 5 |
| 10 | v2.32.0 | 5 |
| 12 | v2.7.0 | 4 |
| 12 | v2.16.0 | 4 |
| 12 | v2.20.0 | 4 |
| 12 | v2.27.0 | 4 |
| 12 | v2.41.2 | 4 |
| *(+9 more versions with ≤3 events each)* | | |

**Takeaway:** `v2.44.0` (the current tip) dominates with 62% of events, expected since most volume is today's session. The long tail of older versions (v1.8.x, v2.7–v2.41.x) reflects historical events retained within the 20-day window, not concurrent installs. `unknown` (40 events, 3%) comes from `install`/`update` events captured before the version was resolved — see § "Observations".

---

## 8. Lista de modelos utilizados agrupada por agente

| Agent | Model(s) used | Notes |
|---|---|---|
| backend-developer | claude-sonnet-5 (177) | single model |
| frontend-developer | claude-sonnet-5 (133) | single model |
| devops-specialist | claude-sonnet-5 (67) | single model |
| security-specialist | claude-opus-5[1m] (63) | single model |
| backend-test-specialist | claude-sonnet-5 (50) | single model |
| frontend-test-specialist | claude-sonnet-5 (50) | single model |
| software-architect | claude-opus-5[1m] (43) | single model |
| test-author | claude-haiku-4-5-20251001 (39) | single model |
| technical-writer | claude-haiku-4-5-20251001 (10) | single model |
| product-analyst | claude-opus-5[1m] (10) | single model |
| code-reviewer | claude-sonnet-5 (6) | single model |
| qa-specialist | claude-sonnet-5 (6) | single model |
| backend-reviewer | claude-sonnet-5 (5) | single model |
| frontend-reviewer | claude-sonnet-5 (5) | single model |

**Takeaway:** every agent in this window called **exactly one** model — no agent split across multiple models or providers. This matches the `tiers.json` tier→model mapping in `CLAUDE.md` (`reasoning`→opus, `backend-exec`/`frontend`→sonnet, `repetitive`→haiku) with no observed drift between configured tier and resolved model.

---

## 9. Dias e horários de maior uso (UTC)

**By day of week:**

| Day | Events |
|---|---|
| **Wednesday** | 829 |
| Thursday | 151 |
| Friday | 137 |
| Saturday | 47 |
| Tuesday | 47 |
| Monday | 43 |
| Sunday | 30 |

**By hour of day (UTC):**

| Hour | Events | | Hour | Events |
|---|---|---|---|---|
| 00 | 46 | | 12 | 11 |
| 01 | 231 | | 13 | 298 |
| 02 | 93 | | 14 | 29 |
| 03 | 28 | | 15 | 22 |
| 04 | 17 | | 16 | 18 |
| 05 | 1 | | 17 | 25 |
| 06 | 9 | | 18 | 40 |
| 07 | 14 | | 19 | 49 |
| 08 | 0 | | 20 | 41 |
| 09 | 0 | | 21 | 25 |
| 10 | 188 | | 22 | 52 |
| 11 | 14 | | 23 | 33 |

**Takeaway:** ⚠️ heavily skewed by today (2026-08-12, a Wednesday, contributed 796 of 1,284 events — see the daily trend in § 11). Peak hours 01:00 and 13:00 UTC correspond to roughly 22:00 and 10:00 in `America/Fortaleza` (UTC-3, the dominant geo from § 6) — consistent with a late-evening and mid-morning working pattern for that single contributor. Treat day-of-week ranking as unreliable until volume is more evenly distributed across weeks.

---

## 10. Taxa de novas instalações vs atualizações

| Event | Count |
|---|---|
| `first_install` | 10 |
| `install` (re-install/update via installer) | 76 |
| `update` (manual `update.sh`) | 33 |

**Takeaway:** re-installs/updates outnumber first installs ~11:1 in this window — expected for an actively-developed local copy being reinstalled/updated repeatedly during testing, not organic new-user growth.

---

## 11. Volume de eventos por dia

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
| **2026-08-12** | **796** |

**Takeaway:** the window is dominated by the current day (62% of total volume) — consistent with this report being generated mid-session on 2026-08-12. Excluding today, 2026-08-06 (119) and 2026-07-24 (93) were the next-heaviest days.

---

## 12. Eficiência de cache

| Metric | Value |
|---|---|
| Total input tokens | 843,081 |
| Total cache-read tokens | 1,747,061,582 |
| Total cache-creation tokens | 136,003,707 |
| **Cache-read : input ratio** | **~2,072 : 1** |

**Takeaway:** cache reads vastly outweigh fresh input tokens across the window — the prompt-cache system is doing the overwhelming majority of context delivery, which is expected behavior for repeated agent invocations sharing a cached system/skill context within the 1-hour TTL. This is a strong efficiency signal, not a concern.

---

## 13. Distribuição de fim de sessão

| `stop_hook_active` | Sessions |
|---|---|
| `false` | 475 |
| `true` | 21 |

**Takeaway:** 96% of sessions ended with the stop hook inactive (i.e., a clean, non-blocked stop) — only 4% hit an active-stop-hook condition (session summary required, lint failures, etc.) at end-of-session.

---

## 14. Comandos/agentes nunca usados no período

Cross-referencing observed `agent_completed` names against the agent roster in `agents/*.md` (17 agents total):

**Agents with zero completions in this window:** `database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist` (4 of 17 — no invocation recorded at all in 20 days).

Cross-referencing observed `command_invoked` names against `scripts/lib/commands.json` (`/devteam:*` roster) is not reliable here — only 5 of the ~25 documented commands fired in the window (`architect`, `review`, `pr`, `sync-rules`, `status`), meaning 20 commands show zero usage. Given the § 1 caveat about `command_invoked` volume being suspiciously low relative to `agent_completed`, this table is **not** trustworthy as an adoption signal yet and is not broken out further — flagged instead as a possible instrumentation gap (see Observations).

---

## Observations

- **This is single-developer dogfood data, not user-base telemetry.** 98% of geo-tagged events trace to one city; treat every ranking above as "how this repo's own maintainer used it," not adoption at large.
- **`command_invoked` under-fires relative to `agent_completed`** (5 vs. 664 in the same 20-day window, despite commands routinely spawning multiple agents). Worth checking whether `scripts/hooks/pre-tool-use/02b-telemetry.sh`'s command-name detection is missing invocation paths (e.g. commands run without the expected trigger phrase).
- **`version: "unknown"` on 40 events (all `install`/`update`/`agent_completed`)** — the version isn't always resolved at capture time; worth checking whether `state.json` is read before or after the write it's reporting on.
- **Zero cross-model agents**: every agent used exactly one model for its entire tier in this window, matching `tiers.json` with no observed drift — a good consistency signal for the tier→model contract described in `CLAUDE.md`.
- **Cache efficiency is very high** (~2,072:1 cache-read-to-input) — the prompt-cache system is carrying nearly all context reuse, which is the intended behavior, not a red flag.
- **Potential privacy documentation gap**: raw `$ip` values were observed in event properties (see § 6 note) despite `PRIVACY.md` stating IPs are stripped at ingestion — recommend a follow-up check of PostHog's IP-anonymization setting for this project, independent of this report.
- **4 agents had zero activity** in the window (`database-specialist`, `mobile-developer`, `ui-ux-designer`, `seo-specialist`) — expected if no matching work (schema, mobile, design, SEO scope) occurred in 20 days, not necessarily a defect.
