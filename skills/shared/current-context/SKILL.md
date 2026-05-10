---
name: current-context
description: Detect the current git branch, worktree session, and staged changes before executing any devteam command.
---

# Current Context Detection

Before executing any devteam command, identify the working context so that analysis and actions stay scoped to the right branch and files.

## Steps

Run these commands in order:

| Command | Purpose |
|---------|---------|
| `git branch --show-current` | Identify the active branch |
| `git diff --name-only HEAD` | List locally modified files |
| `git diff --name-only main...HEAD` | List all files changed in this branch vs main |
| Check `.claude/.worktree-session` (if present) | Identify active worktree and its branch |

## Scope Rule

Restrict all analysis and actions to files and changes within the detected context. Do NOT scan or act on the full codebase unless the task explicitly requests a broader scope.

## Worktree Session

If `.claude/.worktree-session` exists, read it before proceeding:
- `worktree=no` — operating on main working tree; no worktree isolation active
- `worktree=yes branch=<b>` — operating inside a worktree on branch `<b>`; load `skills/shared/worktree/SKILL.md` and follow its isolation protocol

If the file does not exist, assume the main working tree and proceed normally.

## Staged Changes

Use `git status --porcelain` to distinguish:
- `M ` (staged modifications) — already added to the index
- ` M` (unstaged modifications) — modified but not staged
- `??` (untracked files) — new files not yet tracked

This matters when the task involves committing or reviewing only staged work.

## Summary Format

After running the commands, produce a one-line context header before any action:

```
Context: branch=<branch> | worktree=<yes|no> | changed=<N files>
```

This makes the working scope explicit to any subsequent agent or step.
