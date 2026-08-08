---
description: Group staged changes by layer and write commits
argument-hint: [all] [dry-run] [format: <style>]
model: haiku
---

Load the skill at `skills/shared/conventional-commits/SKILL.md` before doing anything.

Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Step 0 — Auto knowledge capture

Before inspecting staged changes, run the `/devteam:learn` pass automatically.

**Skip this step only if:**
- `$ARGUMENTS` contains `--skip-learn`
- The user explicitly wrote "skip learn", "don't learn", "sem learn", or similar in their prompt

**To execute:**
1. Run the `/devteam:learn` flow, Steps 1–4 exactly, with one override: in its Step 3, suppress the "Awaiting your approval before proceeding." line and proceed directly to spawning agents — no user confirmation is needed.
2. Wait for all learn agents to complete before continuing.
3. If the learn pass finds nothing to update (output "Nothing to capture"), proceed immediately.

This ensures all session knowledge is captured in the project's knowledge base before changes are committed.

---

## Step 0.5 — Worktree finalization quiz

Check for an active worktree session:

```bash
cat .dev-team-agents/.worktree-session 2>/dev/null
```

If the file is absent, or reads `worktree=no ...`, skip this step entirely — commit normally.

If it reads `worktree=yes branch=<b>`, use `AskUserQuestion` before staging or committing anything:

**Question:** "This work is in an isolated worktree (and Docker stack, if used). What should `/devteam:commit` do?"

| Option | Effect |
|--------|--------|
| Commit + rebase + merge + teardown (recommended) | Run Steps 1–5 as commits, then follow the worktree skill's finalize flow: rebase onto base → resolve → merge → teardown worktree + isolated Docker stack only |
| Commit + rebase | Run Steps 1–5 as commits, then rebase the worktree branch onto its base branch — no merge, no teardown |
| Commit only | Run Steps 1–5 as commits inside the worktree; leave rebase, merge, and teardown for later |
| Other | Let the user describe a different flow in free text |

Carry the selected option through to Step 5: after commits are executed, perform only the additional actions the user selected (rebase / merge / teardown), never more than what was chosen. For merge + teardown, load `skills/shared/worktree/SKILL.md` and follow its finalize step exactly, including the isolated-Docker-stack-only teardown rule.

---

## Step 1 — Detect the project's commit pattern

Read the **target project's `CLAUDE.md`** (the one in the project root or `.claude/CLAUDE.md`, not the dev-team-agents one). Scan it for any explicit commit message rules, format examples, or references to a specific convention (e.g., Conventional Commits, GitHub-style `[type]`, Jira prefix, plain imperative, etc.).

- If a project-specific pattern is documented → **follow it exclusively** and discard the Conventional Commits default.
- If nothing is mentioned → **use Conventional Commits** as defined in the loaded skill.
- If the user explicitly states a format in `$ARGUMENTS` (e.g., `format: plain`) → use that and skip detection entirely.

## Step 2 — Inspect staged and unstaged changes

Run these commands:

```bash
git status --short
git diff --cached --stat
git diff --stat
```

- Identify which files are staged (`git diff --cached --name-only`)
- Identify which files are unstaged but modified (`git diff --name-only`)
- Do NOT auto-stage everything. Stage only what the user has explicitly staged, unless `$ARGUMENTS` contains `all` or `--all`, in which case run `git add -A` before proceeding.

**If there are no staged files but there are unstaged or untracked changes**, do not stop with a plain-text blocker. Use `AskUserQuestion` with a single-select question:

- `Stage all and commit` — run `git add -A` and continue normally
- `Just show the commit plan` — continue in preview mode as if `--dry-run` had been passed
- `Abort` — stop without staging or committing anything

If there are neither staged nor unstaged changes, output exactly `Nothing to commit.`

Then stop.

## Step 2.5 — Unrelated unstaged changes quiz

Determine which files were touched in today's session: cross-reference `git status --short` output against the paths mentioned in today's `.dev-team-agents/user-data/session-summary.md` entry (if present) and any files this command has read or edited so far in the current conversation.

If there are **unstaged or untracked files that are not part of what was touched in this session today**, do not silently ignore or auto-stage them. Use `AskUserQuestion` with a single-select question:

**Question:** "There are unstaged changes that don't look like they're from today's session. What should `/devteam:commit` do?"

| Option | Effect |
|--------|--------|
| Fazer commits somente do que foi tocado aqui (recommended) | Stage and commit only the files touched in this session today; leave every other unstaged/untracked file untouched |
| Stage e commitar tudo | Run `git add -A` and include the unrelated changes in the commit plan |
| Mostrar só o plano (dry-run) | Continue in preview mode — show what would be committed without staging or committing anything |
| Abortar | Stop without staging or committing anything |

