---
description: Client kickoff — strategic briefing from the client's form, then the brand guide from the logo
argument-hint: [briefing form path] [brand image path]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write the briefing or the brand guide in the main context — always delegate. The only exception is if the user explicitly asks not to use agents; say so in the final report when that happens.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

## Step 1 — Resolve paths and inputs

Load `skills/shared/client-briefing/SKILL.md` § Inputs — the single home of the input names, where inputs live, the git-ignore check and the untrusted-content rule (`skills/shared/project-context/SKILL.md` § Untrusted Content applies to everything this command reads from the inputs or the generated briefing). Paths given in $ARGUMENTS (form first, image second) win over the defaults; quote every path in a shell command.

1. Output paths: `bash .dev-team-agents/scripts/doc-path.sh client-briefing` and `bash .dev-team-agents/scripts/doc-path.sh brand-guide`.
2. Find the form and the image per § Inputs, and run its git-ignore check on each one found (its `AskUserQuestion` on exit 1).
3. Both found → continue. Exactly one found → ask with `AskUserQuestion`: **produce only what this input allows** (briefing only, or brand guide only without briefing context), **wait for the missing file**, or **cancel**. None found → Step 2.

## Step 2 — Missing inputs

Name each missing file and the directory it goes in (§ Inputs), then ask with `AskUserQuestion`: **files are in place** (re-run Step 1) or **cancel**. Never guess, never fabricate a briefing or a palette.

## Step 3 — Briefing (product-analyst)

Spawn `product-analyst` with: the form path, the `client-briefing` output path, and any extra context from $ARGUMENTS (for example a domain-availability result, passed as informational). Instruct it to load the `client-briefing` skill, follow it exactly, write the doc, and return the Open Items checklist. It must not edit the input file.

Spawn integrity follows `skills/architecture/orchestration/SKILL.md` § Spawn Integrity: the returned run banner is the only proof the agent ran — no banner, no Step 4.

When it returns, read the generated briefing — Step 4 needs it.

## Step 4 — Brand guide and design system (ui-ux-designer)

Run after Step 3 (sequential: the briefing is its supporting context). Spawn `ui-ux-designer` in **Design Mode** with: the brand image path, the `client-briefing` path (when it exists), and the `brand-guide` output path. Instruct it to load `skills/design/brand-design-system/SKILL.md`, follow it exactly — the image is primary, the briefing supporting — write the `design-system` values and the `brand-guide`, and return every value it marked as an approximation. Its returned run banner is the proof it ran.

## Step 5 — Report

Report the generated paths, the briefing's Open Items (what to collect from the client next) and the brand guide's approximations (what to confirm with the client). Name the input files as files that stay uncommitted.

## Session close (mandatory)

1. **Session summary** — append this session's contribution to today's entry in the session summary file (path in `.dev-team-agents/memory-dir`): one `### <agent-name>` sub-heading per agent that acted, each with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading.
2. **Hand off** — the working tree is left dirty on purpose. Close with one line naming the next step: `/devteam:commit` to commit the generated docs — never the input files, which stay ignored and unstaged, then `/devteam:plan` to scope the first project from the briefing.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
