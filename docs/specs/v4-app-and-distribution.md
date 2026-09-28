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
release workflow and an operator runbook under `packaging/` — **plus, subsequently, the verification
those files had none of**: a real `brew install` through a throwaway local tap, a CI-portable payload
test, the release rewrite extracted from inline YAML and tested, and a CI gate over the directory.
**M4.3 is the Electron app, and it is not built**: it is blocked on signing credentials the repository
owner holds.

**Every scenario below is marked, and the marks are the point of this document:**

| Mark | Meaning |
|------|---------|
| **[MET]** | Built and asserted, by something named in the scenario itself — either a test that passes today (`tests/test_json_contract.py`, 35 tests; `tests/test_packaging.py`, 12; `tests/test_release_bump.py`, 23; all green, in a suite of 344) or, where a test cannot reach it, a **recorded run**: one execution on one maintainer's machine, with its platform and tooling version stated. A recorded run is evidence, not a channel — nothing re-runs it, and a `[MET]` resting on one says so in its own first line. |
| **[UNVERIFIABLE HERE]** | Stated as the criterion a human must check, against accounts, certificates and third-party review this environment does not have and should not be given. The artifact exists; the criterion has never been exercised. |
| **[UNBUILT]** | The criterion is stated so the client has something to be built against. No code exists. |

A spec that implied the packaging was proven would be worse than no spec. So the boundary is drawn
narrowly: **one** `brew install` is asserted below, of a tarball built with `git archive … HEAD`
(committed sources, not the working tree), through a throwaway local tap, on one maintainer's machine —
a recorded run, not a channel. Nothing here asserts an install from a published tap, a notarisation, a
`winget validate`, a winget acceptance, a release-workflow run, or a running app.

One more boundary, because every `[MET]` below that says "in CI" inherits it: `ci.yml`'s `push`
trigger is `branches: [main]` plus `tags: ["**"]`, and every other branch is covered by
`pull_request` only. So the coverage of every CI-asserted criterion here is **every pull request,
plus pushes to `main` and to tags** — never "every push"; a branch with no open PR gets no CI at all.

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

**Scenario [MET]: the formula's declared payload is enough to start the CLI** — asserted by
`tests/test_packaging.py` (12 tests), on Linux, on every pull request and every push to `main`/tags
- Given the file list read **out of** `packaging/homebrew/devteam.rb`'s `install` block rather than
  from a list written down beside it
- When exactly those paths are staged into a temp tree with the formula's own layout, the formula's
  `inreplace` shebang rewrite is applied, and the staged entry point is invoked through `subprocess`
- Then `devteam path --json` and `devteam version --json` each return one conforming document
- And neither invocation creates a store
- And nothing in the test imports the `devteam` package, so the repository's own `scripts/lib` cannot
  quietly satisfy an import the staged payload is missing
- And a line **containing `.install`** that the parser does not understand is a hard failure naming that
  line, rather than a skip — a payload test that silently stops parsing is a payload test that passes
  forever
- **Not** asserted: that the `install` block does not later subtract from that payload. Every line in
  the block without `.install` in it is skipped outright, so an `rm_f`, a `mv` or a conditional after
  the staging is invisible here, and these criteria would all hold while `brew install` shipped a
  package missing a module the CLI imports at startup. The module's docstring records the same bound

**Scenario [MET]: the formula installs through a real Homebrew and passes its own test block** —
asserted by **one recorded run** of `packaging/verify-formula-locally.sh` on macOS against Homebrew
7.0.6 — a single execution on one maintainer's machine, not a channel and not a CI job. It is not in
CI because the `packaging` gate runs on `ubuntu-latest`, which ships no Homebrew; that is a cost
choice, not an impossibility (Homebrew runs on Linux, and `release.yml` runs this same script on a
`macos-latest` runner)
- Given a tarball built with `git archive … HEAD` — committed sources, not the working tree — carrying
  GitHub's tag-archive directory shape, and a uniquely-named, git-less throwaway tap holding a
  temporary copy of the formula pointed at it
