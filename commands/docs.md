Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all documentation to what changed in this branch/worktree unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `technical-writer` at `.claude/agents/dev-team/technical-writer.md` — README, API docs, runbooks, playbooks, changelogs, release notes, architecture guides

Task: $ARGUMENTS
