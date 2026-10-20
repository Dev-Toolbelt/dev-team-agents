# Codex multi-agent v2 ends an agent only in the parent rollout

**Origin:** /devteam:learn consolidation, Codex multi-agent v2 settlement | 2026-10-19
**Tags:** codex, multi-agent v2, spawn_agent, wait_agent, task_name, FINAL_ANSWER, rollout, agent_message, thread_spawn, agent_path

> Under Codex multi-agent v2, the only signal that a child agent finished is a `FINAL_ANSWER` message in the parent rollout. `wait_agent` does not name the agent.

---

## What it is

A v2 agent has no agent id. It is identified only by its task path, and its end is recorded in the parent's rollout file.

## How it works

1. `spawn_agent` returns `{"task_name": "/root/<name>"}`. There is no agent id.
2. `wait_agent` returns only "Wait completed." It names no agent.
3. The end appears as a `response_item` `agent_message` in the **parent** rollout. Its text starts with `Message Type: FINAL_ANSWER`, and its `author` is the task path.
4. The child rollout's first line, `session_meta.source.subagent.thread_spawn`, names the parent thread and the `agent_path`.

## Gotchas

- Do not match on the `wait_agent` result. It is the same for every agent.
- Match on `author` = task path inside `FINAL_ANSWER` messages in the parent rollout.
- The shared matching rule is `usage.codex_v2_matches`. Use it instead of re-deriving the match.

## References

- `scripts/lib/devteam/usage.py` — `codex_v2_matches`
