# ADR-0018: The task board is captured by hooks into a machine-local per-session record

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

Agents keep a todo list while they work. Planning agents are told to track their work, and every
provider has a native tool for it: Claude Code `TaskCreate` / `TaskUpdate` (which replaced
`TodoWrite` by default), Codex `update_plan`, opencode `todowrite`. The list is visible only inside
the session that owns it. A developer with several sessions across several bound projects cannot see
what is pending, in progress or done anywhere else, nor how long anything has taken.

The desktop app is a pure CLI client (ADR-0015) whose only way into the store is the `--json`
contract (ADR-0011). ADR-0017 already established a channel of the same shape for notifications:
a hook writes a machine-local record, the CLI reads it, the app watches.

Verified while writing this ADR:

| Fact | Source |
|---|---|
| Claude Code hook input carries `agent_id` / `agent_type` when the call comes from a subagent, and a `SessionEnd` event exists | code.claude.com/docs/en/hooks |
| `TodoWrite` is disabled by default in favour of `TaskCreate`/`TaskUpdate`; neither tool's input shape is publicly documented | code.claude.com/docs/en/tools-reference |
| Codex and opencode already receive our `PreToolUse` dispatcher (`.codex/hooks.json`, plugin `tool.execute.before`) | `scripts/install-codex.sh`, `opencode/plugin/dev-team-agents.ts` |
| Whether Codex fires `PreToolUse` for `update_plan` | **not verified** — the installed Codex binary could not be run |

## Decision

**A hook captures the provider's own todo tool; the CLI owns the record; the app only reads.**

1. **Capture is automatic, not cooperative.** Claude Code gets a new `PostToolUse` entry whose
   matcher is limited to the todo tools, plus a `SessionEnd` entry. Codex and opencode reuse the
   `PreToolUse` dispatcher they already have; a sub-script there filters on the tool name in bash
   before forking anything. Agents are not asked to report progress.
2. **One record per session**, `<state-dir>/task-board/<session>.json`, machine-local (ADR-0013). Only the
   CLI writes it (`devteam tasks record|mark`, invoked by the hook through the project's own
   `scripts/cli/devteam`), under a per-session lock, atomically. Per-session files mean two sessions
   never contend for a lock and a corrupt file costs one session, not the board.
3. **Status history, not a snapshot.** Each task keeps an append-only `history` of status changes
   (capped), so time-per-step is computable. Tasks missing from a replace-style list are marked
   `removed_at`, never deleted.
4. **Derived state is computed on read.** Session status (active / idle / ended), stale and abandoned
   tasks, and per-step durations are derived by `devteam tasks list|watch` from timestamps and
   thresholds passed as flags. Nothing runs in the background to maintain them.
5. **The board is read-only.** The app never writes the record, so it is not part of
   `compat.store_schemas()` — that gate answers "may this client write?", and it may not.
6. **Board settings are app-local** (stale threshold, done retention), like the display name
   (ADR-0016). They are view preferences, not framework behaviour, and a new `preferences.json` key
   would cost five mirrors.
7. **Notifications go through `notify.sh`.** The hook raises `tasks.session_done` and
   `tasks.session_abandoned` from what `devteam tasks` returns; the CLI does not write the queue.

## Consequences

- Every provider's todo list reaches the board with no change to any agent body.
- A rewritten task text appears as a new task: replace-style tools carry no stable id, so identity
  is the normalized text. Accepted and documented; ids are used where the provider gives one.
- Times have the granularity of the agent's own updates.
- "Ended" is exact only on Claude Code (`SessionEnd`); elsewhere it is inferred from inactivity.
- Codex coverage depends on an unverified hook behaviour. If Codex does not fire `PreToolUse` for
  `update_plan`, Codex sessions are simply absent from the board; nothing fails.
- Records accumulate. Retention hides old data in the app; deleting it is a future explicit
  command, never an automatic side effect (No-Destruction Rule).
- `devteam tasks list|watch --json` are public API from their first release.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Agents report through `devteam tasks` by instruction | Depends on agent compliance. This repository measured closing run banners at 0 of 6 multi-message runs; a board fed that way goes stale without anyone noticing |
| Parse plan and sprint documents | Only persisted plans are visible, at sprint granularity, with no in-progress signal |
| One append-only event log for all sessions | Every reader replays the whole log, and one lock is shared by every concurrent session |
| Snapshot only, no history | Cannot answer how long a task spent in each step, which is a stated requirement |
