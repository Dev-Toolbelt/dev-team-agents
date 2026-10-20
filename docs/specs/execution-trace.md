---
status: approved
touches: [backend]
depends_on: [task-board.md]
---

## Spec — Execution trace

### User Story
As a developer tuning the harness, I want every agent a session ran laid out as a tree, with who spawned it, how long it took and how many tokens it spent, so that an optimization loop can rank agents, commands and review rounds by cost instead of guessing.

### Context
The task board (ADR-0018, `task-board.md`) captures agent spawns as board tasks but leaves out review/QA agents and provider built-ins, and stores no cost. This spec adds a trace beside it: one span per agent spawn of any named type (a spawn that names no agent type has none, ADR-0041 Decision 2), kept in its own file so the board is untouched. Decision record: [ADR-0041](../development/adrs/0041-execution-trace-kept-beside-the-task-board-record-as-one-span-per-agent-spawn.md).

#### Capture per provider

| Moment | Claude Code | Codex | opencode |
|---|---|---|---|
| Span opens | `PreToolUse` `Agent`/`Task` (`tool_use_id`) | `PreToolUse` `spawn_agent` (`tool_use_id`) | `tool.execute.before` `task` (`callID`) |
| Runtime agent id | `tool_response.agentId` on `PostToolUse` (foreground result or background launch ack) | `spawn_agent` `PostToolUse` `agent_id` (the child thread id); multi-agent v2 answers `task_name` instead, kept as `agent_path` | `agent_session_id`, the child session id from the `task` result's metadata |
| Span ends | `PostToolUse` (foreground); the transcript hand-back at `Stop` (background); `PostToolUseFailure` | `wait_agent` final status; `close_agent`; v2: the first `FINAL_ANSWER` from `agent_path` in the parent rollout, read at `Stop` | `tool.execute.after` `task` |
| Tokens | `<transcript dir>/<session>/subagents/agent-<agentId>.jsonl`, last `message.usage` per `message.id`, summed | `${CODEX_HOME:-~/.codex}/sessions/*/*/*/rollout-*-<agent_id>.jsonl`, last `token_count.info.total_token_usage`; v2: the child rollout whose first line names the parent thread and `agent_path` | `agent_usage`, which the plugin sums from the child session's assistant messages (`info.tokens`) |
| Model | `tool_response.resolvedModel` | the child rollout's `turn_context.model` | the `task` result's `metadata.model.modelID` |

#### The file — `<state-dir>/task-board/trace/<session-key>.json`

```json
{
  "schema": 1, "session_id": "…", "provider": "claude|codex|opencode",
  "harness_version": "2.48.0", "created_at": 0, "updated_at": 0,
  "transcript_path": "… (Claude Code only)",
  "scan": {"opened_at": 0, "tx_path": null, "tx_offset": null, "queue_ids": []},
  "spans": [
    {
      "id": "toolu_…", "agent": "backend-developer", "kind": "agent|review|builtin",
      "owner": "main", "agent_id": null, "background": false,
      "turn_at": 0, "command": "plan",
      "started_at": 0, "ended_at": null, "status": "running|completed|failed|cancelled|interrupted",
      "model": null, "usage": null, "usage_tries": 0, "tool_uses": null, "duration_ms": null,
      "findings": null
    }
  ]
}
```

