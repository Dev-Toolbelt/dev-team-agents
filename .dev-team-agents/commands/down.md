---
description: Stop the local environment /devteam:up started for this checkout
argument-hint: [service ...]
---

Load `skills/shared/current-context/SKILL.md` — only this branch/worktree checkout's environment is in scope. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt. Read `.dev-team-agents/resolved/preferences.json` → `language` (default `en`) and use it for every message and option label.

**This command spawns no agent** — it stops processes the main context started or can see, and asks before stopping any of them.

> No Plan Gate: the confirmation in Step 2 lists every service and the exact stop command, and is the guardrail.
> Runs on the current checkout as it is: the worktree decision cascade does not apply, and no worktree or branch is created. On a provider where this command runs as an agent (opencode), that agent's Plan Mode does not apply either — the Step 2 confirmation replaces it.

Load `skills/devops/local-environment/SKILL.md`. Every step below points into it; do not restate its rules.

---

## Step 1 — Identify what is running

Follow § Stop, steps 1–2. `$ARGUMENTS` may name a subset of services; stop only those. Nothing running for this checkout → say so and end.

## Step 2 — Confirm

Ask the confirmation in § Stop, step 3. A request to also remove volumes, images or data is a separate, explicit confirmation (§ Stop, step 5) — never folded into this one.

## Step 3 — Stop and report

Follow § Stop, steps 4 and 6, with step 5 in force throughout: what stopped, how, and anything left running with the reason.

Arguments: $ARGUMENTS
