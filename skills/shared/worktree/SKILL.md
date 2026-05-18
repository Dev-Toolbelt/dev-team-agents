---
name: worktree
description: Git worktree per task — .worktrees/<context>/<title>.
---

# Worktree — Task Isolation Protocol

Invoke this skill at the **very start** of every task. No code, no file edits, no planning until the worktree decision is resolved.

---

## Session File Decision (load first)

Read `.claude/.worktree-session`:

```bash
cat .claude/.worktree-session 2>/dev/null
```

| File content | Action |
|---|---|
| `worktree=no branch=<b>` | Operate on branch `<b>`; skip worktree setup |
| `worktree=yes branch=<b>` | Load `references/branch-flow.md` using `<b>` as base |
| File absent | Ask the user — see below |

**If file is absent:** Use the `AskUserQuestion` tool with options [Yes, No]:
"Should this task use a git worktree (isolated working directory)?"

- **Yes** → ask for the base branch (default: current branch), write `worktree=yes branch=<base>`, then follow `references/branch-flow.md`
- **No** → ask for a new branch name (suggest `<context>/<brief-title>`), run `git checkout -b <branch-name>`, write `worktree=no branch=<branch-name>`

For full session-file protocol, format rules, and cleanup: load `references/session-protocol.md`.

---

## Worktree Setup (when worktree=yes)

Load `references/branch-flow.md` for the complete step-by-step flow:

1. Load project context (project-config overrides all defaults)
2. Derive name: `<context>/<brief-title>` — lowercase, hyphenated, ≤ 5 words
3. Resolve base branch (`beta` by default if it exists; ask if not found)
4. Check for existing worktree → reuse if present
5. Create: `git worktree add .worktrees/<ctx>/<title> -b <ctx>/<title> <base>`
6. Work exclusively inside `.worktrees/<ctx>/<title>/`
7. Commit with `git -C .worktrees/<ctx>/<title> ...`
8. Cleanup after merge: remove worktree, delete branch, remove session file

---

## Name Format

```
<context>/<brief-title>
```

Examples: `auth/add-oauth-provider`, `payments/fix-refund-calculation`, `api/add-rate-limiting`

For the full naming table, see `references/branch-flow.md` → Naming quick-reference.

---

## Key Rules

- **Never** use `git checkout -b` in the main tree — always `git worktree add`
- **Never** assume `main` or `master` as base — always resolve from project config, `beta`, or the user
- The session file is ephemeral — remove it on cleanup, keep it gitignored
