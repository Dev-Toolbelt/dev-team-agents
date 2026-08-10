# User Preferences

Reference for `.dev-team-agents/user-data/preferences.json`, including defaults, behavior, and how worktree isolation is configured.

---

## Index

- [Summary](#summary)
- [File Location](#file-location)
- [Default Schema](#default-schema)
- [Preference Reference](#preference-reference)
- [Worktree Isolation](#worktree-isolation)
- [Notification and Context Controls](#notification-and-context-controls)
- [Consent-Driven Settings](#consent-driven-settings)
- [Language Policy](#language-policy)
- [Related Documents](#related-documents)

---

## Summary

`preferences.json` is the user-owned runtime configuration file for Dev Team Agents. It controls conversation language, notification thresholds, update behavior, worktree defaults, and other local execution preferences.

The file is not meant to be committed and is preserved across updates.

---

## File Location

```text
.dev-team-agents/user-data/preferences.json
```

Canonical defaults are defined in:

```text
scripts/lib/preferences-defaults.json
```

---

## Default Schema

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
  "session_no_commit_turns": 8,
  "telemetry": true,
  "worktree_active": true,
  "worktree_base_branch": null,
  "worktree_commit_action": "ask",
  "worktree_path": ".worktrees",
  "worktree_docker_isolate": true,
  "qa_browser": null,
  "ci_cd_detected": null
}
```

---

## Preference Reference

| Key | Default | Type | What it controls |
|-----|---------|------|------------------|
| `language` | `"pt-BR"` | string | Language used when agents talk directly to the user |
| `context_window_percent_warning` | `55` | number | Threshold for warning notifications about context usage |
| `context_window_percent_limit` | `60` | number | Threshold for critical notifications about context usage |
| `suppress_notifications` | `false` | bool or array | Notification suppression policy |
| `session_summary_max_days` | `30` | number | Retention window for session-summary entries |
| `session_summary_max_entries` | `30` | number | Maximum number of retained summary entries |
| `docs_stale_after_days` | `30` | number | Staleness threshold for maintained project docs |
| `auto_update` | `true` | bool | Whether update checks may auto-apply updates |
| `update_check_interval_hours` | `24` | number | Delay between update checks |
| `transcript_multiplier` | `1.8` | number | Deprecated compatibility field; no longer applied |
| `model_max_tokens` | `200000` | number | Assumed context window size for warning calculations |
| `session_no_commit_turns` | `8` | number | Turns before warning about long dirty sessions with no commit |
| `telemetry` | `true` | bool | Anonymous telemetry opt-in flag |
| `worktree_active` | `true` | bool | Whether coding tasks default to isolated git worktrees |
| `worktree_base_branch` | `null` | string or null | Preferred base branch for new worktrees |
| `worktree_commit_action` | `"ask"` | string | Default `/devteam:commit` behavior inside an active worktree |
| `worktree_path` | `".worktrees"` | string | Root directory where worktrees are created |
| `worktree_docker_isolate` | `true` | bool | Whether Docker Compose should be isolated per worktree |
| `qa_browser` | `null` | string or null | Preferred browser for the QA agent |
| `ci_cd_detected` | `null` | bool or null | Cached CI/CD detection state |

---

## Worktree Isolation

Worktree behavior is driven primarily by five preferences:

| Key | Default | Effect |
|-----|---------|--------|
| `worktree_active` | `true` | Create a worktree per coding task without prompting on modern installs |
| `worktree_base_branch` | `null` | Use a fixed base branch or auto-detect the repository default |
| `worktree_commit_action` | `"ask"` | Control whether commit flow stops to ask, rebases, finalizes, or only commits |
| `worktree_path` | `".worktrees"` | Choose where generated worktrees live |
| `worktree_docker_isolate` | `true` | Namespace Docker Compose resources per worktree when Docker is in use |

### Decision cascade

Coding agents resolve isolation in this order:

1. `.dev-team-agents/.worktree-session`
2. `preferences.json`
3. Ask once only on legacy installs that lack the preference key

### Session override

`.dev-team-agents/.worktree-session` is a per-session override shared by all agents in the task. It prevents multi-agent flows from asking or deciding differently inside the same task.

### Docker isolation

When `worktree_docker_isolate` is `true` and the project uses Docker Compose, agents can create a task-specific isolated stack. Containers, networks, and volumes are namespaced so the main stack is untouched.

### Finalization

When a task is finalized, the agent rebases onto the base branch, resolves conflicts if needed, merges, and then tears down only the isolated worktree and its isolated Docker resources.

---

## Notification and Context Controls

These settings affect runtime warnings and local noise level:

| Concern | Keys |
|---------|------|
| Context usage thresholds | `context_window_percent_warning`, `context_window_percent_limit`, `model_max_tokens` |
| Notification suppression | `suppress_notifications` |
| Dirty-session reminder | `session_no_commit_turns` |
| Maintained docs staleness | `docs_stale_after_days` |

`suppress_notifications` accepts:

- `false` to allow all notifications
- `true` to suppress all notifications
- arrays such as `["info"]` or `["warning", "critical"]` to suppress selected levels

---

## Consent-Driven Settings

Two keys are treated as explicit consent settings:

| Key | Meaning |
|-----|---------|
| `telemetry` | Anonymous usage reporting |
| `auto_update` | Automatic update application |

They are special because missing values are treated conservatively on existing installs. In practice, absent consent is read as disabled until the user explicitly records a choice.

---

## Language Policy

The language rules are split by output type:

| Output type | Policy |
|-------------|--------|
| Conversation with the user | Use `language` |
| Generated docs, ADRs, changelogs, code comments | Always English |

That separation keeps repository artifacts stable while still letting sessions happen in the user's preferred language.

---

## Related Documents

- [README](../README.md)
- [Harness Architecture](harness.md)
- [Installation Options](installation.md)
- [Credentials Reference](credentials.local.md)
