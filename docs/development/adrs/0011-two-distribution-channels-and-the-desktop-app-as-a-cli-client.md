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

> **Amended by implementation (M4.1) — the milestone was split, and the channels are scaffolded,
> not live.**
>
> **Why the split.** This ADR makes the app a *pure* client: it owns no rule, only screens. A pure
> client is defined entirely by the contract it calls, so building it first would mean discovering
> the contract from whatever the UI happened to need, one screen at a time — which is how a "single
> source of truth" acquires a second one in TypeScript, quietly, for the one case the CLI could not
> answer. M4.1 therefore built the framework's half first: `devteam catalog`,
> `scripts/lib/devteam/compat.py`, and `tests/test_json_contract.py`. The app is M4.3 and is
> blocked on signing credentials the repository owner holds, not on design.
>
> **What exists in `packaging/`, and what each piece still needs from a human.** Every artifact
> below is syntactically valid and none of it has been published, installed, or accepted anywhere.
> `packaging/README.md` is the operator runbook and states the same thing at its head.
>
> | Artifact | State | Needs from a human |
> |---|---|---|
> | `packaging/homebrew/devteam.rb` | Formula for the CLI only (`scripts/cli/devteam` + `scripts/lib/devteam/*.py`), never run through `brew install` or `brew audit` | A published `homebrew-devteam` tap repository to install from; a `brew info python3` check, because the `python@3.12` dependency name drifts as homebrew-core retires versions |
> | `packaging/homebrew/devteam-app.rb` | Cask for an app that does not exist — there is no `app/` directory in this repository | The app build, an Apple Developer ID to sign the `.dmg`, and an app-specific password or API key for `notarytool` |
> | `packaging/winget/manifests/d/DevToolbelt/Devteam/0.0.0/` | Three-file manifest at `manifestVersion 1.12.0`, `PackageVersion 0.0.0` | A decided Windows packaging shape (`InstallerType: exe` is a placeholder, not a decision), an Authenticode certificate, and a reviewed pull request to `microsoft/winget-pkgs` |
> | `.github/workflows/release.yml` | Downloads the pushed tag's GitHub source archive, hashes the bytes it actually received, and opens a PR bumping the formula's `url`/`sha256`. Never triggered | A `vX.Y.Z` tag push. It deliberately does not build a second artifact: `scripts/install.sh` already installs from that same tag archive, so there is one artifact shape rather than one for Homebrew users and one for everyone else |
>
> **The sha256 placeholders differ per channel on purpose, and the difference is the point.** The
> Homebrew formula carries the literal string `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL`, which is not
> hex and not 64 characters, so Homebrew rejects it on sight. The winget installer manifest carries
> 64 literal zeros, because the schema enforces a hex digest of that length — an unparseable string
> would fail validation for the wrong reason and hide the real problem. Neither can be mistaken for
> a real digest, which is the property being bought: a *plausible* fake digest is the one that gets
> committed and shipped.

**The app is a client of the CLI.** Every action in the UI invokes `devteam <command> --json`
and renders the result. No bind rule, no preference merge, no credential resolution is
reimplemented in TypeScript. This costs a stable JSON contract on every subcommand — with
contract tests in CI — and buys a single source of truth, so the terminal and the UI cannot
disagree.

