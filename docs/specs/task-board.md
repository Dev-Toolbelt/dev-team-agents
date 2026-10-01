## Spec — Cross-project task board

### User Story
As a developer running several agent sessions across several bound projects, I want every todo
list an agent creates to appear on a board in the desktop app, so that I can see what is pending,
in progress and done in every project — and how long each task spent in each step — without
opening each session.

### Context
Agents already keep a todo list through their provider's native tool (Claude Code `TodoWrite` /
`TaskCreate` / `TaskUpdate`, Codex `update_plan`, opencode `todowrite`). Until now that list lived
only in the provider's UI. Decision record: [ADR-0018](../development/adrs/0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md).

Data flow, mirroring the notification channel (ADR-0017):

```
provider todo tool ─hook─▶ devteam tasks record ─▶ <state-dir>/task-board/<session>.json
                                                        │
                                  devteam tasks watch ◀─┘ ──▶ app main ──IPC──▶ Board / Kanban
```

#### Where the tasks come from

The board reads only the provider's native task list. A plan written to chat or to a file never
reaches it: every approved plan's Steps table becomes native tasks per
`skills/shared/plan-mode/SKILL.md` § Task List Mirroring. Sessions that never plan and whose
provider never opens a list — a quick question, a `/devteam:status` — correctly stay off the board.

#### Agent spawns are tasks (amendment 2026-09-30)

The framework's commands delegate straight to agents without presenting a plan, so plan mirroring
alone leaves their sessions off the board. Every agent a session spawns is therefore recorded as a
task by the hooks, with no agent cooperation:

| Moment | Claude Code | Codex | opencode | Task |
|---|---|---|---|---|
| Spawn | `PreToolUse` `Agent`/`Task` | `PreToolUse` `spawn_agent` | `tool.execute.before` `task` | created `in_progress`, `kind: "agent"` |
| Result | `PostToolUse` (foreground); transcript hand-back at `Stop` (background) | `PostToolUse` `wait_agent`, matched by the agent id `spawn_agent` returned | `tool.execute.after` `task` (same `callID`) | `completed` |
| Failure | `PostToolUseFailure`; a background hand-back whose `<status>` is `failed`/`killed`/`error` | `wait_agent` reporting `errored`/`not_found`; a `spawn_agent` `PostToolUse` with no agent id | — | `cancelled`, `failed: true` |
| Closed | — | `close_agent` | — | `cancelled` (not failed) |
| Interrupt | settled at `Stop` | settled at `Stop` (an agent that never got an id) | settled at `Stop` (a thrown `task` fires no `after`) | `cancelled`, `interrupted: true` |

- **Identity** — the spawn's own id (`tool_use_id`; opencode `callID`; Codex the spawned agent id),
  never the text, so a task cannot duplicate. **Text** — `<agent>: <description>`.
- **Owner** — the spawning agent (`main`, or the subagent id for nested spawns).
- **Excluded** — provider built-ins (one list, `BUILTIN_AGENTS` in `review_triggers.py`) and the
  review/QA agents (their effect is the In Review column; a task of their own would count as finished
  work in the next review).
- **Hidden on read** — when the same owner also keeps a mirrored plan list (`Step N:` tasks), its
  agent tasks are kept in the record but omitted from columns and counts: the plan is the better grain.
- A spawn with no result when its session ends is `abandoned`, like any open task.

- **Stop settles interrupts** — at `Stop` every `in_progress` agent task that is not background and (Codex) holds no spawned agent id is `cancelled` with `interrupted: true`: a finished turn cannot have a foreground agent running. Background agents and Codex agents awaiting a `wait_agent` survive.
- **`tasks.session_done`** — an agent task's end raises it only from `Stop` (`mark`), never mid-turn from `record` (the owed notification is kept on the record as `done_pending`); it is never raised while a visible task is `failed` or `interrupted`.
- **Review interplay (intended)** — an agent task created after a review's result counts toward the fix rule (the fix is usually delegated to an agent), and an in-progress background agent can enter In Review like any in-progress task.

JSON (additive): task `kind` (`"agent"` | `"todo"`), `failed` (bool) and `interrupted` (bool), all optional for clients.

#### Capture per provider

| Provider | Hook point | Tool | Replace or incremental | Task id |
|---|---|---|---|---|
| Claude Code | `PostToolUse`, matcher `TodoWrite\|TaskCreate\|TaskUpdate` → `post-tool-use.sh` | `TodoWrite` | Replace (full list every call) | none — matched by content |
| Claude Code | same | `TaskCreate` / `TaskUpdate` (the **default** since TodoWrite was disabled in favour of them; `CLAUDE_CODE_ENABLE_TASKS=0` restores TodoWrite) | Incremental | `TaskUpdate.tool_input.taskId`; for `TaskCreate`, parsed from the tool output (`tool_response` or `tool_output`, object or string, e.g. `Task #3 created`), falling back to the next sequential id the session would assign |
| Claude Code | `SessionEnd` → `session-end.sh` | — | marks the session ended | — |
| Codex | existing `PreToolUse` (`*`) → `pre-tool-use.sh` | `update_plan` | Replace | none — matched by content |
| opencode | plugin `tool.execute.before` → `pre-tool-use.sh` (payload gains `sessionID`) | `todowrite` | Replace | `todos[].id` |

