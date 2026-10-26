# Codex 0.160 Subagent Event Payloads

**Origin:** Codex task board capture, reconciled with the multi-agent v2 path | 2026-10-26
**Tags:** codex, 0.160, subagent, hooks, task board, SubagentStart, SubagentStop, spawn_agent, wait_agent, collaboration tools, collaborationspawn_agent

> Codex 0.160 glues the `collaboration` namespace to its tool names (`collaborationspawn_agent`, no dot), encrypts the spawn's message, and reports a child's id and end only as `SubagentStart` / `SubagentStop`.

---

## What it is

Codex 0.160 fires `SubagentStart` and `SubagentStop` around each child agent, besides the tool hooks of `spawn_agent` / `wait_agent`. The shapes were recorded live (2026-10-04) and are pinned in `tests/fixtures/codex-0.160-hook-payloads.json`. For how an agent ends under multi-agent v2 see `codex-v2-agent-ends-only-in-the-parent-rollout.md`; the board uses that path first and these events second.

## How it works

- **Glued tool names.** Hooks receive `collaborationspawn_agent` and `collaborationwait_agent`; older builds and the docs write `collaboration.spawn_agent`. `tasks.codex_tool` reads both, for the `collaboration` namespace only (`foospawn_agent` is no Codex tool). The shell gates, the board, the review window and the execution trace all go through it.
- **Encrypted spawn message.** The spawn's `message` is a `gAAAA…` blob, never text to show. The card text is `<agent_type>: <task_name>` with `/root/` stripped.
- **Spawn answer.** `PostToolUse` answers `{"task_name":"/root/<name>"}`: no agent id, so the task's `agent_ref` is that path. `wait_agent` answers only `{"message":"Wait completed.","timed_out":false}` and names no agent.
- **`SubagentStart`**: parent `session_id`, child `agent_id`, `agent_type`. It links the id to the oldest open spawn of that type with no child id.
- **`SubagentStop`**: the same, plus `last_assistant_message` and `agent_transcript_path`. It settles the linked task when the child stops, and carries a reviewer's `review-result` marker. It carries no failure status, so a failed child settles `completed` there.
- The child's own tool calls carry the parent's `session_id` plus its `agent_id`, which is the owner of its todo items.

## Gotchas

- **A task is ended once.** `SubagentStop`, the rollout's `FINAL_ANSWER` (v2) and `wait_agent` (v1) can all end the same task, in any order. A stop only ends an open task, and a v2 task it ended keeps an `answer_claim` so its `FINAL_ANSWER` is not handed to an open sibling of the same task path.
- **No stop guessing.** A stop whose child was never linked settles nothing; the oldest unlinked spawn may be one the rollout already ended.
- **Not the trace.** Neither event feeds the execution trace: its spans come from the spawn's hooks, so reading them there too would double every span.
- **Codex only.** Claude Code's `Agent`/`Task` calls already reach Pre/PostToolUse; opencode has no such event.
- **`update_plan` is off by default**: set `[tools.update_plan] enabled = true` in `~/.codex/config.toml` or a trusted project's `.codex/config.toml`. `devteam doctor` warns when it is off.
- **New hooks need re-trust.** Codex keeps a `trusted_hash` per hook, so after `devteam sync` the two new hooks do nothing until trusted in `/hooks`.
- **Unverified:** whether a Codex build older than 0.160 accepts a `hooks.json` with the two unknown event keys. 0.160 is the tested minimum.

## References

- ADR-0018, amendment 2026-10-26; `docs/specs/task-board.md` (decision log 2026-10-26)
- `tests/test_codex_subagent_capture.py`
- Related: `docs/wiki/hooks/provider-todo-tool-payloads.md`, `docs/wiki/hooks/codex-v2-agent-ends-only-in-the-parent-rollout.md`
