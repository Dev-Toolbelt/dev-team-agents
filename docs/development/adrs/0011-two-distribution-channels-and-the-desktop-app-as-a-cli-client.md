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

> **Amended by implementation (the client write gate) — the framework can now refuse, three statements
> in the table above were *false when that table was written*, and the `--client-schemas` alternative
> below was *narrowed* rather than reversed.**
>
> Decided and recorded in
> [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md),
> which narrows this ADR without touching its Decision. Reference for the surface:
> `CLAUDE-md/cli.md` § *The client write gate*; the code is `scripts/lib/devteam/compat.py`
> (`client_declaration`, `MUTATING`/`READ_ONLY`, `NEEDS_MACHINE_LAYOUT`, `is_mutating`, `gate`) wired from
> `cli.main`, asserted by `tests/test_client_gate.py` (52 tests, in a suite of 396).
>
> **What shipped.** A caller may declare the shapes it understands, through the global
> `--client-schemas <PATH>` or `DEVTEAM_CLIENT_SCHEMAS` (the flag wins; an empty variable is *unset*).
> A caller that declares is refused every **mutating** command it cannot understand — exit **4**, before
> `store.adopt_machine_layout()` and before any handler, so the store is byte-identical after a refusal —
> a position now asserted by a fabricated pre-split-store fixture, across the whole mutating table, rather
> than resting on a comment. Read-only commands, `compat` among them, are never refused **as writes**:
> this ADR's rule is that an incompatible client *degrades to read-only*, so read-only is precisely what
> must keep working.
>
> **One narrow exception, and it serves that rule rather than qualifying it.** The one-time relocation of a
> pre-ADR-0013 store rewrites `registry` and `bind_manifest` — exactly the shapes an incompatible client
> declared it cannot read — so it is **suppressed** for that caller; a terminal invocation, an anonymous
> caller and a compatible client all still perform it. With the move skipped, every read-only command still
> answers correctly except `devteam list`, which resolves the registry only at the post-split path and
> therefore reported every bound project as unbound at exit **0**. `compat.NEEDS_MACHINE_LAYOUT` names it —
> measured by running every read-only leaf on both layouts, not reasoned about — and it is refused at exit
> **3**, an environment that is not ready rather than a write that is declined, carrying the refusal's seven
> `details` keys plus `machine_layout_pending: true`. A wrong read is not a degraded read: a client told
> `projects: []` would offer to bind a project that is already bound. `compat`, `version` and `path` are
> asserted to answer on that store, so the client can still learn why.
>
> **Why this narrows the Alternatives row below rather than contradicting it.** That row rejects
> *"Have the CLI refuse writes from a client that has **not declared** its schemas"*, on the ground that
> *"A flag every write needs would make the CLI hostile to its primary user"*. The shipped gate refuses
> the opposite population: a client that **has** declared and declared itself behind. A caller that
> declares nothing is affected in no way and retains the entire pre-gate write surface — no flag is
> needed by any write, no detection is attempted, and omitting the declaration is a complete bypass. The
> row's stated objection is therefore untouched, and ADR-0014 § 3 ratifies it explicitly, adding the
> reason this ADR did not give: identification is not authentication, so a mandatory flag would guard
> only against the well-behaved client. **The row's revisit condition was not met, and the gate was
> built anyway.** That condition is *"Revisit when the app ships and 'which CLI does the app invoke' is
> decided — not before, because the answer determines whether the gate is needed at all"*: a **reason**,
> not a schedule note. Neither half of it holds. The app has not shipped. And `depends_on formula:
> "devteam"` does not decide which binary the app invokes — it guarantees the formula is *installed*,
> which the cask's own comment states as making the question "answerable", not answered; that line is
> also older than the condition it is sometimes offered against (`06fd509`, an ancestor of `ed87507`),
> and nothing in this change touched `packaging/`. The deviation is deliberate and the motive is the
> one this ADR already supplies for its own sequencing: retrofitting a refusal path around a released
> client means changing behaviour that client already depends on, so the refusal was built while the
> contract was still being written rather than after.
>
> **Three statements — spread across two rows, not three — in the Risks table above were false when
> that table was written, not overtaken since. They are corrected here rather than rewritten there.**
> The *A client reads `compat` and writes anyway* row supplies two of the three. All three artifacts
> existed at `ed87507`, the commit that wrote the rows, having arrived in `4818176`, `06fd509` and
> `95fa346` respectively — every one of them an ancestor of it.
>
> | Row | False statement | Correction |
> |---|---|---|
> | *A client reads `compat` and writes anyway* | "`unsupported_by()` has no caller outside its tests" | Already false at `ed87507`: `git show ed87507:scripts/lib/devteam/cli.py` has `cmd_compat()` calling `compat.unsupported_by()` and `compat_parser.set_defaults(func=cmd_compat)` wiring it, both added by `4818176`. There are now two production callers — `cli.cmd_compat()` and `compat.gate()`. The CLI still does not ask who is calling it — that part stands — but it **can** now refuse a caller that has told it |
> | *A client reads `compat` and writes anyway* | "the cask declares no dependency on the formula … which `devteam` the app invokes is undecided" | The first clause was already false: `git show ed87507:packaging/homebrew/devteam-app.rb` carries `depends_on formula: "devteam"` at line 52, added by `06fd509`. The second clause **still stands** — the dependency guarantees the formula is installed, not which binary the app invokes, and the cask's comment says so in those words. A bundled CLI shipped outside Homebrew is equally undecided, and is the case the gate catches whenever that CLI declares its shapes |
> | *The JSON contract is public API with no deprecation mechanism* | "no test enumerates one [a command's field set]" | Already false at `ed87507`: `git show ed87507:tests/test_json_contract.py` carries `AppFacingKeySetContractTest` with its `EXPECTED` already holding 16 app-facing commands and 5 per-record shapes, added by `95fa346`. Its docstring cites the `project_id`-from-`bind --json` regression this row describes as unmitigated. The rest of that row stands: `EXPECTED` is hand-maintained with no completeness assertion against the parser walk, and the deprecation policy itself is now ADR-0014 § 2 — decided, with its marker mechanism still unbuilt |
>
> Note the shape of all three: the artifact was in the tree, and the row described the tree as it had
> been some commits earlier. "Stale" would have been the flattering word for it, and it is the wrong
> one — nothing decayed. It is the same defect as the leaf count below, which this amendment had already
> framed correctly ("wrong when it was written rather than overtaken since") while calling these three
> stale in the same breath.
>
> One count is wrong in two places and is corrected here rather than in either: the parser walk is
> described as reaching *"34 invocable leaves and 4 groups today"* (M4.1 amendment, inside
> `## Decision`) and the sweep as covering *"all 34 commands"* (first Risks row). It reaches **35
> leaves** and 4 groups. No command was added by the write gate — `--client-schemas` is a global flag,
> not a leaf — and running the discovery walk at commit `ed87507`, the commit that wrote "34", also
> returns 35, so the number was wrong when it was written rather than overtaken since.
>
> The fourth row — *`min_app_version` and `store_schemas()` both answer "may this client write?"* — is
> no longer undecided either: ADR-0014 § 1 makes `store_schemas()` normative, confines
> `min_app_version` to a kill switch, and records `minFrameworkVersion` as advisory. The residual it
> names survives unchanged: nothing in the code marks the field as advisory, only an ADR does.

