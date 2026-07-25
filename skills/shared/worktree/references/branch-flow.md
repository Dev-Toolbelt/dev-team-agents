# Worktree Branch Flow

Throughout this flow, `<wt-path>` is the configured worktree root — `worktree_path`
from `.dev-team-agents/user-data/preferences.json` (default `.dev-team-agents/worktrees`). The full
tree location is `<wt-path>/<context>/<brief-title>`.

## Step 0 — Load project context

Check for project-specific worktree conventions before applying defaults:

```bash
grep -i "worktree\|base.branch\|branch" CLAUDE.md AGENTS.md 2>/dev/null | head -20
```

Read the worktree preferences:

```bash
python3 -c "import json;d=json.load(open('.dev-team-agents/user-data/preferences.json'));print(d.get('worktree_base_branch') or '', d.get('worktree_path','.dev-team-agents/worktrees'), d.get('worktree_docker_isolate',True))" 2>/dev/null
```

Project config (`CLAUDE.md`/`AGENTS.md`) overrides `preferences.json`, which overrides the skill defaults.

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

Resolve in this order (first match wins):

```
1. worktree_base_branch in preferences.json (if non-null)  → use it.
2. Base branch declared in project CLAUDE.md / AGENTS.md    → use it.
3. Auto-detect the repository default branch:
      git symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##'
      (fallback: git rev-parse --abbrev-ref HEAD)
4. None resolved → STOP and ask the user which branch to use as base.
```

> Never hardcode `main`, `master`, or `beta`. Always resolve in the order above.

---

## Step 3 — Check for existing worktree

```bash
git worktree list
```

If a worktree for this task already exists, switch to it and skip Steps 4–5:

```bash
cd <wt-path>/<context>/<brief-title>
```

---

## Step 4 — Create the worktree

Run from the repo root:

```bash
git worktree add <wt-path>/<context>/<brief-title> -b <context>/<brief-title> <base-branch>
```

This creates `<wt-path>/<context>/<brief-title>/` as an isolated working tree and creates branch `<context>/<brief-title>` starting from `<base-branch>`. The main working tree is not disrupted.

> **Never create worktrees with `git checkout -b` in the main tree.** Always use `git worktree add`.

---

## Step 5 — Confirm the worktree is ready

```bash
git worktree list
```

Report the worktree path to the user. All file edits for this task happen inside `<wt-path>/<context>/<brief-title>/`.

---

## Step 6 — Work in the worktree (Docker isolation)

Point every tool call at the worktree path, not the main repo root.

If `worktree_docker_isolate` is `true` **and** the project uses Docker Compose,
bring up an **isolated compose stack** for this worktree so it never touches the
main project's containers, volumes, or ports.

**Load `references/docker-isolation.md`** for the full protocol (isolated compose
project naming, ports-off override, exec, and safe teardown). Do not reuse the
main stack's containers for worktree work when isolation is enabled.

---

## Step 7 — Commit inside the worktree

```bash
git -C <wt-path>/<context>/<brief-title> add <files>
git -C <wt-path>/<context>/<brief-title> commit -m "..."
```

Intermediate commits during development are normal. The mandatory rebase and
teardown below run only on **finalization** (Step 8), when the user asks to
merge/finish the task.

---

## Step 8 — Finalize: rebase → merge → teardown

When the user asks to **merge / finish** the worktree task, run this sequence in order.
Never skip the rebase, and never tear down the main project infrastructure.

```bash
WT=<wt-path>/<context>/<brief-title>
BRANCH=<context>/<brief-title>
BASE=<base-branch>

# 1. Mandatory rebase of the worktree branch onto its base
git -C "$WT" fetch origin "$BASE" 2>/dev/null || true
git -C "$WT" rebase "$BASE"
#    Resolve ALL conflicts, then: git -C "$WT" rebase --continue

# 2. Commit any remaining resolved work (load conventional-commits first)
git -C "$WT" add -A
git -C "$WT" commit -m "..."   # only if there is staged work

# 3. Merge into the base branch
git checkout "$BASE"
git merge --ff-only "$BRANCH" || git merge --no-ff "$BRANCH"

# 4. Teardown — ONLY the worktree's own infrastructure
#    (isolated Docker stack: see references/docker-isolation.md → Teardown)
git worktree remove "$WT"
git branch -d "$BRANCH"
rm -f .dev-team-agents/.worktree-session
```

Use `git worktree remove --force` only when the user explicitly requests it.

> **Safety:** teardown removes the worktree, its branch, and its **isolated** Docker
> stack only. Never run `docker compose down` without the isolated `-p <project>`,
> and never delete the base branch or the main stack.

---

## Quick-reference cheatsheet

| Action | Command |
|--------|---------|
| Create | `git worktree add <wt-path>/<ctx>/<title> -b <ctx>/<title> <base>` |
| List | `git worktree list` |
| Run command in tree | `git -C <wt-path>/<ctx>/<title> <git-cmd>` |
| Rebase onto base | `git -C <wt-path>/<ctx>/<title> rebase <base>` |
| Remove (finalized) | `git worktree remove <wt-path>/<ctx>/<title>` |
| Remove (force) | `git worktree remove --force <wt-path>/<ctx>/<title>` |
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
