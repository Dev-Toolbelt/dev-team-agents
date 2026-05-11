Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn:
- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` — unit, integration, and E2E tests for backend changes

Also spawn if the context includes frontend changes:
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — component, E2E, and accessibility tests for frontend changes

Task: $ARGUMENTS
