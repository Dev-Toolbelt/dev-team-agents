# ADR-0014: Store schemas as the normative write gate and the JSON contract deprecation policy

**Date:** 2026-09-28
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

[ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) makes the desktop
app a client of the CLI and states that compatibility is declared, not assumed. It does not decide
two things it raises, and it says so itself: both appear in its own `## Risks` table, and both were
repeated as out-of-scope items in `docs/specs/v4-app-and-distribution.md` § Out of Scope, which now
points here instead.

**This ADR narrows ADR-0011; it does not reverse it.** ADR-0011's Decision — two channels, the app as
a pure client, the JSON contract as public API — stands unchanged and is not restated here.

### What is open

1. **Two declarations answer one question.** `min_app_version` and `store_schemas()` both answer
   "may this client write?". ADR-0011's Decision text names the first; the implementation gives
   content only to the second. Its fourth risk row states the consequence: a contributor can bump
   `MIN_APP_VERSION` and believe the compatibility question is handled.
2. **`json_contract` is an integer with no rule attached.** Its first risk row: nothing says what
   bumping it obliges, how long the previous value is honoured, or how a client learns a field it
   reads is going away — and the first real change will be made under release pressure with no
   precedent. It also notes that deciding the policy is cheap now and expensive once a client exists.

### What exists in the code

Verified while writing this ADR, and re-verified against the finished gate. `scripts/lib/devteam/`
modules are cited **by symbol** rather than by line, because a line reference into a file under active
change is a reference that is wrong by the time it is read.

| Fact | Where |
|---|---|
| `MIN_APP_VERSION = None`, commented as "bumped when a released app version stops being able to write this store safely" | `compat.py` → `MIN_APP_VERSION` |
| `JSON_CONTRACT_VERSION = 1` | `compat.py` → `JSON_CONTRACT_VERSION` |
| Five shape numbers read from the modules that own them (`project.SCHEMA`, `project.CURRENT_LAYOUT`, `registry.SCHEMA`, `bind.MANIFEST_SCHEMA`, `creds.SCHEMA`), never copied | `compat.py` → `store_schemas()` |
| All three fields surfaced from one function on one call | `compat.py` → `describe()` |
| An absent or non-integer claim (including `bool`) scores as unsupported; a shape the client knows and the store does not is ignored | `compat.py` → `unsupported_by()` |
| `devteam compat [--client \| --client-file]` returns an explicit `may_write` computed as `not unsupported_by(parsed)`. `min_app_version` is carried in the payload and is **not** an input to it | `cli.py` → `cmd_compat()` |
| That command exits **1** when `may_write` is false — findings, not a usage error | `cli.py` → the `elif args.command == "compat"` exit-code branch |
| `version --json`'s `compat` block is asserted equal to `compat.describe()`'s own source, so the block cannot drift from the module | `tests/test_json_contract.py:552-562` |
| **A test now enumerates field sets.** `AppFacingKeySetContractTest` pins the exact top-level key set of 16 app-facing payloads and the per-record key set of 5 list payloads; 16 tests, green. Its docstring cites the review finding — dropping `project_id` from `bind --json` — that ADR-0011's first risk row describes as unmitigated | `tests/test_json_contract.py` → `AppFacingKeySetContractTest`, its `EXPECTED` and its docstring |
| The declaration seam: one parser for `--client-schemas`, `DEVTEAM_CLIENT_SCHEMAS` and `compat --client/--client-file`, with the flag outranking the variable and an empty variable treated as unset. Every rejection names the **seam** that carried the path, not just the path | `compat.py` → `parse_client_schemas()`, `load_client_schemas()`, `client_declaration()` |
| An **empty flag** (`--client-schemas ""`) is a `UsageError`, not the anonymous path — the asymmetry with the empty variable is deliberate, and a truthiness test on the flag had made the fail-open reachable through `--client-schemas "$SCHEMAS"` with the variable unset | `compat.py` → `client_declaration()`; `tests/test_client_gate.py` → `EmptyFlagValueIsNotSilenceTest` |
| Every path out of the declaration parsers raises `UsageError` (exit 2), including `UnicodeDecodeError` and `RecursionError`, which are neither `OSError` nor `JSONDecodeError` and previously escaped to `cli.main`'s catch-all as exit 3 | `compat.py` → `parse_client_schemas()`, `load_client_schemas()`; `tests/test_client_gate.py` → `UnreadableDeclarationIsADocumentNotATracebackTest` |
| All 35 parser leaves classified — 19 mutating, 16 read-only — with the reason beside each entry, and `is_mutating()` failing closed on an unclassified command | `compat.py` → `MUTATING`, `READ_ONLY`, `classify()`, `is_mutating()` |
| The refusal: exit **4**, raised before `store.adopt_machine_layout()` and before any handler, carrying `{command, declared_by, declaration_source, client_schemas, store_schemas, unsupported, may_write}` in `details` — a key set now pinned **in both directions**, with every value asserted, so all seven are evidence rather than three asserted and four assumed | `compat.py` → `refusal()`, `gate()`; `cli.py` → `main()`, `resolved_command_path()`; `tests/test_client_gate.py` → `RefusalDetailsAreThePinnedContractTest` |
| The gate's **position** relative to `store.adopt_machine_layout()` is asserted, not trusted: a fabricated pre-split store, the store compared by content digest after a refusal, across the whole of `MUTATING`. Moving the gate below the relocation previously left the module green | `tests/test_client_gate.py` → `PreSplitStoreTest` |
| An incompatible declaration **suppresses** the one-time relocation — it writes `registry` and `bind_manifest`, the shapes the caller just declared it cannot read — while a compatible declaration and an anonymous caller still perform it | `cli.py` → `main()`'s `if unsupported and store.machine_layout_pending()` branch |
| One read-only command is refused instead, at exit **3** with `machine_layout_pending: true` beside the seven refusal keys: `list` resolves the registry only at the post-split path, so it reported every bound project as unbound at exit 0. Membership is **measured** — every read-only leaf run on both layouts, the refused set asserted *equal* to the table | `compat.py` → `NEEDS_MACHINE_LAYOUT`, `migration_required()`; `tests/test_client_gate.py` → `PreSplitStoreTest` |
| The pair asserted: refused when declared and behind, performed when nothing is declared — same command, same store | `tests/test_client_gate.py` (52 tests, green; suite 396) |

