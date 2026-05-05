Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and fixes to files and changes within this context. Do NOT touch unrelated code unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn based on where the bug lives (in parallel if both apply):
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` — fix backend issues (spawn if the bug is in server-side code)
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — fix frontend issues (spawn if the bug is in client-side code)

Phase 2 — spawn after Phase 1 completes:
- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` — add or update tests to cover the fix (spawn if backend was touched)
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — add or update tests to cover the fix (spawn if frontend was touched)

Task: $ARGUMENTS