- When `brew style`, `brew audit --formula`, `brew audit --strict --online`,
  `brew install --build-from-source` and `brew test` run against that tap
- Then the install block runs unmodified and `bin/devteam` is executable and resolves through
  `bin.install_symlink`'s relative symlink into the Cellar and on into `libexec`
- And the `inreplace` shebang rewrite has fired — the installed entry point's shebang names the
  **declared** dependency's interpreter, so a still-present `#!/usr/bin/env python3` fails the run
  rather than silently running whichever `python3` is first on `PATH`
- And `cli/` and `lib/devteam` are siblings under `libexec/scripts`, which is what the entry point's
  `parent.parent / "lib"` lookup requires
- And the formula's `test do` block passes under `brew test`
- And the installed binary answers `path --json` and `version --json` with one JSON object carrying
  `ok: true`, creating no store, with `DEVTEAM_HOME` pointed at a temp directory
- And `brew style` and `brew audit --formula` are clean on this formula, as is
  `brew audit --strict --online` — `brew audit` reported three real findings on the formula as first
  written (`Formula[…].opt_bin` where `formula_opt_bin(…)` is wanted, and two `refute_predicate`
  assertions where `refute_path_exists` is wanted); all three are fixed and the re-run was clean. Note
  that these three stages **record a verdict without gating the run**: `PASS` when clean, `FINDINGS`
  when not, and neither changes the exit code
- And `brew audit --new` is deliberately **not** run and its result must not be quoted: every
  new-formula check in Homebrew 7's `FormulaAuditor` is gated on the core tap — the four git-forge
  notability checks via `get_repo_data`'s `return unless @core_tap` (`formula_auditor.rb:858`), the
  rest directly — so on a private-tap formula `--new` is byte-identical to `--strict --online` and
  reports nothing about homebrew-core eligibility. The notability check is unreachable rather than
  passing: called directly, `SharedAudits.github("Dev-Toolbelt", "dev-team-agents")` returns
  `GitHub repository not notable enough (<30 forks, <30 watchers and <75 stars)`. A clean `--new` here
  would mean "the checks did not run", not "the formula would be accepted"
- And the run's own changes are undone and the undoing is verified at exit rather than assumed: formula
  uninstalled, tap untapped and removed, the real `trust.json` and the tracked formula both
  byte-identical
- **Not** asserted: that the run leaves the machine as it found it. Two changes survive it. Formulae
  Homebrew pulled in **transitively** are detected and *reported*, not removed — the script prints them
  with the `brew uninstall` line, because something else may now depend on them. And `brew style` /
  `brew audit` bootstrap Homebrew's dev gems into
  `$(brew --repository)/Library/Homebrew/vendor/bundle` — ~100 MB — which is **permanent** and
  deliberately not undone, since removing it would damage Homebrew's own state
- **Not** asserted: an install from a published tap, or from GitHub's real codeload bytes. Those are
  the next scenario but one.

**Scenario [MET]: the release bump rewrites two lines and refuses everything else** — asserted by
`tests/test_release_bump.py` (23 tests), driving the real
`.github/scripts/release/bump-homebrew-formula.sh` against copies of the real formula
- Given a formula carrying either the `vX.Y.Z`/`REPLACE_WITH_SHA256_OF_RELEASE_TARBALL` placeholders
  or a previous release's real tag and digest
- When the script runs with a tag and a digest
- Then only the `url` and `sha256` lines change, and every other line is asserted byte-identical
- And a second run with the same inputs leaves the file byte-identical and still exits 0
- And a tag that is not `^v[0-9]+\.[0-9]+\.[0-9]+$`, a digest that is not 64 lowercase hex characters,
  a missing formula, an unknown argument, and an absent repository are each refused, with the formula
  left byte-identical
- And a repository name carrying a regex metacharacter cannot match a different repository, because the
  value is escaped before it reaches the ERE
