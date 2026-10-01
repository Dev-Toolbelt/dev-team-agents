# Wiki

Domain knowledge that is **not derivable from reading the code** — non-obvious behaviors,
platform gotchas, and constraints that would surprise the next agent. Format and protocol:
`skills/shared/docs-sync/references/wiki-format.md`.

This index is the only part of the wiki loaded unconditionally. Grep the **Keywords** column to
decide whether an entry is worth opening; entries are never deleted, only superseded.

## Index

| Entry | Keywords | Read it when |
|-------|----------|--------------|
| `bash/empty-array-under-set-u.md` | bash, set -u, unbound variable, empty array, macOS, bash 3.2, KNOWN_DRIFT | A script with `set -u` and a deliberately empty array dies the first time it has something to report |
| `bash/set-e-inside-a-cleanup-trap.md` | bash, set -e, errexit, pipefail, EXIT trap, cleanup, teardown, command substitution, brew uninstall, silent skip | An EXIT-trap teardown stops halfway and the checks that would have reported it are skipped too |
| `bash/shellcheck-blind-spots.md` | shellcheck, SC2034, SC1073, indirect expansion, directive, false positive, source-path | shellcheck reports a variable as unused, or stops checking a file for no visible reason |
| `electron/ipc-channels-need-the-trusted-sender-check.md` | electron, IPC, ipcMain.handle, security, trustedHandler, trustedRenderer, audit trail | After rebasing app work on main, grep for new `ipcMain.handle` calls |
| `electron/project-naming-scope.md` | project, name, BindRequest, settings.json, app-local, not portable, machine-local, product naming | Deciding whether project names belong in the app-local settings or the CLI's committed record |
| `electron/userdata-collides-with-the-cli-store.md` | electron, userData, getPath, productName, APP_NAME, Application Support, APPDATA, second writer, setPath | An Electron app is named after a CLI whose data directory follows the same convention, or a store-wide operation reports a size that makes no sense |
| `git/worktree-exclude-scope.md` | worktree, info/exclude, gitignore, GIT_DIR, GIT_COMMON_DIR, untracked | Keeping generated files out of git in a repository that uses linked worktrees |
| `hooks/a-plan-is-not-a-task-list.md` | task board, plan, plan-mode, TaskCreate, update_plan, todowrite, native task list, empty board | The board shows nothing although the session planned and ran work |
| `hooks/hook-stdout-never-reaches-the-user.md` | hook, stdout, SessionStart, Stop, notification, banner, DEV TEAM AGENTS, model context, provider, desktop app | A hook needs to tell the user something, or a notice a hook prints is never seen |
| `hooks/review-state-is-inferred-not-reported.md` | review state, task board, review window, marker, inferred, outcome, in review, findings | The In Review column is empty, or a task shows "result not read" after a review |
| `hooks/provider-todo-tool-payloads.md` | hook, todo tool, TaskCreate, TaskUpdate, update_plan, todowrite, provider payload, PreToolUse, PostToolUse, task id | Capturing task activity from each provider's different todo tool payload shape |
| `homebrew/verifying-a-formula-without-a-tap.md` | homebrew, brew tap-new, brew trust, trust.json, brew audit, audit --new, brew style, XDG_CONFIG_HOME, Formulary, requires formulae to be in a tap, notable enough | Homebrew rejects a formula file outside a tap, or `brew audit <path>` is disabled |
| `python/exclusive-create-instead-of-a-lock.md` | O_EXCL, os.open, machine-id, circular dependency, lock, os.link, Windows, race, singleton | Creating a file exactly once from concurrent callers, especially when the lock would depend on the file |
| `python/path-containment-and-symlinks.md` | realpath, symlink, containment, relative_to, startswith, /private/var, path traversal | Deciding whether a path stays inside a directory before writing to or removing it |
| `python/tarfile-extraction-filter.md` | tarfile, extractall, filter, data, tarslip, linkname, symlink, CVE, python 3.14 | Extracting an archive you did not create, or pinning which interpreter CI tests |
| `security/credential-guard-heredocs.md` | credential-guard, heredoc, credentials.local.json, session-summary, false positive, false negative, newline, segment, refuse | The credential guard blocks a heredoc that only mentions a credential file, or lets a dump on the line after a heredoc through |
| `security/macOS-keychain-add-generic-password-double-entry.md` | macOS, keychain, security, add-generic-password, double-entry, prompt, exit code, -w flag, readpassphrase, 128 characters, truncation, tty, security -i | Writing a value to the macOS keychain via `security add-generic-password` in a non-interactive context |
| `store/bind-over-a-v2-install.md` | v2, vendored, bind, migrate, doctor, git, tracked, info/exclude, symlink, leftover | A project that used the v2 install was bound instead of migrated, or `git status` shows framework links as modified after a bind |
| `store/pre-root-v2-install.md` | v2, pre-root, .claude/dev-team-agents, migrate, migrate-to-root, bind, project.json, untrack, layout 1 | A project's v2 install sits under `.claude/`, or a bind left `.dev-team-agents/project.json` on a project it refused |
| `store/command-reads-v2-user-data-path.md` | v3, bind, state.json, preferences.json, data-dirs, bound project, user-data, version, health-check, update, git-common-dir | A command shows `vunknown` or default preferences in a bound project, or resolves the project root from `git rev-parse` |
| `store/legacy-preferences-ignored-after-bind.md` | preferences, cascade, v2, user-data, bind, upgrade, collision, quarantine, import, layout 1 | A project's preferences seem ignored after a bind, or `devteam upgrade` refuses because `preferences.json` already exists in the store |
| `store/machine-identity-in-roaming-profile.md` | machine-id, roaming profile, Windows, ADR-0007, data store, network mount, VM clone, disk image | A store in a roaming profile replicates between machines, making a single machine-id ambiguous |
| `store/machine-local-basename-matches-any-depth.md` | machine-local, basename, MACHINE_LOCAL_RECORDS, task-board, portable, export, gitignore | Adding a new machine-local record, or when a user's directory name collides with the classifier |
| `store/plugin-settings-location.md` | plugins, plugin-settings, runtime link, "enabled": true, 02d-plugins.sh, OPTIONAL_TREES, graphify.json, legacy migration, ADR-0019 | Before writing or hand-editing plugin settings, or when a hook ignores an enabled plugin |
| `store/runtime-root-at-the-cited-path.md` | core, pointer, scripts, templates, runtime root, project-relative, new-adr.sh, reuse-lint, design-token-lint, exit 0, silent gate | A framework path an agent runs does not exist in a bound project, or a Stop gate never reports anything |
| `store/sync-wires-hooks-the-linked-core-lacks.md` | devteam sync, hook, hooks.EVENTS, core version, linked tree, missing hook, symlink, scripts | A tool call fails after `devteam sync`, or a project needs to upgrade to resolve its core version |
| `testing/fixture-circularity.md` | fixture, migration, test design, circular, legacy layout, false confidence | Writing a test for a migration away from a layout the current code no longer produces |
| `testing/windows-launcher-testing.md` | windows, launcher, fixture, spawn, shell false, CreateProcessA, _spawnv, argv quoting, PE, .exe, .scenario, PASS_THROUGH_ENV, CVE-2024-27980 | A Windows test spawns the fake CLI and the child gets a mangled argument, no scenario, or nothing executable at all |
