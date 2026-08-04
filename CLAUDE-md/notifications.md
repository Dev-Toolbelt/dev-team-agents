## Notification System

Agents and shell hooks emit structured notifications using the DEV TEAM AGENTS format.

### Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 {icon}  DEV TEAM AGENTS  {icon}
 {message in the user's language}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Types

| Type | Icon | When to use |
|------|------|-------------|
| `info` | ℹ️ | Tips, suggestions, best practices |
| `warning` | ⚠️ | Context approaching limit, stale config, missing prefs |
| `critical` | 🚨 | Context at or beyond limit, broken installation |

### Channels

| Hook | Notifications |
|------|--------------|
| `session-start.sh` | Persistent state: missing `preferences.json`, stale docs, stale/never-run health check |
| `stop/04-notifier.sh` | Session progress: context window warnings, tip of session, uncommitted-progress warning |

### Suppression

Set `suppress_notifications` in `preferences.json`:
- `false` — show all
- `true` — suppress all
- `["info"]` — suppress only the listed types

### Context Window Estimation

`stop/04-notifier.sh` estimates context usage using two strategies (in order of preference):

1. **Transcript-based** (primary): reads `transcript_path` from the Stop hook payload and takes the **last** assistant usage entry's `cache_read_input_tokens + cache_creation_input_tokens + input_tokens`. Prompt caching means that sum is the exact size of the context sent on the most recent API call — no compensating multiplier needed. Result is compared to `model_max_tokens`.
2. **Turn-count heuristic** (fallback): fires when the transcript path is unavailable. Calibrates `100% ≈ 45 turns` and scales linearly. Less accurate for content-heavy sessions.

> **`transcript_multiplier` is deprecated and no longer applied.** The prior implementation summed `input_tokens + output_tokens` across *all* turns, which double-counted history on every turn (each turn's `input_tokens` already includes everything sent before it) — the multiplier existed to compensate for the resulting drift, not for system-prompt/tool overhead. Reading the last usage entry directly gives the exact figure, so the key is read for backward compatibility only and has no effect. It will be removed from `preferences-defaults.json` in a future minor version.

### Health Check Staleness

`session-start.sh` reads `.dev-team-agents/user-data/.last-health-check` — a plain `YYYY-MM-DD` marker that `/devteam:health-check` writes on every run (Step 4, `commands/health-check.md`; see also `setup-health-check/SKILL.md` § Flow). Two cases warn, both gated by `docs_stale_after_days`:
- **Marker present but older than the threshold** — "Last health check was N days ago."
- **No marker at all**, but the project is otherwise in motion (`docs/project.md` or `session-summary.md` already exists) — "No health check has been recorded." A brand-new install is exempt: it already goes through the setup flow.

### Uncommitted-Progress Warning

`stop/04-notifier.sh` fires a `warning` at most once per session when all three hold: the turn count has reached `session_no_commit_turns` (default `8`), `git rev-parse HEAD` matches what `session-start.sh` recorded at session start (`.dev-team-agents/user-data/.session-head`), and `git status --porcelain` is non-empty. That combination is exactly "real work has piled up and nothing has been committed" — a crash, `/clear`, or context compaction loses the most right there. The notifier-state file (`.notifier-state`) gained a fifth `nocommit_warned` field so the warning fires once, not on every subsequent Stop.

### Tip of Session

`stop/04-notifier.sh` emits one `ℹ️ info` tip per session, indexed by `(day_of_month - 1) % 15`.

Tip text lives in **locale data files**, never in the script: `scripts/hooks/stop/tips/tips.<lang>.txt`, one tip per line, 15 lines each. `tips.en.txt`, `tips.pt-BR.txt` and `tips.es.txt` ship today; all other languages fall back to English. Only the selected locale's file is read, and only after the once-per-day gate opens.

Adding a locale is one new file plus one `case` arm in the notifier. Changing a tip never touches the script.

### Stop Sub-script Convention

Canonical version of this table lives in `CLAUDE.md` → "Stop Hook Sub-script Convention", together with the mandatory `NN[a-z]-name.sh` filename pattern the dispatcher enforces. Reproduced here for the notification tier (`04-`):

| Prefix | Reserved for | Current scripts |
|--------|-------------|-----------------|
| `01-` | State detection and collection | `01-session-summary.sh` |
| `02-` | Repository integrity checks | `02-orphan-skill-scan.sh`, `02b-orphan-template-scan.sh` |
| `03-` | Static validation | `03-agent-lint.sh`, `03b-fingerprint-uniqueness.sh` |
| `04-` | User-facing notifications | `04-notifier.sh` |
| `05-` | External reporting (telemetry) | `05-telemetry.sh` |
| `99-` | Final/cleanup tasks | `99-graphify-refresh.sh`, `99b-archive-index.sh` |