Three statements in ADR-0011's `## Risks` table are false, and none of them was made false by this
work — **all three were already false when that table was written.** They sit in two rows, not three:
*"no test enumerates one [a command's field set]"* and *"`unsupported_by()` has no caller outside its
tests"* and *"the cask declares no dependency on the formula"*. Every artifact that contradicts them
existed at `ed87507`, the commit that wrote the rows: `git show ed87507:tests/test_json_contract.py`
carries `AppFacingKeySetContractTest` with its 16 command and 5 record entries (`95fa346`),
`git show ed87507:scripts/lib/devteam/cli.py` has `cmd_compat()` calling `compat.unsupported_by()`
with `set_defaults(func=cmd_compat)` wiring it (`4818176`), and
`git show ed87507:packaging/homebrew/devteam-app.rb` carries `depends_on formula: "devteam"`
(`06fd509`) — all three of those commits ancestors of `ed87507`. Calling them "stale" would imply the tree
moved under the document; it did not. All three are corrected **in ADR-0011 itself**, as
*false-when-written*, by an amendment blockquote appended after its Risks table; its `## Decision`
body is untouched, and nothing in that table's original rows is rewritten.

## Decision

### 1. `store_schemas()` is the normative compatibility statement. `min_app_version` is a kill switch and nothing else.

The per-shape numbers are normative because a release version is the wrong instrument twice over: it
moves for a documentation fix, and it does not move for a schema change. A floor built on it both
over-blocks and under-blocks, and neither failure is visible from the number. The five shape numbers
are read from the modules that own them (`compat.store_schemas()`), so they move exactly when the
shape they describe moves, and they are independently versioned — a `project.json` bump and a
credentials-schema bump are unrelated events, which is why ADR-0011 already rejected collapsing them
into one number.

`min_app_version` is kept, with a stated and narrow purpose: **a kill switch for the case the shape
numbers cannot express** — a released app version known to write this store wrongly for a reason that
is a bug rather than a shape change. It is not deprecated, because ADR-0011's amendment records the
reason it exists before the first app: an app that has to handle the key being absent will handle it
by guessing.

Three consequences follow, and they are the decision:

- **`may_write` is computed from `unsupported_by()` and never from `min_app_version`.** That is what
  `cmd_compat()` does today, and it is now a rule rather than an implementation detail. The same
  holds for the write gate, which delegates the comparison to the same function.
- **Bumping `MIN_APP_VERSION` is not a way to answer a compatibility question.** A contributor facing
  a shape change bumps the owning module's schema number. Reaching for `MIN_APP_VERSION` instead is
  the mistake ADR-0011's fourth risk row predicts, and it is now wrong by decision, not by omission.