> **Amended by implementation (M4.1) — the contract is enforced by a parser-discovered sweep, one
> screen had no command behind it, and the contract already carries a standing exception.**
>
> **The sweep is what makes "the JSON contract is public API" checkable.**
> `tests/test_json_contract.py` walks the real `cli.build_parser()` subparser tree — 34 invocable
> leaves and 4 groups today — and runs every one of them against three store states (empty,
> installed-unbound, installed-bound), in both `--json` and human mode. The walk itself is asserted
> (a group that yields no nested leaf, a leaf with no handler, and a suspiciously small surface all
> fail), because a broken walk silently tests nothing. A **hardcoded command list was rejected
> outright**: it goes stale the moment a command is added, and the first thing to notice would be
> the desktop app, in production, against a user's store. Only `update` (reaches the network) and
> `uninstall` (removes the store the rest of the sweep needs) are excluded, named in
> `SKIP_INVOCATION` with their reason and asserted to still be discoverable.
>
> **What it guards, stated precisely so nobody over-reads it.** The sweep pins the *envelope* for
> every command: exit code within `{0,1,2,3,4}`; stdout empty or exactly one parseable JSON object;
> an `ok` field present and agreeing with the exit code; `error` plus a matching `exit_code` on 2, 3
> and 4 (exit 1 is "ran but found something" and carries neither); stderr never a JSON document;
> human mode never emitting one. It does **not** pin any command's payload *fields* — no test
> enumerates a command's key set, so removing `project_id` from `bind --json` would pass this sweep.
> The envelope is enforced; per-command field shapes are still convention.
>
> **`devteam catalog` was a missing command, not a missing screen.** The app's read-only browse of
> agents and skills had no CLI call behind it at all, which under this ADR means the screen could
> not have been built without reimplementing a tree walk in the client. `catalog` (bare, a summary),
> `catalog agents|skills|commands` and `catalog show <name>` resolve content from the version the
> project is **bound to** — the project's pin via `versions.resolve`, the same resolution `prefs`
> already uses — and create nothing on any path, including no machine identity: reads go through
> `registry.load()`, which probes with `paths.machine_id(create=False)`. A file whose frontmatter
> does not parse is reported as `malformed: true` with its path rather than raising, because a
> catalog that dies on one bad file is useless for finding the bad file. Frontmatter is read by a
> small standard-library reader; a YAML dependency was not worth adding for the flat `key: value`
> shape `helpers/agent-lint.sh` already enforces.
>
> **`devteam cred get` refuses `--json`, and the client must special-case it.** That refusal is
> correct and deliberate (ADR-0010: a JSON document is something a caller pipes, tees or logs
> wholesale, and a secret must not travel that way), and this sweep pins it as *conforming* — the
> refusal is itself a well-formed error document at exit 2. But it is a real cost that M3's decision
> imposes on M4's contract, and it belongs here rather than only in ADR-0010: the app cannot treat
> `devteam <anything> --json` as a uniform call, because exactly one command answers the uniform
> call with an error by design. Every client needs one hardcoded exception, and a client that
> discovers this at runtime will read it as a bug in the framework. Any future command that handles
> a secret joins that list, so the exception is a category, not a single case.

**The app is never a prerequisite.** Every capability is reachable from the CLI. A user who
never installs the app loses nothing but the screens.

**Compatibility is declared, not assumed.** The app states `minFrameworkVersion` and the
framework states `minAppVersion`. When the store is ahead of the app, the app degrades to
read-only and says so, instead of writing a structure it does not understand.

> **Amended by implementation (M4.1) — `min_app_version` is `None`, the store also declares its
> shapes, and that is a second mechanism this ADR should reconcile rather than absorb.**
>
> **`min_app_version` is `None`, and a client must treat that as "no minimum asserted", not as
> "unknown".** `compat.MIN_APP_VERSION = None`, surfaced as `"min_app_version": null` in
> `devteam version --json` and pinned present-and-null by test. Asserting a floor for software that
> has never been released would be a number nobody could act on. The field exists *before* the first
> app precisely so the first app can rely on reading it: an app that has to handle the key being
> absent will handle it by guessing. A client reading `null` proceeds; it does not degrade, and it
> does not report an unknown framework.
>
> **What was built beside it.** `compat.describe()` returns three things, not one: `json_contract`
> (currently `1` — a version of the wire shape), `min_app_version`, and `store_schemas()` — the five
> shape numbers that already existed, read from the modules that own them (`project.SCHEMA`,
> `project.CURRENT_LAYOUT`, `registry.SCHEMA`, `bind.MANIFEST_SCHEMA`, `creds.SCHEMA`) and never
> copied, because a copied version number goes stale in the direction that tells a client it is safe
> to write when it is not. `unsupported_by(client_schemas)` answers which shapes the store is ahead
> of, and **treats a shape the client is silent about as unsupported** — silence is not a claim of
> support, and reading it as one is exactly how a client writes a structure it has never seen. A
> non-integer claim (including `True`, since `bool` subclasses `int`) counts as silence; a shape the
> client knows and the store does not is ignored, because an older store read by a newer client is
> the direction that works.
>
> **Verdict: this is a second mechanism, and it should be reconciled, not described as the first
> one's concrete form.** The honest reading:
>
> | | This ADR's mechanism | What M4.1 built |
> |---|---|---|
> | What is declared | a release-version floor for the *other party* | version numbers of the *data*, plus a wire-shape version |
> | Who decides | each side refuses the other below its floor | the store only publishes; the client decides |
> | Granularity | one bit — compatible or not | per shape, so a client could degrade one screen instead of everything |
> | Built | `min_app_version` exists and is `None`; nothing anywhere reads `minFrameworkVersion` | `store_schemas()` and `unsupported_by()` exist and are tested |
>
> They answer the same question by different means, and both are now declared. That is the drift this
> repository's own Canonical Rule Homes discipline forbids at the documentation layer, arriving at
> the data layer instead. The shape numbers are the *better* mechanism — a release version moves for
> a documentation fix and does not move for a schema change, so a version floor both over-blocks and
> under-blocks — which is an argument for making them normative, not for keeping two.
>
> **The reconciliation to make explicitly (not yet made):** treat `store_schemas()` as the normative
> compatibility statement; keep `min_app_version` as a kill-switch for the case the shape numbers
> cannot express — a released app version known to write the store *wrongly* for a reason that is a
> bug rather than a shape change; and record that `minFrameworkVersion` on the app side is advisory,
> since no framework code reads it and none is planned. Until that is decided, a contributor can bump
> `MIN_APP_VERSION` and believe the compatibility question is handled.
>
> **The comparison is answered by the CLI, not left to the client.** An earlier draft of this
> amendment recorded that `unsupported_by()` had no callers and no CLI surface, so "the app degrades
> to read-only" was a published number with no reader. That was the state at the time and it was the
> wrong state, for this ADR's own reason: if the framework publishes shape numbers and leaves the
> comparison to the app, the compatibility rule **is** reimplemented in TypeScript — in the one place
> where getting it wrong means writing a structure the client does not understand. The Decision above
> forbids exactly that for bind, preferences and credentials; compatibility is not a special case.
>
> `devteam compat` closes it. Bare, it reports what the store requires. With `--client '<json>'` or
> `--client-file <path>` it returns an explicit `may_write` boolean plus, when false, the blocking
> shapes with both numbers — so a client branches on an answer rather than deriving one. It exits
> **1** on incompatibility: a well-formed question with a real negative answer is "findings", the same
> meaning the exit code already carries for `doctor`, `sync` and `cred check`. Malformed client input
> is exit 2, a different failure class that must never be confused with a real "no". The command
> creates nothing, verified by a byte-comparison of the store across the whole input matrix.
>
> What remains the client's responsibility is only the part that must be: **calling it before it
> writes**, and honouring the answer. The framework can now be asked; it still cannot refuse. A user
> can also upgrade the store from a terminal without touching the app, so the answer is valid only at
> the moment it is given — the app has to ask again, not cache it. See the Risks table below.

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

