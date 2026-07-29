Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

## Scope Guard

Scope-specific requests (refactor, design, mobile, fullstack, review) are handled by the corresponding `/devteam:<scope>` command. If $ARGUMENTS matches one of these, tell the user to use the dedicated command instead. This command is for everything else — new project, bug fix, security patch, inherited/legacy code, or general maintenance.

---

## Orchestration

**MANDATORY:** Use the Task tool to spawn the `software-architect` agent. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architecture decisions, system design, trade-offs, ADR authoring, API contracts, design patterns, and orchestration of implementation agents.

**Task prompt:**
> $ARGUMENTS
>
> You are the orchestrator. Follow your full workflow including:
> 1. Architecture planning and documentation in `docs/development/`
> 2. User review gate — wait for explicit approval before proceeding to implementation
> 3. Execution Strategy Gate — present worktree/branch options after plan approval
> 4. Delegate implementation to specialized agents via the Task tool using your "## EXECUTION — Delegate to Model-Aware Subagents" section
> 5. Present a consolidated summary after all agents complete
>
> Do NOT execute implementation tasks in your own context — always spawn subagents for implementation work.

---

## Post-execution — Consolidated Summary

After the software-architect completes its full workflow (including any spawned implementation agents), present the consolidated summary to the user in the main context:

```
## Architecture & Implementation Complete

### Documents produced
[list of files created/modified]

### Agents spawned
[list of agents and what they did]

### Next steps
Run `/devteam:review` for code review and QA handoff, or run `/devteam:qa` for standalone QA validation.
```
