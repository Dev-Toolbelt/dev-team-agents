Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below in parallel. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `security-specialist` at `.claude/agents/dev-team/security-specialist.md` — vulnerability analysis, OWASP, threat modeling, LGPD/GDPR compliance
- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architectural security implications and design mitigations

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
