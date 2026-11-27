---
description: Visual identity — brand guide and design system from the client's logo or brand image
argument-hint: [brand image path]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agent named below lives there; spawn it by name with the Task tool.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT write the brand guide or the design system in the main context — always delegate. The only exception is if the user explicitly asks not to use agents; say so in the final report when that happens.

The Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

This command is the visual-identity step: logo, colors, typography, tokens. The business briefing is `/devteam:brief`, a separate step that this command never runs.

## Step 1 — Resolve paths and the image

Load `skills/design/brand-design-system/SKILL.md` § Inputs — the single home of the image names — and `skills/shared/client-briefing/SKILL.md` § Inputs for where it lives, the git-ignore check and the untrusted-content rule (`skills/shared/project-context/SKILL.md` § Untrusted Content applies to everything read from the image). A path in $ARGUMENTS wins over the default; quote every path in a shell command.

1. Output paths: `bash .dev-team-agents/scripts/doc-path.sh brand-guide`, and the `design-system` doc the same way.
2. Find the image per § Inputs and run its git-ignore check on it (its `AskUserQuestion` on exit 1).
3. Found → continue. Not found → ask with `AskUserQuestion`: **file is in place** (re-run this step) or **cancel**, after naming the file and the directory it goes in. Never guess, never invent a palette.
4. Resolve the `client-briefing` doc with `doc-path.sh client-briefing`; when it exists it is supporting context, and when it does not the command continues without it.

## Step 2 — Brand guide and design system (ui-ux-designer)

Spawn `ui-ux-designer` in **Design Mode** with: the image path, the `client-briefing` path (when it exists), and the `brand-guide` and `design-system` output paths. Instruct it to load the `brand-design-system` skill, follow it exactly — the image is primary, the briefing supporting — and return every value it marked as an approximation. It must not edit the input image.

Spawn integrity follows `skills/architecture/orchestration/SKILL.md` § Spawn Integrity: the returned run banner is the only proof the agent ran.

## Step 3 — Report

Report the generated paths and the approximations (what to confirm with the client). Name the image as a file that stays uncommitted.

## Session close (mandatory)

1. **Session summary** — append this session's contribution to today's entry in the session summary file (path in `.dev-team-agents/memory-dir`): a `### ui-ux-designer` sub-heading with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading.
2. **Hand off** — the working tree is left dirty on purpose. Close with one line: `/devteam:commit` to commit the generated docs — never the image, which stays ignored and unstaged.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