Claude Code hook input carries `agent_id` / `agent_type` when the call comes from a subagent
(https://code.claude.com/docs/en/hooks.md). The input shapes of `TodoWrite` and `Task*` are not
publicly documented, so the normalizers are defensive: unknown keys are ignored, a payload that
cannot be read is a no-op, and both `tool_response` and `tool_output` are accepted.

Codex fires `PreToolUse` for `update_plan`: confirmed in the Codex source (openai/codex @ `92bc601`)
and pinned by a test that replays that exact payload, including a subagent's `agent_id`. It has not
yet been observed in a live Codex session.

#### The record — `<state-dir>/task-board/<session-key>.json`

Machine-local (ADR-0013), one file per session so two sessions never contend for one lock.
Written only by `devteam tasks record|mark`, under a per-session lock, atomically. Never deleted by
any command (No-Destruction Rule); the app hides old data, it does not remove it.

```json
{
  "schema": 1,
  "session_id": "…", "project_id": "…", "provider": "claude|codex|opencode",
  "cwd": "…", "branch": "feat/login",
  "created_at": 0, "updated_at": 0, "last_seen_at": 0, "idle_at": null, "ended_at": null,
  "tasks": [
    {
      "key": "t1", "id": null, "owner": "main", "content": "…",
      "status": "pending|in_progress|completed|cancelled",
      "created_at": 0, "removed_at": null,
      "history": [{"status": "pending", "at": 0}, {"status": "in_progress", "at": 0}]
    }
  ]
}
```

- `owner` is the subagent id when the hook payload carries one, else `main`. A replace-style call
  diffs only the tasks of its own owner, so a subagent's list never overwrites the main list.
- Matching for replace-style calls: provider id when present, else normalized content (trimmed,
  whitespace-collapsed, case-folded), duplicates paired in order. A task absent from the new list
  gets `removed_at`; it is kept, not deleted. A rewritten task text is a new task — accepted limit.
- `history` appends one entry per status change, capped at 50 entries.

#### Derived state — computed by the CLI on read, never stored

| Field | Rule |
|---|---|
| Session `status` | `ended` if `ended_at` is set or `last_seen_at` older than `--ended-after` (default 6 h); `idle` if `idle_at` ≥ last task event; else `active` |
| Task `column` | `todo` (pending), `in_progress`, `done` (completed or cancelled); removed-and-not-completed tasks are excluded from counts and columns |
| Task `stale` | `in_progress`, session not ended, and in that status for longer than `--stale-after` (default 60 min) |
| Task `abandoned` | not done and its session is `ended` |
| Task `durations` | seconds spent per status, from `history`; the current status runs until now (or until the session ended) |

#### CLI surface (`--json` is public API, ADR-0011)

| Command | Purpose |
|---|---|
| `devteam tasks record --project-root <dir> [--provider auto]` | Hook-only. Reads the hook payload on stdin, updates the record, prints `{"recorded": bool, "session": …, "all_done": bool, "became_all_done": bool}` |
| `devteam tasks mark --project-root <dir> --state idle\|ended` | Hook-only. Reads the payload for the session id; no-op when the session has no record. Prints `{"marked": bool, "open": N}` |
| `devteam tasks list [--project <id>…] [--since <epoch>] [--stale-after S] [--ended-after S]` | Every bound project that has at least one task, with sessions, tasks and derived state |
| `devteam tasks watch [same filters]` | `snapshot` events per changed project, `ready`, `heartbeat`, `end` — same lifecycle as `notifications watch` |

#### `tasks list --json` shape (the app codes against this)

Wrapped in the CLI's usual `--json` envelope. `data`:

```json
{
  "generated_at": 1759200000,
  "stale_after": 3600, "ended_after": 21600,
  "projects": [
    {
      "project_id": "…", "root": "/abs/path",
      "providers": ["claude", "codex"],
      "sessions_total": 3, "sessions_active": 1,
      "counts": {"todo": 3, "in_progress": 2, "done": 5, "total": 10},
      "stale": 1, "abandoned": 0,
      "last_activity_at": 1759199000,
      "as_of": 1759200000,
      "sessions": [
        {
          "session_id": "…", "provider": "claude", "branch": "feat/login", "cwd": "…",
          "status": "active|idle|ended",
          "created_at": 0, "last_activity_at": 0, "ended_at": null,
          "resume_command": "cd '/abs/path' && claude --resume '…'",
          "counts": {"todo": 1, "in_progress": 1, "done": 1, "total": 3},
          "tasks": [
            {
              "key": "t1", "content": "…", "owner": "main", "agent_type": null,
              "status": "in_progress", "column": "in_progress",
              "created_at": 0, "status_since": 0, "completed_at": null,
              "durations": {"pending": 120, "in_progress": 300, "completed": 0},
              "stale": false, "abandoned": false
            }
          ]
        }
      ]
    }
  ]
}
```

`as_of` (additive) is the epoch at which the project's derived view was computed — the same clock as
`generated_at` in `tasks list`, and the snapshot's own computation time in `tasks watch`. Live figures
are `durations[current] + (now - as_of)`. `watch` does not treat a moving `as_of` as a change: an
unchanged view is not re-emitted.

Projects are sorted by `last_activity_at` descending; sessions likewise; tasks by `created_at`.
Removed-and-not-completed tasks are omitted. `--since` drops sessions whose last activity is older.
The display name is not here — it is app-local (ADR-0016); the app joins on `project_id`.

`tasks watch --json` emits JSON Lines: `{"event":"snapshot","project": <one project object as above,
or {"project_id": "…", "removed": true} when it no longer has tasks>}`, then `{"event":"ready"}`
after the backlog, `{"event":"heartbeat","ts":…}` every 30 s, and `{"event":"end","reason":…}` —
the same lifecycle, stdin-EOF and SIGTERM handling as `notifications watch`.

#### In Review — the fourth column (amendment 2026-09-30)

A task may go from In progress straight to Done. It passes through **In Review** only when a review
is triggered in its session, and leaves only when the review passed or its findings were fixed.
No provider has a review status, so the column is inferred by the hooks.

**Review window.** A review is a window stored in the session record:

```json
"reviews": [
  {
    "id": "r1", "trigger": "agent|command|prompt", "source": "qa-specialist|/devteam:review|…",
    "opened_at": 0, "last_at": 0, "pending": 1, "fg": ["toolu_1"], "bg": [], "scan": false,
    "result_at": null, "findings": null,
    "resolved_at": null, "resolution": null,
    "task_keys": ["t1", "t2"], "fix_after": null
  }
]
```

**Triggers — open a window** (at most one open window per session; a second trigger while one is
open joins it and adds its token — see *Pending tokens* below):

| Trigger | Claude Code | Codex | opencode |
|---|---|---|---|
| Review/QA agent spawned: `qa-specialist`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer` | `PreToolUse` on `Agent`/`Task`, `tool_input.subagent_type` | `PreToolUse` on `spawn_agent`, `tool_input.agent_type` | `tool.execute.before` on `task`, `args.subagent_type` |
| Command: `/devteam:review`, `/devteam:qa`, `/review` | `UserPromptSubmit`, `prompt` | `UserPromptSubmit`, `prompt` | plugin `chat.message`, text parts |
| Explicit request in the prompt: review, revisar, revisão, revise, QA, testar, test it | same as commands | same | same |

Keyword matching is word-bounded and case-insensitive. It skips a match that a negation (`não`,
`sem`, `no`, `don't`, `without`) directly governs — one of the two words before it, with no
punctuation between them and no `only`/`just`/`apenas`/`somente` in between (`no problem, review the
code` and `not only review but fix` are requests) — and a match inside a question that opens with
`what`/`how`/`why`/`o que`/`como`/`por que` (`what does the QA agent do?`). One linear pass; it lives
in one tested file. `qa` touching a path separator or identifier joiner (`docs/qa/x`, `qa_report`,
`qa-specialist`) is not the word.

**Pending tokens.** `pending` is derived from what the window still waits for, tracked by kind:
foreground agent launches (`fg`, by tool-use id), background agent launches (`bg`) and one
command/prompt scan flag (`scan`, a flag — joining with it already set adds nothing). A finished
turn (`Stop`) retires the scan flag against the final message and retires every foreground launch
still outstanding as **unread** (a turn that ended has no agent running in front of it: its result
was lost to a failed launch, `Esc`, or a Codex wait that never returned it); background launches
survive until their hand-back. A foreground launch whose `PostToolUse` is an async-launch ack
(`isAsync` / `status: async_launched`) without `run_in_background` in its input was backgrounded by
the harness: its token moves from `fg` to `bg`, so `Stop` no longer retires it. Claude `PostToolUseFailure` on `Agent`/`Task` retires that launch as
unread at once. A window with no activity for more than `PENDING_MAX_AGE` (6 h, `tasks.py`) is
settled as unread instead of being joined, on the next open, `Stop` and every view.

**Which tasks enter.** At the moment the window opens: every non-removed task of the session that is
`in_progress`, plus every task `completed` after the previous window was resolved. With no previous
window, "since" is the later of the session's `created_at` and its latest resume (`resumed_at`, set when
a record call finds an ended session alive again); a task completed at or after that instant enters.
Tasks created after the window opened do not enter it.

