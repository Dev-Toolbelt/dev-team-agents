---
name: notifier
description: Dev Team Agents notifications — format, types, conditions, rotation.
---

# Dev Team Agents Notifier

## Notification Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 {icon}  DEV TEAM AGENTS  {icon}
 {message in the user's language}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Types and Icons

| Type | Icon | When to use |
|------|------|-------------|
| `info` | ℹ️ | Tips, suggestions, best practices |
| `warning` | ⚠️ | Context approaching limit, stale config, missing prefs |
| `critical` | 🚨 | Context at or beyond limit, broken installation |

---

## Language

Read the user's preferred language from `.claude/user-data/preferences.json` → `language` field. Emit the notification message in that language. Default to English if the file is absent or unreadable.

---

## Suppression

Before emitting any notification, check `suppress_notifications` in `preferences.json`:

| Value | Behavior |
|-------|---------|
| `false` | Emit all notifications |
| `true` | Suppress all — exit silently |
| `["info"]` | Suppress only the listed types |

Any unrecognized value → treat as `false`.

---

## Channel Rules

| Hook | Notification type | When |
|------|------------------|------|
| `session-start.sh` | Persistent state (`warning`/`critical`) | Once per session, on startup |
| `stop/04-notifier.sh` | Session progress (`warning`/`critical`) + tip (`info`) | After each turn |

**session-start conditions:**
- `preferences.json` missing or incomplete
- `project.md` stale beyond `docs_stale_after_days`
- `session-summary.md` last entry older than `docs_stale_after_days`

**stop/04-notifier conditions:**
- Context window heuristic warning/critical (turn counter)
- Tip of session (once per session, indexed by day)

Do NOT duplicate the session-summary missing-entry warning — that is handled by `01-session-summary.sh`.

---

## Context Window — Agent Instructions

As an agent, monitor your context use and emit a notification when you estimate the conversation has grown large. Read thresholds from `preferences.json` (defaults: warning=55%, critical=60%).

- When you estimate context approaching the `context_window_percent_warning` threshold → emit a `warning` notification before your response.
- When you estimate context at or beyond `context_window_percent_limit` → emit a `critical` notification and recommend `/compact` or a new session.

This is an estimate, not a precise measurement. Be conservative — warn slightly early rather than degrade silently.

**Example warning emission (pt-BR):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ⚠️  DEV TEAM AGENTS  ⚠️
 Sua janela de contexto está se aproximando do limite (≈55%).
 Considere executar /compact ou iniciar uma nova sessão.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Example critical emission (en):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🚨  DEV TEAM AGENTS  🚨
 Context window at ≈60%. Run /compact now or start a new
 session to maintain response quality.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Context Window Heuristic (shell hooks)

The stop hook increments a per-session turn counter stored at `.claude/user-data/.notifier-state`. The session-start hook writes a session ID to `.claude/user-data/.session-id`. When the state's session ID differs from the current session ID, the counter resets.

Default turn thresholds (conservative mapping — agents should use `preferences.json` values):

| Turns | Action |
|-------|--------|
| ≥ 15 | Emit `warning` |
| ≥ 25 | Emit `critical` |

---

## Tip of Session

Emit one `info` tip per session, on the first stop hook call. Index: `(day_of_month - 1) % 15`.

| Index | Tip (English — translate to user's language when emitting) |
|-------|-------------------------------------------------------------|
| 0 | Use `/compact` regularly or start a new session to keep your context window healthy and avoid hallucinations in long sessions. |
| 1 | Run `/devteam:review` before opening a PR — it automatically calls code-reviewer, software-architect, and security-specialist. |
| 2 | Record hard architectural decisions as ADRs: `bash .claude/dev-team-agents/scripts/new-adr.sh "title"`. This prevents agents from questioning settled choices. |
| 3 | Use `/devteam:plan` at the start of any new feature — it runs a multi-agent analysis (architect + product + database + backend/frontend/devops as needed). |
| 4 | Write non-obvious domain knowledge to the project wiki at `.claude/docs/wiki/` after any revealing task — agents read it on startup. |
| 5 | `/devteam:commit` groups your staged changes by layer and generates Conventional Commits automatically. |
| 6 | Use `/devteam:refactor` for structured refactoring — it runs test-first coverage, maps dependencies, and produces ordered commit blocks. |
| 7 | Run a health check occasionally: *"Run a health check on this project"* — it auto-fixes stale hooks, broken symlinks, and outdated preferences. |
| 8 | Use `/devteam:security` before any release or after touching auth, permissions, or data-handling code. |
| 9 | The `session-summary.md` is read by agents on startup — keeping it updated means agents pick up context from your last session without re-asking questions. |
| 10 | Use `/devteam:dba` when adding migrations or modifying schema — the database-specialist catches missed indexes and locking issues before they reach production. |
| 11 | Set `auto_update: true` in `preferences.json` to get automatic updates of dev-team-agents when new versions are released. |
| 12 | Use `/devteam:docs` to generate changelogs, runbooks, and release notes from your git history. |
| 13 | Stack-specific skills (Next.js, Laravel, Vue, etc.) are auto-loaded by agents when detected — check `.claude/skills/` for what is available in your project. |
| 14 | Use `/devteam:tester` when you only need to add or update tests — it avoids spinning up the full dev team when scope is just coverage. |
