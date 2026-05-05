Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context. Do NOT review the full codebase — only what changed in this branch/worktree unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT review inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn in parallel:
- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md` — overall code quality, routes internally to backend-reviewer and/or frontend-reviewer based on what changed
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architectural consistency and design decisions
- `security-specialist` at `.claude/agents/dev-team/security-specialist.md` — security vulnerabilities and OWASP concerns

Also spawn if the task involves database changes:
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — query efficiency, schema correctness, migration safety

Task: $ARGUMENTS
