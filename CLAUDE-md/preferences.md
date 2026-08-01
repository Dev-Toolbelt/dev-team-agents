## User Preferences

All user-level preferences are stored in `.dev-team-agents/user-data/preferences.json` (gitignored). The file is created by `install.sh` on first install and validated/migrated by the health check. The authoritative static default schema lives in `scripts/lib/preferences-defaults.json` — the single source of truth read by both `install.sh` (on install/update) and the `session-start.sh` health-check backfill (on every session).

### Schema

```json
{
  "language": "pt-BR",
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "session_summary_max_days": 30,
  "session_summary_max_entries": 30,
  "docs_stale_after_days": 30,
  "auto_update": true,
  "update_check_interval_hours": 24,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000,
  "telemetry": true,
  "worktree_active": true,
  "worktree_base_branch": null,
  "worktree_path": ".dev-team-agents/worktrees",
  "worktree_docker_isolate": true,
  "qa_browser": null
}
```

**These are the values a preferences.json gets when it does not exist yet.** They are never applied to a file that already exists: `install.sh` merges with existing values winning, and the backfill only adds absent keys. The same holds for `credentials.local.json` — created only when absent, never rewritten.

**Consent keys — `telemetry` and `auto_update`.** Both are `true` in the schema, which is the value a *fresh* file gets (for `telemetry`, still subject to the install prompt below). Neither is ever written as `true` into a preferences.json that already exists: that file's owner never saw a prompt for a field added after they installed, so an absent key means "no". Both `install.sh` and the session-start backfill write `false` in that case.

| Field | Default | Purpose |
|-------|---------|---------|
| `language` | `"pt-BR"` | BCP 47 language tag for agent conversation with the user. The installer prompts for it on first install; this is the value used when nobody answers |
| `context_window_percent_warning` | `55` | % at which agents emit a `warning` notification |
| `context_window_percent_limit` | `60` | % at which agents emit a `critical` notification |
| `suppress_notifications` | `false` | `false` / `true` / `["info"]` — suppress notification types |
| `session_summary_max_days` | `30` | Days before session-summary entries are trimmed |
| `session_summary_max_entries` | `30` | Maximum number of session-summary entries |
| `docs_stale_after_days` | `30` | Days before `project.md` and `session-summary.md` are flagged as stale |
| `auto_update` | `true` on a fresh file, `false` on backfill | Auto-update when a new version is detected. Consent key — see the note above the table |
| `update_check_interval_hours` | `24` | Hours between update checks |
| `transcript_multiplier` | `1.8` | Multiplier applied to transcript token count to estimate full context (compensates for system prompt + tools not stored in transcript) |
| `model_max_tokens` | `200000` | Maximum context window for the active model; used to compute context percentage from transcript tokens |
| `telemetry` | written by consent, not by the schema | Anonymous usage telemetry. On first install `install.sh` **overwrites** the schema value with the user's answer, and it is `false` unless the user actively accepted — see "Telemetry consent" below. Set to `false` at any time to opt out. No personal data is ever collected — see `PRIVACY.md` |
| `worktree_active` | `true` | When `true`, coding agents default to a git worktree per task without asking. See [worktree cascade](#worktree-defaults) |
| `worktree_base_branch` | `null` | Base branch for new worktrees. `null` = auto-detect (`origin/HEAD` → current branch). Project `CLAUDE.md`/config overrides |
| `worktree_path` | `".dev-team-agents/worktrees"` | Directory where worktrees are created (`<path>/<context>/<title>`) |
| `worktree_docker_isolate` | `true` | When `worktree_active` and the project uses Docker Compose, spin up an isolated compose stack per worktree. Gated: no effect unless both conditions hold |
| `qa_browser` | `null` | Preferred browser for `qa-specialist` browser testing when the in-app Claude browser is unavailable (CLI). `null` = ask on first use and offer to save the choice here |

> **Fallback safety**: all scripts that read `preferences.json` use hardcoded defaults for every key. If the file is missing, malformed, or a key is removed, scripts fall back to the defaults above without error. Never leave a key out — the schema above is the authoritative default set.

> **Exception — the `telemetry` read path fails closed.** `scripts/lib/telemetry-guard.sh` is the single definition of the gate (`_telemetry_enabled`), sourced by `scripts/helpers/telemetry-send.sh`, `stop/05-telemetry.sh` and `pre-tool-use/02b-telemetry.sh`. It returns "disabled" for a missing file, an unreadable file, a **missing `telemetry` key**, or no `python3` to read it with — consent that was never recorded is not consent. Never flip that to `true`, and never let a consumer that cannot source the guard fall back to sending.
>
> **The read path and the backfill now agree.** They used to disagree: `preferences-defaults.json` carries `"telemetry": true`, so a legacy file missing the key read as *disabled*, and then the next session start backfilled the schema value and silently flipped it to *enabled*. The fix was not to change the schema value — a fresh install should still default to enabled, subject to the prompt — but to make the backfill consent-aware. `telemetry` and `auto_update` are `CONSENT_KEYS` in both `install.sh` and `scripts/hooks/session-start.sh`: when the key is absent from an **existing** `preferences.json`, `false` is written, not the schema default. Keep the two lists in sync, and do not add a key to either without deciding whether an absent value means "no".

### Telemetry consent

`install.sh` decides the value on **first install only** (no existing `preferences.json`); on every re-install and update an existing value is preserved untouched.

| Situation at install time | `telemetry` written |
|---|---|
| A controlling terminal is reachable (`/dev/tty` opens) and the user answers Enter/`y` | `true` |
| …and the user answers `n` | `false` |
| …and nobody answers within 60s, or stdin hits EOF | `false` — silence is not consent |
| `DEVTEAM_NONINTERACTIVE=1` (CI, image builds, provisioning) | `false`, no prompt |
| No terminal reachable at all | `false`, with a printed note explaining how to enable it later |

The reachability test is "can we open `/dev/tty`", **not** `[ -t 0 ]`. The documented install path is `curl … | bash`, where stdin is a pipe and `[ -t 0 ]` is false even with a human watching — which is how the prompt used to be skipped while the value was preset to `true`.

### Worktree defaults

`worktree_*` keys set the **default** worktree behavior; the per-session file `.dev-team-agents/.worktree-session` overrides them. Coding agents resolve the decision in this order:

| Precedence | Source | Behavior |
|---|---|---|
| 1 (highest) | `.dev-team-agents/.worktree-session` present | Follow the stored per-session decision silently |
| 2 | `worktree_active` present in `preferences.json` | Use it **without asking**; write the session file so the rest of the session is consistent |
| 3 (fallback) | key absent (legacy install) | Ask the user once (original behavior) |

### Health-check backfill

On every session start, `scripts/hooks/session-start.sh` compares `preferences.json` against `scripts/lib/preferences-defaults.json` and writes any **missing** key with its default value. Existing user values are never overwritten; the write is a no-op when the file is already complete. This self-heals installs that predate a new key.

**Consent keys are the exception.** `telemetry` and `auto_update` are backfilled as `false`, never as the schema's `true`. The file already existing means its owner never saw a prompt for a field added later, so the backfill must not decide for them. Nothing else is special-cased.

### Language Rule

| Output | Language |
|--------|---------|
| Documents (ADRs, session-summary, changelogs, code comments) | **Always English** |
| Plans presented for user approval | **`language` field from `preferences.json`** — plans are conversation items, not documents |
| Conversation with the user (responses, questions, notifications) | **`language` field from `preferences.json`** — fallback to English |

### Migration

The legacy `.auto-update` flag file is automatically migrated to `preferences.json → auto_update` by `install.sh` and the health check.
