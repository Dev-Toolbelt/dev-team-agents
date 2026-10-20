# A Nested Directory's Own Git Cannot Vouch for Itself

**Origin:** task-board audit fix pass, ADR-0043 | 2026-10-20
**Tags:** git rev-parse, git-common-dir, gitfile, nested checkout, worktrees, GIT_DIR, GIT_COMMON_DIR, ADR-0043

> Read this first: asking git inside an untrusted directory whether it belongs to this project proves nothing. A planted `.git` gitfile makes git report the project's repository. Trust must come from the project side.

---

## What it is

A nested directory inside the project can contain a `.git` file instead of a directory. Git follows the gitfile and treats the project's repository as its own. Any check that asks the nested directory's git for its identity gets the attacker's answer.

## How it works

1. A `.git` file containing `gitdir: ../../.git` points git at the project's git directory.
2. `git rev-parse --git-common-dir`, run inside the untrusted directory, reports the project's repository.
3. The launcher accepts the directory only when the project side confirms it:
   - the same absolute git directory and the same toplevel, or
   - a `worktrees/<name>` admin directory inside the project's `.git` whose `gitdir` back-link names that work tree.
4. The back-link lives inside the project's `.git`, which the nested directory cannot write. It is the authoritative side.

## Gotchas

- Unset `GIT_DIR`, `GIT_COMMON_DIR`, `GIT_WORK_TREE`, and `GIT_INDEX_FILE` before any check. An inherited variable answers for the caller, not for the directory.
- Querying the nested directory's git is the attack surface, not the defense. Compare against the project's own records.
- The refusal rule is recorded in ADR-0043.

## References

- `docs/development/adrs/0043-hook-launcher-refuses-hooks-from-a-nested-checkout-outside-the-project-repository.md`
- `docs/wiki/git/worktree-exclude-scope.md`
