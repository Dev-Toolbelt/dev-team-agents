Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and refactoring to files and changes within this context. Do NOT refactor unrelated code unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — always spawn first:
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — define the refactoring approach, identify boundaries, and produce a refactoring plan before any code changes

Phase 2 — spawn after architect's plan is approved (in parallel if both apply):
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` — execute backend refactoring (spawn if the refactor involves server-side code)
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — execute frontend refactoring (spawn if the refactor involves client-side code)

Task: $ARGUMENTS
