---
model: haiku
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Step -1 — Uncommitted changes pre-flight

Before any other action, run:

```bash
git diff --cached --name-only   # staged files
git diff --name-only            # unstaged modified files
```

If either command returns output (there are staged or unstaged changes):

1. Inform the user: "There are uncommitted changes in the working tree."
2. Ask (via `AskUserQuestion`):

   > "There are uncommitted changes. What would you like to do before pushing?"
   - **Commit them now** — run the commit routine below, then continue to Step 0
   - **Skip and continue** — proceed to Step 0 without committing
   - **Abort** — stop the command entirely

If the user chooses **Commit them now**, execute the following routine inline (same logic as `devteam:commit`):

### Commit routine

1. Load `skills/shared/conventional-commits/SKILL.md`.
2. Read the target project's `CLAUDE.md` (root or `.claude/CLAUDE.md`) to detect the commit pattern. If a project-specific pattern is documented, follow it; otherwise use Conventional Commits.
3. Run `git status --short`, `git diff --cached --stat`, and `git diff --stat` to identify staged vs. unstaged files. Do NOT auto-stage — only commit what is already staged, unless `$ARGUMENTS` contains `all` or `--all` (then run `git add -A` first).
4. Group staged files into logical commits by layer (data/schema → domain → persistence → infrastructure → application → interface → tests → config/CI → docs). Skip empty layers. Bundle single-context changes into one commit.
5. For each group, write a commit message following the detected pattern. Never add `Co-Authored-By:`, AI attribution, or any non-user authorship footer.
6. Before executing each commit, run lint/type-check/tests if no pre-commit hook is already configured. If a gate fails, ask with `AskUserQuestion` (single-select): **Fix and re-stage** (recommended), **Commit anyway**, or **Abort**.
7. Present the proposed commit plan to the user and execute the commits unless the user says to stop.

Once the commit routine completes successfully, continue to Step 0.

If there are **no** staged or unstaged changes, skip directly to Step 0.

---

## Step 0 — Push, with CI/CD-aware quiz

Load `skills/shared/github-actions/SKILL.md` and follow it in full: it checks its preconditions (gh authenticated + `.github/workflows/*` present, using the cached `ci_cd_detected` preference), then — only if both hold — asks the quiz in its Flow § 0 (watch CI vs. push-only vs. other). If the preconditions fail, push normally without a quiz.

**No Claude attribution**: nothing pushed by this command may reference Claude or AI tooling in any commit message.

---

## Step 1 — Session summary (push is a finalization signal)

After the push completes (regardless of which quiz option was chosen), apply the Session Summary Rule from `CLAUDE.md` right now rather than waiting for session end: check `git status --porcelain`, `git diff --cached`, and today's commits (`git log --since="00:00"`) — the same detection `scripts/hooks/lib/session-summary-detect.sh` uses. If there is a signal and `.dev-team-agents/user-data/session-summary.md` has no entry for today, write one (Done/Decisions/Next, in English) before finishing the command.

---

$ARGUMENTS options:
- `all` / `--all` — stage all changes before committing (only relevant if the commit routine runs)
