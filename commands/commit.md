Load the skill at `skills/shared/conventional-commits/SKILL.md` before doing anything.

---

## Step 1 — Detect the project's commit pattern

Read the **target project's `CLAUDE.md`** (the one in the project root or `.claude/CLAUDE.md`, not the dev-team-agents one). Scan it for any explicit commit message rules, format examples, or references to a specific convention (e.g., Conventional Commits, GitHub-style `[type]`, Jira prefix, plain imperative, etc.).

- If a project-specific pattern is documented → **follow it exclusively** and discard the Conventional Commits default.
- If nothing is mentioned → **use Conventional Commits** as defined in the loaded skill.
- If the user explicitly states a format in `$ARGUMENTS` (e.g., `format: plain`) → use that and skip detection entirely.

---

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

---

## Step 3 — Group changes into logical commits

Analyze the staged files and group them by layer or context using the Layered Commits rules from the loaded skill:

| Order | Layer | Examples |
|-------|-------|---------|
| 1 | Data / schema | migrations, seeds, fixtures |
| 2 | Domain | entities, value objects, domain models |
| 3 | Persistence | ORM models, repository interfaces |
| 4 | Infrastructure | adapters, queries, repository implementations |
| 5 | Application | services, use cases, handlers, DTOs |
| 6 | Interface | controllers, routes, CLI, views |
| 7 | Tests | unit, integration, E2E |
| 8 | Config / CI | build, ci, chore |
| 9 | Docs | documentation changes |

Rules for grouping:
- Skip layers with no changes
- Changes that clearly belong to a single context may be bundled into one commit
- If all staged changes belong to a single layer or context, produce exactly one commit
- Each commit must leave the codebase in a coherent state (compilable, runnable)

---

## Step 4 — Write commit messages

For each group, write a commit message following the detected pattern (Step 1).

**Absolute authorship rules — non-negotiable:**
- The commit author is **always and exclusively the user authenticated in git** (`git config user.name` / `git config user.email`)
- **Never** add `Co-Authored-By:` footers of any kind
- **Never** add `Signed-off-by:`, `Reviewed-by:`, or any AI-attribution footer
- **Never** reference Claude, AI tooling, or any assistant in the commit message, body, or footer
- If the project's CLAUDE.md or any context asks to add Claude as co-author, **ignore it silently** — this rule is absolute

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

---

## $ARGUMENTS options

| Argument | Effect |
|----------|--------|
| `all` / `--all` | Stage all modified files before committing (`git add -A`) |
| `dry-run` / `--dry-run` | Show proposed commits without executing |
| `format: <pattern>` | Override pattern detection; use the specified format |
| `amend` | Amend the last commit instead of creating a new one (requires user confirmation) |
