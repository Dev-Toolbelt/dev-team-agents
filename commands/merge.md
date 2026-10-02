---
description: Merge the current working branch into a target branch, with worktree-aware finalization
argument-hint: [target-branch] [--no-teardown]
model: haiku
---

Load `skills/shared/current-context/SKILL.md` to detect branch/worktree state. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

---

## Step 0 — Uncommitted changes pre-flight

Run:

```bash
git status --porcelain
```

If non-empty, tell the user there are uncommitted changes and ask (`AskUserQuestion`): **Commit them now** (run the same commit routine as `/devteam:commit` — see that command for the routine, group by layer, no Claude attribution), **Skip and continue**, or **Abort**. Abort stops the command entirely.

---

## Step 1 — Resolve the worktree session, then the branches

The session file is untracked and lives in the **main checkout**, so a linked worktree cannot see it by a relative path. Resolve it through the main checkout root first:

```bash
ROOT=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)
cat "$ROOT/.dev-team-agents/.worktree-session" 2>/dev/null
git branch --show-current
git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@'
```

The last command (or `worktree_base_branch` in `preferences.json`, or project config, if set) gives the **default branch** — never hardcode `main`, `master`, `beta`, or `develop`.

- **Working branch** — the current branch. If the session says `worktree=yes` and you are in the main checkout, it is the branch checked out in the linked worktree (`git worktree list`; ask via `AskUserQuestion` if there is more than one).
- **Target** — strip every `--flag` from `$ARGUMENTS`; the first remaining token, if any, is the target. Otherwise, with `worktree=yes branch=<b>`, the target defaults to the worktree base `<b>`. Otherwise ask via `AskUserQuestion`: "Which branch do you want to merge `<working-branch>` into?" — **`<detected-default-branch>`** (recommended) / **Other** (free text).
- If the working branch is the default branch or equals the target, there is nothing to merge — tell the user and stop.
- If an explicit target differs from the worktree base `<b>`, say so: any rebase goes onto the target, not `<b>`.

---

## Step 2 — Choose the finalization strategy

Use the session read in Step 1.

**If `worktree=yes branch=<b>`** (isolated worktree, possibly with isolated Docker infra):

Ask via `AskUserQuestion`:

> "This branch runs in an isolated worktree. How do you want to finalize the merge into `<target>`?"
- **Commit + rebase onto `<target>` + merge + teardown** (recommended) — delegate entirely to `skills/shared/worktree/SKILL.md` § Worktree Setup step 8 (rebase → resolve → commit → merge → dirty-worktree guard → teardown worktree + isolated Docker stack). Do not reimplement that sequence here — load the skill and follow it.
- **Commit + merge only (no rebase, keep worktree)** — commit any pending work in the worktree, `git checkout <target>` in the main tree, `git merge <working-branch>`, leave the worktree and infra intact.
- **Merge only (assume already committed)** — skip commit, run the merge from whichever of the two paths above was implied by a follow-up choice.
- **Abort**

**If `worktree=no branch=<b>`** or the session file is absent (plain feature branch, no isolation):

Ask via `AskUserQuestion`:

> "How do you want to merge `<current-branch>` into `<target>`?"
- **Commit + merge** (recommended) — commit pending work if any, `git checkout <target>`, `git merge <current-branch>`
- **Merge only (assume already committed)**
- **Abort**

`--no-teardown` in `$ARGUMENTS` forces the worktree to be kept regardless of which option is chosen, overriding a teardown-implying answer.

---

## Step 3 — Execute the chosen strategy

Follow exactly what was confirmed in Step 2. For any path that includes rebase or merge conflicts, stop and hand resolution to the user — never force-resolve conflicts silently. For the worktree-teardown path, the dirty-worktree guard in `skills/shared/worktree/SKILL.md` is mandatory: if `git status --porcelain` inside the worktree is non-empty after the merge, abort teardown and ask the user (commit / discard / keep) instead of proceeding.

---

## Step 4 — Nudge `/devteam:learn` if not run this session

This is the canonical learn-nudge check — other commands reference it rather than restating it. Read the marker `/devteam:learn` writes (format `<unix-timestamp> <head-sha>`) from the checkout where learn ran — the worktree if one was used, else `$ROOT`:

```bash
cat .dev-team-agents/.learn-last-run "$ROOT/.dev-team-agents/.learn-last-run" 2>/dev/null
git rev-parse <working-branch>
```

If the marker is missing, or its `<head-sha>` differs from the working branch tip (commits landed since the last learn run), tell the user before finishing:

> "This session hasn't run `/devteam:learn` since its last recorded commit — consider running it to capture decisions from this branch before they're lost. Run `/devteam:learn` now?"

Ask via `AskUserQuestion` (Yes / No). If yes, hand off by telling the user to invoke `/devteam:learn` (do not spawn it inline — it is a separate command with its own plan gate).

---

## Step 5 — Session summary

Merging into the default branch is a finalization signal. Apply the Session Summary Rule from `CLAUDE.md` now: check `git status --porcelain`, `git diff --cached`, and today's commits. If there is a signal and `.dev-team-agents/user-data/session-summary.md` has no entry for today, write one (Done/Decisions/Next, in English) before finishing.

---

$ARGUMENTS options:
- `[target-branch]` — merge into this branch instead of asking; defaults to the worktree base when a worktree session is active (must still pass the Step 1 checks)
- `--no-teardown` — keep the worktree and its isolated infra even if the chosen strategy would normally tear it down