- **`minFrameworkVersion` on the app side is advisory.** No framework code reads it and none is
  planned. An app may state it for its own users' benefit; the framework neither requires nor honours
  it.

### 2. Deprecation policy for `json_contract`

`json_contract` is a single integer, bumped by whole numbers. One value is live at a time.

**What obliges a bump:**

- Removing or renaming a key — top-level or inside a record — in any `--json` payload.
- Changing an existing key's type, or making a non-nullable value nullable.
- Changing the meaning of a key without changing its name.
- Changing which exit code an existing outcome uses, or what an exit code means.
- Moving a key between the envelope (`ok`, `error`, `exit_code`) and the command's payload.

**When the policy starts binding, and the one carve-out on the exit-code clause.** Two qualifications,
both added after the exit-code clause above was read literally against a real change and found to catch
something it was not written for.

- **The policy binds from the first release that ships the CLI. That release has not happened.**
  `scripts/cli/devteam` does not exist at `v2.48.0`, the latest tag; every entry describing it sits under
  `## [Unreleased]` in `CHANGELOG.md`. So `json_contract: 1` has never been published to any client,
  there is no previous value to distinguish a bump from, and a shape or exit-code correction made before
  that release is a correction rather than a break. It is still written into the changelog — that is the
  record the first release is cut from — but it moves no number. Saying so explicitly is cheaper than the
  alternative, which is a contributor bumping the contract twice before anyone can observe either value.
- **Correcting an exit code that was a defect is not "changing which exit code an existing outcome
  uses".** The clause exists to protect a *decided* outcome: a client branching on `$?` must not find the
  meaning moved under it. An outcome that reached the caller through a catch-all as *"unexpected
  `<ExceptionName>`"*, or that answered the wrong thing at exit 0, was never a decided outcome — it was a
  bug whose exit code was an artifact of where it escaped. Fixing it is not a contract change, and calling
  it one would make "never break the contract" an argument for keeping a crash. The obligation that does
  attach is the changelog: a corrected exit code **must** appear in the entry under `### JSON contract`,
  naming the command, the old code, the new code and why the old one was a defect, because a client with an
  exhaustive switch on `$?` still has to be told. The first instance is
  `devteam compat --client-file <not valid UTF-8 | nested too deeply for the parser>`, which moved from
  exit **3** to exit **2** — `json.loads` raises `RecursionError` and `Path.read_text` raises
  `UnicodeDecodeError`, neither an `OSError` nor a `JSONDecodeError`, so both escaped to `cli.main`'s
  catch-all and were reported as environment problems. A malformed declaration is a malformed question.
  **A code moved for any other reason is the clause's subject and obliges the bump. This carve-out is not
  a general licence to re-tune exit codes, and "it was arguably wrong before" is not the test — the test is
  whether the old behaviour was a crash or a wrong answer.**

**What does not oblige a bump:**

- **Adding** a key, a record field, a command, a subcommand or a flag. Clients must ignore keys they
  do not know; additive change is why a well-designed contract version moves rarely.
- Any change to human-mode output.
- The wording of an `error` or `hint` string. A client branches on `exit_code`, never on message text.
- **An error envelope's conditional `hint` starting to appear on a path that did not previously set it.**
  `hint` is optional by construction — `errors.DevteamError.payload()` emits it only when the exception
  carries one — so its presence already varies between two errors of the *same* command, and no client can
  pin it as a fixed key. This is the "adding a key" bullet above applied to the envelope, and it is written
  out because the first instance of it was nearly treated as a key-set change: `devteam compat --client
  '[]'` used to re-wrap a `TypeError` with no hint and now carries one, which
  `tests/test_client_gate.py::CompatErrorDocumentsAreADecidedShapeTest` records as a decision with its
  reasoning. Removing a `hint` from a path that had one is likewise free; *making the envelope's `hint`
  unconditional, or moving it into a command's payload*, is the change that is not.
- Adding a member to an enumerated value set (a new credential `source`, a new `doctor` finding kind).
  This does not bump the contract, but it **must** appear in the changelog entry, because a client
  with an exhaustive switch falls through on a value it has never seen.

**Are two values ever honoured at once? No — and the overlap lives elsewhere.** Emitting two shapes
selected by a caller declaration means two code paths per command, maintained for zero clients, and
the second path is the one nobody exercises. What a client actually needs is not two shapes but *time
to notice*, and that is bought without a second emitter:

