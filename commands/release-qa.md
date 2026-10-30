---
description: End-to-end QA of every feature in a release — local, staging, or production
argument-hint: [local|staging|production] [<branch> ... | <release ref>]
---

Load `skills/shared/current-context/SKILL.md`; this command builds its own release scope, so the active branch is only the default base for a local run. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/shared/release-qa/SKILL.md` — it is the procedure, steps 1 to 6. Load `skills/architecture/orchestration/SKILL.md` § Spawn Integrity and `skills/shared/credentials/SKILL.md`.

**Agent base path:** `.claude/agents/dev-team/` — spawn `qa-specialist` by name with the Task tool.

**MANDATORY:** the main conversation is the orchestrator. It owns the integration worktree, every merge, the manifest, every question and the sign-in; it spawns exactly one `qa-specialist` for the validation (release-qa Step 5). Do NOT validate in the main context. The only exception is if the user explicitly asks not to use agents.

The spawn prompt MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

## Steps

1. Parse $ARGUMENTS into environment, features and credentials group; ask for whatever is missing (release-qa § Inputs).
2. Run release-qa Steps 1 to 4 in order. Each stop condition there ends the command with its reason.
3. Spawn the `qa-specialist` (release-qa Step 5).
4. Write the report (release-qa Step 6). Once a session was created, `devteam qa auth clean --json` runs on every exit, including a stop (release-qa Step 4).

## After the agent returns

If UI was validated, ask the **Visual Check Gate** from the interaction-patterns skill loaded above, built from the agent's **Screens to check** list.

---

**PLAN GATE — mandatory:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` — environment, features, the branches a local run merges — and wait for explicit user approval before creating a worktree, merging, or signing in.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
