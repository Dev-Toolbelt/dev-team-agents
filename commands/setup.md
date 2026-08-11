---
description: Onboard this project into dev-team-agents (first run or refresh)
argument-hint: [notes about the project]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt. Setup writes to project-level files (`CLAUDE.md`, `docs/`) — confirm the branch is the one the user expects before any write, and treat every finite-answer question in this flow as a quiz.

---

## Step 1 — Detect setup mode

```bash
test -f docs/project.md && echo "REFRESH" || echo "FIRST_RUN"
```

| Result | Mode | Behavior |
|--------|------|----------|
| `FIRST_RUN` | Full onboarding | The project has never been onboarded — run the complete setup flow |
| `REFRESH` | Incremental update | The project is already onboarded — patch only what changed since `last-updated` |

Report the detected mode to the user before delegating, so they know whether existing configuration is at stake.

---

## Step 2 — Spawn the agent

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT run the setup flow in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

- `setup-assistant` at `.claude/agents/dev-team/setup-assistant.md` — the entry point for onboarding a project into the dev-team-agents ecosystem. Detects the stack, scans what already exists, configures `CLAUDE.md`, creates the `docs/` structure and the wiki, records user preferences, and optionally wires up an issue tracker. In `REFRESH` mode it patches only what drifted instead of re-asking answered questions.

Pass the detected mode (`FIRST_RUN` / `REFRESH`) and `$ARGUMENTS` to the agent as context.

---

## Step 3 — Coexistence guardrail

`dev-team-agents` is the base layer. Remind the spawned agent explicitly:

- Never overwrite an existing `CLAUDE.md`, `README.md`, `AGENTS.md`, or project config without explicit user consent — additive changes only.
- Any rule already present in the project takes precedence over dev-team-agents defaults.
- Never modify files inside `.dev-team-agents/` — that directory is replaced on every update.

---

**PLAN GATE — mandatory for the spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user. If the file does not exist yet, ask the user for their language first and create it.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before creating or modifying any file.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
