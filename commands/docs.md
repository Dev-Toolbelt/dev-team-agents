Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `technical-writer` at `.claude/agents/dev-team/technical-writer.md` — README, API docs, runbooks, playbooks, changelogs, release notes, architecture guides

Task: $ARGUMENTS
