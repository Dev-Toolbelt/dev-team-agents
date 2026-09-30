## Notification System

Hooks raise notifications into a per-project queue; the desktop app shows them as native OS
notifications and in a bell (ADR-0017). Same hooks, same queue, under Claude Code, Codex and opencode.

```
hook ──devteam_notify──▶ <state-dir>/notifications.jsonl ──devteam notifications watch──▶ app
```

### Why not stdout

Every notice used to be a boxed `━━ DEV TEAM AGENTS ━━` banner on stdout. **No provider shows a
hook's stdout to the user**: `SessionStart` stdout is model context, `Stop` stdout is not
displayed. The banner reached the agent at best — which is why `stop/04-notifier.sh` was disabled on
2026-08-06 for "no observed user-visible benefit". It is re-enabled on the new channel. **A hook
never prints a notice to stdout.** The `[DEVTEAM:*]` markers are not notices: they are instructions
to the agent and stay.

### The record

One JSON line, written by `scripts/hooks/lib/notify.sh` — the only emitter:

| Key | Meaning |
|-----|---------|
| `id` | `<epoch>-<pid>-<random>`; the app validates this shape before it reaches argv |
| `ts` | Epoch seconds |
| `project_id` | From `.dev-team-agents/project.json` |
| `session_id` | From `state.json` |
| `level` | `info`, `warning`, `critical` |
| `code` | Stable identifier a client switches on (see the table in `skills/shared/notifier/SKILL.md`) |
| `message` | Rendered by the hook in the user's `language` |
| `dedupe_key` | A record whose key is already queued is not written again |
| `expires_at` | Epoch seconds; `0` = never. Expired records are not reported |

`notifications.jsonl` lives in the project's machine-local state directory (`state-dir`), is
appended to by hooks only, and is capped at 200 lines **by that writer** — append and trim run under a
short `mkdir` lock (`notifications.jsonl.lock`), so two hooks trimming at once cannot lose a line. A
record with a key of the wrong type (`"ts": null`) is skipped like a malformed line, and `notify.sh`
strips control characters that would make a line invalid JSON. Which records the app has
shown is `notifications-seen.json`, written only by `devteam notifications ack` under a lock — the
CLI never rewrites the queue a hook may be appending to. Both are machine-local records.

### Reading it

| Command | What |
|---------|------|
| `devteam notifications list [--project <id>] [--unseen]` | Live records across bound projects, each with `seen` |
| `devteam notifications ack <id>… \| --all` | Mark seen |
| `devteam notifications watch` | Backlog, then each new record, until stdin closes or SIGTERM. `--json` is JSON Lines |

The app runs one `watch` in its **main process** — so it keeps working with the window closed —
restarts it with a doubling backoff (1 s → 60 s, reset only after a child has stayed up 30 s) and a
90 s heartbeat watchdog, shows each record titled with the project's name, and acknowledges it on
display, one `ack` at a time. A backlog of more than three records — what piled up while the app was
closed — gets one summary banner instead of one each; every record still lands in the bell. A `watch`
that exits 3 (a store this app may not migrate) is reported as unavailable with the CLI's own words,
not retried.

### Channels

| Hook | Notifications |
|------|--------------|
| `session-start.sh` | Update available/applied, broken links, stale `project.md`, stale session summary, stale or never-run health check, `devteam upgrade` pending |
| `stop/04-notifier.sh` | Context window warning/critical, uncommitted progress, tip of the day |
| `post-tool-use/01-task-board.sh`, `pre-tool-use/04-task-board.sh` | `tasks.session_done` (info) — a session's last open task was completed; once per session; a pass that releases the last task in review raises it too |
| `post-tool-use/01-task-board.sh`, `stop/04b-task-board.sh` | `tasks.review_findings` (warning) — a review window recorded `findings > 0`; once per window (dedupe key `tasks.review_findings:<session>:<window>`) |
| `session-end.sh` | `tasks.session_abandoned` (warning) — the session ended with open tasks; Claude Code only, the other providers have no end event |

### Suppression

`suppress_notifications`: `false` (all), `true` (none), or a list of levels (`["info"]`), applied by
`notify.sh` before anything is queued. The app's **Pause** silences banners for its session only;
paused notices still land in the bell.

### Context Window Estimation

`stop/04-notifier.sh` estimates context usage in one python fork per Stop (the transcript grows every
turn, so reading it is inherent — everything else in the script is bash):

1. **Transcript-based** (primary): reads `transcript_path` from the Stop payload and takes the **last**
   assistant usage entry's `cache_read_input_tokens + cache_creation_input_tokens + input_tokens` —
   with prompt caching that sum is the exact size of the context sent on the most recent call.
   Compared to `model_max_tokens`. Scanned incrementally from a cached byte offset.
2. **Turn-count heuristic** (fallback): `100% ≈ 45 turns`, scaled linearly.

Each level fires **once per session** and expires after 2 hours. `transcript_multiplier` is
deprecated and not applied.

### Health Check Staleness

`session-start.sh` reads `last_health_check` from `state.json` — written by `/devteam:health-check`
on every run. `health_check.stale` when older than `docs_stale_after_days`;
`health_check.never` when absent but the project is in motion (`docs/project.md` or a session
summary exists). Both once per day.

### Uncommitted-Progress Warning

`stop/04-notifier.sh` raises `session.uncommitted` once per session when the turn count reaches
`session_no_commit_turns` (default `8`), `HEAD` still equals the `session_head` that
`session-start.sh` recorded, and `git status --porcelain` is non-empty. The git calls run only once
the turn threshold is reached.

### Tip of the Day

One `info` per day, index `(day_of_month - 1) % 15`, from `scripts/hooks/stop/tips/tips.<lang>.txt`
(one tip per line, 15 lines; `en`, `pt-BR`, `es`; others fall back to English). After the first Stop
of the day this is a single `grep` for the day's dedupe key — the tip file is not opened.

### Stop Sub-script Convention

Canonical table: `CLAUDE-md/hooks.md`. The notification tier is `04-`: `04-notifier.sh`.
