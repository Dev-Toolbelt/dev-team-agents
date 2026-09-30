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

Projects are sorted by `last_activity_at` descending; sessions likewise; tasks by `created_at`.
Removed-and-not-completed tasks are omitted. `--since` drops sessions whose last activity is older.
The display name is not here — it is app-local (ADR-0016); the app joins on `project_id`.

`tasks watch --json` emits JSON Lines: `{"event":"snapshot","project": <one project object as above,
or {"project_id": "…", "removed": true} when it no longer has tasks>}`, then `{"event":"ready"}`
after the backlog, `{"event":"heartbeat","ts":…}` every 30 s, and `{"event":"end","reason":…}` —
the same lifecycle, stdin-EOF and SIGTERM handling as `notifications watch`.

#### In Review — an optional fourth column (amendment 2026-09-30)

A task may go from In progress straight to Done. It passes through **In Review** only when a review
is triggered in its session, and leaves only when the review passed or its findings were fixed.
No provider has a review status, so the column is inferred by the hooks.

**Review window.** A review is a window stored in the session record:

```json
"reviews": [
  {
    "id": "r1", "trigger": "agent|command|prompt", "source": "qa-specialist|/devteam:review|…",
    "opened_at": 0, "pending": 1, "result_at": null, "findings": null,
    "resolved_at": null, "resolution": null,
    "task_keys": ["t1", "t2"], "fix_after": null
  }
]
```

**Triggers — open a window** (at most one open window per session; a second trigger while one is
open joins it and increments `pending`):

| Trigger | Claude Code | Codex | opencode |
|---|---|---|---|
| Review/QA agent spawned: `qa-specialist`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer` | `PreToolUse` on `Agent`/`Task`, `tool_input.subagent_type` | `PreToolUse` on `spawn_agent`, `tool_input.agent_type` | `tool.execute.before` on `task`, `args.subagent_type` |
| Command: `/devteam:review`, `/devteam:qa`, `/review` | `UserPromptSubmit`, `prompt` | `UserPromptSubmit`, `prompt` | plugin `chat.message`, text parts |
| Explicit request in the prompt: review, revisar, revisão, revise, QA, testar, test it | same as commands | same | same |

Keyword matching is word-bounded and case-insensitive, and skips a match preceded within three
words by a negation (`não`, `sem`, `no`, `don't`, `without`, `skip`). It lives in one tested file.

**Which tasks enter.** At the moment the window opens: every non-removed task of the session that is
`in_progress`, plus every task `completed` after the previous window was resolved (or ever, if there
is none). Tasks created after the window opened do not enter it.

**Result — read from a marker.** Our four review/QA agents end their final report with
`<!-- review-result: findings=N -->` (rule in `skills/shared/review-result/SKILL.md`, emitted from
each agent's `## Before You Finish`). The hook scans the agent's returned output for it:
Claude `PostToolUse` on `Agent`/`Task` (`tool_response`), Codex `PostToolUse` on `wait_agent`
(`tool_response`), opencode `tool.execute.after` on `task` (`output.output`). Several markers in one
response (parallel reviewers) are summed. Each marker decrements `pending`; the result is recorded
when `pending` reaches 0. For a command/prompt-triggered window, the next `Stop` scans the transcript's
last assistant message (Claude `transcript_path`) for the marker; with no marker anywhere, the window
records `findings: null` — shown as **result not read**.

**Leaving In Review.**

| Case | What happens |
|---|---|
| Result `findings = 0` | Window resolved (`resolution: "passed"`); its tasks go to Done if completed, else back to In progress |
| Result `findings > 0` | Cards show **N findings**; tasks stay in In Review; `fix_after` = result time; notification `tasks.review_findings` |
| Fix rule | Every task created after `fix_after` in the session (the fix list) is completed, and there is at least one → resolved (`"fixed"`) |
| Re-review rule | A later window in the same session returns `findings = 0` → earlier unresolved windows resolved (`"fixed"`) |
| Result not read | Stays in In Review with the **result not read** badge until the fix or re-review rule resolves it |
| Reopened | A task in review that the agent sets back to `in_progress` leaves the window at once (column In progress) |

**Derived fields** (added, nothing removed — additive to the JSON contract):

- task `column` gains `in_review`; task gains `review: {"state": "pending|findings|unread|null", "findings": N|null, "since": epoch}` (null when not in review);
- `counts` gain `in_review` (project and session); project gains `with_findings` (tasks in review with findings);
- `durations` gain `in_review`: time between entering and leaving the window;
- the `status` field keeps the provider's own status; only `column` reflects review.

#### Notifications (emitted by the hook through `notify.sh`, the only emitter)

| Code | When |
|---|---|
| `tasks.session_done` | A record call moves a session from "some open" to "all done" (≥ 1 task) |
| `tasks.review_findings` | A review window records `findings > 0` (dedupe per window) |
| `tasks.session_abandoned` | `SessionEnd` fires while the session still has open tasks (Claude only; other providers have no end event) |

#### Desktop app

- **Board (overview):** only projects with ≥ 1 task. Card: display name, provider icons (the set used
  by its sessions), sessions `total (N active)`, counts and percentages for To do / In progress /
  Done, a stacked progress bar, and badges for stale and abandoned tasks. Period filter
  (today / 7 days / 30 days / all).
- **Project kanban:** three columns. Card: task text, session chip (provider icon + branch), time in
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
