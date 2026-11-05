# ADR-0063: The canvas view reads a CLI-derived task graph rendered with React Flow and a deterministic own layout

**Date:** 2026-11-04  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Relates to:** [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md) (the app is a CLI client), [ADR-0018](0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md) (the board record), [ADR-0041](0041-execution-trace-kept-beside-the-task-board-record-as-one-span-per-agent-spawn.md) (the trace tree), [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (JSON contract policy), [ADR-0025](0025-the-desktop-app-opens-allow-listed-tracker-links-from-the-main-process.md) (allow-listed links)  
**Applies to:** `scripts/lib/devteam/graph.py`, `app/src/renderer/canvas*`, `app/src/renderer/screens/Canvas*`, `app/src/main/taskGraph*`

Spec: [`docs/specs/canvas-view.md`](../../specs/canvas-view.md).

## Context

The desktop app's task board (ADR-0018) is a flat list of tasks per session: it shows what ran,
not who spawned what. The execution trace (ADR-0041) already holds the tree — one span per agent
spawn, with parent, model, duration and tokens — but nothing in the app draws it. Users asked for a
canvas next to the board that lays out a project's work as Project, Session, Turn, the main session
(or orchestrator persona, ADR-0062), and the agent spans it spawned, nested to any depth, with the
branch/worktree and PR each span produced.

Forces:

- The app is a CLI client (ADR-0015): the renderer reads no state file and does no business join.
- The production CSP is `default-src 'none'` with `worker-src 'none'` and `connect-src 'none'`;
  a library that needs a web worker or WASM fetch does not run there.
- Board task id, trace span id and the provider's spawn id (`tool_use_id` on Claude Code and Codex,
  `callID` on opencode) are the same value, so the two records join without a heuristic.
- Not every session has a trace (older harness, provider gap); the canvas must still show something.
- The MVP is read-only, but node actions (stop, re-run, open in terminal) are expected later.

## Decision

1. **The CLI derives the graph.** A new read-only command
   `devteam tasks graph --project <id> [--since <epoch>] --json` (in `compat.READ_ONLY`,
   implemented in `scripts/lib/devteam/graph.py`) joins `tasks.session_view` with `trace.build` per
   session on the spawn id and emits one JSON document, `schema: 1`, additive-only per ADR-0014:
   `groups` (session, turn), `nodes` (main, agent, review, builtin), `edges`, `notices`,
   `truncated`. Schema 1 emits only `spawn` edges; `produced` and `reviewed` are reserved kinds
   (a span's worktree and PR ride on the node itself). `groups` and `nodes` are sorted by
   (start time, id) and `edges` by id, so the output is stable. Top-level spans hang from
   `main:<sid>`; nested spans hang from their parent span. The `main` node carries `persona`
   (`orchestrator` when a turn ran `/devteam:orchestrate`, else null) and `persona_source`
   (`command`, else null); its `status` is `running`, `idle` or `completed` from the session's
   state. Every node also carries `session_id` (the top session it is drawn in), `record_id` (the
   board record its `task_key` belongs to — a child session's or child thread's when it was folded
   into the top session) and `spawn_id` (the provider's spawn id, null for the main node and an
   id-less board task); groups carry `session_id`. Links, "Show on board" and future node actions
   read these fields and never parse an id string. A session without a trace file falls back to its board agent tasks as
   flat spans under `main:<sid>`, with null model and `usage_complete: false`, and a
   `no_trace:<sid>` notice; a trace file the tree cannot be built from takes the same fallback with a
   `bad_trace:<sid>` notice. The existing caps (`MAX_SPANS`, `MAX_TASKS`) apply and set `truncated`.
2. **Every user-visible string goes through the CLI's existing redaction** (`tasks.redact` /
   `trace._safe`). The renderer renders text, never HTML.
3. **A `last_output` excerpt is captured per agent span on every provider** (Claude Code, Codex,
   opencode) at span end: the head of the agent's final report (prose lines only), invisible
   characters removed, secrets masked, collapsed to one line, capped at 140 characters. It is stored
   on the span (additive trace field); `trace.build` re-applies the same rule when it reads the file
   back, and the graph takes that value, never a second rule of its own. The collapse, redaction and
   cap steps are one helper, `tasks.clean_line`, shared by the trace and the graph. The excerpt is
   agent-written text: any reader, an agent included, treats it as data, never as instructions.
