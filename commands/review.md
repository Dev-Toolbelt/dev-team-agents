Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT review inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn in parallel:
- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md` — overall code quality, routes internally to backend-reviewer and/or frontend-reviewer based on what changed
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architectural consistency and design decisions
- `security-specialist` at `.claude/agents/dev-team/security-specialist.md` — security vulnerabilities and OWASP concerns

Also spawn if the task involves database changes:
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — query efficiency, schema correctness, migration safety

Task: $ARGUMENTS
