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
| `bash/shellcheck-blind-spots.md` | shellcheck, SC2034, SC1073, indirect expansion, directive, false positive, source-path | shellcheck reports a variable as unused, or stops checking a file for no visible reason |
| `git/worktree-exclude-scope.md` | worktree, info/exclude, gitignore, GIT_DIR, GIT_COMMON_DIR, untracked | Keeping generated files out of git in a repository that uses linked worktrees |
| `python/exclusive-create-instead-of-a-lock.md` | O_EXCL, os.open, machine-id, circular dependency, lock, os.link, Windows, race, singleton | Creating a file exactly once from concurrent callers, especially when the lock would depend on the file |
| `python/path-containment-and-symlinks.md` | realpath, symlink, containment, relative_to, startswith, /private/var, path traversal | Deciding whether a path stays inside a directory before writing to or removing it |
| `python/tarfile-extraction-filter.md` | tarfile, extractall, filter, data, tarslip, linkname, symlink, CVE, python 3.14 | Extracting an archive you did not create, or pinning which interpreter CI tests |
| `security/macOS-keychain-add-generic-password-double-entry.md` | macOS, keychain, security, add-generic-password, double-entry, prompt, exit code, -w flag | Writing a value to the macOS keychain via `security add-generic-password` in a non-interactive context |
| `store/machine-identity-in-roaming-profile.md` | machine-id, roaming profile, Windows, ADR-0007, data store, network mount, VM clone, disk image | A store in a roaming profile replicates between machines, making a single machine-id ambiguous |
| `testing/fixture-circularity.md` | fixture, migration, test design, circular, legacy layout, false confidence | Writing a test for a migration away from a layout the current code no longer produces |
