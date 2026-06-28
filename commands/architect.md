Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architecture decisions, system design, trade-offs, ADR authoring, API contracts, design patterns. The agent will automatically detect the appropriate workflow from the user's request (new project, bug fix, refactor, security patch, design, mobile, fullstack, review, inherited project) and follow it. Falls back to the maintenance workflow when no clear signal is found.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.claude/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS

---

## Post-execution — Automatic review pass

**Trigger:** runs automatically after the `software-architect` finishes executing the approved plan. Do NOT run during the planning phase. Do NOT ask the user for confirmation.

Spawn the following agents **in parallel** using the Task tool:

- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md`
  Scope: review all files changed in this session (`git diff` against the base branch). Focus on: structural correctness of the architectural decisions, missing contracts or interfaces, coupling violations, security surface introduced.

- `qa-specialist` at `.claude/agents/dev-team/qa-specialist.md`
  Scope: validate that the architectural output is testable. Check: acceptance criteria are defined, testable boundaries are clear, no obvious coverage gaps, edge cases considered.

Both agents run independently and produce their own reports. Do not wait for one to finish before spawning the other.

**After both complete**, synthesize their findings into a single block and present it to the user:

```
## Post-architecture review

### Code review findings
[code-reviewer output — critical findings only, bullets]

### QA findings
[qa-specialist output — gaps or risks, bullets]

### Summary
[1–2 sentences: overall verdict and recommended next step]
```

If both agents report no findings, output exactly:

```
Post-architecture review: no issues found.
```
