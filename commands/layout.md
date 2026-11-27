---
description: Three flow-only layout proposals from a reference folder, for client approval
argument-hint: <reference folder path> [--publish]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agent named below lives there; spawn it by name with the Task tool.

---

## 0. MANDATORY input gate — check this FIRST

The command needs one **reference folder** (briefing files, visual references, logos, photos) from $ARGUMENTS. The optional flag `--publish` is the user's explicit request to publish the result as an Artifact in Step 3; without it nothing leaves the machine. Every other word is the folder path.

- **No path, a path that is not a directory, or an empty folder** → STOP. Spawn nothing. Respond in the user's language from `preferences.json` naming what is missing, and show usage:

  ```
  /devteam:layout <reference folder> [--publish]
  ```

- **Resolved** → quote the path in every shell command, list the files and continue.

This command proposes layouts only: no site code and no implemented motion. `/devteam:design-system` and `/devteam:relayout` come after the client approves a direction.

## Step 1 — Resolve

Load `skills/design/layout-flow-proposals/SKILL.md` § Inputs; its git-ignore and untrusted-content rules apply to the folder.

1. Output: `bash .dev-team-agents/scripts/doc-path.sh layout-proposals`. The HTML page is its sibling, same name with `.html`.
2. **Git-ignore first.** Run the check of `client-briefing` § Inputs on the glob `layout-proposals*.html` before anything is moved or written: it must be ignored (ask once, then write that one line) and is never staged or committed. A page already tracked by git is reported as needing `git rm --cached`, never moved by a plain `mv`.
3. **Versions, never a question.** When the doc already exists, move the current `.md` and `.html` pair to `layout-proposals-v<N>.md` / `.html`, N being the next free number, then write the new run at the original names. Nothing is overwritten or deleted, and an archived doc keeps its Approval section. Mark each archived doc with the historical banner of `skills/shared/docs-sync/SKILL.md` § Document Lifecycle, pointing at the current doc.
4. **Project context, automatically.** Resolve each of these with `doc-path.sh` and pass the ones that exist to the designer as supporting context: `client-briefing`, `brand-guide`, `design-system`, `design-system-full`, `design-tokens`, `prd`, `glossary`. The reference folder and the user's words still win over them (skill § Source Hierarchy). An empty output, or a path with no file, means the doc is absent. Note which were used and which did not exist.
5. Run the same git-ignore check on the reference folder. Never stage or commit its files.

## Step 2 — Proposals (ui-ux-designer)

**MANDATORY:** use the Task tool; do not write the proposals in the main context unless the user explicitly asks not to use agents, and say so in the report. Spawn `ui-ux-designer` in **Design Mode** with: the folder path (never the flag), the output paths and the project context docs found. Tell it not to publish anything: Step 3 belongs to this command. Before spawning, output exactly one line, in the user's language, saying that this command gives its best results with the session on the most capable model at high effort, then continue; never change the model or effort yourself. Instruct it to load the `layout-flow-proposals` skill, follow it exactly, write the `layout-proposals` doc and the HTML page — each direction with its full desktop flow and its full mobile flow, each asset embedded once — and return the assumptions, the unreachable sources and the site type. It must not edit the folder.

The spawn prompt MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

Spawn integrity follows `skills/architecture/orchestration/SKILL.md` § Spawn Integrity: the returned run banner is the only proof the agent ran.

## Step 3 — Publish for the client

The default is local: the HTML file stays on the machine. `--publish` in $ARGUMENTS is the user's own request to publish and asks nothing more. The page embeds the client's logos and photos, so after a publish the report in Step 5 says they went to the Artifact service.

- `--publish` is present and the `Artifact` tool exists → measure the HTML file size first. Within 16MB: load its `artifact-design` guidance, publish the page as a private Artifact and write the link into the doc's Page section. Over 16MB: have the designer split it into `layout-proposals-<direction>.html` pages plus an index (names the git-ignore glob already matches, each page carrying the assets it uses, duplicated across pages), publish them through the tool's `files` map and say so.
- `--publish` absent → leave the file and report its path, mentioning that `--publish` publishes it as a private Artifact.
- `--publish` present but no `Artifact` tool (opencode, Codex) or a refused publish → leave the file, report its path and say why.

## Step 4 — Approval

Ask with `AskUserQuestion` after Step 3 completes: **Direction A**, **Direction B**, **Direction C** (labels from the doc's Directions section), or **Pending / changes needed**; a mix of named parts is chosen through the Other option. Record the answer and date in the doc's Approval section; changes go in as written by the user. Never record an approval the user did not give.

## Step 5 — Report

Report the doc path, the version archived (if any), the context docs used and missing, the page link or path, the assumptions to confirm with the client, and the approval status. After a publish, say that the client's assets went to the Artifact service, that the link is private to the account, and to open it once in a private window to see whether the client can reach it before sending it.

## Session close (mandatory)

1. **Session summary** — append this session's contribution to today's entry in the session summary file (path in `.dev-team-agents/memory-dir`): a `### ui-ux-designer` sub-heading with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading.
2. **Hand off** — the working tree is left dirty on purpose. Close with one line: `/devteam:commit` for the doc only — the page embeds the client's assets and stays ignored and unstaged — then `/devteam:design-system` or `/devteam:brand` once a direction is approved (`/devteam:relayout` only for an existing site).

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
