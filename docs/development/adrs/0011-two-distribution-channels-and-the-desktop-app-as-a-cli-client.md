# ADR-0011: Two distribution channels and the desktop app as a CLI client

**Date:** 2026-09-27
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

v3 ships to macOS and Windows on day one, and adds an Electron desktop app for binding
projects, reading agents and skills, editing preferences and managing credential references.

Homebrew was the requested channel, but **brew does not run on Windows** — it supports macOS
and Linux, and on Windows only inside WSL, which is a different filesystem and a different
`$HOME` than the user's actual projects. One tap cannot cover both targets.

The app raises a second question: it needs the same bind, merge and credential logic the CLI
has. Implementing that logic twice guarantees the two drift, and the one that drifts silently is
the one the user trusts.

## Decision

**Two channels, one release workflow.**

| Target | CLI | App |
|--------|-----|-----|
| macOS | Homebrew tap — formula `devteam` | Homebrew tap — cask |
| Windows | winget | winget |
| Linux | not a release target yet; the path resolver already handles XDG | — |

winget is chosen over Scoop and Chocolatey because it ships with Windows 10/11, so the user
installs nothing before installing this. The cost is publication by pull request to Microsoft's
`winget-pkgs`, with review and a signed installer — accepted, since the Electron build produces
a signed installer regardless.

macOS artifacts are signed and notarised; the Windows installer is code-signed. The app carries
its own auto-update channel; the **framework** is updated by `devteam update`, which is a
different thing on a different cadence.

**The app is a client of the CLI.** Every action in the UI invokes `devteam <command> --json`
and renders the result. No bind rule, no preference merge, no credential resolution is
reimplemented in TypeScript. This costs a stable JSON contract on every subcommand — with
contract tests in CI — and buys a single source of truth, so the terminal and the UI cannot
disagree.

**The app is never a prerequisite.** Every capability is reachable from the CLI. A user who
never installs the app loses nothing but the screens.

**Compatibility is declared, not assumed.** The app states `minFrameworkVersion` and the
framework states `minAppVersion`. When the store is ahead of the app, the app degrades to
read-only and says so, instead of writing a structure it does not understand.

## Consequences

### Positive
- The user installs with the tool their platform already has.
- UI and CLI cannot diverge in behaviour, because there is one implementation.
- The JSON contract that the app needs also makes the CLI scriptable for users and for CI.
- Framework and app update independently, so an app release is not gated on a framework release.

### Negative
- Two publication pipelines, two signing identities, and a winget PR round-trip per release.
- Node enters the repository for the first time. It is confined to `app/` and to CI; the
  framework itself stays python3 + bash.
- The JSON contract becomes public API: changing an output shape is a breaking change.
- Linux users have no channel yet, only a manual install.

### Neutral
- Electron was chosen over Tauri in D1; this ADR records the distribution consequences of that
  choice, not the choice itself.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Homebrew only, telling Windows users to use WSL | WSL has a different `$HOME` and filesystem than the user's projects; the store would bind paths that the Windows-side editor and CLI cannot resolve. |
| Scoop for Windows | A bucket we control with no external review, closest analogue to a tap — but the user must install Scoop first, and the audience is narrower than winget's. |
| Chocolatey | Strong in corporate/CI Windows, but gallery review plus nuspec/PowerShell packaging for no benefit over winget's preinstalled reach. |
| Own installer only (.exe/.msi + PowerShell script) | Full control and no gatekeeper, but a private update channel to maintain and much worse discovery. |
| App with its own implementation of bind/preferences | Removes the JSON contract work, and guarantees that UI and CLI eventually disagree about what a bind is. |
