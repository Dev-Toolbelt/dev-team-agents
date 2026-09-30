# How provider todo tools reach the task board

**Origin:** ADR-0018 implementation for cross-project task board, Codex payload confirmed against source | 2026-09-30
**Tags:** hook, todo tool, TaskCreate, TaskUpdate, update_plan, todowrite, provider payload, PreToolUse, PostToolUse, task id, undocumented

> Each provider's todo tool sends a different payload shape to the hook, with different id semantics and with or without session context.

---

## What it is

The task board (ADR-0018) captures task activity from each provider's native todo tool without any change to agent code. Each provider has its own tool and its own hook point, and the payloads they send are barely documented.

## How it works

| Provider | Hook point | Tool | Payload source | Task id | Session id | Subagent id |
|---|---|---|---|---|---|---|
| Claude Code | `PostToolUse` | `TaskCreate` (default) | `tool_input.taskId` and `tool_output` / `tool_response` | Id in input when updating; parsed from output (e.g. `Task #3 created`) on create, fallback to sequential | Yes (`session_id` at root) | Yes (`agent_id` / `agent_type` at root) |
| Claude Code | `PostToolUse` | `TaskUpdate` (default) | `tool_input` | `tool_input.taskId` | Yes (`session_id` at root) | Yes (`agent_id` / `agent_type` at root) |
| Claude Code | `PostToolUse` | `TodoWrite` (disabled by default; restored by `CLAUDE_CODE_ENABLE_TASKS=0`) | Full task list on every call (replace semantics) | Matched by normalized content | Yes (`session_id` at root) | Yes (`agent_id` / `agent_type` at root) |
| Claude Code | `SessionEnd` | — | Marker only | — | Yes | — |
| Codex | `PreToolUse` | `update_plan` | Built-in control tool keeping registry's default payload shape (`pre_tool_use_payload`) | Matched by normalized content; id is not sent | Yes (`session_id` in payload) | Yes (`agent_id` / `agent_type` in payload) |
| opencode | `tool.execute.before` (plugin) | `todowrite` | `args.todos[]` list | `todos[].id` | No — plugin must add `sessionID: input.sessionID` | Not present |

**Codex `update_plan` source confirmation:**

- `tool_input` carries `{explanation, plan: [{step: string, status: "pending"|"in_progress"|"completed"}]}` — Codex has no `cancelled` status (`StepStatus` in `codex-rs/protocol/src/plan_tool.rs`)
- Confirmed in the Codex source (openai/codex @ `92bc601`): `codex-rs/core/src/tools/registry.rs` (plan handler), `codex-rs/hooks/src/events/pre_tool_use.rs` (`command_input_json` serialization)
- Pinned by test: `tests/test_tasks.py::test_the_exact_payload_codex_sends_for_update_plan_is_recorded_through_the_dispatcher` replays the exact payload
- Status: not yet observed in a live Codex session; coverage depends on Codex releases; if a release stops firing `PreToolUse` for `update_plan`, Codex sessions simply disappear from the board without error

## Gotchas

- **Task id parsing for `TaskCreate` is anchored to tool output**, not the tool input. No documented shape → defensive parsing accepts both `tool_response` (object) and `tool_output` (string), unknown keys ignored.
- **Codex payload documented here, not in Codex's public docs.** Changes to the payload shape would not show up as a breaking release; test breakage is the signal.
- **opencode lacks session id in the payload.** The plugin must add it; the base `tool.execute.before` entry sees `args` but not the session id from `input`.
- **Claude Code input shapes for `Task*` are not publicly documented.** The normalizers are defensive: a payload that cannot be read is a no-op.
- **The pre-tool-use gate must be bash string matching**, not a python parser fork, so that only the relevant tool names (Codex `update_plan` or opencode `todowrite`) trigger `devteam tasks record`. A fork on every hook would be expensive.
- **Replace-style tools (TodoWrite, Codex `update_plan`, opencode `todowrite`) diff only the tasks of their own owner**, so a subagent's list never overwrites the main agent's list.

## References

- ADR-0018: The task board is captured by hooks into a machine-local per-session record
- Codex source reference: openai/codex @ `92bc601`
- Test: `tests/test_tasks.py::test_the_exact_payload_codex_sends_for_update_plan_is_recorded_through_the_dispatcher`
