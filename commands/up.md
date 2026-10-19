---
description: Start the project's local environment as its docs describe (Docker, native, …)
argument-hint: [docker|local] [service ...]
---

Load `skills/shared/current-context/SKILL.md` — the environment belongs to the active branch/worktree checkout. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt. Read `.dev-team-agents/resolved/preferences.json` → `language` (default `en`) and use it for every message and option label.

**This command spawns no agent.** It starts long-lived processes, may need the in-app browser's `preview_start`, and asks the user before running anything — a subagent can do none of that and would hand back processes nobody tracks. Work in the main context.

> No Plan Gate: the confirmation in Step 3 shows the exact commands before anything runs, and is the guardrail.
> Runs on the current checkout as it is: the worktree decision cascade does not apply, and no worktree or branch is created. On a provider where this command runs as an agent (opencode), that agent's Plan Mode does not apply either — the Step 3 confirmation replaces it.

Load `skills/devops/local-environment/SKILL.md`. Every step below points into it; do not restate its rules.

---

## Step 1 — Discover how the project runs

Follow § Discovery Order. `$ARGUMENTS` may name a mode (`docker`, `local` — as that section defines them) and/or a subset of services, validated there; when it names a mode, use it instead of asking. A mode the docs do not describe → say so and list the documented ones.

## Step 2 — Reuse, then pre-flight

Run § Reuse Before Starting for the requested services. Every one already running for this checkout → skip to Step 5 and report them as reused. Otherwise run § Pre-flight for the missing ones only.

## Step 3 — Confirm

Ask the confirmation in § Start, step 1. On anything other than run → adapt or stop; nothing has been executed yet.

## Step 4 — Start and health-check

Follow § Start, steps 2–4. A failed health check ends the command with the redacted log excerpt and the command to rerun.

## Step 5 — Report

Print the § Report table and the `/devteam:down` line. If the command was inferred, ask the documentation question from § Report.

If a web UI is up, offer to open it with the **Visual Check Gate**'s options and Browser Choice from the interaction-patterns skill loaded above. Here it is an open-the-running-app prompt: no screen changed, so its "Ask it when" trigger does not apply, and the environment was already reused or started in Steps 2–4 — the gate only opens the page, with no second start.

Arguments: $ARGUMENTS