## Risks

Added by implementation (M4.1) — the ADR skill requires this section and the original omitted it.
Every row is a condition that exists in the shipped code or in the shipped absence of code, not a
hypothetical.

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **The JSON contract is public API with no deprecation mechanism.** `json_contract` is a single integer with no rule attached: nothing says what bumping it obliges, how long the previous value is honoured, or how a client learns a field it reads is going away. The first real change will be made by whoever needs it, under release pressure, with no precedent to follow. | `tests/test_json_contract.py` makes the envelope impossible to break silently across all 34 commands, and `CLAUDE-md/cli.md` documents the contract. A client can pin against `json_contract` rather than inferring compatibility from a release version that moves for unrelated reasons. | The sweep guards the envelope, not any command's field set — no test enumerates one, so a field can be renamed or dropped and every check still passes. There is no `deprecated` marker, no two-version overlap policy, and no changelog convention that distinguishes an output-shape change from any other change. This is the most likely way a shipped app breaks, and it is unmitigated today. Deciding the policy is cheap now and expensive after the first client exists. |
| **A client reads `compat` and writes anyway.** `unsupported_by()` has no caller outside its tests; the CLI never asks who is calling it and cannot refuse. A client that skips the check, mis-implements it, or ships the check disabled behind a flag gets exactly the same write access as one that honours it. | Writes go through the CLI, so the code performing them understands the store it is writing; `registry.load()` already refuses a registry whose `schema` exceeds what that CLI understands, and `creds`/`project`/`bind` validate on read. Silence is scored as unsupported, so a client that declares partially cannot pass by omission. | Only if the app invokes a `devteam` that matches the store. **The two channels install the CLI and the app separately** — the formula and the cask are independent, and the cask declares no dependency on the formula — so which `devteam` the app invokes (PATH, a pinned absolute path, or one bundled inside the app) is undecided by this ADR. A bundled older CLI writing a newer store is the case where the check is load-bearing, and it is the case nothing currently prevents. Settle "which CLI does the app call" before the app ships; it is a precondition for `compat` meaning anything. |
| **The packaging reads as done because it exists.** A repository with a formula, a cask, three winget manifests and a release workflow looks like a repository with two live channels. Someone — including a future agent summarising this work — will report it as shipped. | Every file carries a header stating it is unverified and why; `packaging/README.md` opens with the same statement, tables the placeholders against who replaces each one, and tables what cannot be verified here and for what account-level reason; the placeholder digests cannot be mistaken for real ones. | Documentation, not a mechanism. Nothing fails if the cask is copied into a tap tomorrow. The strongest available guard is that the placeholder values make a premature publish fail loudly at the packaging tool rather than silently at the user. |
| **`min_app_version` and `store_schemas()` both answer "may this client write?"** A contributor bumps one and believes the question is handled. | Both are surfaced from one function (`compat.describe()`) on one call (`devteam version --json`), so a client reading the block sees all three fields at once; the module docstring explains why the shape numbers are read from their owning modules rather than copied. | Two declarations, one question. The reconciliation is written above but not decided, and the weaker mechanism (`min_app_version`) is the one this ADR's Decision text names — so the ADR currently points at the field with no content. |
| **The Windows CLI has no decided packaging shape.** `InstallerType: exe` assumes a signed executable wrapping the python payload; whether that is PyInstaller, pynsist, or a thin launcher requiring a system python3 is undecided, and the choice changes `InstallerSwitches`, `Dependencies`, and whether the CLI's python floor is satisfied at all. | The manifest comment states it is a design placeholder rather than a decision, and `packaging/README.md` lists "a decided Windows packaging shape" as a prerequisite ahead of the certificate. | The macOS channel can go live while this is open, which means Windows silently becomes the second-class target this ADR chose winget specifically to avoid. |
| **`release.yml` has never run.** Its tag validation, download-with-retry, digest check and anchored `sed` bump are all unexercised against real GitHub behaviour. | It opens a PR rather than pushing to `main`, so a maintainer reviews the two changed lines; it asserts the digest is 64 hex characters and verifies its own edit landed before committing; the logic was dry-run locally against a copy of the formula. | A dry run is not an Actions run. The first real release is the test, and a failure there happens at the moment a version is being cut. |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Homebrew only, telling Windows users to use WSL | WSL has a different `$HOME` and filesystem than the user's projects; the store would bind paths that the Windows-side editor and CLI cannot resolve. |
| Scoop for Windows | A bucket we control with no external review, closest analogue to a tap — but the user must install Scoop first, and the audience is narrower than winget's. |
| Chocolatey | Strong in corporate/CI Windows, but gallery review plus nuspec/PowerShell packaging for no benefit over winget's preinstalled reach. |
| Own installer only (.exe/.msi + PowerShell script) | Full control and no gatekeeper, but a private update channel to maintain and much worse discovery. |
| App with its own implementation of bind/preferences | Removes the JSON contract work, and guarantees that UI and CLI eventually disagree about what a bind is. |