- And a wrong `--repo` cannot write this release's digest into a formula whose `url` already carries the
  requested tag: the url verification matches the whole
  `url "https://github.com/<repo>/archive/refs/tags/<tag>.tar.gz"` line rather than the tag fragment, so
  the case that used to exit 0 having claimed one repository's digest for another's tarball now fails
- And a formula in which more than one `url "…"` or `sha256 "…"` would be rewritten is **refused**
  rather than rewritten on a guess, because `sed` replaces every match and taking the first is a guess
  about which digest users' machines will be told to trust. A `bottle do` block is unaffected — its
  per-platform digests are keyword arguments (`sha256 <platform>: "…"`) and carry no `sha256 "` for the
  anchor to find — so such a formula still bumps correctly
- And a failed run leaves neither a half-rewritten formula nor a temp or backup file: the write is
  staged to a sibling file and renamed into place only after verification passes
- And the rewritten formula still parses as ruby
- **Not** asserted: that the script can tell whether the formula's directory is writable in every case.
  Both `-w` checks are **diagnostics, not gates** — `-w` sees neither an ACL, nor a read-only mount, nor
  an immutable flag — so `mktemp` keeps its own failure path behind them
- **Not** asserted: that `.github/workflows/release.yml` runs. Only the logic it calls is tested; see
  the scenario below.

**Scenario [MET]: `packaging/` is gated in CI at all** — asserted by
`.github/scripts/ci/04-packaging.sh`, blocking, in the `packaging` job of `.github/workflows/ci.yml`,
on every pull request and every push to `main`/tags (see the trigger boundary above)
- Given that nothing in CI read `packaging/` before this gate existed, so a formula could stop being
  valid ruby or the three winget manifests could disagree about the version and the build stayed green
- When the gate runs
- Then `ruby -c` parses both `devteam.rb` and `devteam-app.rb`
- And each winget manifest parses as YAML and is classified by the `ManifestType` it **declares** —
  not by its filename, which cannot distinguish `defaultLocale` from an additional `locale` manifest —
  with the filename then checked against that type, and the required field set for that type enforced
- And an additional `locale` manifest is legal: exactly one each of the three singular types is
  required, while `locale` may appear N times, and no two manifests may declare the same
  `PackageLocale`
- And `PackageIdentifier`, `PackageVersion` and `ManifestVersion` agree across the files, and
  `PackageVersion` matches the name of the version directory they live in — the four-place hand edit a
  `sed` over the files silently half-finishes
- And each installer entry carries `Architecture`, `InstallerUrl` and `InstallerSha256`, with the
  digest 64 lowercase hex characters quoted as a string, and with the URL's release tag agreeing with
  `PackageVersion` — a bump to one side and not the other is refused in both directions
- And the `InstallerUrl`'s origin is checked unconditionally against a prefix **derived from**
  `scripts/install.sh`'s own `GITHUB_OWNER`/`GITHUB_REPO` — a file outside `packaging/`, so the edit
  that redirects the URLs cannot move the goalpost with them — and the tag is read as the first path
  segment after `…/download/` and compared for **exact** equality with `v<PackageVersion>`, so
  `v1.0.0-rc1` no longer satisfies `1.0.0`
- And a 64-zero `InstallerSha256` **fails** once both `PackageVersion` and the URL tag are off their
  placeholders, with no manual promotion step: the zeros are licensed only by the paired scaffold state,
  and a half-bump is itself a blocking finding, so there is no path through the middle
- And the two placeholder advisories are anchored on the `url`/`sha256` **directives** rather than on a
  whole-file grep, so they stop firing once a real tag and digest are written — both formulas name their
  own placeholder strings in header prose, which a `grep -q` would have matched forever
- And a missing `ruby` or an unimportable `pyyaml` is exit 2, not a skip: a gate that skips is not a gate
- And the two placeholder advisories fire and do **not** fail the build, because the Homebrew
  placeholders and the winget `0.0.0` scaffold are the honest current state. The script records when
  each is promoted to blocking: once a release has actually gone out through that channel

