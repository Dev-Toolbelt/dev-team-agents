---
name: feature-learn
description: Automatic per-feature lessons-learned promotion at session close, scoped mirror of /learn.
---

# Feature Learn

Runs automatically at the end of a feature command's **Session close (mandatory)** phase — no user
confirmation, same footing as the mandatory review handoff, because it only writes local docs. It is
a scoped mirror of `/devteam:learn`'s mechanics (`commands/learn.md`), not a replacement: `/learn`
stays the manual, full-session pass; this fires every time a feature closes, so knowledge compounds
feature-to-feature instead of aging inside `session-summary.md` until someone remembers to run `/learn`.

## Scope Derivation

The canonical answer to "what did this session, branch or worktree touch". It is used here and by
`/devteam:learn --auto` (`commands/learn.md`). Resolve top-down and stop at the first match:

| # | Condition | Touched set |
|---|---|---|
| 1 | `.dev-team-agents/.worktree-session` reads `worktree=yes branch=<base>`, **or** the current branch is not the default branch (`git symbolic-ref refs/remotes/origin/HEAD`) | **Branch scope:** `git diff --name-only $(git merge-base <base> HEAD)...HEAD` (`<base>` = the session file's branch, else the default branch) + the working tree |
| 2 | On the default branch | **Session scope:** files of the commits since the `.dev-team-agents/.learn-last-run` hash when it is an ancestor of `HEAD` (`git merge-base --is-ancestor`), otherwise of today's commits (the rule in `scripts/hooks/lib/touched-paths.sh`) + the working tree |
| 3 | The set is empty | Nothing in scope — stop with the "Nothing to update" outcome |

"The working tree" = `git status --porcelain` paths: staged, unstaged and untracked, rename destinations only.
Commits and docs that touch none of the set's paths are out of scope. From the session summary, read only
the entries written since the scope began (row 1: the merge-base commit date; row 2: the marker or today).

## Scoped Evidence (this task only, not full session history)

- `git diff <base>...HEAD --stat` for this task's branch/worktree (scope per § Scope Derivation, row 1)
- The linked spec's `### Amendment Log` (if any) — see `skills/shared/spec-gate/SKILL.md`
- Any `[SPEC-DRIFT]`, `[ARCH-DEVIATION]`, or `[BLOCKER]` finding raised during this task's review
  handoff
- Any decision made during this task's execution that isn't yet reflected in `docs/development/*.md`,
  `docs/wiki/`, or an ADR

## Classify and Promote

Apply the same bucket table `/devteam:learn` Step 2 uses (Doc patch / Wiki entry / ADR candidate /
Session summary / Nothing to update) — do not restate it here, reference `commands/learn.md`. Spawn:

- `technical-writer` — only if at least one bucket has content; writes doc patches and wiki entries
  per `skills/shared/docs-sync/SKILL.md`
- `software-architect` — only if an ADR candidate was identified; follows `skills/shared/adr/SKILL.md`

## Anti-Dead-Log Rule (hard gate)

<HARD-GATE>
An Amendment Log entry, a `[SPEC-DRIFT]` finding, or any other non-obvious discovery from this task
resolves to exactly one of: a wiki entry, a doc patch, an ADR, or an explicit "not worth keeping"
call made out loud to the user. It never sits only in the spec file or the session summary once the
task closes — that is what turns the memory system into a dead log instead of compounding knowledge.
</HARD-GATE>

## Commit

Fold the promoted files into this task's own Session-close commit(s) (layered per
`conventional-commits`), or as one trailing `docs:` commit — never leave promoted docs uncommitted
and unmentioned in the hand-off message.

## Embedded Commit Capture

The learn pass `/devteam:commit` § Step 2.7 runs before grouping commits, via `/devteam:learn --embedded`.
It asks the user nothing, so the guards below stand in for the approval it skips. Canonical home for both sides.

**Session guard (caller).** Skip the pass when `.dev-team-agents/.learn-last-run` exists and its timestamp is
`>=` the newest mtime among the staged files and the session summary (path resolved through
`.dev-team-agents/memory-dir`). A missing marker, or a staged deletion, never skips.

**Learn side (`--embedded`)** — overrides `/devteam:learn` Steps 3–5:

| Rule | Detail |
|---|---|
| Flags | Implies `--auto` and `--no-commit`; scope per § Scope Derivation |
| Evidence | Adds `git diff --cached` hunks for in-scope files (first 300 lines per file) — the work about to be committed |
| No questions | Never calls `AskUserQuestion` nor tells a spawned agent to; anything that would need one becomes a returned suggestion |
| Reuse rules | No reuse-rule pass; candidates are returned as `/devteam:rule …` suggestions |
| ADRs | Written with status `Proposed`, listed in the suggestions for the user to accept |
| Output | Prints nothing — no plan, no "Nothing to capture", no summary. Still checks each spawned agent returned its run banner (`skills/architecture/orchestration/SKILL.md` § Spawn Integrity), without echoing it |
| Return | Only the written paths (`PATCHED` / `ADR created` lines) and the suggestions list |
| Marker | Never written by learn — the caller writes it after its commits |

**Commit side (caller):**

1. Before learn, record the staged paths, `T0=$(git write-tree)`, and the paths with unstaged edits (`git diff --name-only`).
2. Stage a returned path only when it resolves (`realpath`) inside the repo, is not a symlink, is not ignored
   (`git check-ignore -q`), had no unstaged edits before learn, and is under `docs/development/`, `docs/wiki/` or
   is `docs/project.md`.
3. After staging, `git diff --cached --name-only "$T0"` must list only paths staged in item 2, and
   `git diff --name-only` no path absent from item 1's list; anything else means an agent touched the index or a
   file already in the commit.
4. Any path refused by item 2 or flagged by item 3 → one `AskUserQuestion`: keep only the allowed learn docs
   (recommended), also stage the flagged paths, or drop every learn doc. A clean run asks nothing.
5. Secret scan over the learn-staged files before the pre-commit gate: `gitleaks protect --staged` when installed,
   otherwise grep for `AKIA[0-9A-Z]{16}`, `gh[pousr]_[A-Za-z0-9]{36}`, `xox[abpr]-`, `-----BEGIN [A-Z ]*PRIVATE KEY`,
   `(password|secret|token)\s*[:=]\s*\S{8,}`. A hit unstages that file and is reported in one line.
6. A pre-commit gate failure caused only by a learn doc is advisory: unstage that doc, say so, keep committing the work.
7. The commit plan lists learn files under **Added by learn**, with the suggestions after it.
8. No commit made (preview, abort, gate abort): `git restore --staged` the learn docs, leave them in the working
   tree, say so in one line, write no marker.
9. At least one commit made: write the marker in the format `/devteam:learn` § Step 5 item 4 defines, holding the
   branch tip after the commits and any worktree rebase/merge, **before** a worktree teardown, at the main checkout root
   (`ROOT=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)`, the form `commands/merge.md` uses).

## Nothing to Promote

If the scoped evidence yields no bucket hits, skip silently — no agent spawn, no commentary. Mirrors
`/devteam:learn`'s "Nothing to update" behavior so the gate never manufactures busywork on trivial
tasks.
