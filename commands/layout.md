---
description: Three flow-only layout proposals from a reference folder, for client approval
argument-hint: <reference folder path>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agent named below lives there; spawn it by name with the Task tool.

---

## 0. MANDATORY input gate — check this FIRST

The command needs one **reference folder** (briefing files, visual references, logos, photos) from $ARGUMENTS.

- **No path, a path that is not a directory, or an empty folder** → STOP. Spawn nothing. Respond in the user's language from `preferences.json` naming what is missing, and show usage:

  ```
  /devteam:layout <reference folder>
  ```

- **Resolved** → quote the path in every shell command, list the files and continue.

This command proposes layouts only: no site code and no implemented motion. `/devteam:design-system` and `/devteam:relayout` come after the client approves a direction.

## Step 1 — Resolve

Load `skills/design/layout-flow-proposals/SKILL.md` § Inputs; its git-ignore and untrusted-content rules apply to the folder.

1. Output: `bash .dev-team-agents/scripts/doc-path.sh layout-proposals`. The HTML page is its sibling, same name with `.html`.
2. Existing output → ask with `AskUserQuestion`: **overwrite** or **cancel**. When its Approval section is not `Pending`, say so in the question: overwriting discards a recorded approval.
3. Run the folder's git-ignore check. Never stage or commit its files. The HTML page embeds the client's logos and photos, so it gets the same check: it must be git-ignored (ask per `client-briefing` § Inputs) and is never staged or committed.

## Step 2 — Proposals (ui-ux-designer)

**MANDATORY:** use the Task tool; do not write the proposals in the main context unless the user explicitly asks not to use agents, and say so in the report. Spawn `ui-ux-designer` in **Design Mode** with: the folder path, the output paths and $ARGUMENTS. Instruct it to load the `layout-flow-proposals` skill, follow it exactly, write the `layout-proposals` doc and the HTML page, and return the assumptions, the unreachable sources and the site type. It must not edit the folder.

The spawn prompt MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

Spawn integrity follows `skills/architecture/orchestration/SKILL.md` § Spawn Integrity: the returned run banner is the only proof the agent ran.

## Step 3 — Publish for the client

The page embeds the client's logos and photos, and publishing sends it to an external service. Ask with `AskUserQuestion`: **publish as a private Artifact**, **keep the HTML file only**, or **cancel the publish**.

- Artifact chosen, the `Artifact` tool exists and the publish succeeds → load its `artifact-design` guidance, publish the HTML page (private by default), then write the link into the doc's Page section.
- No `Artifact` tool (opencode, Codex), a refused or oversized publish, or **file only** → leave the file, report its path and say why.

## Step 4 — Approval

Ask with `AskUserQuestion` after Step 3 completes: **Direction A**, **Direction B**, **Direction C** (labels from the doc's Directions section), or **Pending / changes needed**; a mix of named parts is chosen through the Other option. Record the answer and date in the doc's Approval section; changes go in as written by the user. Never record an approval the user did not give.

## Step 5 — Report

Report the doc path, the page link or path, the assumptions to confirm with the client, and the approval status.

## Session close (mandatory)

1. **Session summary** — append this session's contribution to today's entry in the session summary file (path in `.dev-team-agents/memory-dir`): a `### ui-ux-designer` sub-heading with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading.
2. **Hand off** — the working tree is left dirty on purpose. Close with one line: `/devteam:commit` for the doc only — the page embeds the client's assets and stays ignored and unstaged — then `/devteam:design-system` or `/devteam:brand` once a direction is approved (`/devteam:relayout` only for an existing site).

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
