---
description: Run this session as the orchestrator — coordinate, relay and supervise the agents
argument-hint: [task to start with]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

This command does not spawn the orchestrator: it makes **this session** the orchestrator (ADR-0062). A spawned orchestrator could not ask the user, and only its last message would come back.

## Step 1 — Adopt the persona

Read the `orchestrator` agent file this provider installed — `.opencode/agents/orchestrator.md` on opencode, the `developer_instructions` of `.codex/agents/orchestrator.toml` on Codex, `orchestrator.md` in the dev-team agents directory on Claude Code — and follow it as your own operating rules for the rest of this session: its Session Guard, Foundational Rule, Route, Relay, Supervise and Report sections. Emit its run banner now. Every plan you present follows `skills/shared/plan-mode/SKILL.md`.

Output exactly one line saying the session now runs as the orchestrator, and how to make it the default: the `orchestrator_default` preference (Claude Code), the agent switcher (opencode), or this command again in each new session (Codex).

## Step 2 — Start

- `$ARGUMENTS` non-empty → treat it as the first request and route it per the agent's § Route.
- `$ARGUMENTS` empty → ask what to work on, and stop until the user answers.
