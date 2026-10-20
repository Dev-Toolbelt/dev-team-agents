# ADR-0041: Execution trace kept beside the task-board record as one span per agent spawn

**Date:** 2026-10-19  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/trace.py`, `scripts/lib/devteam/usage.py`, `scripts/lib/devteam/tasks.py`, `scripts/hooks/lib/agent-usage.sh`, `scripts/hooks/lib/task-board.sh`, `scripts/hooks/pre-tool-use/04-task-board.sh`, `scripts/hooks/post-tool-use/01-task-board.sh`, `scripts/hooks/stop/00b-task-board.sh`, `scripts/lib/ensure-claude-framework.sh`, `opencode/plugin/dev-team-agents.ts`  
**Relates to:** [ADR-0018](0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md) (task board), [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (machine-local records), [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (`--json` contract)

## Context

The harness already records what happened in a session — the task board (ADR-0018), run banners, review-result markers, per-agent token telemetry — but as flat records. Nothing answers "this command spawned this agent, which spawned that one, and each spent N tokens in T seconds". That tree is what an optimization loop needs: it cannot rank agents, commands or review rounds by cost without it.

The task board was the obvious base, since it already captures every agent spawn on every provider. But it deliberately drops review/QA agents and provider built-ins (their effect is the In Review window, or none), and its record drives board columns, notifications and review windows, so new task kinds there risk changing what the board shows. The cost tool that existed, `scripts/hooks/lib/agent-usage.sh`, summed every transcript line of a subagent; Claude Code writes several lines per message while streaming, so it overcounted, and it saw only background agents.

## Decision

1. **One trace file per session**, `<state-dir>/task-board/trace/<session-key>.json`. It sits inside the machine-local `task-board/` directory, so it inherits its classification. Its subdirectory is invisible to the board's listing, which reads `*.json` at the top level only. It is written only by `devteam tasks trace-record`, under its own per-session lock, atomically, and is never deleted.
2. **One span per agent spawn, every named agent type**: board agents, review/QA agents and built-ins alike, each with a `kind` saying which one it is. A span holds spawn id, agent, owner, runtime agent id, turn start and `/devteam:*` command, start and end times, status, model and token usage. A spawn that names no agent type (the provider's default agent) has no span: the hooks leave such a call before forking anything, the same cheap gate the board keeps, so it is a known undercount of `builtin_token_share`.
3. **The tree is derived on read**: session → turn → agent → nested agent. A span's parent is the span whose runtime agent id equals its owner. Nothing in the file stores the tree.
4. **Tokens are read once the agent has ended, at the next `Stop`, with no lock held** (the trace is snapshotted under its lock, the files are read outside it within a per-Stop byte budget, and the result is merged back under the lock), from the provider's own record of the agent: the subagent transcript on Claude Code (last usage per message id), the child rollout's last `token_count` on Codex, and the child session's messages on opencode (summed by the plugin, which owns the SDK client). A provider that exposes nothing leaves `usage: null`. Nothing new runs on ordinary tool calls.
5. **One Claude transcript parser**, `devteam/usage.py`, is used by both the trace and `agent-usage.sh`, so per-message dedup applies to telemetry too.
6. `devteam tasks trace <session> [--json]` is the read surface, additive to the `--json` contract.
7. **Codex multi-agent v2** (`spawn_agent` answering `{"task_name": "/root/<name>"}`, no agent id): the task path is the agent's reference, kept as `agent_path`. Each span keeps where the parent rollout ended at its spawn (`PreToolUse`). At `Stop` the first `FINAL_ANSWER` from that path after that mark ends it, oldest open span first. One rule, `usage.codex_v2_matches`, is shared with the task board. The child's tokens come from the rollout whose first line names the parent thread and that path. A span with no answer is settled by the 6 h running limit.
8. **One shared alias map**, `trace/aliases.json`, routes an opencode child session or a Codex child thread to its top session. It is bounded at 200 entries and drops the oldest, because it routes hook calls and records nothing. An id with its own trace is never aliased, and only opencode's `parent_id` creates an alias before an agent's id is known.
9. **What the optimization loop needs is recorded from day one:** the harness version that wrote the trace, and a review span's `findings` total from its review-result marker.

## Consequences

### Positive
- Cost and duration per agent, per nested agent and per `/devteam:*` command, on all three providers, from hooks that already fire.
- Reviewers are measured, which is where the loop's first questions are (rounds, `stalled`, cost per review).
- Telemetry stops overcounting Claude subagent tokens, and counts foreground agents too.

### Negative
- One extra python fork per agent spawn and per agent result. Spawns are rare next to tool calls, and the ordinary-tool-call gate is untouched.
- Codex multi-agent v2 ends an agent only in the parent rollout (Decision 7): an errored child writes no answer, and a nested spawn or a resumed thread answers in another rollout, so those spans end only at the 6 h limit.
- opencode usage depends on the plugin's SDK calls, which are verified against stored session data, not yet against a live hook.

### Neutral
- The board record is not touched: a trace bug cannot change columns, notifications or review windows.
- Built-in agents that ran before a project was bound leave no span, like any other hook-captured record.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Store spans as new task kinds inside the board record | Board readers branch on `kind` in many places (`_is_native` treats any unknown kind as a provider todo); a new kind risks the board's columns and notifications |
| Store the tree (parent pointers resolved at write time) | A parent's runtime id often arrives after its children's spawns (background launches); deriving on read is order-independent, like the board's own derived state |
| Count tokens on every tool call | Adds a write to the hottest hook path; the provider already keeps cumulative usage per agent |
| A `trace/` directory at the state-dir root | Would need a new `MACHINE_LOCAL_RECORDS` entry with a name no user directory carries; nesting under `task-board/` inherits the classification |
