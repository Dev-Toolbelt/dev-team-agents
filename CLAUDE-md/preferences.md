## User Preferences

All user-level preferences are stored in `.dev-team-agents/user-data/preferences.json` (gitignored). The file is created by `install.sh` on first install and validated/migrated by the health check. The authoritative static default schema lives in `scripts/lib/preferences-defaults.json` — the single source of truth read by both `install.sh` (on install/update) and the `session-start.sh` health-check backfill (on every session).

### Schema

```json
{
  "language": "en",
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "session_summary_max_days": 30,
  "session_summary_max_entries": 30,
  "docs_stale_after_days": 30,
  "auto_update": false,
  "update_check_interval_hours": 24,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000,
  "telemetry": true,
  "worktree_active": false,
  "worktree_base_branch": null,
  "worktree_path": ".claude/worktrees",
  "worktree_docker_isolate": true,
  "qa_browser": null
}
```

| Field | Default | Purpose |
|-------|---------|---------|
| `language` | `"en"` | BCP 47 language tag for agent conversation with the user |
| `context_window_percent_warning` | `55` | % at which agents emit a `warning` notification |
| `context_window_percent_limit` | `60` | % at which agents emit a `critical` notification |
| `suppress_notifications` | `false` | `false` / `true` / `["info"]` — suppress notification types |
| `session_summary_max_days` | `30` | Days before session-summary entries are trimmed |
| `session_summary_max_entries` | `30` | Maximum number of session-summary entries |
| `docs_stale_after_days` | `30` | Days before `project.md` and `session-summary.md` are flagged as stale |
| `auto_update` | `false` | Auto-update when a new version is detected |
| `update_check_interval_hours` | `24` | Hours between update checks |
| `transcript_multiplier` | `1.8` | Multiplier applied to transcript token count to estimate full context (compensates for system prompt + tools not stored in transcript) |
| `model_max_tokens` | `200000` | Maximum context window for the active model; used to compute context percentage from transcript tokens |
| `telemetry` | `true` | Anonymous usage telemetry (set to `false` to opt out). No personal data is ever collected — see `PRIVACY.md` |
| `worktree_active` | `false` | When `true`, coding agents default to a git worktree per task without asking. See [worktree cascade](#worktree-defaults) |
| `worktree_base_branch` | `null` | Base branch for new worktrees. `null` = auto-detect (`origin/HEAD` → current branch). Project `CLAUDE.md`/config overrides |
| `worktree_path` | `".claude/worktrees"` | Directory where worktrees are created (`<path>/<context>/<title>`) |
| `worktree_docker_isolate` | `true` | When `worktree_active` and the project uses Docker Compose, spin up an isolated compose stack per worktree. Gated: no effect unless both conditions hold |
| `qa_browser` | `null` | Preferred browser for `qa-specialist` browser testing when the in-app Claude browser is unavailable (CLI). `null` = ask on first use and offer to save the choice here |

> **Fallback safety**: all scripts that read `preferences.json` use hardcoded defaults for every key. If the file is missing, malformed, or a key is removed, scripts fall back to the defaults above without error. Never leave a key out — the schema above is the authoritative default set.

### Worktree defaults

`worktree_*` keys set the **default** worktree behavior; the per-session file `.dev-team-agents/.worktree-session` overrides them. Coding agents resolve the decision in this order:

| Precedence | Source | Behavior |
|---|---|---|
| 1 (highest) | `.dev-team-agents/.worktree-session` present | Follow the stored per-session decision silently |
| 2 | `worktree_active` present in `preferences.json` | Use it **without asking**; write the session file so the rest of the session is consistent |
| 3 (fallback) | key absent (legacy install) | Ask the user once (original behavior) |

### Health-check backfill

On every session start, `scripts/hooks/session-start.sh` compares `preferences.json` against `scripts/lib/preferences-defaults.json` and writes any **missing** key with its default value. Existing user values are never overwritten; the write is a no-op when the file is already complete. This self-heals installs that predate a new key.

### Language Rule

| Output | Language |
|--------|---------|
| Documents (ADRs, session-summary, changelogs, code comments) | **Always English** |
| Plans presented for user approval | **`language` field from `preferences.json`** — plans are conversation items, not documents |
| Conversation with the user (responses, questions, notifications) | **`language` field from `preferences.json`** — fallback to English |

### Migration

The legacy `.auto-update` flag file is automatically migrated to `preferences.json → auto_update` by `install.sh` and the health check.
