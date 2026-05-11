Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` — implement server-side changes
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement client-side changes
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — handle schema, migrations, queries (spawn only if the task involves database changes)
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system and visual decisions (spawn only if the task involves visual design or UX decisions)

Phase 2 — spawn after Phase 1 completes:
- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` — tests for backend changes
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — tests for frontend changes

Task: $ARGUMENTS
