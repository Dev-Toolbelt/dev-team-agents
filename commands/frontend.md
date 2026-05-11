Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement the frontend changes
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system adherence and visual decisions (spawn only if the task involves visual design or UX decisions)

Phase 2 — spawn after Phase 1 completes:
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — write or update tests for the implemented changes

Task: $ARGUMENTS