**Scenario [UNVERIFIABLE HERE]: a macOS user installs the CLI from a published tap**
- Given a published `homebrew-devteam` tap carrying `packaging/homebrew/devteam.rb`, at a real release
  tag with the digest of GitHub's own codeload tarball for it
- When a macOS user runs `brew install <tap>/devteam`
- Then `devteam` is on `PATH` and resolves the `devteam` package as a sibling of the CLI entry point
- And `devteam path --json` emits one conforming document and creates neither `core/` nor `data/`
- Unverifiable here because: **there is no tap repository**. The tap-less obstacle is gone — Homebrew 7
  rejects a formula file that is **not inside a tap**, separately disables `brew audit <path>` outright,
  and refuses to load a formula from an untrusted tap, and `verify-formula-locally.sh` works around all
  three with a throwaway, trusted, sandboxed tap. (Its own
  `brew install --build-from-source <path-inside-that-tap>` is a file-path install and works: what
  Homebrew rejects is the *tap-less* path, not the path form.) But a throwaway tap is not a published
  one, and nobody has ever run `brew tap` against a real repository and installed this formula from it.
  Nor has any **release tarball** been installed: the formula's `sha256` is still the literal string
  `REPLACE_WITH_SHA256_OF_RELEASE_TARBALL`, and the local verification installs a tarball built with
  `git archive … HEAD` — committed sources, the same file layout but not the same bytes GitHub's
  codeload serves, and packaged from a tree state that did not include the formula edits the same run
  was auditing. `release.yml`'s `macos-latest` job closes the codeload half on the first tag that is
  pushed. The python dependency is no longer part of this: it is current (`python@3.14`) and
  `verify-formula-locally.sh` reports drift against `brew info python3` on every run.

**Scenario [UNVERIFIABLE HERE]: pushing a version tag updates the formula for review, and proves it
installs before anyone merges**
- Given a tag matching `^v[0-9]+\.[0-9]+\.[0-9]+$` pushed to this repository
- When `.github/workflows/release.yml` runs
- Then it downloads that tag's GitHub source archive — the same URL `scripts/install.sh` uses, so
  there is one artifact shape rather than a second one only Homebrew users receive
- And it computes a 64-character hex digest of the bytes it actually received, refusing anything else
- And it calls `.github/scripts/release/bump-homebrew-formula.sh` to rewrite only the formula's `url`
  and `sha256` lines, and opens a pull request against `main` rather than pushing to it
- And a tag of any other shape is refused before anything is downloaded
- And the bump job uploads the rewritten formula as an artifact, which a second `macos-latest` job
  downloads and checks against the digest that job computed: the `url` and `sha256` directives must
  equal it, the url must end in this tag, and **nothing else in the file may have changed** — both files
  normalised on those two values and diffed, which is the one thing the rewrite's own after-the-fact
  grep cannot see
- And that job then runs `packaging/verify-formula-locally.sh` in release mode against that exact URL
  and digest — passed between the jobs as an output rather than re-downloaded — so a formula that does
  not install shows up as a red check on the release run instead of as a failed `brew install` for
  whoever updates first
- **Not** asserted, and stated here because the criterion above reads like a gate: that job **is not a
  gate**. The pull request is opened by the bump job's own last step, so it is already open while the
  `macos-latest` job runs, and no branch rule marks the check required. A red check informs the
  maintainer who merges; it stops nothing. `release.yml`'s own `RESIDUAL` block records this
- Unverifiable here because: **the workflow has never been triggered** — the newest tag in this
  repository predates the commit that added it. What is untested is specifically the Actions run: the
  tag-validation step, GitHub's codeload materialisation timing and the retry loop around it, the PR
  creation, the artifact hand-off, and the digest passed between the two jobs. The **rewrite logic** is
  no longer part of that gap: it was extracted out of two inline `run:` blocks into a script precisely
  because inline in YAML it could only be exercised by pushing a real tag, and it is now covered by the
  23 tests in the scenario above. Nor is the `macos-latest` job's script untested — it is the same
  script a maintainer has run locally; only its release mode, against a real released artifact, has
  never run.

