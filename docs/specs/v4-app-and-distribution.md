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
**M4.3 is the Electron app. Its first slice is built and ships to nobody** — `app/` holds the client
decided by [ADR-0015](../development/adrs/0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md)
(the stack, where the source lives, which process may spawn, which `devteam` is invoked and what happens
when none is found), with 201 passing tests and 1 skipped under `app/test/` and a CI gate at
`.github/scripts/ci/05-app.sh`. Releasing it is still blocked on signing credentials the repository owner
holds: every build is unsigned by configuration, so its scenario below is `[PARTLY MET]`, clause by
clause, and not `[MET]`.

**Subsequently, the framework's half gained the write gate M4.1 stopped short of.** `devteam compat`
answered "may this client write?" and nothing made the answer binding. A caller may now declare the
shapes it understands (`--client-schemas <PATH>` or `DEVTEAM_CLIENT_SCHEMAS`), and a caller that
declares is refused every mutating command it cannot understand, at exit 4, before anything on disk
changes. An incompatible declaration also **suppresses the one-time pre-ADR-0013 layout relocation**,
because that relocation writes the very shapes such a caller said it cannot read — and the single
read-only command whose answer depends on it, `devteam list`, is refused at exit **3** rather than
allowed to report an empty store. A caller that declares **nothing** is unaffected and keeps the entire
pre-gate write surface —
that boundary is a decision, not an unfinished edge, and it is recorded in
[ADR-0014](../development/adrs/0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md)
§ 3 together with the `json_contract` deprecation policy and the ruling that `store_schemas()` is the
normative compatibility statement.

**Every scenario below is marked, and the marks are the point of this document:**

| Mark | Meaning |
|------|---------|
| **[MET]** | Built and asserted, by something named in the scenario itself — either a test that passes today (`tests/test_json_contract.py`, 35 tests; `tests/test_client_gate.py`, 52; `tests/test_packaging.py`, 12; `tests/test_release_bump.py`, 23; all green, in a suite of 407) or, where a test cannot reach it, a **recorded run**: one execution on one maintainer's machine, with its platform and tooling version stated. A recorded run is evidence, not a channel — nothing re-runs it, and a `[MET]` resting on one says so in its own first line. |
| **[UNVERIFIABLE HERE]** | Stated as the criterion a human must check, against accounts, certificates and third-party review this environment does not have and should not be given. The artifact exists; the criterion has never been exercised. |
| **[UNBUILT]** | The criterion is stated so the client has something to be built against. No code exists. |
| **[PARTLY MET]** | Some clauses are asserted by a named test today and the rest are not, so the scenario **as a whole is not met**. Introduced for M4.3, where `[MET]` and `[UNBUILT]` would both be false in opposite directions: the client exists in source and is tested, and nothing about it ships. Every clause carries its own verdict and the test that earns it; a clause with no test named is not met. |

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

**Scenario [MET]: a client that declares shapes it cannot handle is refused every write** — asserted by
`tests/test_client_gate.py` (52 tests), on every pull request and every push to `main`/tags
- Given a caller that names the shapes it understands, through `--client-schemas <PATH>` or
  `DEVTEAM_CLIENT_SCHEMAS`, and is a version behind on every one of them
- When each command classified as mutating runs — swept from `compat.MUTATING` itself, not from a list
  written in the test, so a command added tomorrow is covered the moment it is classified
- Then the process exits **4** (conflict), because nothing ran; `devteam compat`'s exit 1 stays the code
  for a question that ran and answered "no"
- And the message names the command and every blocking shape with both numbers, and `details` carries
  exactly `{command, declared_by, declaration_source, client_schemas, store_schemas, unsupported,
  may_write}` — the **key set** is pinned in both directions, failing on an added key as loudly as on a
  removed one, and every value is asserted rather than only the names
- And the store is byte-identical before and after — every path under it compared by content digest, not
  by name, because a gate that refused *after* rewriting the registry would be invisible to a listing
- And that holds on a store that has **not** yet been relocated to the ADR-0013 split layout, which is
  where the gate's *position* is asserted: the refusal happens before `store.adopt_machine_layout()`, and
  the sweep runs over the whole of `compat.MUTATING` rather than one command, so a gate moved below the
  relocation — or granted a per-command exemption — fails here
- And `declared_by` names the seam the caller actually used, with the flag outranking the environment
  variable in both directions
- And every declaration error names the seam that carried the path — `--client-schemas <PATH>`,
  `--client-file <PATH>` or `DEVTEAM_CLIENT_SCHEMAS <PATH>` — rather than a bare path the caller never
  typed on its own, asserted for all three seams
- And a shape the client never mentioned is reported unsupported with `client: null`, taken from
  `compat.unsupported_by()` rather than re-derived at the call site
- And a client **ahead** of the store is not refused
- And a missing declaration file, one that is not JSON, one that is not an object, one claiming a
  non-integer (including a boolean), one that is not decodable as UTF-8 text, and one nested too deeply
  for the JSON parser are each exit **2** with the file named, and the command does not run — a
  malformed declaration must never read as no declaration, which is the fail-open case