- **A key that is going away is marked before it is removed.** It stays present and populated, and
  the payload that carries it also carries a `deprecated` list naming the keys that will be removed
  at the next bump. The key appears **only in payloads that have something deprecated**, so the
  normal case is unchanged and starting a deprecation is a deliberate, reviewed edit — one that trips
  `AppFacingKeySetContractTest` on purpose, in both directions, when the window opens and when it
  closes.
- **Removal happens no sooner than the release after the one that shipped the marker.** One full
  release, minimum. The commit that removes the keys is the commit that empties the marker and bumps
  `json_contract`.
- **A client discovers the departure from the payload it is already reading.** That is the only
  channel that reaches a running client at the moment it reads the shape; a changelog does not.

**What a contributor does in the same commit as an output-shape change:**

1. Update `AppFacingKeySetContractTest.EXPECTED` by reading the added/removed diff the failure prints
   (`tests/test_json_contract.py:566-588` says why: never by copying the new set in).
2. If the change is in the "obliges a bump" list: bump `compat.JSON_CONTRACT_VERSION` and update the
   literal `"json_contract": 1` in `CLAUDE-md/cli.md` § *Compatibility block in `version`*.
3. Add a changelog entry under the fixed heading **`### JSON contract`** stating: the contract version
   before and after, the commands affected, the keys added / removed / renamed / retyped, and whether
   a deprecation window opens or closes.
4. If the change removes a key, the previous release must already have shipped the `deprecated`
   marker for it. If it did not, this commit ships the marker and the removal waits a release.
5. Mark the commit subject with `!` or add a `BREAKING CHANGE:` footer. `scripts/validate-commit-msg.sh`
   accepts both: the `!` is part of `PATTERN` on **line 4**; the footer is never required, and lines
   **39-46** only reject a `BREAKING CHANGE` footer written *without* its colon.

**Enforceable today, by a named gate:**