> **Amended by implementation (M4.3, first slice) — the app exists in source, this ADR's stack and
> client rules are narrowed by [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md),
> and the "app" column of the channel table above is still empty on both platforms.**
>
> **The forward reference, first, because this ADR names Electron once and decides nothing else about
> the client.** ADR-0015 decides the stack (Electron, TypeScript + Vite + React), that the source lives
> in `app/` in this repository, that every invocation happens in the main process behind named
> operations, that **no second CLI is ever bundled** and in what order one is resolved, that the app
> declares its schemas so ADR-0014's gate binds it, and that it never calls `devteam cred get`. It
> narrows this ADR and reverses nothing in it; the two channels, the app as a pure client, the JSON
> contract as public API and "the app is never a prerequisite" all stand as written.
>
> **What the second Risks row asked for is decided, and its condition is still not met.** That row
> instructs: "Settle 'which CLI does the app call' before the app ships; it is a precondition for
> `compat` meaning anything." It is settled — ADR-0015 § 5, a stated resolution order with no bundled
> fallback and a loud total failure when nothing resolves, implemented in `app/src/cli/resolve.ts` and
> asserted by `app/test/resolve.test.ts`, which also asserts that a candidate is accepted only when
> running `version --json` returns a conforming document carrying a `compat` block. The row's residual
> is unchanged, because the app has **not** shipped: nothing installs it through either channel, so
> the resolution order remains the only thing connecting the two independent installs.
>
> **What `packaging/` can now say, and what it still cannot.** `app/` builds a universal
> `dev-team-agents.app` inside `dev-team-agents-<version>.dmg`, and every such build is **unsigned**:
> `app/electron-builder.yml` sets `mac.identity: null` and `mac.notarize: false`, and the build prints
> `UNSIGNED, UNNOTARISED BUILD — DO NOT DISTRIBUTE`. So this ADR's "macOS artifacts are signed and
> notarised" is still a statement about a release that has not happened, and the M4.1 amendment's
> "blocked on signing credentials the repository owner holds" is still the reason. Two values in
> `packaging/homebrew/devteam-app.rb` stopped being guesses: the macOS floor is now **measured** at
> `">= :monterey"` (the pinned Electron declares `LSMinimumSystemVersion` 12.0, so the previous
> `">= :big_sur"` would have licensed an install on a system the app cannot launch on), and the bundle
> id is read from the build's `appId`. Windows is further behind than this ADR's channel table reads:
> there is **no app manifest at all** under `packaging/winget/`, and `app/electron-builder.yml` has no
> `win` block, deliberately, because adding one would imply a Windows packaging shape this ADR still
> records as undecided.
>
> Nothing in the Decision, the channel table or the Risks rows above is changed by this amendment. The
> app column becomes true when a signed, notarised artifact is published at a real version — and
> `docs/specs/v4-app-and-distribution.md` carries the per-clause state of M4.3 in the meantime.