Added by implementation (M4.1) — options that only became real once there was code:

| Alternative | Why rejected |
|-------------|-------------|
| Build the app first and let the contract follow from what each screen needed | The natural order, and it is the order that produces the second source of truth this ADR exists to prevent. A screen that finds no command behind it does not wait — it grows a tree walk, a preference merge, or a path resolver in TypeScript, which then has to be *removed* later rather than never written. `devteam catalog` is the proof: the browse screen had no command at all, and it was found by asking what the contract owed the app rather than by building the app. |
| One `compat` version number instead of surfacing five store schema numbers | Tidier, and it collapses information the client needs. The five numbers are independently versioned already — a `project.json` bump and a credentials-schema bump are unrelated events — so one aggregate number would have to bump on either, degrading a client that only ever reads credentials. Per-shape numbers let a client degrade one screen; one number degrades the whole app. |
| Have the CLI refuse writes from a client that has not declared its schemas (a `--client-schemas` gate) | Enforcement on the side that can actually enforce, and it inverts this ADR's own model: the client is the party that degrades, the CLI is the single implementation that must keep working for a human in a terminal. A flag every write needs would make the CLI hostile to its primary user to guard against a client that does not exist yet. Revisit when the app ships and "which CLI does the app invoke" is decided — not before, because the answer determines whether the gate is needed at all. |
| A hardcoded command list in the contract sweep | Simpler to read and stale on the next commit. A list omits precisely the command nobody remembered to add, and the sweep exists to catch the command nobody thought about. Discovering from `cli.build_parser()` costs a parser walk that itself has to be asserted — hence the three discovery tests — and buys a sweep that cannot fall behind the surface. |
| Publish nothing under `packaging/` until signing credentials exist | Avoids the "looks done" risk entirely, and defers the one part of this that could be got wrong in a way nobody would notice. The manifest schema version, the one-artifact-shape decision, the placeholder digest formats and the per-channel prerequisite list were all research findings; discarding them would mean rediscovering them under release pressure. They are committed *with* the statement that they are unverified, and the placeholders are built to fail loudly. |
| Build a bespoke release tarball for Homebrew | The obvious reading of "build the package tarball", and it creates a second artifact shape that only Homebrew users receive. `scripts/install.sh` already installs from GitHub's own tag archive; the formula points at that same URL, and `release.yml` hashes the bytes it actually downloaded rather than a locally built archive whose gzip parameters need not match. One artifact, one digest, no drift between how two populations of users get the same version. |
