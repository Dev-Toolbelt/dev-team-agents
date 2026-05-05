Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context. Do NOT scan or act on the full codebase unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement the frontend changes
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system adherence and visual decisions (spawn only if the task involves visual design or UX decisions)

Phase 2 — spawn after Phase 1 completes:
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — write or update tests for the implemented changes

Task: $ARGUMENTS