**Scenario [UNVERIFIABLE HERE]: a Windows user installs the CLI with winget**
- Given a signed Windows installer, real asset URLs, real digests taken after signing, and a version
  directory renamed from `0.0.0` to the release version
- When the three manifests are submitted as a pull request to `microsoft/winget-pkgs` and accepted
- Then `winget install DevToolbelt.Devteam` installs the CLI at user scope and exposes the `devteam`
  command
- Unverifiable here because: **no Windows installer has ever been built**, so both `InstallerSha256`
  values are 64 literal zeros and both `InstallerUrl`s point at assets that do not exist;
  `InstallerType: exe` is a design placeholder, not a decided packaging tool — `packaging/README.md`
  § *The Windows installer shape* now records the three candidates and the `winget validate` /
  `winget install --manifest` test that discriminates them, and deliberately does **not** decide
  between them, because that test needs a Windows machine; shipping unsigned would trigger SmartScreen
  on every install, so an Authenticode certificate is a prerequisite for the `.exe` candidate (the two
  portable candidates make signing recommended rather than required); and acceptance is review by
  Microsoft, on Microsoft's infrastructure. What **was** checked here: `manifestVersion 1.12.0`, the
  required-field set of all three manifest types, and the `InstallerType`/`NestedInstallerType` enums,
  against the schema files in `microsoft/winget-cli`; plus, on every pull request and every push to
  `main`/tags, the cross-file contract
  asserted by `.github/scripts/ci/04-packaging.sh` (see the `[MET]` scenario above). Neither is
  `winget`'s own opinion, and they are not the same authority.

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
  id are guesses to be confirmed from the app's own `Info.plist` once it exists. What the absent
  artifact blocks is precisely the install, the digest and the codesign/notarisation checks — **not**
  static style checking, which does run and is **not clean**: `brew style` on the cask reports four
  cask-cop findings today (`Cask/StanzaOrder` ×2, `Cask/StanzaGrouping`, `Cask/ArrayAlphabetization`),
  none of them fixed. `packaging/README.md` § Verification records them as a known state.

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
- Unbuilt. Both preconditions this scenario used to list as open have since closed, and the residue is
  smaller and more precise: `unsupported_by()` **does** have a caller now — `devteam compat`, with
  `--client`/`--client-file` and an explicit `may_write` — so the comparison no longer has to be
  reimplemented in the client; and the cask **does** declare `depends_on formula: "devteam"`, so which
  `devteam` an app installed through Homebrew invokes is answerable. What remains open is that the app
  must still call `devteam compat` before it writes, because a user can upgrade the store from a
  terminal without touching the app, and nothing on the framework side refuses a client that never
  asks.

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
- **Framework-side enforcement of client compatibility.** `devteam compat --client` now *answers* the
  question — it returns `may_write` and, when false, the blocking shapes with both numbers — but
  nothing makes a client ask it, and no command refuses a write from a client that did not. The client
  is the party that degrades, by design
- **Reconciling `min_app_version` with `store_schemas()`.** ADR-0011's amendment argues they are two
  mechanisms answering one question and proposes which should be normative. That decision is not made,
  and this spec asserts neither outcome