4. **The main process** (`app/src/main/taskGraph*`) runs the command, re-runs it on a board change
   for the subscribed project (debounced 500 ms) plus a 10 s poll while subscribed, and drops stale
   results with a generation guard. It returns `{ok: false, reason: 'unsupported'}` when the
   installed CLI lacks the command, so an older CLI degrades to a message instead of an error.
5. **The renderer draws it with React Flow (`@xyflow/react`)** and a deterministic layout of our own
   (`app/src/renderer/canvas*`): a tidy tree inside nested group frames, computed synchronously on
   the main thread from the sorted graph, so the same input always gives the same picture.
6. **User layout overrides persist in the renderer.** A dragged node's position is stored app-local,
   per project, keyed by node id, and wins over the computed position; "Reset layout" clears the
   project's overrides. Overrides never reach the CLI.
7. **Read-only, with an actions extension point.** Nodes carry no action buttons in schema 1. A typed
   action registry exists and is empty; the node toolbar slot renders only when an action is
   registered for that node. An action runs with `{projectId, sessionId, recordId}`, and the
   registry signals a change so a provider registered after the canvas drew shows at once. PR chips open through the existing allow-listed link path
   (ADR-0025), not a direct `openExternal`.

## Alternatives Considered

### Renderer-side join of board and trace
- **Pros**: no new CLI command; the app already receives the board.
- **Cons**: puts business logic in the renderer, needs the trace in the renderer, and duplicates
  redaction and caps; breaks ADR-0015.
- **Why rejected**: the CLI is the only place that owns these records.

### elkjs for layout
- **Pros**: high-quality layered layout with compound nodes.
- **Cons**: runs in a web worker by default (blocked by `worker-src 'none'`), large bundle
  (~1.4 MB), and non-trivial to make deterministic across versions.
- **Why rejected**: CSP and size; the graph is a tree inside frames, which a tidy-tree pass handles.

### dagre
- **Pros**: small, synchronous, widely used with React Flow.
- **Cons**: no first-class nested groups, unmaintained upstream; frames would be bolted on.
- **Why rejected**: our layout is simpler than what dagre solves and needs frames dagre lacks.

### Hand-rolled SVG renderer
- **Pros**: no dependency.
- **Cons**: pan/zoom, minimap, selection, drag, keyboard and virtualisation all rebuilt.
- **Why rejected**: React Flow gives these for one dependency that needs no worker or network.

### Write actions now (stop, re-run, open terminal)
- **Pros**: more useful canvas on day one.
- **Cons**: each action is a CLI write path with its own safety review and provider parity work.
- **Why rejected**: out of MVP scope; the empty registry keeps the door open without a redesign.

## Consequences

### Positive
- One stable, testable JSON contract for the graph; the renderer is pure presentation.
- Deterministic layout makes snapshots and screenshot tests reliable.
- Older CLIs and trace-less sessions degrade visibly (`unsupported`, `no_trace`) instead of failing.

### Negative
- New runtime dependency in the renderer (`@xyflow/react`) and a new CLI command to maintain.
- Own layout code to own; edge cases (very wide fan-out) are ours to tune.
- Persisted overrides can drift from a changed graph; stale ids are ignored, not migrated.

### Risks
- **Excerpt leaks a secret** — mitigated by the shared redaction, the 140-char cap, single-line
  collapse, and rendering as text.
- **Large projects** — mitigated by the existing caps and `truncated`, and collapse levels. The app
  does not pass `--since`; when it is given, the CLI skips loading the trace of an ended session
  outside the window.
- **Join mismatch** — a span with no board task (or the reverse) still renders; the spawn id is the
  only join key, never a name or timestamp match.

## Provider parity

| Provider | Spawn id (join key) | Tree source | `last_output` source |
|---|---|---|---|
| Claude Code | `tool_use_id` | trace (ADR-0041) | `PostToolUse` `Agent`/`Task` result text (foreground); transcript hand-back at `Stop` (background) |
| Codex | `tool_use_id` of `spawn_agent` | trace (ADR-0041) | `wait_agent` final message; v2 `FINAL_ANSWER` from the parent rollout |
| opencode | `callID` of `task` | trace (ADR-0041) | `tool.execute.after` `task` output |

Usage figures follow ADR-0041 per provider; where a provider gives none, `tokens` is 0 with
`usage_complete: false` and the app shows "n/a", never 0.