> **Amended by implementation (M4.3 closeout) — the app's Windows packaging shape is now decided, and
> a manifest scaffold exists for it. Neither closes the gap the previous amendment recorded; both
> narrow it from "undecided and absent" to "decided and scaffolded, still unbuilt and unsigned".**
>
> **What is now decided.** `app/electron-builder.yml` has a `win` block: NSIS
> (`InstallerType: nullsoft` on the winget side), producing a per-user installer per
> architecture, unsigned by configuration the same way `mac.identity: null` is unsigned by
> configuration — no `certificateFile`/`certificatePassword` keys exist to set, and
> `forceCodeSigning: false` makes a future accidental signing attempt a no-op rather than a build
> failure. MSI and AppX/MSIX were weighed and rejected: MSI needs the WiX toolset for no benefit this
> project needs, and AppX/MSIX requires a trusted signing identity to install outside the Microsoft
> Store at all — unsigned MSIX is refused, not warned, so it was off the table before any other
> trade-off mattered. `packaging/README.md`'s new § "The Windows app installer shape — decided"
> records the full comparison.
>
> **What now exists.** `packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/` — a three-file
> manifest set (version, installer, `defaultLocale`) at the same placeholder-version and
> zero-digest discipline as the CLI's sibling manifest, contract-checked by the same
> `.github/scripts/ci/04-packaging.sh` gate (which groups and validates by directory, so it needed
> no changes to cover a second manifest set).
>
> **What is still blocked on the repository owner, precisely.** No Windows build of the app has ever
> been produced — deciding the shape did not build it, the same way deciding "signed and notarised"
> for macOS did not sign anything. `InstallerUrl` and `InstallerSha256` in the new manifest are
> placeholders in exactly the sense the CLI's are. An Authenticode certificate does not exist; NSIS
> makes it recommended rather than required (SmartScreen warns on an unsigned installer instead of
> refusing it), but a certificate would still remove that warning. And `winget validate` /
> `winget install --manifest` have never been run against this manifest, and cannot be from the
> environment that wrote it — a Windows operator is the only party who can close that.
>
> Nothing in the Decision, the channel table or the Risks rows above is changed by this amendment
> either. The app's Windows column moves from "no shape, no manifest" to "decided shape, scaffolded
> manifest, still unbuilt and unsigned" — a narrower gap, not a closed one.

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
