# A written plan never reaches the task board

**Origin:** a live session planned a whole feature with no task-list call and the board stayed empty | 2026-09-30
**Tags:** task board, plan, plan-mode, TaskCreate, update_plan, todowrite, native task list, empty board, Task List Mirroring

> The board reads only the provider's native task list. A plan in chat or in a `.md` file is invisible to it until its steps are mirrored as native tasks.

---

## What it is

The task board is fed by hooks on each provider's todo tool (ADR-0018). The agents of this framework
plan in chat or in files by default, and the provider opens its own list only when it decides the work
needs one. A session can therefore run for minutes, write a full plan and delegate to subagents with
every hook firing correctly — and still leave nothing on the board.

## How it works

`skills/shared/plan-mode/SKILL.md` § Task List Mirroring closes the gap: on approval, one native task
per Steps row; `in_progress` / `completed` in step with Progress Reporting. Skills are read raw by
every provider, so the section names each provider's tool itself; agent and command bodies get theirs
from `scripts/lib/tool-map.json` at render time.

## Gotchas

- An empty board is not a capture bug until the session's transcript shows a `TaskCreate`,
  `TaskUpdate`, `TodoWrite`, `update_plan` or `todowrite` call. Check that first.
- Tasks are created only on approval: a plan still waiting for the user's answer has no tasks yet.
- Commands that never plan (`/devteam:status`, a quick question) correctly stay off the board.
