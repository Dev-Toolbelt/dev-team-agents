Before acting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only HEAD` — locally modified files
- Run `git diff --name-only main...HEAD` — all changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Restrict all analysis and actions to files and changes within this context. Do NOT audit the full codebase — only what changed in this branch/worktree unless $ARGUMENTS explicitly requests a broader scope.

---

**MANDATORY:** Use the Task tool to spawn the agents below in parallel. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `security-specialist` at `.claude/agents/dev-team/security-specialist.md` — vulnerability analysis, OWASP, threat modeling, LGPD/GDPR compliance
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architectural security implications and design mitigations

Task: $ARGUMENTS
