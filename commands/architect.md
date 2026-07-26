Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architecture decisions, system design, trade-offs, ADR authoring, API contracts, design patterns. Scope-specific requests (refactor, design, mobile, fullstack, review) are handled by the corresponding `/devteam:<scope>` command; for everything else — new project, bug fix, security patch, inherited/legacy code, or general maintenance — the architect handles the request with its own analysis-first behavior.

---

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.
4. After the user approves the plan, the spawned agent **MUST** present the Execution Strategy Gate (worktree, new branch, current branch) before executing any step — this is enforced inside the agent.

Task: $ARGUMENTS

---

## Post-execution — Present plan to user

**Trigger:** runs automatically after the `software-architect` finishes executing the approved plan. Do NOT run during the planning phase. Do NOT ask the user for confirmation.

Present the architect's output to the user in the main context:

```
## Architecture Analysis Complete

### Documents produced
[list of files created/modified]

### Summary
[1-2 sentences: key decisions and overall direction]

### Agents spawned
[list of specialized agents that were spawned for implementation, if any]

### Next steps
Run `/devteam:review` for code review and QA handoff, or run `/devteam:qa` for standalone QA validation.
```
