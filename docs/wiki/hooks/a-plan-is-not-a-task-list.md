# A written plan never reaches the task board

**Origin:** a live session planned a whole feature with no task-list call and the board stayed empty | 2026-09-30
**Tags:** task board, plan, plan-mode, TaskCreate, update_plan, todowrite, native task list, empty board, Task List Mirroring, agent spawn, direct work

> The board reads only the provider's native task list. A plan in chat or in a `.md` file is invisible to it until its steps are mirrored as native tasks. Since agent spawns now appear as tasks automatically, an empty board after a command that delegated to agents means the capture hooks did not fire.

---

## What it is

The task board is fed by hooks on each provider's todo tool (ADR-0018). The agents of this framework
plan in chat or in files by default, and the provider opens its own list only when it decides the work
needs one. A session can therefore run for minutes, write a full plan and delegate to subagents with
every hook firing correctly — and still leave nothing on the board.

## How it works

`skills/shared/plan-mode/SKILL.md` § Task List Mirroring closes the gap. Skills are read raw by every
provider — nothing rewrites them at render time — so the section names each provider's tool itself.

## Gotchas

- An empty board after agent delegation is not a capture bug until the session's transcript shows an `Agent` / `spawn_agent` / `task` tool call (for spawned agents) or a `TaskCreate`, `TaskUpdate`, `TodoWrite`, `update_plan` or `todowrite` call (for task-list tools). Check those first. If the board stayed empty but the session spawned agents, the hooks did not fire — check the project's `.claude/settings.json` (Claude Code), `.codex/hooks.json` (Codex), or `.opencode/plugins/` (opencode) for the task-board hook entries, and run `devteam sync` to repair.
- Tasks are created only on approval: a plan still waiting for the user's answer has no tasks yet.
- A renamed or renumbered step shows twice on a whole-list tool (`TodoWrite`, `update_plan`,
  `todowrite`): the board matches those by exact text, or by `id` on opencode.
- Commands that never plan (`/devteam:status`, a quick question) may still appear on the board if they spawn agents; only commands with no work and no agent spawns correctly stay off the board.
- Work the session does itself lands on one **Direct work** card per session — In progress for a write (an edit, a commit), To Do for a turn that only read — but only when no plan step is `in_progress` and no agent was spawned in that turn; the plan or the agent is the better grain. A missing card is a gate question first: was it a subagent (`agent_id`, opencode `parent_id`), a prompt answered with no tool at all, a To Do card past the app's lifetime setting, or does the project still run a core version without the gate (`grep -c direct .dev-team-agents/scripts/hooks/pre-tool-use/04-task-board.sh`)? A card stuck in To Do after an edit means `tasks.writes()` read the shell call as read-only (it reads through `ssh host '<cmd>'` and knows container/cluster/service subcommands, but not an API call such as `curl -X POST`), or `.directw-<session>` already existed for that turn.
- Built-in agents (Claude Code: `Explore`, `Plan`, `general-purpose`, `claude-code-guide`, `statusline-setup`, `claude`; one list per provider in `review_triggers.BUILTIN_AGENTS`) and review/QA agents (`qa-specialist`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer`) do not appear as tasks — they are internal infrastructure or handled separately through review windows.