Carry the selected scope into Step 3 — only the files matching the chosen option are staged and grouped into commits.

## Step 3 — Group changes into logical commits

Analyze the staged files and group them by layer or context using the **Layered Commits** ordering table in the `conventional-commits` skill loaded above — that table is the single source of truth for layer order and examples; do not restate it here. It ends at layer 7 (tests); this command continues with **8 — Config / CI** (build, ci, chore) and **9 — Docs** (documentation changes).

Rules for grouping:
- Skip layers with no changes
- Changes that clearly belong to a single context may be bundled into one commit
- If all staged changes belong to a single layer or context, produce exactly one commit
- Each commit must leave the codebase in a coherent state (compilable, runnable)

**Graphify isolation.** `graphify-out/` is regenerated output (produced by manually running `bash .dev-team-agents/scripts/graphify-refresh.sh`, see `CLAUDE-md/hooks.md` § Disabled Hooks), not hand-authored work. If staged or unstaged changes include anything under `graphify-out/`, **never bundle them into the same commit as the task's actual changes** — always split them into their own trailing commit(s), after every other group, e.g.:

```
chore(graphify): refresh dependency graph
```

If `graphify-out/` changes are unstaged when the rest of the task's changes are staged, stage them separately for their own commit rather than leaving them out or folding them into `git add -A`.

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

### 4.5a — Lint

| Project signal | Command |
|----------------|---------|
| `package.json` with `lint` script | `npm run lint --silent` |
| `.eslintrc*` or `eslint.config.*` present | `npx eslint <staged-js-ts-files>` |
| `.prettierrc*` or `prettier` in devDependencies | `npx prettier --check <staged-files>` |
| `phpcs.xml` or `phpcs.xml.dist` present | `vendor/bin/phpcs <staged-php-files>` |
| `pyproject.toml` with `ruff` | `ruff check <staged-py-files>` |
| `Makefile` with `lint` target | `make lint` |

### 4.5b — Type-check

| Project signal | Command |
|----------------|---------|
| `tsconfig.json` present | `npx tsc --noEmit` |
| `pyproject.toml` with `mypy` dependency | `mypy <staged-py-files>` |
| `pyrightconfig.json` or `pyright` in devDependencies | `npx pyright` |

### 4.5c — Tests (scoped to the staged files)

Load `skills/shared/scoped-test-execution/SKILL.md` and run only the tests covering the staged files and their direct dependents. Do not run the project's full suite here — CI owns that, and the skill's single exception (an explicit user request) does not fire from a `/devteam:commit` invocation.

### 4.5d — Commit message validation

Before executing each commit, validate the message against the project's commit format:

```bash
# Validate commit message (skipped if project has its own commit-msg hook)
if [ -f ".dev-team-agents/scripts/validate-commit-msg.sh" ]; then
    echo "$COMMIT_MSG" | bash .dev-team-agents/scripts/validate-commit-msg.sh
fi
```

This runs the `validate-commit-msg.sh` script (if present) to catch format violations before `git commit` is called. Skip if the project already has a `commit-msg` git hook configured.

If any gate (lint, type-check, tests, or commit message validation) returns non-zero:
- Show the output to the user
- Ask with `AskUserQuestion` (single-select): **Fix and re-stage** (recommended), **Commit anyway**, or **Abort**
- Do NOT auto-fix without explicit user consent

---

## Step 5 — Execute commits

Present the proposed commit plan to the user:
- List each commit with its message and the files it covers
- If there is only one commit, show the full message

Then **execute the commits directly** using `git commit` unless:
- `$ARGUMENTS` contains `dry-run` or `--dry-run` → show the plan only, do not commit
- The user explicitly says not to execute (e.g., "just show me", "don't commit", "preview only")

For multiple commits, stage each group individually with `git add <files>` before each `git commit -m`.

Use a HEREDOC for multi-line messages:

```bash
git commit -m "$(cat <<'EOF'
type(scope): short description

Optional body explaining the WHY.
EOF
)"
```

After all commits, run `git log --oneline -5` and show the output so the user can verify the result.

## $ARGUMENTS options

| Argument | Effect |
|----------|--------|
| `all` / `--all` | Stage all modified files before committing (`git add -A`) |
| `dry-run` / `--dry-run` | Show proposed commits without executing |
| `format: <pattern>` | Override pattern detection; use the specified format |
| `amend` | Amend the last commit instead of creating a new one (requires user confirmation) |
