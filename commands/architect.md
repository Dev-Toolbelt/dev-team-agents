Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

## Scope Guard

Scope-specific requests (refactor, design, mobile, fullstack, review) are handled by the corresponding `/devteam:<scope>` command. If $ARGUMENTS matches one of these, tell the user to use the dedicated command instead. This command is for everything else — new project, bug fix, security patch, inherited/legacy code, or general maintenance.

---

## Phase 1 — Architecture Planning (Read-Only)

**MANDATORY:** Use the Task tool to spawn the software-architect. Do NOT handle this in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Spawn `software-architect` at `.claude/agents/dev-team/software-architect.md`:

Prompt:
> "Analyze the following using the project context:
>
> $ARGUMENTS
>
> Produce architecture documents in `docs/development/`:
> - `architecture.md` — system design, layers, component boundaries, integration patterns
> - `tech-stack.md` — chosen technologies with rationale, what was rejected and why
> - `code-standards.md` — patterns, naming conventions, linting rules specific to the project's stack
> - `database.md` — if schema or data decisions are needed (otherwise skip)
> - `api-contracts.md` — if API design decisions are needed (otherwise skip)
> - ADRs for every significant decision in `docs/development/adrs/` — use `skills/shared/adr/SKILL.md`
>
> This is a **read-only planning phase**. Do NOT modify any code files. Do NOT spawn implementation agents. Your deliverables are documentation only.
>
> After writing all docs, present a summary of what was produced and the key decisions made."

After the Task completes, present the architect's output to the user:

```
## Architecture Planning Complete

### Documents produced
[list of files created/modified]

### Summary
[1-2 sentences: key decisions and overall direction]

### Next steps
Review the architecture documents above. If implementation is needed, let me know which scope to work on.
```

▶ **Await explicit user approval** before proceeding to Phase 2.

---

## Phase 2 — Implementation (Optional, After Approval)

Ask the user which agents to spawn:

> "The architecture is documented. Which areas need implementation?"

Offer multi-select via `AskUserQuestion` with options based on the project context and $ARGUMENTS. Use these standard options:

| Option | Agent spawned |
|--------|---------------|
| Backend | `backend-developer` at `.claude/agents/dev-team/backend-developer.md` |
| Frontend | `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` |
| Mobile | `mobile-developer` at `.claude/agents/dev-team/mobile-developer.md` |
| Database | `database-specialist` at `.claude/agents/dev-team/database-specialist.md` |
| DevOps | `devops-specialist` at `.claude/agents/dev-team/devops-specialist.md` |
| Security | `security-specialist` at `.claude/agents/dev-team/security-specialist.md` |
| Do not implement | Proceed to summary |

**If the user selects agents that depend on each other (e.g. Database before Backend), spawn them sequentially. Otherwise, spawn all selected agents in parallel.**

For each spawned agent, include in the Task prompt:
- The task description from the architecture scope
- Reference to the architecture docs: `docs/development/architecture.md`, `docs/development/tech-stack.md`, `docs/development/code-standards.md`
- Any relevant ADRs from `docs/development/adrs/`
- "Read the architecture documents before implementing. Load `skills/shared/model-identity/SKILL.md` and announce your model at the start."

After all implementation agents complete, present the consolidated summary.

---

## Post-execution — Consolidated Summary

```
## Implementation Complete

### Agents spawned
[list of agents and what they did]

### Documents produced / modified
[list]

### Next steps
Run `/devteam:review` for code review and QA handoff, or run `/devteam:qa` for standalone QA validation.
```