**Result — read from a marker.** Our four review/QA agents end their final report with
`<!-- review-result: findings=N -->` (rule in `skills/shared/review-result/SKILL.md`, emitted from
each agent's `## Before You Finish`). The hook scans the agent's returned output for it:
Claude `PostToolUse` on `Agent`/`Task` (`tool_response`), Codex `PostToolUse` on `wait_agent`
(`tool_response`), opencode `tool.execute.after` on `task` (`output.output`). Only the agent's answer is
read, never the echoed `prompt`/input. A result from `Agent`/`Task`/opencode `task` counts only when
the call names one of our review agents (`subagent_type`); a `general-purpose` agent that quotes the
marker changes nothing (marker-only acceptance is Codex `wait_agent`'s alone, which does not name its
agent). The marker counts only as the **last non-empty line** of a report or final message, standing
alone, after fenced and inline code have been removed. One report retires one slot and carries one
marker; markers of distinct reports (parallel reviewers) are summed. The result is recorded when
no token is left. For a command/prompt-triggered window, the next `Stop` scans the transcript's
last assistant message (Claude `transcript_path`) for the marker; with no marker anywhere, the window
records `findings: null` — shown as **result not read**. A routing-only pass (`code-reviewer` in router
mode, which only delegates) emits no marker; the specialists it spawns do.

A **background** agent's hand-back is read from the transcript at `Stop`. It counts only when it is
the harness-injected form (a `queue-operation` entry, or the `user` entry whose task id mirrors a
queue entry already seen; a user entry that stands alone is never one), its id (`tool-use-id`, else
`task-id`) is a background token the open window launched, and the marker is in its `<result>`
section only; a notification with no `<result>` (a Bash job's `<summary>`) carries no report. A
transcript line longer than the per-`Stop` read cap is skipped rather than waited for.

A Codex `wait_agent` that returns after `Stop` already settled its launch as unread reattaches to
the most recent window that is unresolved and closed unread (only that one, only within
`PENDING_MAX_AGE` of its result) and recomputes it: `0` releases the tasks, `> 0` holds them with
findings.

**Leaving In Review.**

| Case | What happens |
|---|---|
| Result `findings = 0` | Window resolved (`resolution: "passed"`); its tasks go to Done if completed, else back to In progress |
| Result `findings > 0` | Cards show **N findings**; tasks stay in In Review; `fix_after` = result time; notification `tasks.review_findings` |
| Fix rule | Every task created at or after `fix_after` in the session (the fix list) is completed, and there is at least one → resolved (`"fixed"`). Tasks that existed when the result arrived (`known_keys`) and the window's own members are never fixes |
| Keyword-only window closes unread | A window whose only triggers were prompt keywords (no agent, no review command) and that closes with no marker resolves at once (`resolution: "unread-dismissed"`); its tasks return to their normal columns and nothing is held. Command- and agent-triggered windows keep the hold below |
| Re-review rule | A later window in the same session returns `findings = 0` → earlier unresolved windows resolved (`"fixed"`) |
| Result not read | Stays in In Review with the **result not read** badge until the fix or re-review rule resolves it; both rules apply to any window that has a result, unread included (a lost, failed or expired launch settles as unread) |
| Reopened / moved out | A task in review that the agent sets back to `in_progress`, or moves out of `in_progress`/`completed` (to `pending`, cancelled) or drops unfinished, leaves the window at once (`left`) and stops accruing `in_review` time |

**Derived fields** (added, nothing removed — additive to the JSON contract):

- task `column` gains `in_review`; task gains `review: {"state": "pending|findings|unread|null", "findings": N|null, "since": epoch}` (null when not in review). `state` is never `passed`: a zero result resolves its window and holds nothing;
- `counts` gain `in_review` (project and session); project gains `with_findings` (tasks in review with findings);
- `durations` gain `in_review`: time between entering and leaving the window. Durations **partition** the task's life: while a task is inside a review window its seconds count to `in_review` only, not to its provider status (`pending`/`in_progress`/`completed`), so the values sum to the elapsed time;
- the `status` field keeps the provider's own status; only `column` reflects review.

#### Notifications (emitted by the hook through `notify.sh`, the only emitter)

| Code | When |
|---|---|
| `tasks.session_done` | A record call moves a session from "some open" to "all done" (≥ 1 task) |
| `tasks.review_findings` | A review window records `findings > 0` (dedupe per window; a `Stop` that closes several windows raises one per window with findings) |
| `tasks.session_abandoned` | `SessionEnd` fires while the session still has open tasks (Claude Code and Codex; opencode has no session-end event) |

#### Desktop app

- **Board (overview):** only projects with ≥ 1 task. Card: display name, provider icons (the set used
  by its sessions), sessions `total (N active)`, counts and percentages for To do / In progress /
  In Review / Done, a stacked progress bar, and badges for stale and abandoned tasks and for tasks
  with findings. Period filter
  (today / 7 days / 30 days / all).
- **Project kanban:** four columns — To do, In progress, **In Review**, Done — with In Review empty
  when no task is in review. The columns sit side by side in one row that never stacks: they share
  the width when it fits and the row scrolls horizontally when it does not (mouse, trackpad, or the
  arrow keys — the row is a tab stop only while it overflows). A column is at most as tall as the
  visible part of the page, measured, so its heading stays on screen and its cards scroll inside it
  (a column's card list is a tab stop too while it overflows); columns are as tall as their cards up
  to that cap.
  Tasks in review carry a badge: **N findings**, **result not read**
  (`unread`), **pending** (the review has not answered yet) or a neutral **In review** for a state
  this app version does not know. A "with findings" filter
  shows only tasks in review that have findings. Card: task text, session chip (provider icon + branch), time in
  current column; on hover/focus, time per step. Filters: session, period, show/hide done older than
  the retention setting. Per-session header with status and a **Copy resume command** button.
- **Settings (app-local, `settings.ts`):** stale threshold (minutes, default 60), done retention
  (days, default 7). Not preferences.json keys.
- Resume commands: `cd <dir> && claude --resume <id>`, `cd <dir> && codex resume <id>`,
  `cd <dir> && opencode --session <id>`, where `<dir>` is the session's recorded `cwd` when that
  directory still exists (a linked worktree or subdirectory), else the project root. Always one
  line, shell-quoted.

### Acceptance Criteria

1. **Given** project A with three sessions of 3, 5 and 2 tasks and project B with two sessions of 3
   and 2 tasks, **When** the Board opens, **Then** it shows exactly A and B, with 10 and 5 tasks, the
   right per-column counts and percentages, and the provider icons their sessions used.
2. **Given** a bound project whose sessions never created a task, **When** the Board opens, **Then**
   that project is not shown.
3. **Given** a task that went pending → in_progress → completed, **When** its kanban card is
   inspected, **Then** it shows the time spent pending and in progress.
4. **Given** `TodoWrite` is called by a subagent, **When** the main agent later calls `TodoWrite`
   with its own list, **Then** neither list removes the other's tasks.
5. **Given** a replace-style call omits a task, **Then** the task is marked removed and kept in the file.
6. **Given** a task in progress longer than the stale threshold in a non-ended session, **Then** it
   is flagged stale on the card and counted on the project card.
7. **Given** a session ends with open tasks, **Then** those tasks are flagged abandoned, and on
   Claude Code a `tasks.session_abandoned` notification is raised.
8. **Given** a session's last open task is completed, **Then** a `tasks.session_done` notification
   is raised once.
9. **Given** the hook runs for any tool other than a todo tool, **Then** no python process is forked.
10. **Given** a malformed payload or an unwritable state dir, **Then** the hook exits 0 and the
    provider is not disturbed.
11. `devteam tasks list --json` and `watch --json` are covered by `tests/test_json_contract.py`.
12. **Given** any project, **When** its kanban opens, **Then** it shows four columns in order — To do,
    In progress, In Review, Done — with In Review empty when no task is in review — side by side in
    one row; **When** the window is narrower than the four columns' minimum width, **Then** the row
    scrolls horizontally and the columns never stack.
13. **Given** a task in review whose window recorded 2 findings, **Then** its card shows **2 findings**;
    with no marker read it shows **result not read**; with no answer yet it shows **pending**.
14. **Given** the findings filter is on, **Then** only tasks in review with findings are listed.
15. **Given** a review that returns `findings=0`, **Then** the tasks leave In Review at once and no
    card ever shows a "passed" state.

### Out of Scope
- Editing, moving or deleting tasks from the board (read-only).
- A "Blocked" column and plan titles as activity names (need agent cooperation).
- Cross-machine sync; deleting old records (`devteam tasks prune` is future work).
- A notification for stale tasks (badge only).

### Dependencies
- ADR-0013 (machine-local records), ADR-0015/0011 (app as CLI client, JSON contract),
  ADR-0017 (notification channel).

### Amendment Log
| Date | Change | Reason |
|---|---|---|
| 2026-09-30 | `sessions_active` counts sessions whose status is not `ended` (active or idle); `tasks watch` also re-emits a project's `snapshot` on a 30 s clock refresh when the derived view changed (stale/abandoned move with time, not with the file); `record`/`mark` `--project-root` is optional (defaults to the resolved root); Stop marks idle through `stop/04b-task-board.sh`; the opencode plugin's `session.idle` payload now carries `session_id` so that hook can name the session | Spec was silent on these; each is needed for the stated behavior to hold |
| 2026-09-30 | `ready` carries no extra keys; session ids that are not filename-safe are hashed by `record`, but the bash-side `mark` callers (Stop, SessionEnd) skip them, so such a session is never marked idle/ended | Provider ids in practice are UUIDs; skipping avoids a bash re-implementation of the hashing |
| 2026-09-30 | Resume command `cd`s into the record's `cwd` when it is still a directory, else the project root | Providers find a session by working directory; one started in a linked worktree or subdirectory did not resume from the root |
| 2026-09-30 | A removed task whose last status was `completed` or `cancelled` is not a match candidate for a later replace; the equal item becomes a new task | Reviving it as pending erased the completion the board still showed |
| 2026-09-30 | The state directory is `<state-dir>/task-board/` (was `tasks/`); tasks are ordered by creation time then numeric key; `record` clears `idle_at`; a non-empty todo list with no readable entry is a no-op rather than "clear all"; a structurally invalid record is skipped by readers | `tasks` is too generic a basename for the machine-local classifier (`wiki/tasks/` would match); the rest are correctness fixes from review |
| 2026-09-30 | Codex capture confirmed: `PreToolUse` fires for `update_plan` with the parsed arguments, `session_id`, `cwd` and a subagent's `agent_id`/`agent_type` (openai/codex @ `92bc601`); a test replays that exact payload through the dispatcher | The spec had recorded Codex as unverified because the local Codex binary could not run |
| 2026-09-30 | Optional In Review column: review windows opened by review/QA agents, review commands and explicit prompt requests; result read from a `review-result` marker; tasks leave when the review passes or its findings are fixed | User request: a review state between In progress and Done that is not mandatory |
| 2026-09-30 | In Review implementation details the spec left open: (1) the transcript scan at `Stop` runs inside `tasks mark --state idle`, not as a second command, and `mark` gains `review_result`, `review_window`, `review_findings`, `became_all_done`; the final message is `last_assistant_message` (Codex, and the opencode plugin) else the tail of `transcript_path` back to the last real user prompt. (2) Each trigger adds 1 to `pending`; a command/prompt trigger's token (`scan`) is retired at `Stop` and is never consumed by an agent marker; if the window already holds agent markers the final message is not read, so a summary that repeats a marker is not double counted. (3) A review agent that returns with no marker records `unread` on Claude Code/opencode (the spawn names the agent); on Codex an unmarked `wait_agent` is ignored (it does not name the agent). (4) A `run_in_background` agent launch and Codex `spawn_agent`'s `PostToolUse` are never results. (5) Result rule: `findings` is null when no marker was seen, or when a source went unread and the markers seen sum to 0 — an unread reviewer never turns another's zero into a pass. (6) No window opens when the session has no record or no task would enter it. (7) A task is in review only while `in_progress` or `completed` and not removed; reopen means `completed` → `in_progress`/`pending`. (8) The fix rule compares `created_at` strictly after `fix_after`, ignores removed tasks, and is re-evaluated on every record and on a copy in every view. (9) `durations.in_review` is additional to the per-status durations (it overlaps them); overlapping windows are merged. (10) A task in review is never `stale`; an ended session's tasks in review are `abandoned` and counted as open. | Behaviors the spec table did not decide |
| 2026-09-30 | Background reviewers (Claude Code): a `run_in_background` agent's `PostToolUse` is a launch ack (`isAsync`/`status: async_launched`, or `run_in_background` in the input) and never a result, so the window stays `pending`. Its report arrives later as a `<task-notification>` (transcript entries of type `queue-operation` and `user`, carrying `<tool-use-id>` of the launch and `<result>`). At `Stop`, inside the same `tasks mark --state idle`, the transcript is read incrementally from `tx_offset` (recorded at window open from `transcript_path`, else the tail), at most 2 MiB and only complete lines per Stop. Each notification newer than `opened_at` and not yet consumed is attributed to the open window: its markers decrement `pending`; a notification whose id is a background token of the window (`bg`, by tool-use id) with no marker is `unread`; a marker-less notification of an unknown agent is ignored. Consumption is idempotent by id (`consumed`: the notification's tool-use-id, shared with the foreground result's `tool_use_id`, so a result is never counted twice, nor the queue and user copies of one notification). opencode's `task` is synchronous and Codex's `wait_agent` is already read, so neither needs the scan | The main path in this harness: reviewers run in the background, and the window would otherwise stay pending forever |
| 2026-09-30 | `tasks.session_done` requires every task in the Done column, so it does not fire while a task is in review; the pass of the review (`review-result`, or the `Stop` scan) raises it when that releases the last open task | A session is not finished while its review is unresolved; reusing the same notification keeps the app's contract unchanged |
| 2026-09-30 | Detector additions: commands `$devteam-review` / `$devteam-qa` (Codex skill aliases of the two slash commands); keyword `revisao` (unaccented); negations `nao`, `not`, `dont` beside the spec list (`do not review`, `don't`, `dont`). Bash gates are substring tests (`review`, `revis`, `qa`, `test`) on the text after the `"prompt"` key; the detector in `scripts/lib/devteam/review_triggers.py` is the authority | The Codex commands are skills, not slash commands, and "do not review" is the same refusal the list already meant |
| 2026-09-30 | Hooks wiring: Claude `PostToolUse` matcher widened to `TodoWrite\|TaskCreate\|TaskUpdate\|Agent\|Task` and `install.sh` upgrades an existing narrow entry in place; new `UserPromptSubmit` dispatcher; Codex managed events gain `PostToolUse` (matcher `*`, narrowed to `.*wait_agent` in the round-1 fixes below), `UserPromptSubmit` and `SessionEnd`; the opencode plugin's `runHook` now spawns the script and writes the payload to its stdin (`exec` ignores an `input` option, so every plugin hook previously waited on an empty stdin until its timeout) | Required for the triggers to reach the CLI |
| 2026-09-30 | In Review round-1 review fixes: (1) pending accounting is by kind (`fg`, `bg`, `scan`) instead of a counter; `Stop` retires foreground launches as unread and the scan flag against the final message, background launches survive; `PostToolUseFailure` (Claude, `Agent\|Task`, same dispatcher, wired by `bind` and `install.sh`) retires a failed launch as unread; `PENDING_MAX_AGE` = 6 h settles a stalled window as unread on open/`Stop`/view; only a live background token receives a late result (a foreground token is retired at `Stop`, so its late result finds no slot and adds only its marker). A Codex `spawn_agent` is a foreground launch, so an unmarked or timed-out `wait_agent` now settles at `Stop` as unread (it no longer wedges the window). Records written with only `pending` migrate: each agent slot becomes a foreground token (this legacy migration matters only for unreleased branch-local records). (2) A prompt/command joining with the scan flag set adds nothing. (3) One report = one slot and its LAST marker; only reports add up; only the agent's answer is scanned (`prompt`/input echoes in `tool_response` are dropped). (4) The negation scan is one linear pass with a two-word window. (5) Background scan: only `queue-operation` (top-level `content`) and `user`-role entries; an entry without a timestamp is ignored; a transcript shorter than the stored offset (compaction) or a different path continues from its end instead of byte 0. (6) Codex has `SessionEnd` (openai/codex `92bc601`, `codex-rs/hooks/src/events/session_end.rs`: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `reason`); docs corrected. (7) opencode plugin: stderr ignored, process group killed on timeout, final text stops at the last user message, the fallback payload keeps `last_assistant_message`. (8) Codex `PostToolUse` matcher `*` -> `.*wait_agent`; dispatchers pipe the payload with `printf '%s\n'`. (9) `install.sh` widens only its own `PostToolUse` entry and only from a matcher it shipped before (`TodoWrite\|TaskCreate\|TaskUpdate`), else warns; detector: negation must directly govern the keyword (no `only`/`just`, no punctuation between) and a keyword in a question opened by `what/how/why/o que/como/por que` is ignored. (10) `durations` partition time (in-review seconds are no longer also counted under the provider status); this supersedes item (9) of the implementation-details row above. | Findings of the first review of the In Review column |
| 2026-09-30 | In Review round-2 review fixes: (1) a keyword-only window (`strong` false: no agent, no review command ever joined) that closes without a marker resolves immediately as `unread-dismissed` — nothing is held; command/agent windows keep the hold. "Completed since the last review" with no earlier window starts at the later of the session's `created_at` and `resumed_at`. (2) A foreground `Agent` whose `PostToolUse` is an async-launch ack moves its token `fg` -> `bg`. (3) Codex `wait_agent` takes one slot and one marker per marker returned (summed); `Agent`/`Task`/opencode `task` keep last-marker-per-report, and a wait's own tool-use id retires no launch by id. (4) A real result id the window never launched retires no token; only a missing or synthetic (`anon:`, `off:`) id falls back to the oldest token of its kind. (5) Background-report fallback ids are `off:{offset}:{line}`. (6) Every project object in `tasks list` and each `tasks watch` snapshot gains `as_of`, the epoch its view was computed (additive; `watch` ignores it when deciding whether the view changed). (7) Any transition out of `in_progress`/`completed` inside a window records `left`. (8) The fix list is `created_at >= fix_after`, excluding tasks known at result time and the window's members. (9) `hooks.wire` rewrites an entry's matcher only from a value a previous release shipped (`TodoWrite\|TaskCreate\|TaskUpdate`), otherwise keeps it and warns (as `install.sh` does). (10) Spec accuracy: `launch_ids` became the `fg`/`bg` token model; only a live background token receives a late result; the legacy `pending` migration applies only to unreleased branch-local records | Findings of the second review of the In Review column |
| 2026-09-30 | In Review round-3 review fixes: (1) a result from `Agent`/`Task`/opencode `task` needs a known review agent (`subagent_type`); marker-only acceptance stays for Codex `wait_agent` only. (2) Background hand-backs: only a known `bg` token of the open window, marker only from `<result>`; an entry without `tool-use-id` and `task-id` is dropped (the `off:` fallback ids are gone from the scan); a user-role notification counts only when it mirrors a queue entry (task ids kept per window in `queue_ids`, at most 64) and opens the entry's text. (3) A late Codex `wait_agent` result reattaches to the latest unresolved, unread window within `PENDING_MAX_AGE` of its result and recomputes it; `review.state` is `pending\|findings\|unread` only, and a window with a zero result left unresolved holds nothing. (4) The marker is the last non-empty line of a report/final message, alone on it, after fenced and inline code are removed. (5) `session_id` in the bash gates is the FIRST session key of the payload (the opencode plugin now puts `sessionID` first). (6) `skip` is no longer a negation; `qa` next to `/ \ _ @ # -` (or after `.`) is a path/identifier, not a request. (7) `tasks mark --state idle` gains `review_results: [{window, findings}]` (one per window closed by that Stop; `review_window`/`review_findings` mirror the last), `became_all_done` is computed after every outcome, and the hook raises one `tasks.review_findings` per window with findings. (8) opencode plugin: `callID` forwarded as `tool_use_id`, `subagent_type` remembered from `before` by `callID` (256 entries) for `after`; task-board hooks get a 12 s timeout (the record lock waits up to 10 s, so a shorter kill would lose the write; other hooks keep 5 s); a slash command is detected from the raw text, or rebuilt from `input.command`/`input.arguments` when opencode supplies them (whether it delivers `/devteam:review` raw or expanded is unverified: see `docs/providers.md`). (9) Desktop app section updated to the four-column board, badges and findings filter; acceptance criteria 12-15. | Findings of the third review of the In Review column |
| 2026-09-30 | Approved plans become native tasks per `plan-mode` § Task List Mirroring | A live session planned a whole feature without one task-list call, so the board stayed empty |
| 2026-09-30 | Agent spawns are tasks: every non-built-in, non-review agent a session spawns is recorded by the hooks (`kind: "agent"`, `failed` on failure), hidden when the owner keeps a mirrored plan | A live `/devteam:backend` run delegated to two agents without a plan and the board stayed empty |
| 2026-09-30 | Agent spawns implementation details the amendment left open: (1) a Codex task's `id` is the `spawn_agent` call's `tool_use_id` (its `PreToolUse` fires before an agent id exists); the spawned agent id from the `PostToolUse` response is stored as `agent_ref`, and `wait_agent` matches on it, so the Codex `PostToolUse` matcher widens to `.*(wait_agent\|spawn_agent)`. (2) `wait_agent` settles each agent whose state is final: `completed` → `completed`; `errored`/`not_found` → `cancelled`, `failed: true`; `shutdown` → `cancelled` (not failed); running states change nothing. (3) A background agent's hand-back marks it `completed` regardless of the notification's own status (a failed background agent is not distinguished). (4) A result, ack or failure that matches no recorded spawn never starts a record and never touches one; a spawn replayed with the same id adds nothing. (5) Agent tasks are not todo-list members: `TodoWrite`/`update_plan`/`TaskUpdate` diffs and id lookups skip them, so a replace never removes one. (6) Agent tasks still enter a later review window as finished work, unless hidden; hidden agent tasks are excluded from review entry, the fix rule, counts and `all_done`. (7) Hook gates: the spawn gate is the tool key alone; a review-typed spawn (`subagent_type`/`agent_type`) takes the review path and needs a record, any other agent forks `tasks record`; results fork only when the session has a record. Built-ins fork python once and are dropped by the CLI (one list, in Python). (8) The opencode plugin needed no change: it already forwards `callID` and `args` for `task`. |
| 2026-09-30 | Agent spawns review fixes: (1) a background hand-back's `<status>` decides the outcome: `completed` or any other word → `completed`; `failed`/`killed`/`error` (case-insensitive) → `cancelled`, `failed: true`; this supersedes item (3) of the implementation-details row above. (2) The shared background cursor restarts at the transcript's end when a background spawn or ack arrives and no other agent task is background and `in_progress`; one `Stop` reads chunks of 2 MiB until the transcript end or a 64 MiB cap (review windows read the same way). (3) `Stop` settles every foreground agent task left `in_progress` as `cancelled` with `interrupted: true` (not on Codex while it holds an `agent_ref`); additive `interrupted` in the task view, and `session_done` is also withheld while a visible task is `interrupted` (deviation: the spec only named `failed`, but a cut-off run is not a finished session). (4) Codex: a `spawn_agent` `PostToolUse` with no agent id → `cancelled`, `failed: true`; `close_agent` → `cancelled` (not failed), so the Codex matcher is `.*(wait_agent\|spawn_agent\|close_agent)` and `install-codex.sh` writes it; opencode's thrown `task` is covered by (3). (5) An agent's end raises `became_all_done` only from `Stop`, via `done_pending` on the record; never with a `failed`/`interrupted` task visible. (6) Free gate in both bash scripts: a spawn payload with neither `"subagent_type"` nor `"agent_type"` exits before forking. (7) `claude` (the catch-all agent) joins `BUILTIN_AGENTS["claude"]`. (8) Agent tasks created after a review's result count toward its fix rule and an in-progress background agent can enter In Review: intended, documented above. (9) A spawn with no id is deduplicated by agent, text and owner against an open id-less agent task (a replay adds nothing). (10) App fixture task `t5` is `cancelled` + `failed`; `app/README.md` words the Failed badge as a failed spawned agent run. | Findings of the review of Agent spawns are tasks |
| 2026-10-01 | The project kanban is one horizontally scrolling row of columns with a minimum width, each scrolling its own cards, instead of a responsive grid | The grid stacked the columns 2×2 or 1×4 in a narrower window, which no longer read as a kanban |