`usage` is `{"input", "output", "cache_read", "cache_write"}`, in tokens. `input` excludes cached input on every provider (Codex's `input_tokens` includes the cached part, so it is subtracted). `findings` is the total of a review agent's `<!-- review-result: findings=N -->` markers when its report reached a hook (Claude Code, opencode; a Codex `wait_agent` carries no report), else `null`. `harness_version` is the dev-team-agents version that wrote the trace, so the optimization loop can compare cost across harness changes. A span still `running` 6 hours after it started is settled `interrupted`. A Stop reads usage for at most 20 spans, and each span at most 3 times. `duration_ms` and `tool_uses` are the provider's own figures when it reports them (Claude Code). Otherwise they stay `null`, and the duration is `ended_at - started_at`.

#### Child sessions — `<state-dir>/task-board/trace/aliases.json`

An opencode subagent runs in a child session, and a Codex subagent in a child thread. Their own hook calls name that child, not the top session, so `aliases.json` maps each child id to its top session: `{"schema": 1, "aliases": {"<child>": "<top>"}}`. An entry is written when a span learns its runtime agent id, and also, on opencode, when the plugin names a call's `parent_id`. Only opencode's `parent_id` is honored, and an id that already has its own trace is never aliased. The map is shared by every session of the project, written under its own lock, and bounded at 200 entries; the oldest entry drops out, because it only routes hook calls and records nothing. `devteam tasks trace <child id>` shows the top session's trace.

#### Read surface — `devteam tasks trace <session> [--json]`

The tree is derived on read: session → turn (`turn_at`, `command`) → span → nested span, where a span's parent is the span whose `agent_id` equals its `owner`. A span whose owner matches no span hangs from its turn. Every node carries `tokens` (sum of `usage`, its own), `subtree_tokens`, and `usage_complete`, which is false when any node in its subtree has `usage: null` (unknown is never shown as zero). A cycle of owners cannot hide a span: a span whose owner chain loops back hangs from its turn. JSON (additive, ADR-0014): `{session_id, provider, harness_version, totals: {spans, tokens, duration_s, usage_complete}, turns: [{turn_at, command, tokens, usage_complete, spans: [<span + children>]}]}`.

### Acceptance Criteria

**Scenario S1: a spawned agent becomes a span**
- Given a bound project and a session on any supported provider
- When the session spawns a named agent and the agent returns
- Then the trace file holds one span for it, with `started_at`, `ended_at` and status `completed`

**Scenario S2: review agents and built-ins are traced too**
- Given a session that spawns `code-reviewer` and `Explore`
- When both return
- Then each has a span, `kind: "review"` and `kind: "builtin"`, and the task board shows neither as a task

**Scenario S3: nested agents form a tree**
- Given agent A spawns agent B
- When `devteam tasks trace <session> --json` runs
- Then B is a child of A, and A's `subtree_tokens` includes B's tokens

**Scenario S4: tokens per provider**
- Given an agent whose provider exposes its usage
- When the agent ends and the next `Stop` runs
- Then its span carries `usage` and `model`, and Claude Code usage counts each message once, however many transcript lines it streamed

**Scenario S5: background agents are counted once they finish**
- Given a Claude Code agent launched with `run_in_background`
- When its hand-back reaches the transcript and a `Stop` runs
- Then the span is ended at the hand-back's time and its usage is read then, not at launch

**Scenario S6: interrupted and failed agents**
- Given a foreground span still `running` when its turn's `Stop` fires, or a spawn that failed
- When the trace is read
- Then the first is `interrupted` and the second `failed`, both with `ended_at` set

**Scenario S7: no usage available**
- Given a provider or agent whose usage cannot be read (no runtime id, missing file)
- When the agent ends
- Then `usage` is `null` and the span is still in the tree

**Scenario S8: turns group by command**
- Given a turn that started with `/devteam:plan` (or `$devteam-plan`)
- When agents are spawned in that turn, directly or nested
- Then their spans carry `command: "plan"` and the trace groups them under that turn

### Out of Scope
- Aggregates across sessions and any recommendation built on them (the optimization loop itself)
- A desktop-app view of the trace
- Per-tool-call spans
- Sending the trace to remote telemetry

### Dependencies
- **Depends on**: `task-board.md` (the hooks and machine-local directory it already established)
- **Blocks**: the optimization loop plan

### Amendment Log
- 2026-10-19 | main conversation | Codex multi-agent v2 is supported: `agent_path` from `task_name`, end from the parent rollout's `FINAL_ANSWER`, `findings` from its marker, tokens from the child rollout | v2 spawns used to stay `running` with no usage
- 2026-10-19 | main conversation | Usage is read at the next Stop outside the trace lock within a byte budget, not on the result hook; one v2 matching rule shared with the board; `harness_version` is the installed version directory (pre-releases included); a spawn with no agent type has no span; crafted names are hidden in `tasks trace`; the session id `aliases` is refused | Branch review findings (security S1-S3, architect A7, code C1, C7)
