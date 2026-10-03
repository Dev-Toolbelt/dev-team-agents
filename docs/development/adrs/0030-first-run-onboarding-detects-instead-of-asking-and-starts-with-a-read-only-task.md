# ADR-0030: First-run onboarding detects instead of asking and starts with a read-only task

**Date:** 2026-10-02  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers

## Context

The goal is one: a new user gets a first useful result in **under ten minutes, without reading
documentation**. Today that path requires understanding bind, layout, store and layered preferences,
choosing a project type in a conversation with `setup-assistant`, and picking one of 35 commands.
The packaging in `packaging/` has never been published, and on macOS the app cannot install the CLI.

Existing decisions that shape the answer:

- [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) — the app is a
  CLI client; every capability is reachable from the CLI; `--json` is the app's public API.
- [ADR-0028](0028-the-devteam-cli-installs-with-its-dependencies-on-windows-and-macos.md) — the CLI
  installs with its dependencies; the app installs the newest *published* CLI, never a copy of its own.
- [ADR-0029](0029-mandatory-accounts-owned-by-the-cli-licensed-through-a-signed-offline-entitlement.md)
  — sign-in is owned by the CLI. **The CLI must therefore exist before the user can sign in.**

## Decision

### 1. The first-run order is fixed: CLI → sign-in → prerequisites → project → first task

The app installs the CLI first (Windows: the verified installer of ADR-0028; macOS: `brew install`
when Homebrew is present, otherwise the published `install-cli.sh`), then shows sign-in, then the
machine prerequisites, then the project. After sign-in the user needs **at most three clicks**:
choose a folder, confirm what was detected, start the first task.

### 2. Detection lives in the CLI, the app only displays it

`devteam detect --json` reports, for a folder: the providers installed on the machine (binaries on
`PATH`), the providers the project already uses, the primary stack, and a suggested project type
(`new` / `unfinished` / `maintenance`). The stack signals have one canonical home,
`scripts/lib/stack-signals.json`; the `stack-detection` skill points at it. `setup-assistant` reads
the same result instead of asking. Every detected value is shown and can be changed in one click; on
ambiguity a sensible default is used rather than a question.

`devteam doctor --machine` reports git, Python and the providers, each finding carrying a `fix`
command and an `auto_fixable` flag. The app offers a "Fix" button only for `auto_fixable` findings,
and runs nothing without the user's click. Installing a provider itself is never automatic.

### 3. Internal concepts are hidden on first run

The first-run screens and `devteam start` never say *bind*, *layout*, *store* or *preference layers*.
They apply the defaults the CLI already has. Those settings appear under "Advanced settings" after the
first task has run.

### 4. The first task is read-only, enforced by the provider

The suggested first task is "Audit this module" (`audit`, report only) or, when the project has a
pull request or a branch ahead of the base, "Review your last PR" (`review`). Read-only is enforced
by the provider's permission mode, not by prompt wording. The per-provider launch map lives in
`scripts/lib/first-task.json` and is tested over `ALL_PROVIDERS`. A provider with no read-only mode
gets no automatic first-task suggestion; the map records why.

### 5. Five featured commands, the rest revealed by use

`plan`, `fix`, `review`, `commit` and `pr` carry `featured: true` in `scripts/lib/commands.json`. The
session-start banner, the app's catalog default view and `devteam start` show only those five. Every
command stays installed on every provider — removing or hiding command files would break existing
users and behave differently per provider. Use of a command is recorded in the machine-local record
`command-usage.json`, and related commands are suggested after use (for example `commit` → `push`,
`merge`).

### 6. Distribution is the critical path

The app is the front door only once it opens without a warning. Until the app is signed and
notarised, `brew install devteam` / `winget install DevToolbelt.Devteam` followed by `devteam start`
is the primary path, and it reaches the same first task.

## Consequences

- A new CLI surface (`detect`, `start`, `doctor --machine`) — additive to the `--json` contract.
- One new machine-local record, `command-usage.json`, mirrored wherever `MACHINE_LOCAL_RECORDS` is.
- Signing needs an Apple Developer ID and an Authenticode certificate; until both exist ADR-0027 stays
  in force for the app.
- `setup-assistant` stops asking the project type when `detect` answers it with confidence.
