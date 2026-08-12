# Prompt — PostHog Usage Report (last N days)

**Purpose:** Have an agent pull dev-team-agents anonymous usage telemetry from PostHog
for a given window and turn it into a human- and LLM-readable report at
`docs/reports/metrics-last-<N>-days.md`.

This file is a **reusable prompt**, not a script. Paste its content (or the whole file)
to an agent session to run the collection + report flow. Defaults to a 20-day window;
change the number where marked `[N]`.

---

## Prompt

You are generating a usage-metrics report for the `dev-team-agents` project from its
PostHog telemetry data. Follow these steps in order.

### 1. Read the API key

Read the PostHog **Personal API Key** from `credentials.local.json` at the repository
root (`posthog.personalApiKey`). This file is gitignored and holds a private key —
**never print its value, never commit it, never paste it into this report.** If the
file or the key is missing, stop and tell the user how to create it (see the "How to
get the key" section in this repo's conversation history / PostHog docs — Personal API
Keys are created under Account Settings → Personal API Keys with `insight:read` and
`query:read` scopes).

### 2. Identify the project

Resolve the PostHog **project ID**. If not already known, call
`GET https://us.i.posthog.com/api/projects/` with the personal API key
(`Authorization: Bearer <key>`) and pick the project whose name matches this repo
(`dev-team-agents`) or ask the user to confirm if more than one project exists. The
ingestion region is `us.i.posthog.com` (see `scripts/helpers/telemetry-send.sh`
`POSTHOG_ENDPOINT`) unless `DEVTEAM_POSTHOG_ENDPOINT` indicates a self-hosted instance.

### 3. Query events for the last **[N=20]** days

Use the HogQL query endpoint:

```
POST https://us.i.posthog.com/api/projects/:project_id/query/
Authorization: Bearer <PERSONAL_API_KEY>
Content-Type: application/json
```

Query the `events` table filtered to `timestamp >= now() - interval '[N] days'`. The
known event vocabulary (from `PRIVACY.md`) is:

| Event | Key properties |
|---|---|
| `first_install` | `version`, `os` |
| `install` | `version`, `os` |
| `update` | previous version, new version, `mode` |
| `agent_spawned` | `os`, `version` |
| `command_invoked` | command name, `os`, `version` |
| `session_end` | `stop_hook_active`, `os`, `version` |
| `agent_completed` | agent name, resolved model, `provider`, token counts (input/output/cache_creation/cache_read) |

All events also carry `$lib` (always `dev-team-agents`), `version`, `os`, and
PostHog's own **geoip enrichment properties** (`$geoip_country_name`,
`$geoip_subdivision_1_name` as state/region, `$geoip_city_name`) — these are derived
server-side from the request IP, which is itself discarded at ingestion (see
`PRIVACY.md` § "What we do NOT collect"), so no raw IP is ever exposed, only the
resolved geography.

Pull the full raw event set for the window (event name, timestamp, and all
`properties.*` needed below) rather than pre-aggregating in the query, so all metrics
below can be computed from one consistent dataset.

### 4. Compute the following metrics

1. **Comandos mais chamados** — count of `command_invoked` grouped by command name, ranked desc.
2. **Agentes mais chamados** — count of `agent_spawned` (and/or `agent_completed`) grouped by agent name, ranked desc.
3. **Ranking de modelos utilizados, agrupado por provider** — from `agent_completed`, group by `provider` → `model`, counts.
4. **Ranking de consumo de tokens** — total tokens (input + output + cache_creation + cache_read) per agent, ranked desc.
5. **Agentes/comandos que mais consomem tokens em média** — average tokens per invocation, per agent (from `agent_completed`) and, if determinable, per command.
6. **Ranking de país, estado e cidade** — from `$geoip_country_name`, `$geoip_subdivision_1_name`, `$geoip_city_name`, each ranked by event count.
7. **Ranking das versões usadas no período** — group all events by `properties.version`, ranked desc.
8. **Lista de modelos utilizados agrupada por agente** — for each agent name, the distinct set of models it invoked (and their counts), to spot agents calling unexpected models.
9. **Dias e horários de maior uso** — event count by day-of-week and by hour-of-day (use event `timestamp`, convert to a stated timezone — default UTC, note it explicitly in the report), to identify usage patterns.

**Suggested additional metrics** (include unless the user says otherwise):

10. **Taxa de novas instalações vs atualizações** — `first_install` vs `install`/`update` counts in the window.
11. **Volume de eventos por dia** — daily event count trend across the window (line/table), not just aggregated day-of-week.
12. **Eficiência de cache** — for `agent_completed`, ratio of `cache_read_tokens` to `input_tokens` (aggregate and per top agents) — signals context reuse efficiency.
13. **Distribuição de fim de sessão** — `session_end` count where `stop_hook_active=true` vs `false`.
14. **Comandos/agentes nunca usados no período** — cross-reference the observed command/agent names against the canonical lists (`scripts/lib/commands.json`, `agents/*.md`) to flag zero-usage entries — a coverage gap, not just a ranking.

If any metric cannot be computed from the available event properties (e.g. a property
was never populated in the window), state that explicitly in the report instead of
omitting the section silently.

### 5. Write the report

Create `docs/reports/metrics-last-[N]-days.md` (overwrite if it already exists for the
same window) with this structure:

- **Header**: report title, date range covered (explicit start/end dates), generation
  timestamp, total event count, timezone used for time-based metrics.
- **One section per metric above**, each as a markdown table, ranked descending, with
  a one-line takeaway sentence above or below the table (e.g. "X is the most-used
  command, called N times, Y% of all command invocations").
- **Closing "Observations" section**: 3-5 bullet points of notable patterns, anomalies,
  or gaps found (e.g. skewed adoption, unexpected model usage, a zero-usage command).
- Use consistent, scannable formatting: tables over prose, bold on the top row of each
  ranking, no more than one paragraph of prose per section. Optimize for a human
  skimming quickly and for an LLM re-reading it later as structured context — no
  narrative fluff.

### 6. Do not leak the key

Never write the API key, the raw HTTP request/response containing it, or
`credentials.local.json`'s contents into the report or into any committed file. The
key is a **read-scoped Personal API Key** — treat it as a secret throughout this task.

---

## Notes for the agent running this prompt

- This report is descriptive/analytical output, not a change to `dev-team-agents`
  behavior — it does not require the Plan Gate defined in `CLAUDE.md`.
- Follow `skills/shared/conventional-commits/SKILL.md` if asked to commit the
  generated report.
- If PostHog's HogQL query API differs from what's assumed here (endpoint shape,
  auth scheme) at execution time, adapt using PostHog's current API docs — this
  prompt reflects the schema known as of this repo's `scripts/helpers/telemetry-send.sh`
  and `PRIVACY.md` at authoring time and may drift as new telemetry events are added.