- And `--client-schemas ""` (or whitespace) is exit **2** as well, not the anonymous path: a shell cannot
  distinguish an absent variable from an empty one, so "empty means unset" holds for the variable and for
  nothing else. A flag given an empty value is a caller that meant to declare and got the value wrong —
  `--client-schemas "$SCHEMAS"` with `SCHEMAS` unset — and downgrading it to silence dropped the gate on
  exactly that invocation. Asserted through the CLI and against `compat.client_declaration` directly, and
  asserted not to fall through to a *compatible* exported variable, which is how the mistake would have
  been hidden behind an unrelated declaration
- And the last two of those — not UTF-8, nested too deeply — reach the caller as **one** parseable
  document on stdout under `--json` with no traceback on stderr; both previously escaped as exit 3
  ("unexpected `UnicodeDecodeError` / `RecursionError`"), which a client branching on `$?` reads as an
  environment problem rather than as its own malformed question
- And every one of the 35 leaves the parser walk discovers is classified as mutating or read-only, with
  no leaf in both tables and no table entry naming a command that no longer exists;
  `compat.is_mutating()` treats an unclassified command as mutating, asserted rather than assumed
- And `compat`, `version`, `path`, `catalog`, `list`, `store list`, `prefs list/get` and
  `cred list/get/check/backends` are never refused **as writes**, so a client that has fallen behind can
  still read — including reading a credential value — and can still ask how far behind it is
- And `cred get --json` still answers with its documented exit-2 refusal under an incompatible
  declaration, rather than an exit 4 that would send every client looking in the wrong place

**Scenario [MET]: a caller that declares nothing is affected in no way** — asserted by
`tests/test_client_gate.py`, the same suite
- Given the same store and the same mutating command as above
- When it is invoked with no `--client-schemas` and no `DEVTEAM_CLIENT_SCHEMAS`
- Then it performs the mutation, and the pair is asserted both ways round in one test: refused when
  declared, performed when not
- And an empty or whitespace-only `DEVTEAM_CLIENT_SCHEMAS` is treated as *unset*, so a wrapper that
  unsets by assigning empty lands on the anonymous path instead of being refused every write — and the
  **flag** does not share that treatment, which the scenario above asserts as the deliberate asymmetry
- And the gate leaks nothing into the `--json` contract: `bind --json` carries no `client_schemas` and
  no `unsupported` key, asserted at the point of the change, and the 16 pinned app-facing key sets in
  `tests/test_json_contract.py` are unchanged
- And a read-only command answers byte-for-byte identically whether the caller declares nothing, a
  compatible client, or an incompatible one
- **Not** asserted, and by decision rather than omission: that an undeclared client is detected,
  warned about or logged. It is not. An anonymous invocation is byte-for-byte a human at a terminal, so
  omitting the declaration is a complete bypass of the gate; ADR-0014 § 3 records why and what would
  have to be true to reopen it

**Scenario [MET]: the store's one-time layout relocation does not happen on an incompatible client's
behalf, and the one command that cannot answer without it says so** — asserted by
`tests/test_client_gate.py::PreSplitStoreTest`, the same suite
- Given a store whose machine-local records still sit at the pre-ADR-0013 paths — fabricated by
  de-splitting a store a real `bind` wrote, including the project's own `state-dir` and `memory-dir`
  pointers, so the records hold exactly what the current code produces and a difference the sweep reports
  is the layout and nothing else
- When any command runs under a declaration that is behind on at least one shape
- Then `store.adopt_machine_layout()` does not run, because it rewrites `registry` and `bind_manifest` —
  the exact shapes the caller declared it cannot read — and performing it for that caller is the gate
  letting through the one write it exists to stop
- And a **compatible** declaration, and an **anonymous** caller, both still get the relocation, so no
  store is stranded by this; the anonymous case also still reports the move on stderr
- And every read-only command answers **identically** on the pre-split store and on the same store after
  relocation, or is refused — asserted by running each leaf of `compat.READ_ONLY` twice under the same
  declaration and comparing exit code and document
- And the set of commands that must be refused is asserted **equal** to `compat.NEEDS_MACHINE_LAYOUT`, so
  the table is measured rather than trusted: a command that starts reading a machine-local record fails
  this sweep instead of quietly joining the wrong side
- And that set is exactly `{devteam list}` today, because `paths.registry_file()` resolves only the
  post-split path: `list` read no registry at all and reported every bound project as unbound — exit 0,
  `projects: []`, no error anywhere. The remaining read-only commands resolve through the project's own
  pointers or through the core store, so the layout never reaches their answer
- And `devteam list` is therefore exit **3**, not 4: the caller is entitled to read, and what is not ready
  is the **environment**, whose repair is a write the caller cannot accept. Its `details` carry the
  refusal's seven keys **plus `machine_layout_pending: true`**, and its `hint` names the fix that does not
  require upgrading the client — run any `devteam` command from a terminal with no declaration
- And the positive control is asserted beside it: the same store, the same command, invoked anonymously,
  relocates and finds the bound project — without it, "refused" could be a store that genuinely has
  nothing bound
- And `devteam compat`, `devteam version` and `devteam path` — the three escape hatches that hint names —
  answer on the un-relocated store and relocate nothing, so the guidance is not a dead end for the caller
  it is written for
