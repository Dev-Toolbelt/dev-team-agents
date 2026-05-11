Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `qa-specialist` at `.claude/agents/dev-team/qa-specialist.md` — validate feature behavior, acceptance criteria, regression, and end-to-end correctness

Task: $ARGUMENTS