- **The Windows packaging shape for the CLI.** Still undecided, and deliberately so: the choice moves
  `InstallerType`, `InstallerSwitches`, `NestedInstallerType`/`NestedInstallerFiles` and `Dependencies`
  together. `packaging/README.md` § *The Windows installer shape* now records three candidates — a
  signed `.exe`, a `zip` + `portable` nest around a built `devteam.exe`, and the same nest around the
  python sources plus a launcher with a `PackageDependencies` entry for python — with the
  discriminating test written out for each, and the one open question that separates the last two:
  whether winget's `portable` nest accepts a non-`.exe` file. The schema does not constrain it and
  Microsoft's manifest documentation does not address it, so only `winget validate` and
  `winget install --manifest` on a real Windows machine answer it. This spec asserts no outcome
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
  (green, 35 tests — this entry originally said 19, which was already wrong when it was written); five
  cannot be exercised without an Apple Developer ID, an Authenticode
  certificate, a published tap, or review by Microsoft; one describes software that does not exist.
  Marking them separately is what makes the document usable as a checklist when those credentials
  arrive, instead of a claim that the channels are live.
- 2026-09-28 | technical-writer | Four scenarios added as `[MET]` and two re-marked in place, after
  M4.2 was taken from "the files exist" to "everything provable here is proven". New: the formula's
  declared payload runs (`tests/test_packaging.py`, 10 tests then, 12 today); the formula installs
  through a real Homebrew and passes `brew test` (a recorded run of
  `packaging/verify-formula-locally.sh` on macOS, Homebrew 7.0.6, via a throwaway tap); the release bump
  rewrites two lines and refuses everything else (`tests/test_release_bump.py`, 15 then, 23 today); and
  `packaging/` is gated in CI at all
  (`.github/scripts/ci/04-packaging.sh`). The two `[UNVERIFIABLE HERE]` packaging scenarios keep their
  marks but had their stated reasons corrected, because both were wrong rather than merely incomplete:
  the macOS one claimed `brew install` and `brew audit` could not be run without a tap — a throwaway
  tap removes that obstacle, and what is actually unproven is the **published** path and the real
  codeload bytes — and it named a `python@3.12` drift that is now current and machine-reported. The
  release one claimed its logic had only been dry-run by hand; the logic is extracted and tested, and
  only the Actions run is untested. The `[MET]` legend now distinguishes a CI test from a recorded run,
  because this milestone produced the first criterion that only a maintainer's machine can assert, and
  collapsing the two would have been the same overstatement in a new place. Two stale M4.1 statements
  corrected while here: `unsupported_by()` has a caller (`devteam compat`), and the cask declares
  `depends_on formula: "devteam"`. M4.3 is untouched and stays `[UNBUILT]`.
- 2026-09-28 | technical-writer | **Eleven claims corrected against the artifacts; no mark moved.** Every
  correction weakens a sentence — this document's failure mode is asserting more than the artifacts
  support, and four claims in the repository's own ADRs had already had to be retracted for it. What
  changed: "on every push" (three places) is now "every pull request, plus pushes to `main` and to tags",
  which is what `ci.yml`'s trigger actually is; "a tarball built from the working tree" (three places) is
  now `git archive … HEAD`, committed sources, with the consequence named — the recorded run packaged
  committed sources while auditing an uncommitted formula; the `brew audit --new` claim is **removed
  rather than restated**, because on a private-tap formula every `--new` check is gated on the core tap
  and a clean result would mean "the checks did not run"; "the run leaves the machine as it found it" is
  false in two ways now stated (transitive formulae reported not removed; ~100 MB of Homebrew dev gems
  permanent by design); "never a skip" in the payload scenario is bounded to lines containing
  `.install`; the release-workflow scenario now says outright that its `macos-latest` job **is not a
  gate**; the cask scenario records four unfixed `brew style` cask-cop findings instead of implying the
  missing `.dmg` blocks static checking; and every test count is re-measured (12 / 23 / 35, suite 344).
  The `[MET]` legend now says a recorded run is one execution on one machine, not a channel. One number
  in the first amendment entry was factually wrong when written (19 for `test_json_contract.py`, which
  was 35 already) and is corrected in place; the second entry's counts were accurate then, so they are
  annotated "then / today" rather than rewritten. M4.3 stays `[UNBUILT]`; nothing about signing,
  notarisation, the tap repository or the winget PR has become done.

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
