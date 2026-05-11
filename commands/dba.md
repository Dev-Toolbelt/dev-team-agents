Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below in parallel. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — schema design, migrations, query optimization, indexing, replication
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architectural data modeling implications and cross-service impact

Task: $ARGUMENTS
