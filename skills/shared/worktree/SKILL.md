---
name: worktree
description: Git worktree per task — <worktree_path>/<context>/<title>, default .claude/worktrees.
---

# Worktree — Task Isolation Protocol

Invoke this skill at the **very start** of every task. No code, no file edits, no planning until the worktree decision is resolved.

---

## Decision Cascade (load first)

Resolve the worktree decision top-down; stop at the first that applies:

| # | Source | Action |
|---|--------|--------|
| 1 | `.dev-team-agents/.worktree-session` present | Follow the stored per-session decision silently |
| 2 | `worktree_active` in `preferences.json` | Use it **without asking**; write the session file so the rest of the session is consistent |
| 3 | key absent (legacy install) | Ask the user once — see below |

```bash
cat .dev-team-agents/.worktree-session 2>/dev/null   # source 1
```

| Session-file content | Action |
|---|---|
| `worktree=no branch=<b>` | Operate on branch `<b>`; skip worktree setup |
| `worktree=yes branch=<b>` | Load `references/branch-flow.md` using `<b>` as base |

**If the session file is absent**, read `worktree_active` from `preferences.json`:
`true` → set up a worktree without the yes/no prompt; `false` → skip the yes/no prompt and ask only for a new branch name;
key absent → use the `AskUserQuestion` tool with options [Yes, No]:
"Should this task use a git worktree (isolated working directory)?"

- **Yes** → resolve the base branch (auto-detect default branch), write `worktree=yes branch=<base>`, follow `references/branch-flow.md`
- **No** → ask for a new branch name (suggest `<context>/<brief-title>`), run `git checkout -b <branch-name>`, write `worktree=no branch=<branch-name>`

For the full cascade, base-branch resolution, format rules, and cleanup: load `references/session-protocol.md`.

---

## Worktree Setup (when worktree=yes)

`<wt-path>` = `worktree_path` from `preferences.json` (default `.claude/worktrees`).
Load `references/branch-flow.md` for the complete step-by-step flow:

1. Load project context (project-config → preferences.json → skill defaults)
2. Derive name: `<context>/<brief-title>` — lowercase, hyphenated, ≤ 5 words
3. Resolve base branch: `worktree_base_branch` → project config → auto-detect default branch → ask
4. Check for existing worktree → reuse if present
5. Create: `git worktree add <wt-path>/<ctx>/<title> -b <ctx>/<title> <base>`
6. Work exclusively inside `<wt-path>/<ctx>/<title>/` — when `worktree_docker_isolate` and the project uses Docker, load `references/docker-isolation.md`
7. Commit with `git -C <wt-path>/<ctx>/<title> ...` (intermediate commits are normal)
8. Finalize on merge: rebase onto base → resolve → commit → merge → teardown worktree + isolated Docker stack only

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
- **Never** hardcode `main`, `master`, or `beta` as base — resolve from `worktree_base_branch`, project config, or the auto-detected default branch
- **Finalization is mandatory**: on merge, rebase onto the base first, then merge, then tear down **only** the worktree and its isolated Docker stack — never the main infra
- The session file is ephemeral — remove it on cleanup, keep it gitignored
