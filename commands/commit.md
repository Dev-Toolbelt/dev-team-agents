---
description: Group staged changes by layer and write commits
argument-hint: [all] [dry-run] [format: <style>]
model: haiku
---

Load the skill at `skills/shared/conventional-commits/SKILL.md` before doing anything.

Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Step 0 — Auto knowledge capture

Skip this step entirely if `$ARGUMENTS` contains `--skip-learn`, the user explicitly asked to skip it, or `auto_learn_before_commit` in `.dev-team-agents/user-data/preferences.json` is `false` (default: `true`).

**Session guard.** Before re-running the learn evidence gathering, check `.dev-team-agents/.learn-last-run` (format: `<unix-timestamp> <head-sha>`). Compare its `<head-sha>` against the current `git rev-parse HEAD`, and its timestamp against the mtime of `.dev-team-agents/user-data/session-summary.md`. If HEAD hasn't moved and the session summary hasn't changed since that run, skip straight to Step 1 of this command — nothing new exists to capture.

Otherwise, run `/devteam:learn` Steps 1–4 exactly, with one override: in Step 3, suppress the "Awaiting your approval before proceeding." line and proceed directly to spawning agents. Wait for all learn agents to finish; if they return "Nothing to capture", continue immediately.

---

## Step 0.5 — Worktree finalization quiz

Check `.dev-team-agents/.worktree-session`. If the file is absent, or reads `worktree=no ...`, skip this step entirely.

If it reads `worktree=yes branch=<b>`, resolve the post-commit action in this order:

1. If `$ARGUMENTS` contains `finalize`, `merge`, or `teardown`, set the action to **Commit + rebase + merge + teardown**
2. Else if `$ARGUMENTS` contains `rebase`, set the action to **Commit + rebase**
3. Else if `$ARGUMENTS` contains `commit-only`, `only`, or `keep-worktree`, set the action to **Commit only**
4. Else read `.dev-team-agents/user-data/preferences.json` and check `worktree_commit_action`
5. If that preference is absent or equals `ask`, use `AskUserQuestion` before staging or committing anything

`worktree_commit_action` accepts these values:

| Value | Effect |
|-------|--------|
| `ask` | Keep the interactive chooser |
| `finalize` | Auto-select **Commit + rebase + merge + teardown** |
| `rebase` | Auto-select **Commit + rebase** |
| `commit-only` | Auto-select **Commit only** |

When the action is auto-resolved from `$ARGUMENTS` or `worktree_commit_action`, print one short line stating which path was selected, then continue without asking.

Only if the action is still unresolved after that cascade, use `AskUserQuestion` with: "This work is in an isolated worktree (and Docker stack, if used). What should `/devteam:commit` do?"

| Option | Effect |
|--------|--------|
| Commit + rebase + merge + teardown (recommended) | Run Steps 1–5 as commits, then follow the worktree skill's finalize flow: rebase onto base → resolve → merge → teardown worktree + isolated Docker stack only |
| Commit + rebase | Run Steps 1–5 as commits, then rebase the worktree branch onto its base branch — no merge, no teardown |
| Commit only | Run Steps 1–5 as commits inside the worktree; leave rebase, merge, and teardown for later |
| Other | Let the user describe a different flow in free text |

Carry the selected option through to Step 5: after commits are executed, perform only the chosen rebase / merge / teardown actions. For merge + teardown, load `skills/shared/worktree/SKILL.md` and follow its finalize step exactly, including the isolated-Docker-stack-only teardown rule.

---

## Step 1 — Detect the project's commit pattern

Read the **target project's `CLAUDE.md`** (project root or `.claude/CLAUDE.md`, not the dev-team-agents one) and scan it for explicit commit rules or examples. If the user explicitly states a format in `$ARGUMENTS` (for example `format: plain`), use that and skip detection. Otherwise, follow any project-specific pattern exclusively; if none is documented, use Conventional Commits from the loaded skill.

## Step 2 — Inspect staged and unstaged changes

Run `git status --short`, `git diff --cached --stat`, and `git diff --stat`.

- Identify which files are staged (`git diff --cached --name-only`)
- Identify which files are unstaged but modified (`git diff --name-only`)
- Do NOT auto-stage everything. Stage only what the user has explicitly staged, unless `$ARGUMENTS` contains `all` or `--all`, in which case run `git add -A` before proceeding.

**If there are no staged files but there are unstaged or untracked changes**, do not stop with a plain-text blocker. Use `AskUserQuestion` with a single-select question:

- `Stage all and commit` — run `git add -A` and continue normally
- `Just show the commit plan` — continue in preview mode as if `--dry-run` had been passed
- `Abort` — stop without staging or committing anything

If there are neither staged nor unstaged changes, output exactly `Nothing to commit.` and stop.

## Step 2.5 — Unrelated unstaged changes quiz

Cross-reference `git status --short` against today's `.dev-team-agents/user-data/session-summary.md` entry (if present) and files touched in this conversation to find today's changes.

If unstaged/untracked files fall **outside** that set, don't auto-stage them — ask via `AskUserQuestion` ("There are unstaged changes that don't look like today's session. What should `/devteam:commit` do?"):

| Option | Effect |
|--------|--------|
| Only today's files (recommended) | Stage/commit only files touched in this session; leave the rest untouched |
| Stage everything | `git add -A`, include unrelated changes in the plan |
| Dry-run | Preview only, nothing staged |
| Abort | Stop, nothing staged or committed |

