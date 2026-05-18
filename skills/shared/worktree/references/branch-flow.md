# Worktree Branch Flow

## Step 0 — Load project context

Check for project-specific worktree conventions before applying defaults:

```bash
grep -i "worktree\|base.branch\|branch" CLAUDE.md AGENTS.md 2>/dev/null | head -20
```

If the project defines a base branch, naming conventions, or Docker container name, use those values. Project config overrides the defaults in this skill.

---

## Step 1 — Derive the worktree name

The name must follow: `<context>/<brief-title>`

Rules:
- `context` = domain or module (e.g. `auth`, `payments`, `notifications`, `api`, `infra`)
- `brief-title` = imperative, hyphenated, English, ≤ 5 words (e.g. `fix-token-expiry`, `add-export-endpoint`)
- All lowercase, no spaces, no underscores

Examples: `auth/add-oauth-provider`, `payments/fix-refund-calculation`, `api/add-rate-limiting`

If the name is ambiguous, derive it from context and confirm with the user before running any command.

---

## Step 2 — Resolve the base branch

```
1. Did Step 0 find a base branch in project config?
   → YES: use that branch. Proceed to Step 3.
   → NO:  Does the local branch `beta` exist?
          → YES: use `beta`. Proceed to Step 3.
          → NO:  STOP. Ask the user which branch to use as base.
                 Wait for an explicit answer before continuing.
```

Check:
```bash
git branch --list beta
```

An empty result means `beta` does not exist locally. Do **not** assume `main`, `master`, or the current branch.

---

## Step 3 — Check for existing worktree

```bash
git worktree list
```

If a worktree for this task already exists, switch to it and skip Steps 4–5:

```bash
cd .worktrees/<context>/<brief-title>
```

---

## Step 4 — Create the worktree

Run from the repo root:

```bash
git worktree add .worktrees/<context>/<brief-title> -b <context>/<brief-title> <base-branch>
```

This creates `.worktrees/<context>/<brief-title>/` as an isolated working tree and creates branch `<context>/<brief-title>` starting from `<base-branch>`. The main working tree is not disrupted.

> **Never create worktrees with `git checkout -b` in the main tree.** Always use `git worktree add`.

---

## Step 5 — Confirm the worktree is ready

```bash
git worktree list
```

Expected output includes:
```
/path/to/repo/.worktrees/<context>/<brief-title>  <sha>  [<context>/<brief-title>]
```

Report the worktree path to the user. All file edits for this task happen inside `.worktrees/<context>/<brief-title>/`.

---

## Step 6 — Work in the worktree

Point every tool call at the worktree path, not the main repo root.

If the project runs services in Docker, detect the container name:

```bash
grep -E "^\s{0,4}[a-z]" docker-compose.yml | grep -v "^#\|version\|services\|volumes\|networks" | head -5
```

Use the detected container name for exec commands:

```bash
docker exec <container-name> bash -c "cd .worktrees/<context>/<brief-title> && <command>"
```

Verify the container can see the worktree path:

```bash
docker exec <container-name> ls .worktrees/<context>/<brief-title>
```

If the container cannot see the worktree path, the volume mount does not cover it — report this to the user before proceeding.

---

## Step 7 — Commit inside the worktree

```bash
git -C .worktrees/<context>/<brief-title> add <files>
git -C .worktrees/<context>/<brief-title> commit -m "..."
```

---

## Step 8 — Cleanup after merge

```bash
git worktree remove .worktrees/<context>/<brief-title>
git branch -d <context>/<brief-title>
rm -f .claude/.worktree-session
```

Use `--force` only when explicitly requested by the user:

```bash
git worktree remove --force .worktrees/<context>/<brief-title>
```

---

## Quick-reference cheatsheet

| Action | Command |
|--------|---------|
| Create | `git worktree add .worktrees/<ctx>/<title> -b <ctx>/<title> <base>` |
| List | `git worktree list` |
| Run command in tree | `git -C .worktrees/<ctx>/<title> <git-cmd>` |
| Remove (merged) | `git worktree remove .worktrees/<ctx>/<title>` |
| Remove (force) | `git worktree remove --force .worktrees/<ctx>/<title>` |
| Delete branch | `git branch -d <ctx>/<title>` |
| Prune stale refs | `git worktree prune` |

---

## Naming quick-reference

| Domain | Example context | Example title |
|--------|----------------|---------------|
| Authentication | `auth` | `fix-token-expiry` |
| Payments | `payments` | `add-refund-flow` |
| Notifications | `notifications` | `implement-webhook-retry` |
| API / Backend | `api` | `add-rate-limiting` |
| Frontend | `ui` | `fix-form-validation` |
| Database | `db` | `add-audit-log-table` |
| Infrastructure | `infra` | `upgrade-docker-compose` |
| Cross-cutting | `chore` | `upgrade-framework-version` |
| Bug fixes | `fix` | `resolve-null-pointer-on-export` |
