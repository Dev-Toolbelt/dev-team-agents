# The app's environment allowlist hid Git Bash from the CLI

**Origin:** opencode and Codex bind failed from the desktop app on Windows while the same command worked in a terminal | 2026-11-25
**Tags:** Windows, Git Bash, ProgramFiles, environment, allowlist, childEnvironment, desktop app, bash not found, codex, opencode

> A command that works in the user's terminal and fails from the app usually differs in the environment the app passed, not in the machine.

---

## What it is

The app starts the CLI with `childEnvironment` (`app/src/cli/invoke.ts`), which keeps only the variables in
`PASS_THROUGH_ENV`. On Windows the CLI uses an absolute Git Bash only (ADR-0026), found by
`devteam.shells.find_git_bash`. Git for Windows adds `<root>\cmd` to PATH, never `<root>\bin`, so `bash`
is not on PATH and the lookup falls back to `%ProgramFiles%\Git\bin\bash.exe`. `ProgramFiles` was not in
the allowlist, so from the app that fallback never ran and every opencode or Codex install failed with
"bash ... was not found on PATH", on a machine with Git in its default folder.

## How it works now

- The app passes `ProgramFiles`, `ProgramFiles(x86)` and `ProgramW6432`.
- `find_git_bash` also derives `<root>\bin\bash.exe` from the `git.exe` on PATH (`cmd`, `bin`,
  `mingw64\bin` layouts), which covers a non-default install and any caller with a reduced environment.
- Every step accepts an absolute path only. `shutil.which` on Windows also searches the current folder,
  so a relative result could run a `bash.exe` shipped by the cloned project the CLI runs in.
- The Windows error names Git Bash and lists every place it looked (`shells.GIT_BASH_SEARCH`).

## Gotchas

- Adding a variable to the allowlist is the fix only for what the CLI reads directly. The installers get a
  second, smaller environment from `providers._installer_env`.
- Diagnose by comparing environments: `Get-Command git` in the user's terminal shows where Git is, and the
  app's allowlist shows what the CLI can see of it.
