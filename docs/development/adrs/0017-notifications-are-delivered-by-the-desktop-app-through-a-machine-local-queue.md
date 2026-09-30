# ADR-0017: Notifications are delivered by the desktop app through a machine-local queue

**Date:** 2026-09-29
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

The framework has always had notifications: a stale `project.md`, a health check never run, an
update available, `devteam upgrade` pending, broken links, the context window near its limit,
many turns with no commit, a tip of the day. The triggers were right. **None of them ever
reached the user**, and the reason is the channel, not the logic:

- `session-start.sh` printed a boxed `━━ DEV TEAM AGENTS ━━` banner to stdout. A provider's
  `SessionStart` stdout is **model context** — the agent saw the box; the user did not.
- `stop/04-notifier.sh` printed the same box from a `Stop` hook, whose stdout is **not shown**
  at all. It was disabled on 2026-08-06 as "no observed user-visible benefit relative to its
  per-Stop cost" — an accurate finding about a channel that could not deliver.
- The same hooks run under Claude Code, Codex and opencode, so no provider-specific output
  mechanism fixes it everywhere.

The desktop app (ADR-0011, ADR-0015) is a process the user sees, that can raise native OS
notifications, and that is already a client of the CLI. It is the channel the hooks lacked.

Three existing rules shape how it can be one:

- **ADR-0015: the app is a pure client of the CLI.** It may not read the store's files itself.
- **ADR-0013: what one machine observed is machine-local.** A context warning from this laptop's
  session means nothing on another host.
- **Hooks stay bash and stay cheap** (ADR-0009, `CLAUDE-md/hooks.md`): a Stop hook runs every turn.

## Decision

**A hook appends; the CLI reads; the app shows.**

1. **The queue.** A hook raises a notification by appending one JSON line to
   `<state-dir>/notifications.jsonl` through `scripts/hooks/lib/notify.sh` — the only emitter.
   The record is `id, ts, project_id, session_id, level, code, message, dedupe_key, expires_at`;
   `message` is rendered by the hook in the user's language, `code` is stable for a client to
   switch on. `notify.sh` applies `suppress_notifications`, skips a record whose dedupe key is
   already queued, and keeps the newest 200 lines. It forks no python.
2. **Seen marks are a separate file.** `notifications-seen.json`, written only by the CLI, under
   a store lock, atomically. **The CLI never rewrites the queue**: a rewrite racing a hook's
   append would drop the line being written. Only the writer trims it. Both files are
   machine-local records (`paths.MACHINE_LOCAL_RECORDS`).
3. **Three commands.** `notifications list` (read), `notifications ack <id>` (mutating, gated by
   the client write gate like every other write), and `notifications watch` — a long-running
   command that stats each registered project's queue once a second and emits one JSON event per
   new record. **`watch --json` is JSON Lines**, the one exception to "exactly one document":
   one compact document per event, each with `ok`, ending with `{"event": "end"}` — or, when it
   fails, with `{"event": "error", "ok": false, …}` and the matching exit code. It stops on
   stdin EOF — so a reader that dies without cleaning up does not leave it polling forever — or
   on SIGTERM. `list` and `watch` walk the registry and are in `NEEDS_MACHINE_LAYOUT` with `list`.
4. **The app owns the stream in its main process**, not the renderer: one `watch` child,
   restarted with a doubling backoff (1 s → 60 s) and by a 90 s heartbeat watchdog. Each record
   becomes a native notification titled with the project's name — never its id — and is
   **acknowledged on display**, so it is never shown twice across a stream restart, an app
   restart, or a second window. A bell in the header mirrors the feed.
5. **Background mode.** Because the stream lives in the main process, closing the window hides
   it; a tray / menu-bar icon reopens or quits; a single-instance lock keeps two `watch`
   children from showing everything twice; **start at login is opt-in** and the UI shows what
   the OS actually recorded, not the user's choice alone.
6. **The boxed banner is removed from every hook.** The `[DEVTEAM:*]` markers stay: they are
   instructions to the agent, not notifications to the user.

## Consequences

### Positive
- The notifications exist for the first time, for every provider, since all three run the same
  hooks and write the same queue.
- A hook's cost is one append. The re-enabled stop notifier forks python once per Stop (the
  transcript scan is inherent: the transcript grows every turn), not up to six times.
- The app still reads nothing directly: the CLI remains the single reader of the store.
- Notifications raised while the app is closed are not lost: they wait in the queue, subject to
  their `expires_at`, and the backlog streams first when `watch` starts.

### Negative
- Without the app, nothing is shown — which is exactly what happened before, now without a
  per-session banner in the model's context.
- `watch` is a process that lives as long as the app, stat-ing N small files a second.
- Ack-on-display means a notification shown while the user was away counts as seen; the bell is
  the record. Accepted as the user's choice over re-showing until clicked.
- An unsigned macOS build may have its login item refused or left pending approval; the app
  reports it, it cannot fix it. Signing is ADR-0011's open item.

### Neutral
- The Windows tray and login item are covered by tests against a simulated OS and the Windows CI
  job; the experience itself is verified by the manual checklist in `app/README.md`.
- A per-type suppression list (`["info"]`) is honoured by `notify.sh`; the app's settings screen
  still edits `suppress_notifications` as on/off only, because the CLI cannot write the list form.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep printing, but in a provider-visible form (Claude Code `systemMessage` JSON) | Fixes one provider; Codex and opencode have no equivalent. And a notice in the chat competes with the work, where an OS notification does not |
| The hook calls `devteam` to record the notification | ~100 ms of python start-up per Stop — the cost that got the notifier disabled — for what a bash append does in ~1 ms |
| The app reads `notifications.jsonl` itself (fs.watch) | Breaks ADR-0015's pure-client rule, and makes the app a second reader of the store's layout, which is what that rule prevents |
| The app polls `notifications list` | A python process every few seconds, all day, while running in the background. `watch` is one process that stats files |
| The hook shows an OS notification directly (`osascript`, PowerShell toast) | Needs no app — but three platform-specific code paths in bash, no bell or history, no dedupe across windows, and the notification's name is "osascript" or "PowerShell" |
| One file with the seen flag written into each queue line | The CLI would rewrite the file a hook appends to; a concurrent append is lost |
