Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `devops-specialist` at `.claude/agents/dev-team/devops-specialist.md` — CI/CD pipelines, Docker, infrastructure-as-code, deploy scripts, environment config, monitoring

Task: $ARGUMENTS