- **Not** asserted: that `NEEDS_MACHINE_LAYOUT` is correct for a layout other than the one this fixture
  builds. The sweep measures one de-split shape, which is the shape that exists; a future layout change
  brings its own fixture

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
- Unverifiable here because: **there is no signed, notarised `.dmg` and no release to attach one to.**
  The reason has narrowed since this scenario was written, and the narrowing is worth stating rather
  than leaving the old sentence standing: `app/` now exists and `npm run dist:mac` produces a universal
  `dev-team-agents.app` inside `dev-team-agents-<version>.dmg`, so "there is no build" is no longer the
  obstacle. **Every such build is unsigned by configuration** — `app/electron-builder.yml` sets
  `mac.identity: null` and `mac.notarize: false`, `app/build/after-build.cjs` prints
  `UNSIGNED, UNNOTARISED BUILD — DO NOT DISTRIBUTE`, and `app/src/main/build-info.ts` carries
  `CODE_SIGNED = false` as a greppable source constant — and an unsigned build is not this scenario's
  subject: `brew audit --cask` verifies a Developer ID signature and a notarisation ticket, so its
  correct verdict on an ad-hoc-signed artifact is *reject*. Signing needs a paid Apple Developer ID and
  notarisation needs an app-specific password or API key, which are account-level credentials this
  environment does not have. No CI job builds the artifact either: `.github/scripts/ci/05-app.sh` runs
  `typecheck`, `lint` and `test` and deliberately never `dist:mac`. Two of the cask's guesses are no
  longer guesses: the macOS floor is **measured** at `">= :monterey"` (the pinned Electron's
  `Info.plist` declares `LSMinimumSystemVersion` 12.0, so the previous `">= :big_sur"` licensed an
  install on a system the app cannot launch on) and the bundle id is read from the build's `appId`.
  What the absent **release** artifact blocks is precisely the install, the digest and the
  codesign/notarisation checks — **not**
  static style checking, which does run and is **not clean**: `brew style` on the cask reports four
  cask-cop findings today (`Cask/StanzaOrder` ×2, `Cask/StanzaGrouping`, `Cask/ArrayAlphabetization`),
  none of them fixed. `packaging/README.md` § Verification records them as a known state.

**Scenario [PARTLY MET]: the app is a client, and never a prerequisite**
- Given the desktop app (milestone M4.3), whose first slice now exists in `app/` — Electron,
  TypeScript, Vite, React, decided by
  [ADR-0015](../development/adrs/0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md),
  with 201 passing tests and 1 skipped under `app/test/` and a CI gate at
  `.github/scripts/ci/05-app.sh`
