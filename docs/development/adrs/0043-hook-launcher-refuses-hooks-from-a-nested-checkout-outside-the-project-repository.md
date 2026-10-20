# ADR-0043: Hook launcher refuses hooks from a nested checkout outside the project repository

**Date:** 2026-10-20  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/hooks.py`, `scripts/install.sh`, `scripts/lib/codex_hooks_merge.py`  
**Relates to:** [ADR-0026](0026-on-windows-shell-scripts-run-only-under-an-absolute-git-bash-with-a-resolved-python.md) (how hook commands are shaped on Windows)

## Context

A provider runs a hook command in the session's current directory, and a Claude Code session keeps the directory a Bash call `cd`-ed into. To keep hooks working there, the registered command walks up from that directory to the nearest `.dev-team-agents/scripts/hooks` (or `core-dir` pointer) and runs the dispatcher it finds. That walk deliberately accepts a match below the opened project: a monorepo sub-project with its own install, or a worktree with its own hooks.

The same walk also accepts a cloned repository or an installed package that ships its own `.dev-team-agents/`. After an agent `cd`s into one, the next tool call runs that checkout's hooks — code nobody reviewed, with the user's rights, outside the permission system — in place of the project's own hooks, the credential guard included. A planted `core-dir` pointer can send the same `exec bash` to any path. Found by the task-board audit of 2026-10-20 (S2).

## Decision

1. **A match must be the opened project, one of its ancestors, or a work tree the project's own `.git` vouches for.** Below `$CLAUDE_PROJECT_DIR` the nested directory's git dir must be the project's (and then its toplevel must be the project's toplevel), or one of the project's `worktrees/<name>` admin dirs whose `gitdir` back-link names that very work tree. Asking the nested directory alone is not enough: a planted `.git` gitfile (`gitdir: ../../.git`) makes the nested git report the project's repository. Inside the vouched work tree, a git-ignored directory other than its root (`node_modules/<pkg>`) is refused. A match outside the project (a directory added with `/add-dir`, or a symlink inside the project pointing out of it) is refused too. Anything else — another repository, no repository, git failing — is refused. The git calls run in one subshell with `GIT_DIR`, `GIT_COMMON_DIR`, `GIT_WORK_TREE` and `GIT_INDEX_FILE` unset, so an inherited override cannot vouch for a clone.
2. **A refused match falls back to the opened project** and prints one line to stderr. The project's own hooks keep running; the nested ones never do.
3. **The check runs only in the nested case**, inside the registered command itself, because the dispatcher it would otherwise call is the untrusted code. The common path (a match at or above the opened project) costs nothing extra.
4. **Strict on workspaces.** A folder that is not a git work tree, opened above several repositories that each have an install, no longer runs those nested installs' hooks. Open the project itself, or install at the workspace.
5. **Per provider.** Claude carries the guard (`hooks.py` `NESTED_GUARD`, mirrored byte for byte by `scripts/install.sh` `_HOOK_TEMPLATE`). Codex does not: each `exec_command` is its own process, so the hook directory never follows a `cd`. opencode does not walk: its plugin spawns hooks with the project directory as `cwd`. `tests/test_hook_project_root.py` `NESTED_GUARD` keeps this decision per provider in `ALL_PROVIDERS`.

## Consequences

### Positive
- Entering an untrusted checkout no longer runs its hooks, nor drops the project's credential guard.
- Existing installs pick the guard up on the next `devteam sync` (`hooks.wire` rewrites our command in place) or, for a v2 install, on the next `update.sh`/`install.sh`, which now also rewrites an earlier root-walk command of ours (a user's wrapper around it is kept).

### Negative
- A git submodule carrying its own install is refused: its repository is not the project's.
- A non-git workspace with nested installs loses those installs' hooks (decision 4).
- The nested case adds about four `git` forks per hook call.

### Neutral
- Remaining exposure, by design: an untracked, non-ignored directory inside the project's work tree (an archive extracted into `dl/pkg/`) is part of the work tree and keeps its hooks; so does any match when `$CLAUDE_PROJECT_DIR` is unset.
- Codex's exemption rests on each `exec_command` running as its own process; it is not pinned by a test.
- `case` patterns in the guard open with `(`: macOS `/bin/bash` 3.2 cannot parse a bare `pat)` inside `$(…)`.
- Codex and opencode launchers are unchanged; a provider whose hook directory can follow the agent must add the guard and flip its entry in the test map.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Accept a nested match only if the store's registry lists it | The store path is platform-specific and a planted pointer names its own fake store; the trusted store would have to be resolved inside a one-line shell command |
| Stop walking below `$CLAUDE_PROJECT_DIR` entirely | Breaks monorepo sub-projects and worktrees with their own hooks, both supported and tested |
| Allow nested installs when the opened folder is not a git repository | Leaves the hole open in exactly that setup |
| Compare `--show-toplevel` instead of the common dir | A worktree of the same repository has its own toplevel and would be refused |
