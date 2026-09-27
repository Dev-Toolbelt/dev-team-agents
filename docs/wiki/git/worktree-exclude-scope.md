# Which info/exclude a linked worktree actually reads

**Origin:** v3 bind — keeping per-developer artifacts out of git across worktrees | 2026-09-27
**Tags:** worktree, info/exclude, gitignore, GIT_DIR, GIT_COMMON_DIR, untracked

> A linked worktree ignores its own `$GIT_DIR/info/exclude`. Only the shared `$GIT_COMMON_DIR/info/exclude` has any effect, so an exclude block is repository-wide and cannot be scoped per worktree.

---

## What it is

`git rev-parse --absolute-git-dir` inside a linked worktree returns
`<main>/.git/worktrees/<name>`, and that directory has its own `info/` — which looks like the
natural place for per-worktree excludes. It is not read.

## How it works

Verified directly, not inferred from documentation:

```bash
cd <worktree>
echo probe.txt > "$(git rev-parse --absolute-git-dir)/info/exclude"
git status --porcelain | grep -c probe.txt      # → 1  (NOT ignored)

rm "$(git rev-parse --absolute-git-dir)/info/exclude"
echo probe.txt > "$(git rev-parse --git-common-dir)/info/exclude"
git status --porcelain | grep -c probe.txt      # → 0  (ignored)
```

## Gotchas

- Any write to the exclude file affects **every** checkout of the repository. Clearing it when one
  worktree is torn down un-ignores the artifacts of all the others — the reason `bind.unbind` only
  clears its managed block when no other bound checkout of the same repository is still live.
- This makes "scope the exclude per worktree" an impossible fix, however reasonable it sounds. The
  workable shapes are a shared block whose entries are the union of what every checkout needs, or a
  refcount on teardown.
- `$GIT_DIR` and `$GIT_COMMON_DIR` differ only inside a linked worktree; in the main checkout both
  point at `.git`, which is why the difference is easy to miss while testing there.

## References

- `scripts/lib/devteam/bind.py` — `_local_exclude_file`, `_other_checkouts_bound`
- `docs/development/adrs/0007-global-core-and-data-store-replacing-per-project-vendored-install.md`
