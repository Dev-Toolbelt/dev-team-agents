---
touches: [] # CLI/tooling and packaging change — none of backend, frontend, database or mobile is involved
depends_on: [v3-global-install, v3-credentials]
---

## Spec — the client contract, the catalog and the two distribution channels (milestone M4)

### User Story
As a developer who wants a desktop client for dev-team-agents and an install command my platform
already has, I want every capability exposed as a machine-readable CLI call and every release
published through my platform's own package manager, so that the UI and the terminal cannot disagree
about what my projects are bound to, and so that installing the framework is not a `curl | bash`.

### Context
ADR-0011 decides two things: the framework ships through **Homebrew on macOS and winget on Windows**,
and the desktop app is a **pure client of the CLI** — every screen invokes `devteam <command> --json`
and renders the result, so no bind rule, preference merge or credential resolution is reimplemented
in the app. That arrangement is only safe if the contract it calls is stable and if compatibility is
declared rather than assumed.

Milestone **M4 was split**, and this spec covers it in that order. **M4.1 built the framework's half
first**: `devteam catalog` (the command the app's browse screen had no call behind),
`scripts/lib/devteam/compat.py` (what a client must understand before it writes), and
`tests/test_json_contract.py` (the sweep that makes "changing an output shape is a breaking change"
checkable). **M4.2 is the packaging scaffold** — a Homebrew formula and cask, winget manifests, a
release workflow and an operator runbook under `packaging/`. **M4.3 is the Electron app, and it is
not built**: it is blocked on signing credentials the repository owner holds.

**Every scenario below is marked, and the marks are the point of this document:**

| Mark | Meaning |
|------|---------|
| **[MET]** | Built and asserted by a test that passes today. `tests/test_json_contract.py` is 19 tests and green. |
| **[UNVERIFIABLE HERE]** | Stated as the criterion a human must check, against accounts, certificates and third-party review this environment does not have and should not be given. The artifact exists; the criterion has never been exercised. |
| **[UNBUILT]** | The criterion is stated so the client has something to be built against. No code exists. |

A spec that implied the packaging was proven would be worse than no spec, so nothing here asserts a
`brew install`, a notarisation, a winget acceptance, or a running app.

### Acceptance Criteria

**Scenario [MET]: every command answers in one envelope, in every store state**
- Given the command surface obtained by walking the real `cli.build_parser()` subparser tree
- When each invocable leaf runs with `--json` against an empty store, an installed-but-unbound store,
  and inside a freshly bound project — each invocation in its own fresh directory
- Then the process exit code is within `{0, 1, 2, 3, 4}`
- And stdout is either empty or exactly one parseable JSON object
- And that object carries an `ok` field, true exactly when the exit code is 0
- And on exit 2, 3 or 4 it also carries a non-empty `error` and an `exit_code` equal to the process
  exit code
- And exit 1 ("ran, but reported a finding") is not required to carry either
- And stderr never carries a JSON document
- And the same command without `--json` never writes a JSON document to stdout

**Scenario [MET]: the sweep discovers the surface, so it cannot fall behind it**
- Given no hardcoded list of commands anywhere in the suite
- When the parser walk runs
- Then it reports at least 20 invocable leaves and reports none of them twice
- And every group it classifies as a group contributes at least one nested leaf — a group yielding
  none means the walk is broken, not that the surface shrank
- And every leaf resolves to a handler, named individually rather than failing later as an attribute
  error
- And a command that is both a valid bare call and a group of subcommands is reported as both
  (`catalog` is that shape today, and is asserted by name)
- And exactly two commands are excluded from invocation — `update`, which reaches the network, and
  `uninstall`, which removes the store the rest of the sweep needs — each recorded with its reason
  and each asserted to still be discoverable

**Scenario [MET]: `devteam cred get` refuses `--json`, and the refusal conforms**
- Given a bound project with one credential stored through `devteam cred set`
- When `devteam cred get <key> --json` runs
- Then it exits 2 and stdout is one conforming error document with `ok: false`, `exit_code: 2`, and
  `--json` named in `error`
- And neither stdout nor stderr contains the stored value
- And the same command without `--json` exits 0 and prints the value on stdout and nothing else

**Scenario [MET]: the catalog reports what the bound version contains**
- Given a project bound to a resolved version
- When `devteam catalog --json` runs
- Then it reports that version, the project id, a count per kind for `agents`, `skills` and
  `commands`, and how many of each were malformed
- And `devteam catalog agents|skills|commands --json` lists entries carrying `name`, `path` and the
  `version` they came from, with `tier` and `model` for agents and `category` for skills
- And `devteam catalog show <name> --json` resolves one bare name across all three kinds and returns
  its metadata plus its body
- And a name that matches nothing, or that is ambiguous across kinds, is a usage error naming what to
  run instead
- And the version reported is the one the project is **pinned** to when it carries a pin, and the
  active version otherwise

**Scenario [MET]: one malformed file degrades to a flagged entry, and only that entry**
- Given a version containing three distinct malformed shapes — a file with no frontmatter at all, a
  frontmatter line with no colon, and a frontmatter block that is never closed
- When each kind is listed
- Then the command exits 0
- And each malformed file appears as an entry with `malformed: true`, its path, and the parse error
- And well-formed files in the same listing are unflagged and carry their frontmatter values
- And a malformed entry is not reachable through `catalog show <name>`, because its reported name came
  from a file whose frontmatter could not be trusted — it is reachable only through the listing that
  flagged it

**Scenario [MET]: browsing creates nothing**
- Given a store with an active version, and a working directory that is not a bound project
- When every `catalog` form runs, including one that fails
- Then the set of paths under the data store is identical before and after every invocation
- And no machine identity is minted, no registry entry is written, and no project record is created

**Scenario [MET]: the store declares what a client must understand before it writes**
- Given `devteam version --json`
- Then the payload carries a `compat` block with `json_contract`, `min_app_version` and
  `store_schemas`
- And `min_app_version` is **present and null** — "no minimum asserted yet", readable by the first app
  rather than absent and guessed at
- And `store_schemas` reports `project`, `project_layout`, `registry`, `bind_manifest` and
  `credentials`, each equal to the constant in the module that owns it, so no number is a copy
- And the human output names the contract version and every shape number

**Scenario [MET]: a client's silence about a shape is not a claim of support**
- Given a client that states which shape versions it understands
- When the store is asked which shapes it is ahead of
- Then a shape the client does not mention at all is reported unsupported, with `client: null`
- And a shape the client claims one version behind is reported with both the store's number and the
  client's
- And a shape claimed with a non-integer — including a boolean, which subclasses `int` — is reported
  unsupported rather than coerced
- And a shape the client knows that this store does not carry is not reported, because an older store
  read by a newer client is the direction that works
- And a client claiming every current shape gets an empty result, meaning it may write
- And a non-mapping argument raises rather than being interpreted

**Scenario [UNVERIFIABLE HERE]: a macOS user installs the CLI with the tool they already have**
- Given a published `homebrew-devteam` tap carrying `packaging/homebrew/devteam.rb`
- When a macOS user runs `brew install <tap>/devteam`
- Then `devteam` is on `PATH` and resolves the `devteam` package as a sibling of the CLI entry point
- And `devteam path --json` emits one conforming document and creates neither `core/` nor `data/`
- Unverifiable here because: **there is no tap repository**, so `brew install` and `brew audit` cannot
  be run; the formula's `sha256` is the literal string `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL` and no
  release tarball exists for any digest to describe; and the `python@3.12` dependency name must be
  re-checked with `brew info python3` at publish time, because homebrew-core retires python versions.

**Scenario [UNVERIFIABLE HERE]: pushing a version tag updates the formula for review**
- Given a tag matching `^v[0-9]+\.[0-9]+\.[0-9]+$` pushed to this repository
- When `.github/workflows/release.yml` runs
- Then it downloads that tag's GitHub source archive — the same URL `scripts/install.sh` uses, so
  there is one artifact shape rather than a second one only Homebrew users receive
- And it computes a 64-character hex digest of the bytes it actually received, refusing anything else
- And it rewrites only the formula's `url` and `sha256` lines, verifies both edits landed, and opens
  a pull request against `main` rather than pushing to it
- And a tag of any other shape is refused before anything is downloaded
- Unverifiable here because: **the workflow has never been triggered** — no tag has been pushed since
  it was added. Its logic was dry-run locally against a copy of the formula with a fake tag and
  digest, which is not an Actions run against GitHub's real codeload behaviour.

**Scenario [UNVERIFIABLE HERE]: a Windows user installs the CLI with winget**
- Given a signed Windows installer, real asset URLs, real digests taken after signing, and a version
  directory renamed from `0.0.0` to the release version
- When the three manifests are submitted as a pull request to `microsoft/winget-pkgs` and accepted
- Then `winget install DevToolbelt.Devteam` installs the CLI at user scope and exposes the `devteam`
  command
- Unverifiable here because: **no Windows installer has ever been built**, so both `InstallerSha256`
  values are 64 literal zeros and both `InstallerUrl`s point at assets that do not exist;
  `InstallerType: exe` is a design placeholder, not a decided packaging tool; shipping unsigned would
  trigger SmartScreen on every install, which defeats the reason winget was chosen, so an Authenticode
  certificate is a prerequisite; and acceptance is review by Microsoft, on Microsoft's
  infrastructure. What **was** checked here: `manifestVersion 1.12.0` and the required-field set of
  all three manifest types, against the schema files in `microsoft/winget-cli`.

**Scenario [UNVERIFIABLE HERE]: the macOS app installs as a signed, notarised cask**
- Given a built, signed and notarised universal `.dmg` attached to an `app-v*` release
- When a macOS user installs `packaging/homebrew/devteam-app.rb` from the same tap
- Then `brew audit --cask` verifies the code signature and the notarisation ticket against the
  Developer ID, and the app installs
- And uninstalling with `--zap` trashes only the app's own Electron chrome and leaves the CLI's core
  and data store — which the app shares and does not own — untouched
- Unverifiable here because: **there is no `app/` directory and no build**, so there is no `.dmg` to
  sign, notarise or hash (`sha256` is the literal `NO_RELEASE_SHA256_DOES_NOT_EXIST_YET`); signing
  needs a paid Apple Developer ID and notarisation needs an app-specific password or API key, which
  are account-level credentials this environment does not have; and the cask's macOS floor and bundle
  id are guesses to be confirmed from the app's own `Info.plist` once it exists.

**Scenario [UNBUILT]: the app is a client, and never a prerequisite**
- Given the desktop app (milestone M4.3)
- When any action in the UI runs
- Then it invokes `devteam <command> --json` and renders the result
- And no bind rule, preference merge or credential resolution exists in the app's own code
- And the app reads the `compat` block before it writes, and when `store_schemas` reports a shape it
  does not understand it degrades to read-only **and says so**
- And it special-cases `devteam cred get`, which answers `--json` with a conforming error by design
- And every capability the app exposes remains reachable from the CLI alone, so a user who never
  installs the app loses only the screens
- Unbuilt, and two preconditions are open regardless of the app's code: **nothing calls
  `unsupported_by()` today** — the CLI never asks a caller what it understands and cannot refuse one —
  and **which `devteam` binary the app invokes is undecided**. The formula and the cask are
  independent installs and the cask declares no dependency on the formula, so a bundled or older CLI
  writing a newer store is the exact case the compat check exists for, and the case nothing currently
  prevents.

### Out of Scope
- **The Electron app itself.** Milestone M4.3, blocked on signing credentials the repository owner
  holds. Its criteria are stated above as `[UNBUILT]` so the client has a target; none of them is met
- **A deprecation policy for the JSON contract.** `json_contract` is a single integer with no rule
  attached: nothing states what bumping it obliges, how long the previous value is honoured, or how a
  client learns a field is going away. Recorded as the first risk in ADR-0011; no mechanism is
  specified here and none is built
- **Per-command payload field contracts.** The sweep pins the *envelope* for every command. No test
  enumerates any command's key set, so a renamed or dropped field passes every check that exists.
  Nothing in this spec asserts otherwise
- **Framework-side enforcement of client compatibility.** There is no `--client-schemas` flag or
  equivalent; `unsupported_by()` is a library function whose only callers are its tests. The client is
  the party that degrades, by design
- **Reconciling `min_app_version` with `store_schemas()`.** ADR-0011's amendment argues they are two
  mechanisms answering one question and proposes which should be normative. That decision is not made,
  and this spec asserts neither outcome
- **The Windows packaging shape for the CLI.** Whether the `.exe` wraps the python payload (PyInstaller,
  pynsist) or is a thin launcher requiring a system python3 is undecided, and the choice changes
  `InstallerType`, `InstallerSwitches` and `Dependencies` together
- **Linux as a release channel.** The path resolver already handles XDG; no channel is decided, and a
  manual install remains the only route
- **Scoop and Chocolatey.** Rejected in ADR-0011 — Scoop needs installing first, Chocolatey adds
  gallery review and nuspec packaging for no gain over winget's preinstalled reach
- **The app's own auto-update channel**, which ADR-0011 keeps separate from `devteam update`
- **Publishing to the tap.** Copying the formula into a `homebrew-devteam` repository is a manual step
  with no tooling, and the repository does not exist

### Dependencies
- **Depends on**: [`v3-global-install.md`](v3-global-install.md) (the store, the bind, version
  resolution and pinning, the `--json` exit-code contract this sweep generalises, quarantine),
  [`v3-credentials.md`](v3-credentials.md) (the `cred get --json` refusal this contract must carry as
  a standing exception), ADR-0011
- **Blocks**: the desktop app (M4.3), and both publication pipelines

### Amendment Log
- 2026-09-28 | software-architect | Spec created after M4.1 and M4.2 landed, with every scenario
  marked `[MET]`, `[UNVERIFIABLE HERE]` or `[UNBUILT]` rather than written as uniform criteria. |
  Milestone M4 was split, so a single unmarked spec would have read as one delivered feature and
  implied the packaging was proven. Eight scenarios are asserted by `tests/test_json_contract.py`
  (green, 19 tests); five cannot be exercised without an Apple Developer ID, an Authenticode
  certificate, a published tap, or review by Microsoft; one describes software that does not exist.
  Marking them separately is what makes the document usable as a checklist when those credentials
  arrive, instead of a claim that the channels are live.

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
