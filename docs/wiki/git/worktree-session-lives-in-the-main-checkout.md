# Worktree session file lives in the main checkout

**Origin:** audit backlog — linked worktree could not see session file via relative path | 2026-10-02
**Tags:** worktree, git-common-dir, .worktree-session, linked worktree, untracked, relative path, session protocol, commands/merge, finalization

> `.dev-team-agents/.worktree-session` is untracked and lives only in the main checkout, so a linked worktree cannot see it by relative path. Use `git rev-parse --git-common-dir` to resolve the main checkout root first.

---

## What it is

When a session operates in a linked worktree, it records its worktree mode (`worktree=yes/no`) and branch in `.dev-team-agents/.worktree-session`. The file is untracked and lives in the main repository checkout at `<main>/.dev-team-agents/.worktree-session`.

Inside a linked worktree, relative path lookups resolve to `<main>/.git/worktrees/<name>/` (the worktree's `GIT_DIR`), not the main checkout. A relative `cat .dev-team-agents/.worktree-session` from the worktree directory fails with "no such file."

## How it works

Resolve the main checkout first, then read the session file:

```bash
# From anywhere (main checkout or linked worktree), get the main checkout root
ROOT=$(cd "$(git rev-parse --git-common-dir)/.." && pwd)
cat "$ROOT/.dev-team-agents/.worktree-session" 2>/dev/null
```

`git rev-parse --git-common-dir` returns the `.git` directory (main checkout) in both cases:
- Main checkout: `.git`
- Linked worktree: `<main>/.git`

Stepping up one level and resolving the absolute path gives the repository root regardless of where the command runs.

## Gotchas

- **`git rev-parse --absolute-git-dir` is not the right choice.** It returns the worktree's own `GIT_DIR` (`.git/worktrees/<name>`), which has no `.dev-team-agents/` subdirectory.
- **The session file must be read before checking the working branch.** Commands like `/devteam:merge` need to know if they are in a worktree before deciding which branch to merge or what the target should be.
- **Cleanup on teardown must be careful not to delete what another worktree session left behind.** The file is machine-local, not worktree-local. `scripts/hooks/session-start.sh` renames stale session files to `.worktree-session.stale` in the machine-local state directory (No-Destruction Rule), never deletes them.

## References

- `commands/merge.md` — Step 1, canonical learn-nudge check in Step 4 (resolves `ROOT` and checks both locations)
- `scripts/hooks/session-start.sh` — startup read and stale-session rotation
- `skills/shared/worktree/references/session-protocol.md` — lifecycle and rotation rules
