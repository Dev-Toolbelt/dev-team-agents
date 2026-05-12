Load and follow the workflow defined in `.claude/dev-team-agents/workflows/security-patch.md`.

Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Follow every step in the workflow exactly as defined. Spawn the required agents via the Task tool at each step — do NOT handle steps inline. Present the output of each step to the user before proceeding to the next.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.claude/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Every workflow step that modifies files or runs commands requires a plan presented in the user's language before execution. Do not skip this even when the workflow implies "do X" — the agent must still plan and await approval.
3. Do not execute and then explain — plan first, execute second.

Vulnerability or patch description: $ARGUMENTS
