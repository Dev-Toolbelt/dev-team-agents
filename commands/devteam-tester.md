Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context. Write or update tests only for what changed in this branch/worktree unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn:
- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` — unit, integration, and E2E tests for backend changes

Also spawn if the context includes frontend changes:
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — component, E2E, and accessibility tests for frontend changes

Task: $ARGUMENTS
