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
     version is left alone, and an existing `current` is never moved; when it differs, the
     installer prints the `devteam store use` command that would move it.
   - `bin\` is appended to the user `PATH`; the uninstaller removes that entry and only the
     entries it wrote — never a recursive delete of the install directory, which a `/D=` or
     `winget --location` could point at a shared folder; an install directory not named
     `devteam` gets a `devteam` folder created under it. It **never touches the store**
     (`core/`, `data/` survive, as with every channel).
2. **Git for Windows is offered, not bundled.** When no Git Bash is found (the same folders
   `devteam.shells.find_git_bash()` searches), the interactive installer offers
   `winget install --id Git.Git -e --scope user`. A silent install (`/S`, which winget uses) skips the
   prompt; the winget manifest declares `Git.Git` as a package dependency instead.
3. **The hooks may use the CLI's Python.** `scripts/lib/python.sh` falls back to
   `%LOCALAPPDATA%\Programs\devteam\python\python.exe` on Windows after `python3`, `python` and
   `py -3`, so a machine with no system Python runs the hooks too.
4. **macOS: a Homebrew tap plus a script for machines without Homebrew.** The formula is published
   from the public `Dev-Toolbelt/homebrew-devteam` tap (`brew install dev-toolbelt/devteam/devteam`),
   which pulls in Python. The tap holds no formula until the first release that contains the CLI;
   until then the script is the macOS channel, and the app's remedy names only the script.
   `scripts/install-cli.sh` (`curl | bash`, fetched from `main`) serves everyone else: it requires
   the Command Line Tools (starting `xcode-select --install` when they are missing), installs the CLI
   into `~/.local/share/devteam` with a `~/.local/bin/devteam` launcher naming the verified
   interpreter, and runs `store install`. It is idempotent, and installs only from a `vX.Y.Z`
   *release* — a bare tag is not enough.
5. **The app searches both new locations and can install the CLI itself.** `resolve.ts` adds
   `%LOCALAPPDATA%\Programs\devteam\bin` (Windows) and `~/.local/bin` (macOS) as a last step, so an
   app started before `PATH` changed still finds the CLI. On Windows the no-CLI screen gets an
   **Install the CLI** action: the main process reads the newest `vX.Y.Z` GitHub release, downloads
   the installer for the host architecture and that release's `SHA256SUMS.txt` from GitHub hosts
   only, refuses on a digest mismatch, runs the installer (no shell) and looks again. Only a release
   `release.yml` created (author `github-actions[bot]`) is accepted, the download is capped and timed
   out, one install runs at a time, and the file is written with a Mark-of-the-Web so SmartScreen
   evaluates it. On macOS the remedy gives the script. The app still **ships** no CLI: what it
   installs is the newest published one.
6. **The CLI is upgraded by its channel, not by `devteam update`.** `devteam update` installs a new
   *framework* version into the store; it never replaces the CLI's own code. The CLI moves with
   `brew upgrade`, a re-run of `install-cli.sh`, or a re-run of the Windows installer (the app's
   action included). Until a CLI-versus-store check exists, an old CLI can run against a newer
   store; ADR-0011's schema refusal (`registry.load()`) is what bounds the damage.
7. **Releases are created by the workflow, and a `vX.Y.Z` stays "latest".** On a `vX.Y.Z` tag,
   `release.yml`:
   - `windows-cli-installer` builds both installers on a Windows runner, installs the **x64** one
     silently, checks `devteam.exe version --json`, that `store list --json` reports the bundled
     version as current, the user PATH, and an uninstall that leaves the store; then **creates the
     tag's GitHub release when it has none** (public, not a draft) and attaches the installers and
     `SHA256SUMS.txt`. The arm64 installer is built and published but not run: hosted x64 runners
     cannot execute it.
   - `publish-homebrew-tap` pushes the formula to the tap **after** the macOS job installed it from
     the real tarball and passed its test, and before the in-repo bump PR is merged. That departs
     from ADR-0011's "a maintainer reviews the diff before it lands" on purpose: the reviewed
     artifact would be the same bytes, and the verify job is the stronger check. The PR keeps the
     repository's copy in step.
   - A `vX.Y.Z` release must stay GitHub's "latest": `devteam update`, `install.sh` and the update
     check read `releases/latest`. The app's `app-v*` releases are therefore published as
     pre-releases not marked latest (`app/README.md`). The new code paths also pick the newest
     `vX.Y.Z` by version — a second guard for the same rule, not a second rule.

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
| **The digest proves integrity, not authorship.** The app checks the installer against `SHA256SUMS.txt` from the same release, so whoever can publish a release can publish both. | Only workflow-created releases are accepted; immutable releases; the Mark-of-the-Web lets SmartScreen judge the file; the workflow builds from the tag. | **Open:** a compromised workflow, or a token that can push a tag, still produces an accepted release. Authenticode signing, a signed sums file, or verified build attestations would close it — a decision for the maintainers. |
| **`install-cli.sh` checks transport only.** The source tarball has no digest or signature. | Releases only, never bare tags; the script body runs only once fully downloaded. | GitHub's tag archives are not byte-stable, so a digest needs a release asset of its own — not done yet. |
| **The pinned Python ages.** A CPython security release does not reach installed CLIs by itself. | The pin is one file; re-running the installer replaces `python\`. | Depends on a maintainer bumping it. |
| **Windows-only paths are not run on the maintainers' Macs.** The installer, the launcher and the PATH edit run only on Windows. | The release workflow installs the x64 installer silently on a Windows runner and checks `devteam.exe`, the store, the PATH and the uninstall. | The interactive wizard, the Git prompt, an upgrade over a running install and the arm64 installer are exercised only by a person. |
| **`curl \| bash` asks the user to trust a script.** | The script is in the repository, served from `main`, wrapped so a truncated download runs nothing, and does nothing that needs `sudo`. | The same trust the existing `install.sh` already asks for. |
