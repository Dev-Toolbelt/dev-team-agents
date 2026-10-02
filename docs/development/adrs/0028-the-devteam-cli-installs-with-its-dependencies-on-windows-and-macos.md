# ADR-0028: The devteam CLI installs with its dependencies on Windows and macOS

**Date:** 2026-10-02  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers

## Context

The desktop app is a client of the `devteam` CLI and ships no copy of it (ADR-0011, ADR-0015 § 5).
ADR-0027 put the app in users' hands as a direct-download beta, but left the CLI without a channel:
its risk table records that "no formula or winget package exists", and that on Windows the app finds
the CLI only through `DEVTEAM_CLI_PATH` or `cliPath` with Python 3 on PATH. The first Windows install
of the beta ended exactly there — a working app on a screen that said "No devteam CLI on this host".

ADR-0011's risk table had already named the gap: the winget manifest's `InstallerType: exe` was "a
design placeholder, not a decision", and whether the CLI would be frozen, wrapped, or need a system
python3 was open. The Homebrew formula works (`packaging/verify-formula-locally.sh` installs it
through a real Homebrew) but no tap publishes it, and a user without Homebrew had only a clone.

What the CLI and the harness need at runtime, measured from the tree:

| Dependency | Needed by | Windows | macOS |
|---|---|---|---|
| Python 3.9+ | the CLI; the hooks (`scripts/lib/python.sh`, ADR-0026) | absent by default | present only with the Command Line Tools |
| Git (and its bash) | the hooks are bash and call `git`; ADR-0026 resolves Git Bash | Git for Windows | the Command Line Tools |
| `curl`, `tar` | `update`, installers | shipped with Windows 10/11 | shipped |

The CLI imports only the standard library, so any CPython 3.9+ runs it.

## Decision

