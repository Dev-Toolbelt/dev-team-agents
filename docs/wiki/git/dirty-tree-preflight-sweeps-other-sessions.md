# The Dirty-Tree Pre-flight commits other sessions' files

**Origin:** /devteam:merge dirty-tree pre-flight in a checkout shared with other Claude Code sessions | 2026-10-25
**Tags:** dirty-tree pre-flight, shared checkout, parallel sessions, git restore --staged, git status porcelain, explicit path list, commit sweep, default branch

> The Dirty-Tree Pre-flight commits every uncommitted change in the checkout. In a shared checkout that includes other sessions' files, so list the tree and commit by explicit path before running it.

---

## What it is

`/devteam:commit`, `/devteam:push`, `/devteam:merge` and `/devteam:pr` run the Dirty-Tree Pre-flight (`skills/shared/git-workflow/SKILL.md`) on uncommitted changes. It assumes the working tree belongs to the current session. Several sessions can share the main checkout, and others can work in `.worktrees/`.

## How it works

Before committing from a shared checkout:

1. List every change, including untracked files: `git status --porcelain --untracked-files=all`.
2. Compare the list with the files this session created or edited, from its own diff and plan.
3. Unstage anything foreign: `git restore --staged -- <path>`. Another session may already have staged files, such as `A  docs/reports/...`.
4. Commit by explicit path list, never `git add -A` or a bare `git commit -a`.
5. Verify that each own file appears in exactly one commit, for example with `comm` against the list.
6. Ask with `AskUserQuestion` when foreign files exist, before any commit.
7. On the default branch, create a branch first.

## Gotchas

- A staged file from another session is committed by a plain `git commit`, even though this session never touched it.
- Staging state is shared across sessions in one checkout. A clean `git status` at the start does not stay clean.
- Confirm the user's intent before running the pre-flight. Its "commit everything" default is the wrong default here.

## References

- `skills/shared/git-workflow/SKILL.md` § Dirty-Tree Pre-flight
- `docs/wiki/git/worktree-session-lives-in-the-main-checkout.md` (where the session file lives when sessions share a checkout)
