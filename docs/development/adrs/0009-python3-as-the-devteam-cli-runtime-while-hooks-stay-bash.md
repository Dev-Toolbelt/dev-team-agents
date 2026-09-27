# ADR-0009: Python3 as the devteam CLI runtime while hooks stay bash

**Date:** 2026-09-27
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

v3 introduces a real CLI (`devteam bind|sync|pin|update|migrate|doctor|cred`) and, with it, the
first release target on Windows. The repository today is bash plus optional python3: every hook
is `#!/usr/bin/env bash`, and `scripts/lib/state.sh` guards each python call with
`command -v python3` and falls back when it is absent. `scripts/lib/render_provider.py` is the
one component already written in python.

Two constraints shape the choice:

1. **bash is already mandatory on every platform.** The providers invoke the hooks, and the
   hooks are bash. On Windows that means git-bash/MSYS is already a prerequisite. Choosing a
   CLI language does not remove that.
2. **The CLI is where paths hurt.** It resolves `%APPDATA%` versus `%LOCALAPPDATA%`, writes
   absolute store paths into project artifacts, creates symlinks or falls back to copies, takes
   locks, and merges JSON. Under MSYS, absolute-path translation is exactly the layer that
   corrupts this class of work.

## Decision

The CLI is **python3**, shipped as `scripts/cli/devteam` with the implementation in the
`scripts/lib/devteam/` package. Hooks remain bash and are unchanged by this ADR.

python3 is promoted from "optional, with fallback" to a **hard dependency of the CLI**. The
Homebrew formula and the winget package declare it, so the user never resolves it by hand. The
v2 code paths that already tolerate its absence — `state.sh`, the `install.sh` no-python3
fallback heredoc — keep their fallbacks for one deprecation cycle, per the Immutability
Contract.

**The floor is python 3.9**, checked in `scripts/cli/devteam` before the first import so an older
interpreter gets a one-line message instead of a SyntaxError from a library module, and tested
explicitly in CI. Testing only the newest interpreter is not equivalent: it hid a real defect
once — `tarfile`'s extraction filter defaults to `data` only from 3.14, which masked an
unsafe-member bug on every version a user is likely to have.

Only the standard library is used: `json`, `pathlib`, `os`, `shutil`, `urllib`, `argparse`,
`uuid`, `secrets`, `hashlib`, `ssl`, `tarfile`, `unittest`. No third-party dependency, no
virtualenv, no lockfile. That keeps the
install surface identical to what brew and winget can express in a single dependency line.

The CLI also owns the `--json` contract every command must honour, because the Electron app is
a client of the CLI (ADR-0011) and must never parse human-formatted output.

Since CI had **no python gate at all** — `.github/scripts/ci/01-lint.sh` runs shellcheck over
`scripts` and `helpers` and nothing over `*.py` — this ADR adds a blocking compile + unit-test
step. A CLI with no gate is a CLI that breaks silently on a platform the author did not use.

## Consequences

### Positive
- Native path handling on Windows, with no MSYS translation between the CLI and the filesystem.
- `os.replace` for atomic writes, real locking, `shutil` for copy modes, `urllib` for updates —
  all stdlib, all cross-platform, none of it reimplemented in bash.
- JSON becomes a first-class data structure instead of a `python3 -c` heredoc inside bash.
- Testable: `unittest` with `$DEVTEAM_HOME` pointed at a temporary directory.

### Negative
- A hard dependency where there was a soft one. A user with bash and no python3 can still run
  hooks, but not the CLI.
- Two languages in one codebase, with the boundary (hooks vs CLI) needing to stay explicit.
- Shellcheck no longer covers the most complex logic in the repository, which is why the python
  gate is added in the same change rather than later.

### Neutral
- `render_provider.py` already established python in `scripts/lib/`; this extends a precedent
  rather than introducing a language.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| bash | Zero new dependencies and perfectly consistent with today's tree, but puts the store's absolute paths and symlink fallbacks inside MSYS on Windows — the single place this design is most fragile. |
| Node/TypeScript shared with the Electron app | One language and shared types across CLI and app, but Node becomes a hard dependency of the whole framework, including for users who never open the app. |
| Compiled binary (Go/Rust) | Best startup time and no runtime dependency, but adds a cross-compilation matrix and a toolchain to a repository whose contributors work in bash and markdown. |
