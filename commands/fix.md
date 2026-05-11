Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn based on where the bug lives (in parallel if both apply):
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` — fix backend issues (spawn if the bug is in server-side code)
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — fix frontend issues (spawn if the bug is in client-side code)

Phase 2 — spawn after Phase 1 completes:
- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` — add or update tests to cover the fix (spawn if backend was touched)
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — add or update tests to cover the fix (spawn if frontend was touched)

Task: $ARGUMENTS