- When any action in the UI runs
- Then it invokes `devteam <command> --json` and renders the result
  - **[MET] for the invocation.** `--json` is appended by the invocation layer itself, not by callers,
    so no operation can omit it — `app/test/invoke.test.ts` · *appends --json itself so no operation can
    forget it*. The renderer supplies no command: every argument vector is built in
    `app/src/cli/operations.ts` from a closed `ALLOWED_COMMANDS` list, and
    `app/test/operations.test.ts` · *runs nothing the framework has not classified at all* asserts every
    entry of that list is classified by `compat`. Spawning is argv-array and never a shell string
    (*never builds a shell string from the arguments*, *passes arguments as an array, so shell
    metacharacters are inert*).
  - **[MET] for "and renders the result", and this is the clause that moved.** `app/test/renderer/`
    mounts the screens against a stubbed `window.devteam` and compares what is displayed with what the
    bridge answered: `projects.test.tsx` (11 tests) and `doctor.test.tsx` (3). The assertions were
    chosen against the failure mode ADR-0015's fourth Risks row names rather than for coverage —
    `path_exists` is asserted in **all three** states (`true`, `false`, and `null` rendered as *not
    checked*, never as an affirmative "missing" beside a path that exists), an `ok: true, outcome:
    'findings'` result renders the report rather than an error, an `ok: false` renders its `message`
    **and** its `hint`, and a successful write's `notice` is displayed when present and renders nothing
    when absent.
  - **The render suite found a real defect on its first pass, which is the evidence that it is testing
    something.** A row-level write's success notice was unreadable by construction: the write called
    `reload()`, `useOperation` reset to `loading`, the whole table was replaced by a spinner, and that
    unmounted the very row whose notice had just been set. A reload now keeps the result already on
    screen (`useOperation`'s `refreshing`), only the first load blanks it, and the test that documented
    the defect is now the regression that asserts the notice survives — plus a second one asserting the
    table stays mounted mid-reload and the refresh is announced.
- And no bind rule, preference merge or credential resolution exists in the app's own code
  - **[MET] for credential resolution, by non-invocation.** `app/test/operations.test.ts` · *never runs
    `cred get` — a value must not enter this app* asserts no allowed command so much as **starts**
    with `cred`, so no credential value can enter the process by any route the app has.
  - **Not asserted for the other two, unchanged by this round.** No `prefs` command is wired, so no
    merge can be reached — still an absence inferred from the command list rather than a test, and
    ADR-0015's second amendment now records *why* `prefs set`/`prefs unset` stay unwired: the cascade has
    three personal layers, and a UI that edits one without showing which layer answered would
    misrepresent the model it is editing. Nothing asserts ADR-0015 § 4's stronger rule that the **main
    process reads no store file directly** either; it is held by review. The bind *rule* is likewise an
    inference: the app now invokes `bind`, and that it reimplements none of the rule follows from the
    argv being a `devteam bind` rather than from an assertion.
- And the app reads the `compat` block before it writes, and when `store_schemas` reports a shape it
  does not understand it degrades to read-only **and says so**
  - **[MET], within the limit that the slice has no write to gate.** The declaration is the app's own
    frozen constant, never derived from a store (`app/test/handshake.test.ts` · *names every shape
    `store_schemas()` declares*, *is frozen, so nothing can derive it from a store at runtime*), and
    `app/test/real-cli.test.ts` · *agrees with the real store_schemas, so the app's constant is not a
    guess* pins it against the real CLI. An exit-1 answer is read as a **verdict, not a failure**, and
    `may_write` is never inferred from `unsupported` (*treats the exit-1 answer as a verdict, not a
    failure, and stays read-only*; *does not infer the verdict from `unsupported` when no boolean was
    returned*). "Says so" is asserted, not assumed: the same test requires the plain-language summary
    to contain both `read-only` and the offending shape's name. Three further tests assert the
    degradation when the handshake cannot complete at all. Against the real gate,
    `app/test/real-cli.test.ts` · *handshakes as behind, read-only, when the app declares an older
    shape* and *is refused with exit 4 on a mutating command when the declaration is behind*.
  - **[MET] for "before it writes", and it stopped being vacuous.** The clause used to be satisfied by
    there being no write to gate. There are now six — `bind`, `unbind`, `sync` (single and `--all`),
    `pin`, `upgrade` — and every one declares on the invocation that performs it, so the gate re-compares
    on each call and a store upgraded from a terminal is covered by the app's next call. `app/test/
    real-cli.test.ts` drives the refusal through an operation rather than a hand-built argv: *is refused
    with exit 4 on a mutating command when the declaration is behind*. The app also **withholds** write
    actions itself when its own declaration could not be written, and the gating **fails closed** — before
    the environment report arrives, write actions are disabled rather than enabled, which is asserted by
    `app/test/renderer/projects.test.tsx` · *fails closed while the environment is unknown*. ADR-0015's
    second amendment records which commands remain deliberately unwired and why.
- And it special-cases `devteam cred get`, which answers `--json` with a conforming error by design
  - **Not met as written, and satisfied in a stronger way.** The app has no special case, because it
    never calls `cred get` at all (ADR-0015 § 7), which the test named above asserts. The exception is
    still owed as a **category** — the first secret-handling command anyone wires needs it — so this
    clause is not deleted; it is recorded as not applicable to a client that never reaches the command.
- And every capability the app exposes remains reachable from the CLI alone, so a user who never
  installs the app loses only the screens
  - **Still not met, and now for a better reason than "no surface".** Every command the app runs is a
    `devteam` command by construction — *runs nothing the framework has not classified at all* asserts
    exactly that against `compat`'s own tables — so nothing the app does is unreachable from a terminal.
    What is unasserted is the **converse direction the criterion is really about**: that no capability
    the UI offers is *only* reachable through the UI. With six write actions this is finally a claim with
    content, and nothing mechanical checks it: the argument is that `ALLOWED_COMMANDS` is a closed list of
    CLI subcommands and a reviewer can read it, which is review, not a test.
- **The scenario as a whole is not met, and no amount of passing tests moves it.** The app is unsigned
  (`CODE_SIGNED = false`, `mac.identity: null`), unreleased, installable by nobody: no cask artifact,
  no winget manifest for the app at all, and `KEEP_ROOT` drops `app/` from every installed project. A
  client that ships to nobody cannot have satisfied a criterion about what a user who installs it gets.
- Three preconditions this scenario used to list as open have since closed, and the residue is
  smaller and more precise each time: `unsupported_by()` **does** have a caller now — `devteam compat`,
  with `--client`/`--client-file` and an explicit `may_write`, and `compat.gate()` — so the comparison no
  longer has to be reimplemented in the client; the cask **does** declare
  `depends_on formula: "devteam"`, so which `devteam` an app installed through Homebrew invokes is
  answerable; and the framework **can** now refuse — see the two gate scenarios above. What remains open
  is exactly one half of what this bullet used to claim, and the halves are worth separating:
  - **Closed:** an app that declares its shapes is refused every mutating command it cannot understand,
    at exit 4, before anything on disk changes. It does not have to remember to call `devteam compat`
    first, and it cannot cache a stale "yes" — the gate re-compares on every invocation, so a user who
    upgrades the store from a terminal without touching the app is covered by the next call the app
    makes. The framework also declines to migrate the store's layout on such an app's behalf, and tells
    it so at exit 3 on the one read-only command that cannot answer without the migration, rather than
    handing it an empty project list.
  - **Open by decision, not omission:** an app that declares **nothing** is still not refused, and no
    framework code detects it. The gate binds the caller that identifies itself; omitting the
    declaration bypasses it entirely. So the criterion above — the app reads the `compat` block,
    degrades to read-only and says so — remains the **app's** obligation, and the framework's half is
    now a safety net for an honest app rather than a guarantee against a silent one. ADR-0014 § 3
    records the reasoning and the reopening condition.
  - **The client now declares, and that is the part that moved.** This bullet used to read "still
    unbuilt regardless: the app — nothing in this scenario is met, because there is no client to
    declare anything." There is one: it declares its own frozen constant on every gated invocation, and
    `app/test/real-cli.test.ts` drives the framework's refusal end to end. So the framework's half is no
    longer a safety net waiting for a client to be honest towards — it has one. What has not moved is
    shipping: the client is unsigned, unreleased and installed by nobody, which is why the scenario is
    `[PARTLY MET]` and not `[MET]`.

### Out of Scope
- **Everything about the Electron app beyond its first slice.** Milestone M4.3 is no longer wholly
  outside this spec's scope, and the bullet is rewritten rather than left standing: the app's stack and
  its operating rules as a CLI client are decided in
  [ADR-0015](../development/adrs/0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md),
  and a first slice exists in `app/` with its criteria now marked `[PARTLY MET]` above, clause by clause,
  each against a named test. **What remains out of scope, and why each one is:**
  - **Signing, notarisation and release.** Still blocked on credentials the repository owner holds — an
    Apple Developer ID and an Authenticode certificate. Every build is unsigned by configuration, so
    there is no artifact any channel can describe
  - ~~**A winget manifest for the app.**~~ **No longer out of scope — scaffolded, and the shape is
    decided: NSIS, per-user, unsigned by configuration.** `app/electron-builder.yml` has a `win`/`nsis`
    block and `packaging/winget/manifests/d/DevToolbelt/DevteamApp/0.0.0/` holds the three manifests,
    expressing the CLI dependency through `Dependencies.PackageDependencies` — winget's closest
    equivalent to the cask's `depends_on formula: "devteam"`, and **not** a confirmed winget behaviour.
    What remains out of scope is everything that needs a built artifact or Windows tooling: real
    `InstallerUrl`/`InstallerSha256` values, and any run of `winget validate` or `winget install
    --manifest`. `packaging/README.md` § Verification records those as unverified by name
  - ~~**Every write action.**~~ **No longer out of scope — built.** ADR-0015 § 8 sequenced them after
    the declaration seam had been driven by a real client; that happened, and the project lifecycle
    (`bind`, `unbind`, `sync` single and `--all`, `pin`, `upgrade` as plan-then-apply) is now wired and
    marked above. What stays out is the rest of `compat.MUTATING` — `update`, `uninstall`, `store
    install|use|gc`, `export`/`import`, `migrate`, `prefs set|unset`, and every `cred` command — each with
    its own recorded reason in ADR-0015's second amendment, not as a backlog
  - ~~**Any assertion about what a screen renders.**~~ **No longer out of scope — `app/test/renderer/`
    mounts the screens.** What stays out is anything needing a real browser or a packaged build: no test
    launches Electron, drives the real window, or exercises the native directory picker, so
    `chooseProjectDirectory`'s dialog is asserted only through its stub. ADR-0015's fourth Risks row is
    narrowed by this, not closed
  - **A build or release job for the app.** CI typechecks, lints and tests it (`05-app.sh`) and never
    builds an artifact, because a gate that produces an unsigned `.dmg` is shipping, not checking
- **Implementing the JSON contract's deprecation mechanism.** The *policy* is no longer open: ADR-0014
  § 2 states what obliges a `json_contract` bump, what does not — including its ruling that an error
  envelope's conditional `hint` appearing on a path that did not previously set it is additive and free,
  its named carve-out for an exit code **corrected** from a crash rather than moved, and when the policy
  starts binding at all (the first release that ships the CLI; nothing has) — that one value
  is live at a time, and
  that a departing key is marked in the payload for one full release before it is removed. What is out
  of scope is the mechanism — **no payload emits a `deprecated` list, nothing reads one, and no test
  mentions it.** The first deprecation implements it; there is nothing to deprecate at
  `json_contract: 1`. Four of the policy's five contributor steps have no gate, which ADR-0014's first
  risk row records rather than resolves
- **Per-command payload field contracts, beyond the pinned set.** The generic sweep pins the *envelope*
  for every command. On top of it, `tests/test_json_contract.py::AppFacingKeySetContractTest` pins the
  exact top-level key set of **16** app-facing payloads and the per-record key set of **5** list
  payloads — 16 tests, green — so dropping `project_id` from `bind --json`, the finding that class's
  docstring cites by name, now fails the build. What is out of scope is the rest: `EXPECTED` is a
  hand-written list with **no assertion tying it to the parser walk**, so a payload nobody added —
  among them `sync`, `unbind`, `pin`, `prefs set/unset`, `cred set/unset/import`, `store install/use/gc`,
  `migrate`, `upgrade`, `export`, `import`, `uninstall` — can still be renamed or dropped with every
  check passing. This spec asserts the 21 pinned sets and nothing beyond them
- **Framework-side enforcement against a client that declares nothing.** The enforcement that *is*
  built has its own two `[MET]` scenarios above: a caller that declares its shapes is refused every
  mutating command it cannot understand. What stays out of scope, by ADR-0014 § 3's decision rather than
  for want of work, is the other half — nothing makes a caller declare, nothing detects one that does
  not, and an undeclared caller retains the entire pre-gate write surface. The reopening condition is
  stated in that ADR; "make the flag mandatory" does not satisfy it, because identification is not
  authentication
- **Reconciling `min_app_version` with `store_schemas()`.** Decided in ADR-0014 § 1 after this spec was
  written: `store_schemas()` is the normative compatibility statement, `min_app_version` survives only
  as a kill switch for a released app version that writes wrongly for a reason no shape number can
  express, and `minFrameworkVersion` on the app side is advisory. What remains out of scope is any
  *mechanism* for that ruling — `min_app_version` is still consulted by nothing, and only the ADR marks
  it as non-normative. This spec asserts that `version --json` carries the field and that it is null
  (above); it asserts nothing about anything honouring it
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
  a standing exception), ADR-0011, ADR-0014 (the write gate, and the `json_contract` deprecation policy)
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
- 2026-09-28 | technical-writer | **The client write gate added as two `[MET]` scenarios, and three
  `Out of Scope` items corrected — two of which this document was understating.** New scenarios, both
  resting on `tests/test_client_gate.py` (30 tests, green): a caller that declares shapes it cannot
  handle is refused every mutating command at exit 4 with the store left byte-identical; and a caller
  that declares nothing is affected in no way. They are stated as a pair on purpose — the second is the
  property most easily broken in silence, and the test asserts the same command refused when declared
  and performed when not. **`[UNBUILT]` M4.3 is not upgraded**; there is no app. Its residue paragraph
  is split instead, because half of "nothing on the framework side refuses a client that never asks"
  is now closed and the other half is closed *by decision*: an undeclared caller keeps the entire
  pre-gate write surface, per ADR-0014 § 3. Corrections: **"No test enumerates any command's key set"
  was false when written** — `AppFacingKeySetContractTest` has pinned 16 payloads and 5 record shapes
  since M4.1, and cites the `project_id`-from-`bind --json` finding by name. Understating what exists is
  the same defect as overstating it: both are a document that does not match the tree, and a reader
  cannot tell from the sentence which direction it failed in. That is stated here as a principle, not as
  a quotation — the previous round wrote only that *"this document's failure mode is asserting more than
  the artifacts support"*, which is the overstating half, so attributing the symmetry to it would be a
  small version of the same error. The deprecation-policy item is now the *mechanism*, not the policy —
  ADR-0014 § 2 decides the policy — and the `min_app_version` item records ADR-0014 § 1's ruling while
  keeping the absence of any mechanism for it in scope. Test counts re-measured: suite 374,
  `test_client_gate.py` 30.
- 2026-09-28 | technical-writer | **A claims audit of the entry above, and of the same round's ADR text:
  thirteen assertions found wrong, ten of them in these documents and corrected here. The framing error
  is the finding, not the facts.** (The other three are not documentation: a `compat.py` docstring, a
  test-coverage gap behind this document's `details` clause, and one scenario's `Given` naming a seam the
  sweep does not exercise. All three are being fixed in the code and the tests; no clause here was
  weakened to match a gap.) ADR-0011's amendment called three of its Risks-table statements "now stale"
  and ADR-0014 said two of them "went stale with the gate". All three were **false when the rows were
  written**: every contradicting artifact existed at `ed87507`, the commit that wrote them —
  `AppFacingKeySetContractTest` from `95fa346`, `cmd_compat()` calling `compat.unsupported_by()` from
  `4818176`, and the cask's `depends_on formula: "devteam"` from `06fd509`, all three commits ancestors
  of `ed87507`. "Stale" implies decay and there was none, and this round's
  own documents contradicted each other about it: the entry above says "was false when written" of the
  third statement while ADR-0011's amendment called the same fact "now stale". Both are now
  false-when-written, and the three statements are counted as **three across two rows**, since the
  *A client reads `compat` and writes anyway* row supplies two. Also corrected: ADR-0011's
  *"Revisit when the app ships…"* condition is **not met**, in either half — `depends_on formula:`
  guarantees the formula is installed, not which binary the app invokes (the cask's own comment says
  "answerable", not answered), that line predates the condition, and nothing here touched `packaging/`;
  "met by half" is struck and the deviation stated. The envelope sweep covers every discovered leaf
  **except `update` and `uninstall`** (`SKIP_INVOCATION`), and accepts **empty or** exactly one document,
  both of which ADR-0011's M4.1 amendment already stated precisely. `validate-commit-msg.sh` accepts `!`
  through `PATTERN` on line 4, not at `:40-44` (the footer-colon guard); its callers are two, not one —
  `skills/shared/conventional-commits/SKILL.md` presents the invocation as well, and it is the skill the
  mitigation depends on being loaded. `CLAUDE-md/cli.md` and the CHANGELOG said "four" judgment-call
  classifications while naming **six**, and claimed each carries its reason when `upgrade` does not.
  `CLAUDE-md/cli.md`'s example refusal payload was hand-written and unproducible — three shapes, one
  reported unsupported, `registry` at 3 — and is replaced by the real emission of
  `devteam bind --json --client-schemas …` against a throwaway store: five store shapes, two silences
  and one behind number all reported, plus the `hint` key the invented example omitted. The § 3 claim
  that a human's invocation is "byte-identical … asserted rather than argued" is weakened on both counts:
  `--client-schemas PATH` now appears in every command's `--help`, and no test compares against a
  pre-gate baseline. **No mark moved and no scenario weakened** — this round changed only sentences about
  the artifacts, never a criterion.
  **Neither README is changed, and the reason is recorded here because it was not recorded anywhere.**
  The earlier pass reached the right conclusion on two wrong grounds. It is *not* true that "the README
  documents no `devteam` flags at all": `README.md:62`, `:68` and `:69` carry
  `devteam store install --from .`, `devteam migrate --apply` and `devteam upgrade --apply`, and
  `README.pt-BR.md` mirrors all three at the same lines. And the Auto-Docs Rule's "script flags" trigger
  carries no "flags a person invokes" qualifier — read literally, `--client-schemas` fires it. The actual
  defence is narrower and does not need the rule re-read: `README.md:74` and `README.pt-BR.md:74` already
  **delegate** the `--json` contract and exit codes to `CLAUDE-md/cli.md`, which is where this flag, its
  exit 4 and its refusal payload are documented — so the mirror the rule points at is the one that was
  updated. `CLAUDE.md` delegates its whole CLI surface to that same file for the same reason.
- 2026-09-28 | technical-writer | **Four defects found in the write gate were fixed in the code, and
  seven observable behaviours this document did not carry are now recorded: one new `[MET]` scenario, six
  new bullets on the two existing gate scenarios, and one bullet corrected because it was wrong.** The
  new scenario is the pre-split store — an incompatible declaration now suppresses
  `store.adopt_machine_layout()`, because that relocation writes `registry` and `bind_manifest`, the exact
  shapes such a caller declared it cannot read; a compatible declaration and an anonymous caller still
  perform it; and `devteam list`, the single read-only command whose answer depends on it, is refused at
  exit **3** with `machine_layout_pending: true` instead of reporting `projects: []` at exit 0.
  `compat.NEEDS_MACHINE_LAYOUT` holds that one entry because the membership was **measured** — every
  read-only leaf run twice under the same declaration, once on each layout, with the refused set asserted
  *equal* to the table — and the reason only `list` qualifies is recorded: the others resolve through the
  project's own pointers or the core store rather than through the registry. **The corrected bullet** said
  "`compat`, `version`, `catalog`, `list` and `cred get` are not gated"; `list` *is* refused on a
  pre-split store, so the clause is now "never refused **as writes**" and names the read-only set in full.
  Also added: `--client-schemas ""` is exit 2 rather than the anonymous path (the environment variable
  keeps "empty means unset"; the asymmetry is the point, and a truthiness test on the flag had made the
  fail-open reachable through `--client-schemas "$SCHEMAS"` with `SCHEMAS` unset); a declaration file that
  is not UTF-8 or nested too deeply is exit 2 as one parseable document, where both previously escaped as
  exit 3 "unexpected `UnicodeDecodeError` / `RecursionError`"; every declaration error names the seam that
  carried the path; the refusal's seven `details` keys are now pinned **in both directions** with every
  value asserted, which is what makes this document's long-standing `[MET]` on that clause true — three of
  the seven were asserted by no test at all when the mark was written; and the gate's position relative to
  the relocation is asserted rather than trusted, across the whole of `compat.MUTATING` rather than one
  command. **No mark moved and no criterion weakened; M4.3 stays `[UNBUILT]`** — the app does not exist,
  and nothing here is evidence about it. Test counts re-measured with
  `python3 -m unittest discover -s tests -t tests`: suite **396** (was 374), `test_client_gate.py` **52**
  (was 30), `test_json_contract.py` 35, `test_packaging.py` 12, `test_release_bump.py` 23 — all unchanged
  except the gate's own file. One earlier entry's counts were accurate when written and are left alone.
  **One finding is carried out of this round rather than absorbed.** ADR-0014 § 2 lists *"changing which
  exit code an existing outcome uses"* under **obliges a `json_contract` bump**, and one change here does
  exactly that: `devteam compat --client-file <not-UTF-8 | too-deeply-nested>` moved from exit 3 to exit 2.
  Read literally, that is a contract break. Two facts decide it instead of a judgment call, and both are
  now recorded in § 2 rather than here: the old exit 3 was a crash the catch-all labelled *"unexpected
  …"*, not a decided outcome; and **the CLI has never been released** — `scripts/cli/devteam` does not
  exist at `v2.48.0`, the latest tag, so `json_contract: 1` has never been published to any client and
  there is no prior value for a bump to distinguish it from. The other exit-code differences in this round
  are not changes at all: `--client-schemas` and everything reached through it are new in the same
  unreleased change set, so `--client-schemas ""` at exit 2 and `devteam list` at exit 3 replace no
  released behaviour. `json_contract` stays at **1**.
- 2026-09-28 | technical-writer | **M4.3's first slice landed, so its scenario stops being `[UNBUILT]`
  and becomes `[PARTLY MET]` — a fourth mark, added to the legend in the same edit.** `app/` now holds
  the Electron client decided by ADR-0015, with 133 passing tests and 1 skipped under `app/test/` and a CI
  gate at `.github/scripts/ci/05-app.sh`. Neither existing mark could describe it honestly: `[MET]`
  would claim a client users can install, `[UNBUILT]` would claim no code exists, and both are false in
  opposite directions. So the scenario is annotated **clause by clause**, each verdict naming the test
  that earns it, and each clause with no test says so. Moved to met: the invocation half of "invokes
  `devteam <command> --json`" (`invoke.test.ts` · *appends --json itself…*, plus the closed
  `ALLOWED_COMMANDS` list asserted against `compat`'s tables); credential resolution, by the app never
  running any `cred` command at all (`operations.test.ts` · *never runs `cred get`…*); and reading the
  `compat` block, degrading to read-only **and saying so**, which is asserted against both a fake and the
  real CLI (`handshake.test.ts`, `real-cli.test.ts` · *…refused with exit 4 on a mutating command when the
  declaration is behind*). **Explicitly not moved:** "renders the result" (no test opens a window), the
  absence of a bind rule or preference merge (an absence inferred from the command list, not asserted),
  the `cred get` special case (not met as written — the app never reaches the command, which is stronger,
  and the exception is still owed as a category), and "every capability remains reachable from the CLI
  alone" (a four-screen slice has no surface to establish it). **The scenario as a whole is not met, and
  the reason is not test coverage:** the app is unsigned (`CODE_SIGNED = false`, `mac.identity: null`),
  unreleased, and installable by nobody. The `[UNVERIFIABLE HERE]` cask scenario keeps its mark and had
  its **stated reason corrected** — it said "there is no `app/` directory and no build", which is no
  longer why; the obstacle is now a signed, notarised artifact at a real version, and two of the cask's
  guesses became measurements (the macOS floor is `">= :monterey"`, from `LSMinimumSystemVersion` 12.0 in
  the pinned Electron's `Info.plist`; the bundle id comes from the build's `appId`). `## Out of Scope`
  now points at ADR-0015 and enumerates what is still excluded and why, instead of excluding the app
  wholesale. No `[MET]` scenario was touched and no framework-side criterion moved.
- 2026-09-28 | main session | **Test counts re-measured; no mark moved and no criterion changed.** The
  review round that followed M4.3's first slice added tests on both sides, and the three places in this
  document that state a count as *current* had gone stale: the python suite is **407** (was 396) and
  `app/test/` is **139 passing plus 1 skipped** (was 133 plus 1), re-measured with `python3 -m unittest
  discover -s tests -q` and `npm test` in `app/`. Corrected in § Context, in the `[MET]` legend and in the
  `[PARTLY MET]` scenario's Given. **The two dated entries above keep their original numbers** — they were
  accurate when written, and a log that is rewritten to match today stops being a log. Per-file counts in
  the legend (`test_json_contract.py` 35, `test_client_gate.py` 52, `test_packaging.py` 12,
  `test_release_bump.py` 23) are unchanged; the growth is in files the legend does not enumerate.
- 2026-09-29 | main session | **M4.3's second slice: the write actions are wired, the screens are tested,
  and the Windows shape is decided. The scenario stays `[PARTLY MET]`, and the reason is unchanged.**
  Three clauses moved to `[MET]` and each names the test that earns it: *"and renders the result"*
  (`app/test/renderer/projects.test.tsx` 11 tests, `doctor.test.tsx` 3 — `path_exists` asserted in all
  three states, `findings` rendered as a report rather than an error, `hint` rendered, `notice` displayed
  and absent); *"before it writes"*, which stopped being vacuous now that there are six writes to gate;
  and, in Out of Scope, the three exclusions this round built rather than deferred — every write action,
  the app's winget manifest, and screen assertions — each rewritten to say what **remains** excluded
  instead of being deleted. Suite: **201 passing, 1 skipped** under `app/test/` (was 139/1), python
  unchanged at **407**. **The render suite earned its place by failing usefully on its first pass:** a
  row-level write's success notice was unreadable by construction, because the write's own `reload()`
  reset `useOperation` to `loading`, blanked the table, and unmounted the row that would have shown it.
  Fixed by keeping a result on screen across a reload; the test that documented the defect is now the
  regression. **What did not move, and why it is the same reason as before:** the app is unsigned by
  configuration on both platforms, no cask or winget artifact exists at any version, and `KEEP_ROOT` drops
  `app/` from every installed project — a client that ships to nobody cannot satisfy a criterion about
  what a user who installs it gets. Two clauses are also honestly *re-argued* rather than moved: the
  preference-merge absence is still inferred from the command list rather than asserted (ADR-0015 now
  records why `prefs set|unset` stays unwired), and "every capability remains reachable from the CLI
  alone" is still unasserted — but for a better reason than "no surface to test": with six write actions
  the claim finally has content, and what checks it is a reviewer reading a closed `ALLOWED_COMMANDS`.

**2026-09-29 — Windows and macOS stop being simulated, and the app gains a diagnosis of itself.**
Every scenario above that reads *"unverifiable here"* or *"simulated on Linux"* did so against the same
underlying fact: all seven CI jobs ran on `ubuntu-latest`, so the only assertions about Windows were pure
functions handed the string `'win32'`. Two of those jobs now matrix over `ubuntu-latest`,
`windows-latest` and `macos-latest` — `python` (the CLI's stdlib suite) and `app` (typecheck, lint,
vitest) — with `fail-fast: false`. **This closes the execution gap, not the artifact gap:** the five
remaining jobs stay ubuntu-only because their subjects are bash installers, shellcheck, ruby and jq, and
`winget validate` / `winget install --manifest` still have never run, because they need an installer that
has never been built. The `packaging` gate's ubuntu-only note above therefore still stands as written.
Three POSIX-only test groups are now skipped on Windows with a stated reason rather than adapted —
permission-bit assertions (NTFS has none), `test_release_bump.py` (its subject is a bash script, and two
tests branch on `os.geteuid()`), and the staged-CLI run (Windows does not honour a `#!` line) — because a
check loosened until it passes everywhere has stopped testing what it was written for. One documentation
claim was false rather than merely untested and is corrected in `secrets.py`: the fallback secret
backend's "mode-0600 JSON file" is not enforced on Windows at all, and `dpapi`, the backend that should
be reached instead, is itself UNVERIFIED. Separately, `doctor` covered the store, machine, registry and
project but nothing about the app, and it still must not — so the app now evaluates its own
preconditions in `selfCheck()`, a pure function over values the bridge already returned, adding no IPC
channel. It is what finally compares `min_app_version` against the app's own version, a value that had
been read and displayed and never used. Suite: **226 passing, 1 skipped** under `app/test/` (was 201/1),
python **420** (was 417).

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
