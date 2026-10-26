---
description: Architecture decisions, ADRs, and trade-offs
argument-hint: <decision or question>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Scope Guard

Scope-specific requests (refactor, design, mobile, fullstack, review) are handled by the corresponding `/devteam:<scope>` command. If $ARGUMENTS matches one of these, tell the user to use the dedicated command instead. This command is for everything else — new project, bug fix, security patch, inherited/legacy code, or general maintenance.

---

## Orchestration

**MANDATORY:** Use the Task tool to spawn the `software-architect` agent. Do NOT handle this task in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

- `software-architect` at `.claude/agents/dev-team/software-architect.md` — architecture decisions, system design, trade-offs, ADR authoring, API contracts, design patterns, and orchestration of implementation agents.

**Task prompt:**
> $ARGUMENTS
>
> Follow your full workflow: architecture planning and documentation in `docs/development/`, then delegation of the implementation to specialized agents. You cannot ask the user — return the plan approval and every other decision per `interaction-patterns` § Sub-agent Question Relay, and do not create a worktree or branch: the main conversation resolves them and continues you with `WORKTREE_PATH` and `BRANCH`. Every implementation spawn carries both, and no file is written outside `WORKTREE_PATH`. Do NOT execute implementation tasks in your own context.

**Sequence — the main conversation owns it:**
1. Spawn `software-architect`; relay its Open Decisions (§ Sub-agent Question Relay) until the plan is approved.
2. Answer the architect's strategy Open Decision by running the **Execution Strategy Gate** from `skills/architecture/orchestration/SKILL.md` yourself — asked once, never twice — or its Autonomous Sprint Protocol when the user asked for autonomous execution — create the worktree or branch, and write the session file.
3. Continue the same `software-architect` with `WORKTREE_PATH=<path>` and `BRANCH=<branch>` to delegate the implementation; keep relaying any decision it returns. Its report carries every spawned agent's run banner unchanged — those banners fill the summary below.

Under the Autonomous Sprint Protocol, execution decisions take the protocol's defaults and its review cycle runs from the main conversation; a plan approval or a product decision is still asked — the relay never answers for the user.

---

## Post-execution — Consolidated Summary

After the software-architect completes its full workflow (including any spawned implementation agents), present the consolidated summary to the user in the main context — the agents list is filled from returned run banners only (orchestration § Spawn Integrity, check 3):

```
## Architecture & Implementation Complete

### Documents produced
[list of files created/modified]

### Agents spawned
[list of agents and what they did]
```

Then run the **Review Next-Step Gate** from the interaction-patterns skill loaded above.
