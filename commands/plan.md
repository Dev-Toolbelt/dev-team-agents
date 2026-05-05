Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context. Do NOT scan or act on the full codebase unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below in parallel. Do NOT plan inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn (in parallel):
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — system design, trade-offs, API contracts, ADR authoring
- `product-analyst` at `.claude/agents/dev-team/product-analyst.md` — scope closure, acceptance criteria, backlog generation
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — data modeling, schema decisions, migration planning

Also spawn if the task involves backend code or server-side changes:
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` — backend implementation planning

Also spawn if the task involves UI, pages, or client-side changes:
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — frontend implementation planning

Also spawn if the task involves infrastructure, CI/CD, or deploy:
- `devops-specialist` at `.claude/agents/dev-team/devops-specialist.md` — infra and pipeline planning

All agents collaborate to produce a unified plan. Present the consolidated plan to the user and wait for approval before any execution begins.

Task: $ARGUMENTS