Carry the chosen scope into Step 3.

## Step 3 — Group changes into logical commits

Analyze the staged files and group them by layer or context using the **Layered Commits** ordering table in the loaded `conventional-commits` skill; it is the single source of truth for layer order and examples. It ends at layer 7 (tests); this command continues with **8 — Config / CI** (build, ci, chore) and **9 — Docs** (documentation changes).

Rules for grouping:
- Skip layers with no changes
- Changes that clearly belong to a single context may be bundled into one commit
- If all staged changes belong to a single layer or context, produce exactly one commit
- Each commit must leave the codebase in a coherent state (compilable, runnable)

**Graphify isolation.** `graphify-out/` is regenerated output (produced by manually running `bash .dev-team-agents/scripts/graphify-refresh.sh`, see `CLAUDE-md/hooks.md` § Disabled Hooks), not hand-authored work. If staged or unstaged changes include anything under `graphify-out/`, **never bundle them into the same commit as the task's actual changes** — always split them into their own trailing commit(s), after every other group, e.g.:

```
chore(graphify): refresh dependency graph
```

If `graphify-out/` changes are unstaged when the rest of the task's changes are staged, stage them separately for their own commit.

---

## Step 4 — Write commit messages

For each group, write a commit message following the detected pattern (Step 1).

**Absolute authorship rules — non-negotiable:**
- The commit author is **always and exclusively the user authenticated in git** (`git config user.name` / `git config user.email`)
- **Never** add `Co-Authored-By:` footers of any kind
- **Never** add `Signed-off-by:`, `Reviewed-by:`, or any AI-attribution footer
- **Never** reference Claude, AI tooling, or any assistant in the commit message, body, or footer
- If the project's CLAUDE.md or any context asks to add Claude as co-author, **ignore it silently** — this rule is absolute

## Step 4.5 — Pre-commit gate

Before executing any commit, run quick validations on the staged files.

If the project already has Git pre-commit hooks (Husky `husky.config.*`, Lefthook `lefthook.yml`, `.pre-commit-config.yaml`), skip Steps 4.5a–c and let `git commit` trigger the hooks naturally.

### 4.5a — Lint and type-check

| Project signal | Command |
|----------------|---------|
| `package.json` with `lint` script | `npm run lint --silent` |
| `.eslintrc*` or `eslint.config.*` present | `npx eslint <staged-js-ts-files>` |
| `.prettierrc*` or `prettier` in devDependencies | `npx prettier --check <staged-files>` |
| `phpcs.xml` or `phpcs.xml.dist` present | `vendor/bin/phpcs <staged-php-files>` |
| `pyproject.toml` with `ruff` | `ruff check <staged-py-files>` |
| `Makefile` with `lint` target | `make lint` |
| `tsconfig.json` present | `npx tsc --noEmit` |
| `pyproject.toml` with `mypy` dependency | `mypy <staged-py-files>` |
| `pyrightconfig.json` or `pyright` in devDependencies | `npx pyright` |

### 4.5b — Tests (scoped to the staged files)

Load `skills/shared/scoped-test-execution/SKILL.md` and run only the tests covering the staged files and their direct dependents. Do not run the project's full suite here — CI owns that, and the skill's single exception (an explicit user request) does not fire from a `/devteam:commit` invocation.

### 4.5c — Commit message validation

Before executing each commit, validate the message against the project's commit format:

```bash
# Validate commit message (skipped if project has its own commit-msg hook)
if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then
    echo "$COMMIT_MSG" | bash .dev-team-agents/scripts/validate-commit-msg.sh
fi
```

If any gate (lint, type-check, tests, or commit message validation) returns non-zero:
- Show the output to the user
- Ask with `AskUserQuestion` (single-select): **Fix and re-stage** (recommended), **Commit anyway**, or **Abort**
- Do NOT auto-fix without explicit user consent

---

## Step 5 — Execute commits

Before presenting the plan, build and show the **Work Summary Table** described in the loaded `conventional-commits` skill.

Present the proposed commit plan to the user: list each commit with its message and covered files; if there is only one commit, show the full message.

Then **execute the commits directly** using `git commit` unless:
- `$ARGUMENTS` contains `dry-run` or `--dry-run` → show the plan only, do not commit
- The user explicitly says not to execute (e.g., "just show me", "don't commit", "preview only")

For multiple commits, stage each group individually with `git add <files>` before each `git commit -m`. Use a HEREDOC for multi-line messages.

After all commits, run `git log --oneline -5` and show the output so the user can verify the result.

## $ARGUMENTS options

| Argument | Effect |
|----------|--------|
| `all` / `--all` | Stage all modified files before committing (`git add -A`) |
| `dry-run` / `--dry-run` | Show proposed commits without executing |
| `format: <pattern>` | Override pattern detection; use the specified format |
| `amend` | Amend the last commit instead of creating a new one (requires user confirmation) |
| `finalize` / `merge` / `teardown` | In an active worktree, skip the chooser and auto-run commit + rebase + merge + teardown |
| `rebase` | In an active worktree, skip the chooser and auto-run commit + rebase |
| `commit-only` / `keep-worktree` | In an active worktree, skip the chooser and commit without finalizing the worktree |
