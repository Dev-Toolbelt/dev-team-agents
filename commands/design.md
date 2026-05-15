Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system, component design, UX flows, visual decisions

Also spawn if the task includes implementation of design changes (when $ARGUMENTS contains "implement" or "build"):
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement the design changes in code

Also spawn if mobile implementation is needed (ios/, android/, *.swift, *.kt, App.tsx, pubspec.yaml, *.dart AND implementation requested):
- `mobile-developer` at `.claude/agents/dev-team/mobile-developer.md` — implement design changes for mobile platforms

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.claude/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
