# ADR-0060: devteam tools installs the pinned helper tools without asking, on install, bind and health check

**Date:** 2026-10-31  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/tools.py`, `scripts/lib/devteam/tool-pins.json`, `scripts/lib/provision-tools.sh`

## Context

Agents work better with a few tools on the machine: `rg`, `fd`, `jq`, `ast-grep`, `tokei` and
`delta` cut token cost, `graphify` gives code navigation, `gitleaks` powers the commit guard
(ADR-0059) and `semgrep` the security audits. Until now they were optional: the health check
only warned, and `/devteam:install` asked before each install. Most users do not know these
tools and cannot judge the question, so the tools were usually missing, and with them the
secret-scan gate.

The install also went through system package managers, which on Linux means `sudo` and cannot
run unattended. The skill installed graphify by the wrong package name (`graphify` instead of
the PyPI distribution `graphifyy`).

## Decision

`devteam tools install` is the one place that installs these tools, and it installs every
missing one without asking:

- **Where it runs:** the CLI installers (`install-cli.sh`, the Windows installer), every
  `devteam bind` (all providers), the standalone project installers (`install.sh`,
  `install-opencode.sh`, `install-codex.sh` through `provision-tools.sh`), the health check
  (Category 13) and `/devteam:install`. Homebrew installs the CLI's tools as formula
  dependencies, because a formula cannot download into the user's home. `sync`, `sync --all`
  and `migrate` never install. `bind --no-tools` and `start --no-tools` skip the step; the
  desktop app uses them and runs `tools install` as a step of its own, because its deadline for
  a write (5 minutes) is shorter than a first download can take.
- **Who may run it:** `tools` is exempt from the account gate (ADR-0029). The tools carry no
  license value, and the CLI installers run the command before anyone has signed in.
- **What it installs:** exactly the tools in `tool-pins.json`. A binary tool is a pinned release
  asset, checked against its sha256 before anything is written, with only the named executable
  read out of the archive. A Python tool gets its own virtualenv, created with a settled
  interpreter (3.13 down to the tool's floor, before any newer one) and
  `pip install --only-binary=:all: <package>==<version>`, run isolated (`-I`) from the tools home
  so a project's files can never shadow `venv` or `pip`. No source build ever runs. Homebrew is a fallback for a platform with no pinned
  build, installed into Homebrew's own user-owned prefix; no `sudo`, no `apt`, `dnf`, `winget`
  or other system package manager.
- **What the user sees:** the list, one line per tool, as it installs, under a header naming the
  opt-out. `DEVTEAM_SKIP_TOOLS=1` turns every install off.
- **Failure never propagates:** a tool that cannot be installed is reported as `skipped` or
  `failed` with a reason; the install, bind or health check carries on, and the next bind or
  health check retries.

This is a named exception to two rules. The health check's "WARN only" for tools
(`setup-health-check`, Categories 12–13) no longer holds for Category 13; Category 12 (Python
itself) stays WARN only. And it stands beside ADR-0058's Command Run Plan without breaking it:
that rule excludes a `devteam` CLI call a command prescribes (`/devteam:install`, the health
check), and the installers and `bind` are not agent-run command flows at all.

## Consequences

### Positive
- A newly bound project has the tools its agents expect, including the gitleaks guard.
- One code path installs on every OS, without `sudo`, with verified downloads.

### Negative
- The first install downloads well over 100 MB (semgrep is most of it) and can take minutes.
  Later binds on the same machine download nothing.
- Pins age. `tool-pins.json` has to be bumped by hand; `tests/test_tools.py` checks its shape
  and platform coverage, not freshness.
- Python tools pin the top-level version only. Transitive dependencies resolve at install time
  from PyPI over HTTPS, as wheels; hashing them all would mean vendoring a lock file per platform
  and interpreter. This runs on every bind and health check that finds the tool missing.
- tokei publishes no digests and no binaries newer than 12.1.2; its digests were computed from
  the downloaded assets (trust on first use).
- Network failures, proxies and missing platforms leave tools uninstalled until the next run.

### Neutral
- semgrep has no supported native Windows build and is skipped there with a pointer at WSL or
  Docker. graphify and semgrep need Python 3.10+; with only an older interpreter they are skipped
  unless Homebrew can install them.
- `bind --json` gains a `tools` field. The change is additive (ADR-0014).

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep asking before each install | Users do not know the tools and cannot answer; in practice they stayed missing |
| System package managers (`apt`, `dnf`, `winget`) | `sudo` or UAC prompts break an unattended install, and versions differ per distribution |
| Install at CLI install time only | A failed or skipped install never recovers until someone runs the health check |
| Install in `sync` as well | `sync --all` touches every project at once and should never reach the network |
