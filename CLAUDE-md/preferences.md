## User Preferences

All user-level preferences are stored in `.claude/user-data/preferences.json` (gitignored). The file is created by `install.sh` on first install and validated/migrated by the health check.

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
  "model_max_tokens": 200000
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

> **Fallback safety**: all scripts that read `preferences.json` use hardcoded defaults for every key. If the file is missing, malformed, or a key is removed, scripts fall back to the defaults above without error. Never leave a key out — the schema above is the authoritative default set.

### Language Rule

| Output | Language |
|--------|---------|
| Documents (ADRs, session-summary, changelogs, code comments) | **Always English** |
| Plans presented for user approval | **`language` field from `preferences.json`** — plans are conversation items, not documents |
| Conversation with the user (responses, questions, notifications) | **`language` field from `preferences.json`** — fallback to English |

### Migration

The legacy `.auto-update` flag file is automatically migrated to `preferences.json → auto_update` by `install.sh` and the health check.
