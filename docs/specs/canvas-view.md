---
status: approved
touches: [backend, frontend]
depends_on: [task-board.md, execution-trace.md]
ai: false
---

## Spec — Canvas view

### User Story
As a developer running agent sessions on a project, I want a canvas next to the task board that shows who spawned what — session, turn, main session, agents and their sub-agents — with status, cost and what each one produced, so that I can understand a run at a glance instead of reading a flat list.

### Context
The task board (`task-board.md`, ADR-0018) lists a session's tasks flat; the execution trace (`execution-trace.md`, ADR-0041) already records the spawn tree. The canvas draws that tree for one project, read-only, in the desktop app. Decision record: [ADR-0063](../development/adrs/0063-the-canvas-view-reads-a-cli-derived-task-graph-rendered-with-react-flow-and-a-deterministic-own-layout.md).

### Links
- **PRD rules**: none — no PRD (development layout)
- **Contract**: none — the graph JSON contract is recorded in ADR-0063 and the shared task contract; no separate contract doc
- **Flow**: none — single screen beside the board, no multi-step flow

### Acceptance Criteria

**Scenario S1: Open the canvas from a project**
- Given a project with at least one recorded session is selected in the app
- When the user opens the Canvas view from that project
- Then the canvas shows one frame per session, each holding one frame per turn, and the view fits all content on screen

**Scenario S2: Nesting of main session, agents and sub-agents**
- Given a session whose trace has a top-level agent that spawned two sub-agents
- When the canvas renders that session
- Then the main session node (labelled "Orchestrator" when the session ran the orchestrate command, otherwise "Main session") links to the top-level agent, and the top-level agent links to both sub-agents

**Scenario S3: Session without a trace falls back to the board**
- Given a session that has board agent tasks but no execution trace
- When the canvas renders that session
- Then its agent tasks appear as flat nodes under the main session, their usage shows "n/a", and the session shows a notice that the tree is unavailable for it

**Scenario S4: Status and role styling**
- Given nodes that are running, completed, failed and interrupted, and nodes of kind agent, review and built-in
- When the canvas renders them
- Then each status has a distinct, labelled visual state that does not rely on color alone, and each kind is visually distinguishable

**Scenario S5: Unknown usage shows n/a, never zero**
- Given an agent node whose provider reported no token usage
- When the node and its frames show token figures
- Then the node shows "n/a" instead of 0, and any frame total that includes it is marked as incomplete

**Scenario S6: PR chip opens only an allow-listed link**
- Given an agent node that produced a pull request
- When the user activates its PR chip
- Then the PR opens in the system browser through the app's allow-listed link path, and a URL that fails the allow-list is not opened

**Scenario S7: Collapse levels**
- Given a project with several sessions and nested agents
- When the user picks a collapse level (sessions only, turns, top-level agents, everything) from the toolbar's level menu
- Then nodes below that level are hidden, the hidden count is shown on the parent, and changing the level back restores them

**Scenario S8: Focus mode**
- Given a canvas with many nodes
- When the user selects one agent node and turns on the toolbar's Focus button
- Then that node, its ancestors and its descendants stay prominent, everything else is dimmed, and leaving focus restores the full view

**Scenario S9: Token heatmap toggle**
- Given agent nodes with different token totals
- When the user turns the toolbar's Token heatmap button on
- Then node emphasis scales with each node's subtree tokens, nodes with unknown usage are shown as unknown rather than lowest, and turning it off restores the status styling

**Scenario S10: Drag, persist and reset layout**
- Given the canvas in its automatic layout
- When the user drags a node, closes the app and opens the canvas again
- Then the node is where the user left it, other nodes keep their automatic positions, and "Reset layout" returns every node of that scope to the automatic layout

**Scenario S11: Same input, same picture**
- Given the same project data
- When the canvas is opened twice with no user overrides
- Then every node is laid out in the same position both times

**Scenario S12: Outline keyboard navigation**
- Given the canvas is open
- When the user uses the outline, open by default in a panel to the right of the canvas, with the keyboard (arrow keys to move, expand and collapse, Enter to select)
- Then the same hierarchy is reachable as an accessible tree, selecting an item selects the matching node on the canvas, and the toolbar's Outline button hides and shows the panel

