---
name: user-preferences
description: User preferences — language and settings from preferences.json.
---

# User Preferences

All user-level preferences for dev-team-agents are stored in a single file:

```
.dev-team-agents/user-data/preferences.json
```

This file is gitignored (covered by `.dev-team-agents/user-data/` in `.gitignore`).

---

## Schema and Defaults

> **Canonical source:** `scripts/lib/preferences-defaults.json` is the single source of truth for the default schema. It is read by `install.sh` (on install/update) and by the `session-start.sh` health-check backfill, which fills any missing key on every session. The block below mirrors it — keep them in sync.

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
  "worktree_docker_isolate": true
}
```

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `language` | string | `"en"` | Conversation language (BCP 47 tag). Docs remain English. |
| `context_window_percent_warning` | number | `55` | % at which agents emit a `warning` notification |
| `context_window_percent_limit` | number | `60` | % at which agents emit a `critical` notification |
| `suppress_notifications` | bool or array | `false` | `false` = none suppressed; `true` = all suppressed; `["info"]` = suppress by type |
| `session_summary_max_days` | number | `30` | Days before session-summary entries are trimmed |
| `session_summary_max_entries` | number | `30` | Maximum number of entries in session-summary.md |
| `docs_stale_after_days` | number | `30` | Days before project.md and session-summary.md are considered stale |
| `auto_update` | bool | `false` | Auto-update dev-team-agents when a new version is detected |
| `update_check_interval_hours` | number | `24` | Hours between update checks |
| `transcript_multiplier` | number | `1.8` | Multiplier to estimate full context from transcript tokens |
| `model_max_tokens` | number | `200000` | Context window for the active model |
| `telemetry` | bool | `true` | Anonymous usage telemetry (opt out with `false`) |
| `worktree_active` | bool | `false` | Default to a git worktree per task without asking |
| `worktree_base_branch` | string or null | `null` | Base branch for worktrees (`null` = auto-detect) |
| `worktree_path` | string | `".claude/worktrees"` | Directory where worktrees are created |
| `worktree_docker_isolate` | bool | `true` | Isolated Docker Compose stack per worktree (when Docker present) |

---

## Language Policy

Two distinct rules govern language in dev-team-agents:

| Output type | Language rule |
|-------------|--------------|
| Documents (ADRs, session-summary, plans, changelogs, code comments) | **Always English** — regardless of `preferences.json` |
| Conversation with the user (responses, questions, explanations, notifications) | **Use `language` from `preferences.json`** — fallback to English if absent or unreadable |

**How agents read the user's language:**

```bash
PREFS=".dev-team-agents/user-data/preferences.json"
USER_LANG="en"
if [ -f "$PREFS" ] && command -v python3 >/dev/null 2>&1; then
    USER_LANG=$(python3 -c \
        "import json; d=json.load(open('$PREFS')); print(d.get('language','en'))" \
        2>/dev/null || echo "en")
fi
```

For agents: read `.dev-team-agents/user-data/preferences.json` at the start of each session. Use the `language` value when writing any response directed at the user. If the file does not exist, use English.

---

## suppress_notifications Handling

| Value | Behavior |
|-------|---------|
| `false` | No suppression — all notifications shown |
| `true` | All notifications suppressed |
| `["info"]` | Only `info` type suppressed |
| `["warning", "critical"]` | `warning` and `critical` suppressed |

Any unrecognized value → treat as `false` (no suppression). Never fail — graceful degradation only.

---

## Missing File Behavior

If `preferences.json` does not exist:
- Use English as the conversation language
- Use all schema defaults for thresholds and intervals
- Emit a `warning` notification at session start prompting the user to run setup-assistant

If a specific field is missing from the file (partial schema), use its default value.

---

## Reading Individual Fields (shell)

```bash
_pref() {
    local field="$1" default="$2"
    python3 -c \
        "import json,sys; d=json.load(open('.dev-team-agents/user-data/preferences.json')); \
         print(d.get('$field', $default))" 2>/dev/null || echo "$default"
}

LANG=$(_pref language '"en"')
WARN_PCT=$(_pref context_window_percent_warning 55)
LIMIT_PCT=$(_pref context_window_percent_limit 60)
SUPPRESS=$(_pref suppress_notifications false)
STALE_DAYS=$(_pref docs_stale_after_days 30)
AUTO_UPDATE=$(_pref auto_update false)
CHECK_HOURS=$(_pref update_check_interval_hours 24)
```