1. **Windows: a per-user NSIS installer for the CLI, carrying its own Python.** `packaging/windows-cli/`
   builds `devteam-setup-<version>-<arch>.exe` (x64, arm64). It installs into
   `%LOCALAPPDATA%\Programs\devteam` without elevation:
   - `python\` — the official CPython *embeddable* distribution, pinned by version and SHA-256 (the
     digest cross-checked against python.org's sigstore bundle) in `packaging/windows-cli/pins.json`.
   - `cli\scripts\` — the CLI exactly as the Homebrew formula installs it: `scripts/cli/devteam` and
     the `devteam` package beside it.
   - `bin\devteam.exe` — a real executable, so the app's resolution finds it without a shell
     (ADR-0015 § 5 never starts one). It is distlib's script launcher, the stub pip uses for every
     console script, written at install time with an absolute shebang to `python\python.exe`.
     PyInstaller was rejected: an unsigned PyInstaller executable is a common antivirus false
     positive, and this installer is unsigned until an Authenticode certificate exists.
   - `payload\` — the framework tree of the same version, installed into the store with
     `devteam store install` so the CLI is usable offline right after setup. An already-installed
     version is left alone, and an existing `current` is never moved.
   - `bin\` is appended to the user `PATH`; the uninstaller removes that entry and the install
     directory, and **never touches the store** (`core/`, `data/` survive, as with every channel).
2. **Git for Windows is offered, not bundled.** When no Git Bash is found (the same folders
   `devteam.shells.find_git_bash()` searches), the interactive installer offers
   `winget install --id Git.Git -e --scope user`. A silent install (`/S`, which winget uses) skips the
   prompt; the winget manifest declares `Git.Git` as a package dependency instead.
3. **The hooks may use the CLI's Python.** `scripts/lib/python.sh` falls back to
   `%LOCALAPPDATA%\Programs\devteam\python\python.exe` on Windows after `python3`, `python` and
   `py -3`, so a machine with no system Python runs the hooks too.
4. **macOS: a Homebrew tap plus a script for machines without Homebrew.** The formula is published
   from the `Dev-Toolbelt/homebrew-devteam` tap that `packaging/README.md` already names
   (`brew install dev-toolbelt/devteam/devteam`), which pulls in Python. Creating that repository
   is a maintainer action outside this tree; until it exists the script below is the macOS channel,
   and the app's remedy names only the script. `scripts/install-cli.sh` (`curl | bash`) serves everyone else: it requires the Command
   Line Tools (starting `xcode-select --install` when they are missing), installs the CLI into
   `~/.local/share/devteam` with `~/.local/bin/devteam`, and runs `store install`. It is idempotent.
5. **The app searches both new locations and can install the CLI itself.** `resolve.ts` adds
   `%LOCALAPPDATA%\Programs\devteam\bin` (Windows) and `~/.local/bin` (macOS) to its known locations,
   so an app started before `PATH` changed still finds the CLI. On Windows the no-CLI screen gets an
   **Install the CLI** action: the main process reads the latest `vX.Y.Z` GitHub release, downloads the
   installer for the host architecture and that release's `SHA256SUMS.txt` from GitHub hosts only,
   refuses on a digest mismatch, runs the installer (no shell) and looks again. On macOS the screen
   shows the two commands to copy. The app still **ships** no CLI: what it installs is the newest
   published one, which then updates itself through `devteam update` — the failure ADR-0011 forbids,
   an older bundled CLI writing a newer store, cannot arise from it.
6. **Releases carry the Windows installers.** The `vX.Y.Z` release workflow builds them on a Windows
   runner, smoke-tests a silent install, and uploads them with their `SHA256SUMS.txt`.

## Alternatives Considered

### Require a system Python, installed through winget
- **Pros**: a smaller installer; the system Python serves other tools too.
- **Cons**: depends on winget being present and working; changes the user's global Python; the
  Microsoft Store `python3` stub (ADR-0026) still shadows it in Git Bash.
- **Why rejected**: the embedded interpreter is 12 MB and makes the CLI independent of everything
  on the machine except Windows itself.

### Freeze the CLI with PyInstaller
- **Pros**: one executable, no interpreter directory.
- **Cons**: unsigned frozen executables are routinely flagged by Defender; the hooks would still
  need a Python.
- **Why rejected**: the embedded Python serves the CLI and the hooks, and the launcher is a stub
  every pip install already puts on Windows machines.

### Bundle the CLI inside the app
- **Why rejected**: ADR-0011 forbids it — a bundled, older CLI writing a newer store.

### A signed `.pkg` for macOS
- **Why rejected for now**: without a Developer ID the `.pkg` is blocked harder by Gatekeeper than a
  script the user runs, and it would still need Python from somewhere.

## Consequences

### Positive
- A Windows user installs the CLI and the app, and the app works — Git is one confirmation away.
- The hooks work on Windows without a system Python.
- macOS users get `brew install` or a one-line script; both end with the app finding the CLI.

### Negative
- The Windows installer is unsigned, like the app (ADR-0027): SmartScreen warns, and the user
  approves software the OS could not verify.
- The pinned Python must be bumped by hand for security fixes.
- The app gains its first outbound network call from the main process, restricted to GitHub hosts.

## Risks

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **The digest proves integrity, not authorship.** The app checks the installer against `SHA256SUMS.txt` from the same release. | Same as ADR-0027: immutable releases; the workflow builds from the tag. | Whoever controls the GitHub account controls both files, until signing. |
| **The pinned Python ages.** A CPython security release does not reach installed CLIs by itself. | The pin is one file; re-running the installer replaces `python\`. | Depends on a maintainer bumping it. |
| **Windows-only paths are not run on the maintainers' Macs.** The installer, the launcher and the PATH edit run only on Windows. | The release workflow installs silently on a Windows runner and runs `devteam.exe path --json`. | The interactive wizard and the Git prompt are exercised only by a person. |
| **`curl \| bash` asks the user to trust a script.** | The script is in the repository, served from a tag, and does nothing that needs `sudo`. | The same trust the existing `install.sh` already asks for. |
