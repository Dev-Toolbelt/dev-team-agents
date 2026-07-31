Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `ui-ux-designer` — design system, component design, UX flows, visual decisions

Also spawn if the task includes implementation of design changes (when $ARGUMENTS contains "implement" or "build"):
- `frontend-developer` — implement the design changes in code

Also spawn if mobile implementation is needed (ios/, android/, *.swift, *.kt, App.tsx, pubspec.yaml, *.dart AND implementation requested):
- `mobile-developer` — implement design changes for mobile platforms

## Session close (mandatory)

After the phases above complete — including any resolution agents:

1. **Session summary** — append this session's contribution to today's entry in `.dev-team-agents/user-data/session-summary.md`: one `### <agent-name>` sub-heading per agent that acted, each with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading. Skip only if no file was created or modified.
2. **Hand off** — the working tree is left dirty on purpose. Close with one line naming the next step: `/devteam:commit` to group and commit the changes, then `/devteam:pr` when the branch is ready for review.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
