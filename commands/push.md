---
description: Push the current branch, with a CI-aware quiz if Actions is configured
argument-hint: [all] [skip-commit|abort-on-dirty]
model: haiku
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Step -1 — Uncommitted changes pre-flight

Load `skills/shared/git-workflow/SKILL.md` and run its **Dirty-Tree Pre-flight** before any other action: with uncommitted changes, the `/devteam:commit` flow runs automatically (no "commit now?" question), then this command continues to Step 0 and pushes. `skip-commit` and `abort-on-dirty` opt out.

---

## Step 0 — Push, with CI/CD-aware quiz

Load `skills/shared/github-actions/SKILL.md` and follow it in full: it checks its preconditions (gh authenticated + `.github/workflows/*` present, using the cached `ci_cd_detected` preference), then — only if both hold — asks the quiz in its Flow § 0 (watch CI vs. push-only vs. other). If the preconditions fail, push normally without a quiz.

**No Claude attribution**: nothing pushed by this command may reference Claude or AI tooling in any commit message.

---

## Step 1 — Session summary (push is a finalization signal)

After the push completes (regardless of which quiz option was chosen), apply the Session Summary Rule from `CLAUDE.md` right now rather than waiting for session end: check `git status --porcelain`, `git diff --cached`, and today's commits (`git log --since="00:00"`) — the same detection `scripts/hooks/lib/session-summary-detect.sh` uses. If there is a signal and `.dev-team-agents/user-data/session-summary.md` has no entry for today, write one (Done/Decisions/Next, in English) before finishing the command.

---

$ARGUMENTS options:
- `all` / `--all` — stage all changes before committing (forwarded to the `/devteam:commit` flow when the pre-flight runs it)
- `commit` — accepted for compatibility; committing uncommitted changes first is now the default (Dirty-Tree Pre-flight)
- `skip-commit` — when uncommitted changes exist, push without committing them first
- `abort-on-dirty` — when uncommitted changes exist, stop instead of committing
