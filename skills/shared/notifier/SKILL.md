---
name: notifier
description: Dev Team Agents notifications — hooks queue them, the desktop app shows them.
---

# Dev Team Agents Notifier

## How a notification reaches the user

```
hook ──devteam_notify──▶ <state-dir>/notifications.jsonl ──devteam notifications watch──▶ desktop app ──▶ native notification + bell
```

- **Hooks raise them; agents do not.** A hook appends one record through `scripts/hooks/lib/notify.sh`. The desktop app streams the queue and shows each record as an OS notification titled with the project's name (ADR-0017).
- **Never print a `DEV TEAM AGENTS` box.** Hook stdout never reached the user — `SessionStart` stdout is model context, `Stop` stdout is not shown — and a box in an agent's reply is noise the hook already covers. The format is retired.
- The `[DEVTEAM:*]` markers a hook prints (`FIRST_TIME_SETUP`, `SESSION_BANNER`, `SYMLINK_BROKEN`, `TEST_SCOPE_RULE`) are **instructions to you**, not notifications. Act on them as their own rules say.

## Levels

| Level | Use for |
|-------|---------|
| `info` | Tips, suggestions |
| `warning` | Context approaching its limit, stale docs or health check, work without a commit, an update available |
| `critical` | Context at or past its limit, broken links (the dev-team is not loaded) |

`critical` stays on screen until dismissed where the OS allows it.

## What raises what

| Code | Level | Raised by | Once per |
|------|-------|-----------|----------|
| `update.available` / `update.applied` | warning / info | `session-start.sh` (update check) | version pair |
| `symlinks.broken` | critical | `session-start.sh` | day |
| `docs.project_stale`, `docs.session_summary_stale` | warning | `session-start.sh` | day |
| `health_check.stale`, `health_check.never` | warning | `session-start.sh` | day |
| `layout.upgrade_available` | warning | `session-start.sh` | day |
| `context.warning`, `context.critical` | warning / critical | `stop/04-notifier.sh` | session (expires after 2 h) |
| `session.uncommitted` | warning | `stop/04-notifier.sh` | session |
| `tip.daily` | info | `stop/04-notifier.sh` | day |

Thresholds come from preferences: `context_window_percent_warning`, `context_window_percent_limit`, `model_max_tokens`, `session_no_commit_turns`, `docs_stale_after_days`. Messages are rendered by the hook in `language`.

## Suppression

`suppress_notifications` in the resolved preferences, applied by `notify.sh` before anything is queued:

| Value | Behavior |
|-------|---------|
| `false` | Queue all |
| `true` | Queue none |
| `["info"]` | Skip only the listed levels |

The app's own **Pause** only silences banners for that app session; paused notices still land in the bell.

## Raising a new one (hook authors)

```bash
. "${SCRIPT_DIR}/lib/notify.sh"
devteam_notify_init "$MAIN_REPO_ROOT" "$STATE_DIR" "$SUPPRESS" "$SESSION_ID"
devteam_notify warning my.code "Message in the user's language." 86400 "my.code:$(date +%Y-%m-%d)"
```

- Pick a stable `code` — clients switch on it; the message may change.
- Always pass a dedupe key: a notice raised on every turn is a notification per turn.
- Pass a TTL for anything tied to a moment (context, a session); `0` only for what stays true until acted on.
- Keep the Stop path python-free unless the check cannot be done without it.

Full reference: `CLAUDE-md/notifications.md`.

## Context window — what an agent does

Nothing to emit: `stop/04-notifier.sh` measures the real context size from the transcript every turn. If the user asks, or you judge the conversation is degrading, say so plainly in your reply and suggest `/compact` or a new session.
