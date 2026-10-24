# Docs Layout Migration — `development` → `gated`

Moves an existing project's docs into the gated layout (`../SKILL.md` § Doc Layout). **Opt-in and manual:**
it runs only when the user asks for it — never from a hook, an update, `devteam sync` or a health check
on its own. `/devteam:health-check` Category 14 mentions it once for a `development` project and stops there.

The work is done by one shipped script, `.dev-team-agents/scripts/docs-migrate.py`. This page is the
procedure around it; never re-implement a step by hand.

| Guarantee | How |
|---|---|
| Nothing is deleted | Every path is moved with `git mv`; merged originals stay where they are, marked historical (`skills/shared/docs-sync/SKILL.md` § Document Lifecycle) |
| Nothing is overwritten | A target that already exists is a **conflict**: the source is moved to `<write-root>/legacy/migration-<YYYY-MM-DD>/` and the target is left untouched |
| Paths come from the map | Every move is a key whose `development` and `gated` paths differ in `.dev-team-agents/scripts/lib/doc-layouts.json` — no path is typed here |
| Reversible until committed | It starts from a clean tree, rewrites only files git tracks, and commits nothing; `git status` / `git diff -M` show every change |
| Never leaves the checkout | A tracked symlink in the docs write root, `CLAUDE.md` or `AGENTS.md` refuses the run; no symlink is followed and no path outside the project root is read or written |

## Step 1 — Preconditions

The script checks them itself and prints `REFUSE <reason>` (exit 1) at the first one that fails: a bound
project, layout `development`, a git work tree run from its top level, a clean tree, no tracked symlink in
scope. Only python3 is checked here:

```bash
command -v python3 >/dev/null && echo "PYTHON3: OK" || echo "PYTHON3: MISSING"
```

| Result | Stop with |
|---|---|
| `PYTHON3: MISSING` | Hand over: install python3 |
| `REFUSE not a bound project` | The layout key lives in `project.json` — hand over `devteam bind` |
| `REFUSE … already 'gated'` | Nothing to migrate |
| `REFUSE not a git work tree` | The migration needs git to move files |
| `REFUSE … dirty` | Commit or stash first (`/devteam:commit`). A move on a dirty tree mixes the user's edits into the migration diff |
| `REFUSE … symlink …` | Show the line; the user replaces the symlink with a regular file and commits. Never work around it |

## Step 2 — Dry run

```bash
python3 -I .dev-team-agents/scripts/docs-migrate.py plan
```

Read-only. It prints:

| Line | Meaning |
|---|---|
| `MOVE <key> <src> -> <dst>` | `git mv`, one per tracked file (the `adr` folder moves file by file and keeps every ADR file name) |
| `MERGE <key> <src> -> <dst>` | `backlog-readme`, `dod` and `backlog-index` are merged into the gated `backlog-index` doc (`docs/backlog.md`) |
| `CONFLICT <key> <src> -> <dst> (source quarantined to <q>)` | The target exists: the source goes to quarantine, the target is not touched. A merge whose target exists is a conflict for all three sources |
| `LINKS <file>` (or `<old> -> <new>`) | A tracked Markdown file under the docs root, or a tracked `CLAUDE.md` / `AGENTS.md`, whose links or root-anchored paths will be rewritten |
| `UNTRACKED <path>` | Not tracked by git (ignored): left in place and never rewritten — the user updates it by hand |
| `SKIP <path> (<reason>)` | Not rewritten: larger than 1 MiB, not UTF-8, or not a regular file |
| `LAYOUT development -> gated` / `SUMMARY …` | The layout it records last, and the counts |

Keys whose path is the same in both layouts (`specs`, `wiki`, `design-system`, `overview`, `sprints`,
`project`, `infrastructure`) do not move.

## Step 3 — Consent

Show the dry-run lines as a table, then ask with `AskUserQuestion`:

- **Migrate as listed** (recommended) — description: moves N files, merges the backlog index, quarantines C conflicts, rewrites links in L files, then records `docs_layout: gated`; nothing is committed
- **Not now** — nothing changes; Category 14 keeps reporting the `development` layout as OK

## Step 4 — Apply

```bash
python3 -I .dev-team-agents/scripts/docs-migrate.py apply     # must end with: APPLIED
```

`apply` recomputes the plan on the tree as it is now — it never trusts the dry run — and refuses on the
same checks. It prints its plan and changes the tree in the same run, so compare its lines with the approved ones afterwards; on any difference, show it and have the user review `git status` / `git diff` before anything is committed (nothing is committed, and git undoes it). What it
does, in order:

1. `git mv` every `MOVE` source to its gated path, and every `CONFLICT` source to its quarantine path
2. Rewrites links: a relative Markdown link is resolved against the file's **old** location and rewritten relative to its new one; a root-anchored mention (`docs/development/database.md`, `docs/development/adrs/`) becomes the gated path. A link to a quarantined source points at its quarantined copy, so it keeps resolving
3. Writes `docs/backlog.md` in the form of `skills/shared/backlog-template/SKILL.md` § Gated Layout: `## Definition of Done` (from `dod`), `## Definition of Ready` (the doc-flow pointer plus `### Project additions`), `## Sprints` (from `backlog-index`), `## Backlog Notes` (from `backlog-readme`). Every line of each source is copied except its H1; headings are demoted one level and links rewritten for the new location
4. Adds the Document Lifecycle historical banner under the H1 of each merged original, which stays at its path
5. Records `docs_layout: gated` in `.dev-team-agents/project.json`, keeping every other key

A `REFUSE` during `apply` after a move means it stopped part-way: show `git status` and stop.

## Step 5 — Complete the layout

1. Ask for `HAS_UI` / `USES_LLM` with `AskUserQuestion` when `docs/project.md` lacks either line, and add it under `## Type & Config`
2. Confirm `bash .dev-team-agents/scripts/doc-path.sh --layout` prints `gated`
3. Create what the gated layout still lacks (`process`, `source`, `prd`, …) per `skills/shared/docs-templates/SKILL.md` § Gated Skeleton — creates only, never over a moved file
4. Run `/devteam:health-check` Category 14 and `bash .dev-team-agents/scripts/index-lint.sh` to confirm the new paths resolve

## Step 6 — Report

List moved, merged, quarantined and created paths, the files whose links changed, and every `UNTRACKED`
or `SKIP` path the user still has to update by hand. Say that nothing is committed and offer
`/devteam:commit`. Quarantined sources are the user's to merge into their gated target by hand; never
delete the quarantine folder.
