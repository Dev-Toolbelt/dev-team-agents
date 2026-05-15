Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.


**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement the frontend changes
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system adherence and visual decisions (spawn only if the task involves visual design or UX decisions)

Phase 2 — spawn after Phase 1 completes:
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — write or update tests for the implemented changes

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.claude/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