**Scenario S13: Last output excerpt is redacted and capped**
- Given an agent whose final message contains a secret-shaped value and runs over several lines and more than 140 characters
- When the user views that agent's node details, on any supported provider
- Then the last-output excerpt shows the secret as redacted, on one line, at most 140 characters, rendered as plain text

**Scenario S14: Older CLI without the graph command**
- Given the app is paired with a CLI version that has no task graph command
- When the user opens the Canvas view
- Then the canvas shows a message that the installed CLI does not support the canvas and how to update, and the task board keeps working

**Scenario S15: Live updates while open**
- Given the canvas is open and an agent in that project starts or finishes
- When the board record changes
- Then the canvas reflects the change within a few seconds without the user reloading, and the user's dragged positions and current view are kept

**Scenario S16: Full screen**
- Given the canvas is open
- When the user presses the toolbar's Full screen button
- Then the canvas with its outline and details panels covers the whole app window, the button reads "Exit full screen", and pressing it or Esc returns to the normal view; while it is on, what it covers cannot take focus, and it closes by itself when nothing is left to show; it does not use the system Fullscreen API, whose permission the app's session refuses

**Scenario S17: Ended and idle sessions stand out**
- Given a session that has ended and a session, with its main node, that is idle
- When the canvas renders them
- Then the ended session's frame has a green border and the word "Ended" with an icon, and the idle session's frame and its main node have an amber border and the words "Idle · waiting" with an icon, explaining that the session may need the user's answer to continue

**Scenario S18: Controls inside the canvas**
- Given the canvas is open
- When the user looks for the canvas controls
- Then they are a vertical toolbar of icon buttons in the canvas's top-left corner, each named for assistive technology and explained by a tooltip, and the collapse level is chosen from a menu

**Scenario S19: The work reads once, and the details lead with what matters**
- Given an agent whose task text starts with its own name, as in "software-architect: Architect plan for VHI-712"
- When the canvas shows its node and the user opens its details
- Then the node's header names the agent and its text reads only "Architect plan for VHI-712"; the details panel shows that text as its title, then Model and Tokens as badges, then Took, Started and Finished, before the remaining facts

### Out of Scope
- Node actions (stop, re-run, open terminal, open worktree) — only the empty extension point ships
- Editing the board or trace from the canvas
- Cross-project canvases and sharing or exporting the canvas
- Separate artifact nodes for worktrees and PRs (shown as chips on the agent node)
- Review-to-PR and produced edges: schema 1 emits only `spawn` edges (`produced` and `reviewed` are reserved)

### Dependencies
- **Depends on**: `task-board.md`, `execution-trace.md`
- **Blocks**: none

### Amendment Log
- 2026-11-04 | software-architect | Created from the approved canvas-view plan | Spec for the MVP read-only canvas
- 2026-11-04 | backend-developer (canvas view) | Out of Scope names every non-`spawn` edge kind, not only review edges | Schema 1 emits `spawn` edges only
- 2026-11-04 | main conversation (/devteam:review) | Nodes carry `session_id`, `record_id`, `spawn_id`; a child session's PR chip and "Show on board" resolve against `record_id`; the main node shows the session's token total and an `idle` status; a frame or agent expanded by hand opens even where the collapse level folds it | /devteam:review findings (architect 1–2, code-reviewer 1–3, qa 1)
- 2026-11-05 | frontend-developer (canvas toolbar) | S7–S9 and S12 name the in-canvas toolbar; the outline opens by default on the right; added S16 (full screen), S17 (ended and idle session highlights) and S18 (vertical icon toolbar inside the canvas) | Canvas toolbar plan approved by the user
- 2026-11-05 | main conversation (canvas detail polish) | S16 covers the app window instead of the system full screen, which the session's permission policy refuses; added S19 (agent name not repeated in the node text, details panel order and badges) | User report: full screen did nothing; detail panel order requested by the user