| Obligation | Gate |
|---|---|
| Step 1 — a dropped, renamed or added key in any of the 16 pinned app-facing payloads or 5 pinned record shapes fails the build | `tests/test_json_contract.py::AppFacingKeySetContractTest`, run by the CI job **`python` — "Python … (devteam CLI)"** via `.github/scripts/ci/03-python.sh:25` (`python3 -m unittest discover -s tests -t tests`) |
| The envelope — exit code in `{0,1,2,3,4}`, stdout **empty or exactly one** parseable document (ADR-0011's own phrasing; the sweep accepts empty stdout), `ok` agreeing with the exit code, `error` + `exit_code` on 2/3/4, stderr never JSON, human mode never JSON — across every invocable leaf the parser walk discovers **except the two in `SKIP_INVOCATION`**: `update` (reaches the network) and `uninstall` (removes the store the rest of the sweep needs) are discovered and asserted to still be discoverable, but never invoked. ADR-0011's M4.1 amendment names that exclusion, so omitting it here would lose precision the amended document already had | the same file's generic sweep, the same CI job |
| The `compat` block cannot drift from `compat.describe()` | `tests/test_json_contract.py:552-562`, the same CI job |

**Convention only — nothing fails if it is skipped:**

- **The bump itself.** `tests/test_json_contract.py:561` compares the payload against
  `compat.JSON_CONTRACT_VERSION`, so bumping — or failing to bump — passes either way. This is
  deliberate: a test pinning the literal `1` would have to be edited on every legitimate bump, which
  teaches contributors to edit it reflexively and destroys the signal.
- The `CLAUDE-md/cli.md` `"json_contract": 1` literal staying in step with the constant.
- The changelog heading and its contents. CI has six jobs — `tag-name`, `lint`, `python`,
  `provider-contracts`, `slim-bootstrap`, `packaging` — and none reads `CHANGELOG.md`.
- The `deprecated` marker's lifecycle and the one-release window.
- Step 5. `scripts/validate-commit-msg.sh` is not registered as a git hook by `scripts/install.sh`, and
  no CI job runs it. Its two callers are both authoring-flow documents: `commands/commit.md:145-146`
  runs it, and `skills/shared/conventional-commits/SKILL.md:119-126` presents the same invocation.
- The field shapes of every command **not** in `EXPECTED` — among them `sync`, `unbind`, `pin`,
  `prefs get/set/unset`, `cred set/unset/import`, `store install/use/gc`, `migrate`, `upgrade`,
  `export`, `import`, `uninstall`. `EXPECTED` is a hand-maintained list with no assertion tying it to
  the parser walk, so a new command's payload is unpinned by default.

### 3. A caller that declares nothing is not refused, and that boundary stays open

The gate refuses a caller that **declares** shapes it cannot handle, on a mutating command. It does
not, and will not, refuse a caller that declares nothing. This is a decision, not an unfinished edge.

**What ADR-0011 rejected, and why this gate is not it.** ADR-0011's § Alternatives Considered carries a
row naming this feature almost by its flag name, and it must be read as written rather than by its
title. Its full text:

> *Have the CLI refuse writes from a client that has not declared its schemas (a `--client-schemas`
> gate)* — "Enforcement on the side that can actually enforce, and it inverts this ADR's own model: the
> client is the party that degrades, the CLI is the single implementation that must keep working for a
> human in a terminal. A flag every write needs would make the CLI hostile to its primary user to guard
> against a client that does not exist yet. Revisit when the app ships and 'which CLI does the app
> invoke' is decided — not before, because the answer determines whether the gate is needed at all."

The rejected population is *"a client that has **not** declared"*. The shipped gate refuses the
complement: a client that **has** declared, and declared itself behind. Every clause of the objection
survives intact against the narrow form:

| ADR-0011's objection | Why the narrow form escapes it |
|---|---|
| "A flag every write needs" | No write needs a flag. A caller that passes nothing is not compared, not detected, not warned and not logged — `gate()` returns before it classifies the command. |
| "hostile to its primary user" | What a human *types* is unchanged: no write needs a new argument, and `NoDeclarationIsUnchangedTest` in `tests/test_client_gate.py` asserts that the same mutating command runs, and that a read-only command answers byte-for-byte identically, whether the caller declares nothing, a compatible client or an incompatible one. Two qualifications, because "byte-identical to pre-gate behaviour" would be too strong. The `--help` output *did* change — `--client-schemas PATH` now appears in the `usage:` line and options list of **every** command (`python3 scripts/cli/devteam bind --help`), which is the price of a global flag. And no test compares against a pre-gate baseline: `NoDeclarationIsUnchangedTest` compares declaration states *within the current code*, which catches the regression that matters (the gate starting to refuse anonymous callers) but is not the same assertion. That the flag is optional and that a `--help` line is not hostility are **argued**, here; that the anonymous path still mutates is **asserted**, there. |
| "the client is the party that degrades" | Still true, and now assisted: the client decides by reading `compat`; the gate only holds a client to what it already said about itself. No read is refused **as a write**, so "degrade to read-only" remains reachable. One read-only command has a narrow exception that supports the rule rather than breaking it: on a store still at the pre-ADR-0013 paths, `devteam list` is refused at exit **3**, because the only thing that would let it answer is a write to shapes the caller declared it cannot read, and the alternative was answering `projects: []` at exit 0 — a wrong read, not a degraded one. `compat`, `version` and `path` are asserted to answer on that store, so the client can still learn why. |
| "to guard against a client that does not exist yet" | The guard is against the *honest* client of ADR-0011's own second risk row — one installed or bundled independently of the CLI, which knows its schema numbers and states them. That client is not hypothetical the moment any client ships. |
| "Revisit when the app ships and 'which CLI does the app invoke' is decided — **not before, because the answer determines whether the gate is needed at all**" | **Not met, in either half. The gate was built anyway, and that is a deviation from a stated reason rather than a schedule slipped.** The app has not shipped. And `depends_on formula: "devteam"` does not decide which binary the app invokes — it guarantees the formula is *installed*; the cask's own comment calls that making the question "answerable", not answered. That line also predates this condition (`06fd509`, an ancestor of `ed87507`) and nothing in this change touched `packaging/`, so it is not progress this work can claim. The defensible motive is the one ADR-0011 already uses for its own sequencing: retrofitting a refusal path around a released client means changing behaviour that client already depends on, so the refusal is cheaper to build before the client than after. That argument answers "why not wait"; it does not convert the condition into met. |

So this is a **narrowing**, not a reversal, and ADR-0011 records it as one in an amendment appended
after its Risks table. Had the gate refused undeclared callers, it would have contradicted that row
outright; that is precisely the version this ADR declines.

Read in `scripts/lib/devteam/compat.py`: `gate(command_path, declaration)` returns an empty mapping
immediately when `declaration is None`, before it classifies the command at all; a declaration is
resolved by `client_declaration()` from `--client-schemas` or `DEVTEAM_CLIENT_SCHEMAS`, and is `None`
when neither is present. So an undeclared invocation does not reach the comparison. Two further
properties support the boundary rather than weakening it: `is_mutating()` treats an **unclassified**
command as mutating, so an omission from the tables cannot open a hole for a declared client; and
`READ_ONLY` keeps `compat` itself ungated, because a client that has fallen behind must still be able
to ask how far. The relocation suppression is scoped the same way: it keys on `unsupported` being
non-empty, not on a declaration being present, so an anonymous caller and a compatible client are both
outside it and no store is stranded by a client that asked one read-only question. `tests/test_client_gate.py` asserts the boundary in both directions, on the same
command in the same store — refused when declared and behind, performed when nothing is declared —
because it is the property most easily broken in silence.

Why the boundary is where it is:

- **The CLI's primary user is a human at a terminal.** `bind`, `sync`, `prefs set` and `cred set`
  must keep working with no extra flag. ADR-0011 rejected a mandatory declaration for exactly this
  reason (§ Alternatives Considered, the `--client-schemas` gate row) and that rejection is ratified
  here, now that a gate exists to ratify it against.
- **Identification is not authentication.** A flag or environment variable is set by any process that
  wants to, including a buggy client that sets it wrongly. A mandatory declaration buys the
  appearance of enforcement, and the appearance is worse than the absence because it invites relying
  on it.
- **There is nothing to check.** An anonymous invocation is byte-for-byte a human invocation. No
  property of the calling process is both visible to the CLI and unforgeable by a client.

**What this leaves open, stated plainly:** the gate adds a refusal path that only a declaration can
trigger. A caller that declares nothing is therefore affected by it in no way and retains the entire
pre-gate write surface — every mutating command, at the store's current shapes, exactly as a human
has. The protection is against the *honest* old client: one installed or bundled independently of the
CLI (ADR-0011's second risk row) that knows its own schema numbers and states them. That is the case
that actually occurs, and it is the case the gate closes.

**Reopening condition.** Revisit only when both hold: a shipped client is observed writing while
declaring nothing, **and** a mechanism exists that a human's terminal use does not pay for. Neither
is true today, and "make the flag mandatory" satisfies the second only by ignoring the first bullet
above.

## Consequences

### Positive
- One mechanism answers "may this client write?", and it is the one with content. A contributor facing
  a shape change has exactly one place to change a number: the module that owns the shape.
- The first `json_contract` bump has a procedure to follow instead of a precedent to invent. The
  expensive part of ADR-0011's first risk — deciding under release pressure — is paid now.
- Additive change is explicitly free. A new key, command or flag needs no version negotiation, which
  keeps the contract version meaningful when it does move.
- The anonymous-caller boundary is recorded as decided, so it cannot be re-litigated as a bug, and a
  future summary cannot report it as an oversight.

### Negative
- Most of the deprecation policy is convention. Four of its five contributor steps have no gate, and
  the one that does covers 16 commands out of the parser's full surface.
- The `deprecated` marker is specified and not built. The first deprecation implements it.
- `min_app_version` survives with a purpose narrow enough that it may never be used, and an unused
  field invites being repurposed by the next person who reads it as a general version floor.
- A client can still write to a store it does not understand by saying nothing, and no framework code
  prevents it. That is the accepted cost of item 3.

### Neutral
- Nothing about ADR-0011's channels, signing or packaging is touched. This ADR is about the contract
  and the gate only.
- `json_contract` stays at `1`. No payload key is added, removed, renamed or retyped here. One exit code
  **is** corrected — `devteam compat --client-file <not UTF-8 | too deeply nested>` from 3 to 2 — and § 2's
  carve-out plus the fact that no release has ever shipped the CLI are why that does not move the number.
  Both reasons are recorded there rather than left to the next reader to reconstruct.

## Risks

Every row is a condition in the shipped code or in the shipped absence of code.

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **`json_contract` can be bumped, or left unbumped, with nothing failing.** `tests/test_json_contract.py:561` asserts the payload equals `compat.JSON_CONTRACT_VERSION`, so the test passes whatever that constant says. The policy's central obligation is the one thing no gate checks. | `AppFacingKeySetContractTest` makes the *shape* change loud for the 16 app-facing payloads, so a contributor making a breaking change is already stopped, already reading the diff, and already in the commit where step 2 applies. The steps are listed in one place, in this ADR, in the order they are performed. | Convention. A shape change to an unpinned command — `sync`, `prefs set`, `cred import` and the rest — changes nothing in CI and need not touch the contract number at all. The most likely silent breach is a payload nobody pinned. |
| **`EXPECTED` has no completeness assertion.** It is a hand-written list of 16 command labels and 5 record shapes (`tests/test_json_contract.py:594`), with one test method each; the parser walk discovers a far larger leaf set and the two are not tied together. A newly added app-facing command is unpinned unless somebody remembers to add it — and remembering is what the sweep was built to stop relying on. | The generic sweep still pins the envelope for every discovered leaf, so a new command cannot emit a malformed document; the class docstring requires each set to be written out in full so an edit is conscious and reviewable. | The gap is exactly the one the sweep's own design rejected for the command list: "a list omits precisely the command nobody remembered to add". A completeness assertion against the parser walk is mechanical and is not built. Named here rather than decided, because which payloads the app reads is a coverage question, not an architectural one. |
| **The `deprecated` marker does not exist in any payload.** Nothing emits it, nothing reads it, and no test mentions it. The policy's only channel to a running client is, today, a paragraph. | There is nothing to deprecate: `JSON_CONTRACT_VERSION` is `1`, no key has been removed, and no client exists. The first use of the policy is also the first implementation of the marker, and the design question — one shape at a time, marker plus a one-release window — is settled before that commit is written. | The first deprecation pays for the mechanism under whatever pressure produced the shape change. This ADR removes the design decision from that moment, not the work. |
| **`min_app_version` is published, reads as authoritative, and is consulted by nothing.** Its comment in `compat.py` describes it as a write-safety floor; `describe()` publishes it beside the normative numbers; `cmd_compat()` computes `may_write` without it, and `gate()` delegates to `unsupported_by()` only. A bumped value would appear in `version --json` and in `devteam compat` and change no behaviour. | All three fields come from one function on one call, so a client reading the block sees `may_write`'s inputs and this field together; this ADR states it is non-normative and names its single purpose. | A published number that a careful client might honour, disagreeing with `may_write` and degrading when the store would have accepted it. Nothing in the code marks the field as advisory — only this ADR does. |
| **The mutating / read-only classification is a hand-maintained table.** The gate decides from `MUTATING` and `READ_ONLY` in `compat.py`, keyed by parser path tuples. Whether a command writes is a judgment in several entries — `doctor` is listed as mutating because it repairs, `store gc` because of what `--apply` can do, `cred get` as read-only despite appending an audit line. | `is_mutating()` fails closed: `classify()` returns `None` for a command in neither table and `is_mutating()` reads anything that is not explicitly read-only as mutating, so the likeliest error — forgetting a new command — cannot open a hole. `tests/test_client_gate.py::ClassificationCompletenessTest` walks the real parser and fails on an unclassified leaf, a leaf in both tables, and an entry naming a command that no longer exists, so the table cannot fall behind the surface or keep a corpse. Each entry carries its reason in the table, so a reclassification has to argue with a recorded one. | Failing closed protects one direction only. A command wrongly placed in `READ_ONLY` is invisible to that default, and no mechanism re-derives the judgment — the reasons in the table are prose, checked by review. |
| **`NEEDS_MACHINE_LAYOUT` is measured against one fabricated layout, and the layout it describes is the one being retired.** The suppression of `store.adopt_machine_layout()` for an incompatible client means a read-only command answers against whatever shape is on disk, and `compat.NEEDS_MACHINE_LAYOUT` names the commands that must be refused instead. Its single entry, `list`, was established by running every read-only leaf on both layouts and comparing — but the pre-split store is *fabricated* by de-splitting a bound store, and no fixture exists for a layout nobody has invented yet. | `tests/test_client_gate.py::PreSplitStoreTest` asserts the refused set **equal** to the table, not merely contained in it, so a command that starts reading a machine-local record fails rather than quietly answering wrong; the de-split fixture is built from what a real `bind` wrote, including the project's own `state-dir`/`memory-dir` pointers, so a difference it reports is the layout and nothing else; and the entry carries its reason beside it in `compat.py`. | The next layout migration must bring its own fixture, and nothing forces it to. The failure mode is the one this entry exists to name: a read-only command silently answering against a shape it cannot read, at exit 0, which is how `list` reported every bound project as unbound in the first place. |
| **`CLAUDE-md/cli.md` is on the policy's own path and hardcodes the contract version.** It carries the literal `"json_contract": 1` in § *Compatibility block in `version`*, which step 2 obliges a contributor to update and no gate checks. (Two dead ADR links found alongside this one have been fixed in the same change that added the write gate: § *The `--json` contract* linked ADR-0011 as `0011-the-devteam-cli-is-the-desktop-apps-api.md`, and § *Credentials* linked ADR-0010 as `0010-credential-references-and-the-secret-backend-cascade.md`. Neither filename has ever existed; both sections are the ones a contributor reaches for when checking a contract or credential rule.) | The literal is a documentation example next to the block it documents, so it is visible whenever that section is read at all. | Not mechanically checked. CI's `lint` job runs the repo's doc-sync check, but that pairs every `*.pt-BR.md` with its EN counterpart (`.github/scripts/ci/02-readme-sync.sh`); the repo's resolving scans cover skill and template references (`helpers/orphan-skill-scan.sh`, `helpers/orphan-template-scan.sh`), not ADR links, so the next dead ADR reference in `CLAUDE-md/` will be just as invisible to CI as that one was. |
| **Step 5 has no gate on this repository's own commits.** `scripts/validate-commit-msg.sh` accepts `!` through `PATTERN` (`:4`) and never requires a `BREAKING CHANGE:` footer (`:39-46` only reject one written without its colon), but `scripts/install.sh` registers no `commit-msg` hook and no CI job invokes the script. Both of its callers are authoring-flow documents: `commands/commit.md:145-146` and `skills/shared/conventional-commits/SKILL.md:119-126`. | The commit rule in `CLAUDE.md` requires loading the conventional-commits skill before writing any message — and that skill is one of the two places the invocation is written down, so the mitigation and the second caller are the same fact rather than two. The marker belongs to the authoring flow, not to the build. | A breaking output-shape change can be committed with a `fix:` subject and no footer, and nothing objects. The mitigation holds only for an author who loaded the skill; nothing checks that they did. A reader scanning history for contract breaks will miss it. |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep `min_app_version` and `store_schemas()` as co-equal, and document which wins | Documenting a precedence leaves two declarations in the payload and removes only the excuse for bumping the wrong one. ADR-0011's fourth risk row is about a contributor's belief, and a sentence in a document does not reach the contributor who never read it — a rule that `may_write` ignores the field does, because it is what the code already does. |
| Delete `min_app_version` outright | Tidier, and it re-opens a question ADR-0011 already answered: the field exists before the first app precisely so the first app can rely on reading it, and an app that must handle an absent key will handle it by guessing. The kill-switch case is also real and inexpressible in shape numbers — a released app that writes wrongly because of a bug, with no shape change to hang a refusal on. |
| Make `json_contract` a semver string | Three components invite encoding "additive" in the minor, which is the change that must not move the version at all. A single integer makes "did the contract break?" a comparison, not a parse, and the policy's value is precisely that additive changes leave it alone. |
| Honour two contract versions at once, selecting on a caller declaration | Two emitters per command, maintained for zero clients, and the second is the one nobody exercises. What a client needs is time to notice, not a second shape — which the `deprecated` marker plus a one-release window supplies with one code path. |
| Announce deprecations only through `devteam compat` or `CHANGELOG.md`, with no per-payload marker | Both are checked by a developer, once, at a moment they choose. The client that breaks is the one running against a store it did not expect, and the only place it is certain to look is the payload it already parses. The marker rides along there at no extra call. |
| Pin every command's field set now, or assert `EXPECTED` covers the parser walk | The right coverage answer and not a decision this ADR is for: which payloads the app reads is mechanical, and writing it while the gate was landing in the same test tree would collide. Recorded as the second risk row so it stays visible instead of being absorbed by an ADR that claims to have closed it. |
| Require every caller to declare its schemas before any mutating command | Already rejected by ADR-0011 (§ Alternatives Considered, the `--client-schemas` gate row) for the reason that it makes the CLI hostile to its primary user to guard against a client that does not exist. Ratified here, with the reason ADR-0011 did not give: identification is not authentication, so the mandatory flag would not guard against the client it targets — only against a well-behaved one. |
| Refuse an anonymous caller by detecting it (TTY check, parent process, environment heuristics) | Every signal is forgeable by the client and wrong about the human. A CI job, a `make` target and a shell script all run without a TTY; a client can spawn under any parent and set any environment. The check would block legitimate scripted use — which ADR-0011's own "the CLI is scriptable for users and for CI" consequence depends on — while a client that omits the declaration passes by accident and one that lies passes on purpose. |
