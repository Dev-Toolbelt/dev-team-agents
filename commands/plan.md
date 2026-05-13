Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/plan-mode/SKILL.md` to anchor the canonical plan format (STEPS table, Par. column, Definition of Done) for all spawned agents.

---

**MANDATORY:** Use the Task tool to spawn the agents below in parallel. Do NOT plan inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Always spawn (in parallel):
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — system design, trade-offs, API contracts, ADR authoring
- `product-analyst` at `.claude/agents/dev-team/product-analyst.md` — scope closure, acceptance criteria, backlog generation
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — data modeling, schema decisions, migration planning

To decide which optional agents to spawn, load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS before spawning.

All agents collaborate to produce a unified plan. Present the consolidated plan to the user and wait for approval before any execution begins.

Task: $ARGUMENTS
