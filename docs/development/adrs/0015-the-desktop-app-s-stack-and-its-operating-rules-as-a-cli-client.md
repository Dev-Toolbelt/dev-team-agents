# ADR-0015: The desktop app's stack and its operating rules as a CLI client

**Date:** 2026-09-28
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

[ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) decides that the
desktop app is a **pure client of the CLI** and names Electron once, in a `### Neutral` line that says
the choice was made "in D1" and that the ADR "records the distribution consequences of that choice,
not the choice itself." Nothing below that is decided anywhere: not the renderer stack, not where the
source lives, not which process may spawn a subprocess, not which `devteam` binary the app invokes, and
not what the app does when it cannot find one.

**This ADR narrows ADR-0011; it does not reverse it.** ADR-0011's Decision — two channels, the app as a
pure client, the JSON contract as public API, the app never a prerequisite — stands unchanged and is not
restated here. The compatibility mechanism is
[ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md)
and the credential split is
[ADR-0010](0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md); both are
referenced below and neither is restated.

### Why these are open, and why now

Two of them are open *by ADR-0011's own record*. Its Risks table names "which `devteam` does the app
invoke" as "the case where the check is load-bearing, and it is the case nothing currently prevents,"
and instructs: "Settle 'which CLI does the app call' before the app ships; it is a precondition for
`compat` meaning anything." ADR-0014 § 3 then decided that the framework will **not** refuse a caller
that declares nothing — so honouring the handshake is the app's obligation, and that obligation has to
be written down on the app's side or it exists nowhere.

### State of the tree while this was written

Read at the moment of writing, on branch `app/electron-client-skeleton` at `86e2f04`: **there was no
`app/` directory in this repository.** The skeleton was being written in parallel with this document.
When this ADR was committed (commit `b2bc7cc`), the `app/` directory had already existed for three
commits. The ADR's statements were held as decisions the implementation would be bound to at the time
of writing; the existence of code since then is a verification, not a revision. `packaging/homebrew/devteam-app.rb`
states its own corresponding absence in the header ("there is no `app/` directory, no build pipeline,
and no signed artifact"), which is now false in the same way: the app exists in source and is tested,
and nothing about it ships (the cask remains unsigned).

## Decision

### 1. Electron, and the cost of it is the bundle

The app is **Electron**. Two reasons, and the second is weaker than it looks:

- ADR-0011 names Electron, and the M4.2 packaging scaffold is shaped around what an Electron build
  produces — a signed, notarised universal `.dmg` behind a Homebrew cask, and a code-signed Windows
  installer behind winget.
- Reversing the stack would invalidate that scaffold. This is the weaker argument and is recorded as
  weak: the scaffold is unverified by its own headers, and a Tauri build also produces a `.dmg` and a
  Windows installer, so most of `devteam-app.rb` would survive a reversal. What would actually change
  is the macOS floor, the bundle id, the artifact size and the toolchain in CI — not the cask's shape.

**Tauri's advantage is real and is stated plainly, not minimised:** a Tauri bundle is roughly 5–10 MB
against Electron's 100 MB+, and its resident memory is materially lower because it uses the OS webview
instead of shipping Chromium. For an app whose entire job is to spawn a subprocess and render JSON, that
is the correct instinct.

**The cost being accepted, stated as a cost:** every user downloads and stores 100 MB+ for a window that
runs `devteam <command> --json`; the app's baseline memory is Chromium's, not the OS webview's; and the
repository takes on Chromium's CVE cadence, which means the app has a security-driven release rhythm the
framework does not have. That is an ongoing maintenance obligation, not a one-time download.

**What buys it:** ADR-0009 holds the framework at python3 and bash, deliberately, and rejected a compiled
binary because it "adds a cross-compilation matrix and a toolchain to a repository whose contributors
work in bash and markdown." Tauri would add Rust *and* that matrix to the same repository. Electron
confines the new language to TypeScript in one directory, which is the same containment ADR-0011 already
recorded ("Node enters the repository for the first time. It is confined to `app/` and to CI").

### 2. TypeScript + Vite + React in the renderer

TypeScript for the whole app, Vite as the build tool, React for the renderer.

The argument is **contributor review capacity, not output size.** A compile-time framework (Svelte,
Solid) would ship less JavaScript, and in a window this small the difference is invisible next to the
100 MB the previous section already accepted. What is not invisible is review: this is not a JS shop —
the framework is python3 and bash, and the reviewers are the same people. React is the stack a reviewer
with no history in this repository is most likely to already read, and a mis-reviewed client of a store
is a worse outcome than a larger bundle. TypeScript is non-negotiable for the same reason the CLI has a
pinned JSON contract: the payload shapes the app reads are the contract, and an untyped client discovers
a shape change at runtime, in front of a user's store.

### 3. The app source lives in `app/`, in this repository

Not a separate repository. The JSON contract's tests and its only client must move in one commit: a
payload change and the client that reads it are the same change, and ADR-0014 § 2's contributor steps
(update `AppFacingKeySetContractTest.EXPECTED`, bump `json_contract`, open or close a `deprecated`
window) are unperformable across a repository boundary in one review.

**Verified, because the claim is load-bearing:** `scripts/install.sh` → `KEEP_ROOT` is
`(agents scripts skills templates commands)`, and the loop immediately below it `rm -rf`s every
top-level entry not in that list. `app/` is therefore dropped from an installed project by the
allowlist's default behaviour — the same way `packaging/`, `tests/`, `helpers/` and `docs/` are — with
no entry to add and nothing to maintain. Living in this repository costs a user nothing.

### 4. Every CLI invocation happens in the main process

The renderer never spawns a process, never touches the filesystem, and never holds a path it resolved
itself. `contextBridge` exposes **named operations** — one function per screen action, each mapping to
one fixed command path with typed, validated arguments — and never a generic `run(command)` or
`exec(args)`.

The reason is the subprocess: this app shells out to a tool that can mutate a store. A renderer able to
ask for an arbitrary command turns `contextIsolation` into decoration — the sandbox would still hold,
and a compromised or buggy renderer would still be able to request `devteam uninstall`. Named operations
make the reachable command set a property of the main process's source, reviewable in one file, rather
than a property of whatever string the renderer assembled.

Three properties follow and are part of the decision:

- **The main process does not read the store directly either.** Not `project.json`, not `registry.json`,
  not a preferences layer — not even for a read. A file read is a second implementation of the
  resolution rules ADR-0011 exists to keep singular, and it is the form the drift would actually take,
  because reading looks harmless. Reads go through `devteam <command> --json`.
- **Spawn with an argv array, never a shell string.** No `shell: true`. Project paths, branch names and
  credential keys are user data, and a shell string makes them injection surface.
- **`nodeIntegration` off, `contextIsolation` on, `sandbox` on** in every renderer, with no remote
  content loaded in an app window.

### 5. No second CLI is ever bundled

The app resolves exactly one `devteam` on the host. It never ships a copy, and it never falls back to
one.

This answers the question ADR-0011's Risks table left open, and its reasoning is that row's: with the
formula and the cask as independent installs, a bundled older CLI writing a newer store is the case
where the compat check is load-bearing and the case nothing prevented. A bundled CLI also guarantees the
divergence in the direction nobody sees — the user's terminal and the app would be two different
versions of the single source of truth, which is the outcome ADR-0011's Decision exists to forbid.

**Resolution order — a decision, not a reading.** The `app/` skeleton was being written in parallel and
did not exist when this was written; the implementation is held to this order. The table was corrected
before the ADR was committed: the variable name in row 1 is `DEVTEAM_CLI_PATH`, not `DEVTEAM_CLI` as
this text stated. `app/src/cli/resolve.ts` carries the implemented version and takes the corrected
precedence (environment variable before settings file); this ADR's own amendment does not record the
correction, and the implementation's comment claiming it does is inaccurate.

| # | Source | Why it is where it is |
|---|--------|----------------------|
| 1 | `DEVTEAM_CLI_PATH` in the environment | The narrower, more deliberate act: a developer explicitly setting this variable has decided on a path more deliberately than one editing settings. Lets a contributor point the app at a working tree without editing settings |
| 2 | An explicit path the user configured in the app | The only escape hatch for a non-standard install; a user who sets it means it |
| 3 | `devteam` on `PATH` | The normal case on both platforms: the Homebrew formula and the winget package both put it there |
| 4 | Known per-platform channel locations | Homebrew's `bin` on macOS (both Apple-silicon and Intel prefixes), winget's shim directory on Windows. A GUI app launched from Finder or the Start menu does not inherit a login shell's `PATH`, which is the ordinary way step 3 fails for a correctly installed CLI |
| 5 | — | **No step 5.** Resolution fails |

**On failure the app opens and does nothing else.** It shows which locations it tried, the install
command for the platform, and a retry. Every screen is unavailable — this is not the read-only
degradation of § 6, because there is nothing to read: the store is reachable only through the CLI, and
falling back to reading it directly is forbidden by § 4. An app that cannot find a `devteam` is an app
with no data, and saying so is the whole of its behaviour.

### 6. The app declares its schemas and calls the handshake before every write

- **The app declares on every invocation**, read-only ones included, through `--client-schemas` or
  `DEVTEAM_CLIENT_SCHEMAS`. It opts into ADR-0014's gate deliberately: the gate binds only a caller that
  identifies itself, so declaring is how the app buys the framework's refusal. Declaring on read-only
  calls too means a corrupt declaration file is reported on the app's first call rather than on its
  first write.
- **The declared schema numbers are the app's own constant, compiled into its source.** The app never
  derives them from the store, from `devteam version --json`, or from a `compat` response. Copying the
  store's numbers into the declaration and sending them back makes the comparison compare a value with
  itself, which passes always — a vacuous check that reports success. The declaration is a statement
  about the app's code, and only the app's code may be its source.
- **On an unsupported shape the app degrades to read-only and says so in plain language** — which shapes
  it does not understand and what to do about it, not an error code. ADR-0011 already requires this; the
  mechanism, the exit codes and the `may_write` computation are ADR-0014 and `CLAUDE-md/cli.md` §
  *The client write gate*, and are not restated here.

### 7. The app never calls `devteam cred get`

It renders credential **references** only, from `devteam cred list --json`. A value never enters the
app's process. ADR-0010 is why: a value must not leave the OS secret store, and `cred get` deliberately
refuses `--json` so a secret cannot ride inside a document a caller would pipe, tee or log wholesale —
a refusal ADR-0011's amendment records as the one hardcoded exception every client needs. The app does
not need that exception for `cred get`, because it never calls it; it still needs it as a *category*,
since any future secret-handling command joins the same list.

A consequence that is part of the decision: the app's subprocess logging is **per-operation and
allow-listed**, never a generic "log every subprocess's stdout." A blanket logger is how a value would
reach a log file the day a command like `cred get` is wired by someone who did not read this section.

### 8. The first slice is read-only, and no mutating command is wired

The first app slice wires **nothing** from `compat.MUTATING`. Not `bind`, not `prefs set`, not
`cred set`. It reads: `devteam version`, `path`, `compat`, `list`, `catalog`, `prefs get`,
`cred list`, `doctor`.

This is a sequencing decision, not a scope cut:

- It proves the whole architecture — resolution, spawn, the JSON envelope, the declaration seam, the
  typed IPC surface, rendering — while **no screen in the app is capable of damaging a store.** The
  worst first-slice bug is a wrong display.
- The write path depends on the handshake, and the handshake is unexercised by any client: ADR-0014's
  gate is asserted by `tests/test_client_gate.py` against fabricated declarations, never against a real
  one. Wiring a write before a real client has driven the declaration seam means discovering the seam's
  defects with a user's store as the test fixture.
- `devteam doctor` is in the read slice although `compat.MUTATING` classifies it as mutating (it
  repairs). It is invoked **without** its repair flag; the classification is the command's, not the
  invocation's, and the app treats the whole command as out of the first slice for writing purposes.

> **Amended by implementation (M4.3, first slice) — § 8's title claim is wrong and is corrected here:
> the first slice is not read-only. It wires exactly one command from `compat.MUTATING`, `devteam
> doctor`, and the Diagnosis screen stays.**
>
> The tree this ADR was written ahead of now exists. `app/` holds the Electron client — TypeScript,
> Vite, React, shadcn/ui, Tailwind v4 — with the invocation layer in `app/src/cli/`, the main process
> in `app/src/main/`, 133 passing tests plus 1 skipped under `app/test/`, and a CI gate at
> `.github/scripts/ci/05-app.sh` (the `app` job in `ci.yml`: preflight, node pin from `app/.nvmrc`,
> `npm ci`, `typecheck`, `lint`, non-vacuous tests). That gate closes the residual of this ADR's
> second Risks row, which said "the gate is not built"; the row is left as written, because it was
> true when written and its reasoning is why the gate exists.
>
> **What § 8 got wrong, and what was decided instead.** § 8 is titled "The first slice is read-only,
> and no mutating command is wired" and then, in its own last bullet, puts `devteam doctor` in the
> read slice while conceding that `compat.MUTATING` classifies it. Both cannot be true. The
> implementation flagged it rather than filing `doctor` quietly under read-only, and the decision
> taken — recorded here, not made here — is to **keep the Diagnosis screen and fix the claim**:
>
> - `doctor` repairs what it finds. `compat.MUTATING` says so in the table itself: it "rewrites the
>   directory pointers, relocates a moved registry entry, and reassigns identity with
>   `--reassign-identity`. Read the actions it returns, not the word 'diagnose', before reclassifying
>   this one." The app does not reclassify it. `app/src/cli/operations.ts` carries it in a separate
>   `GATED_COMMANDS` constant — deliberately not in `READ_ONLY_COMMANDS` — and
>   `app/test/operations.test.ts` asserts both memberships against the framework's own tables, so a
>   later edit cannot move it by accident.
> - **What protects the store is the declaration plus the framework's gate, not the absence of a
>   mutating command.** The app declares its schemas on the invocations that can be gated, so
>   ADR-0014's gate refuses `doctor` at **exit 4** whenever the store is ahead of the app, before
>   anything on disk changes; `app/test/real-cli.test.ts` drives that refusal against the real CLI.
>   `--reassign-identity` is never passed, and a source-level test asserts the string appears in no
>   argument vector. Dropping the most useful screen in the slice to satisfy a label would have been
>   the worse trade, and it would have bought a safety property the label was never the source of.
> - **The distinction this turns on, stated once:** the classification belongs to the **command**, not
>   to the **invocation**. `doctor` without its repair flag is still a mutating command, because what
>   the gate and the classification tables reason about is what the command may do, not what one
>   argument vector happens to ask for. § 8's last bullet states that principle correctly and then
>   files the command in the read slice anyway — which is the step the section title generalises into
>   "read-only", and the step corrected here. Nothing about the invocation changes: the flag was never
>   passed before and is not passed now.
> - Two downstream restatements of the same claim inherit the correction: § 8's "wires **nothing** from
>   `compat.MUTATING`", and § Consequences → Positive's "the first slice cannot corrupt a store". Read
>   both as: the first slice exposes no write action, and the one mutating command it runs is held by
>   the declaration and the framework's gate rather than by its absence.
> - The app therefore says **"no write actions"**, not "read-only": `app/src/main/build-info.ts`
>   exports `NO_WRITE_ACTIONS` with `doctor` named in its docstring, the IPC layer reports the gated
>   command list to the renderer (`mutatingCommandsRun`), and the UI header carries a
>   `no write actions` badge beside an `unsigned build` badge. No screen exposes a write action; one
>   command the app runs can nevertheless change the store, and the app says which.
>
> **Two smaller divergences between this ADR and the shipped slice, recorded so the next reader is not
> misled by the older text.** Neither is a reversal and neither changes a decision:
>
> - § 8 lists `path`, `prefs get` and `cred list` in the read slice. The first slice wires none of
>   them: `ALLOWED_COMMANDS` is `version`, `compat`, `list`, `catalog` (bare and its three kinds),
>   `catalog show` and `doctor`. The slice is **narrower** than § 8 describes, which is the safe
>   direction; § 7's rule stands untouched and is now asserted — no allowed command begins with
>   `cred`, so `cred get` cannot be reached even by a typo.
>
> **And one place where § 6's "declares on every invocation" is literally narrower than it reads.**
> Every *operation* — every call behind a screen — carries `--client-schemas`, because the main
> process attaches the declaration file in one place (`app/src/main/ipc.ts` → `context()`), so no
> operation can forget it and the gate binds all of them. Two calls do not carry the file: the
> resolution probe (`devteam version`) and the handshake (`devteam compat --client <inline>`). Both
> are in `compat.READ_ONLY` and ungated by construction; the handshake declares the same constant
> inline, which is stronger for that call, since an inline declaration cannot be a stale file. The
> substance of § 6 holds — nothing that can be gated runs undeclared — but "every invocation" is not
> what the code does, and an audit that greps for the flag should know which two calls it will not
> find it on.

## Consequences

### Positive
- One `devteam` per machine, chosen by a stated order, so the terminal and the app cannot be two
  versions of the single source of truth.
- The reachable command set is a reviewable list in the main process, not an emergent property of
  renderer strings.
- The first slice cannot corrupt a store, so the architecture is provable before the risky part exists.
- `app/` in this repository means a payload change and its client move in one commit, under one review,
  with ADR-0014 § 2's steps performable.
- The user pays nothing for `app/` living here: `KEEP_ROOT` already excludes it.

### Negative
- 100 MB+ per user and Chromium's memory baseline, for a window that renders JSON.
- Chromium's CVE cadence becomes a release obligation for this repository.
- Node, npm and a lockfile enter a repository whose CI has no JavaScript job today.
- The resolution order is five branches of platform-specific path logic — exactly the class of code
  ADR-0009 moved into python3 to stop writing twice, now written a third time in TypeScript. It is
  confined to finding one executable and resolves no store path.
- The read-only first slice means the app ships without the actions most users will want first.

### Neutral
- ADR-0011's channels, signing and packaging are untouched. This ADR decides the stack and the client's
  rules only.
- The IPC surface is internal: it is not the `--json` contract, and changing it obliges nothing under
  ADR-0014 § 2.

## Risks

Every row is a condition in the shipped code or in the shipped absence of code.

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **Any build produced now is unsigned, and the cask cannot describe it.** There is no Apple Developer ID and no Authenticode certificate — `packaging/README.md` § Prerequisites lists both as account-level access the repository owner holds and this environment does not; `packaging/homebrew/devteam-app.rb` carries `sha256 "NO_RELEASE_SHA256_DOES_NOT_EXIST_YET"` and a `depends_on macos:` floor its own comment calls "a guess, not a measured value". | The placeholders cannot be mistaken for real values, and `brew audit --cask` would reject the cask on sight rather than install an unsigned artifact. The cask's macOS floor and bundle id are marked as to-be-confirmed from the app's `Info.plist`. | An unsigned Electron app is Gatekeeper-blocked on macOS and SmartScreen-warned on Windows, and the workaround a user finds on their own is to bypass both. Nothing in this ADR or in `packaging/` prevents an unsigned build being handed to someone. `brew style` on the cask already reports four unfixed cask-cop findings. |
| **An Electron dependency tree lands in a repository with no JavaScript gate.** CI's jobs are `tag-name`, `lint` (shellcheck over `scripts` and `helpers`), `python`, `provider-contracts`, `slim-bootstrap` and `packaging`. No `package.json` exists anywhere in the tree today, nothing in `.github/workflows/ci.yml` or `.github/scripts/ci/` mentions node or npm, and the repository's one existing TypeScript file — `opencode/plugin/dev-team-agents.ts` — ships as source with no build, type-check or lint step. ADR-0009 records the precedent: "CI had **no python gate at all**" when python became load-bearing, which is why that ADR added one in the same change. | ADR-0011 confines Node to `app/` and CI, and `KEEP_ROOT` keeps `app/` out of every installed project, so a dependency defect cannot reach a user through the framework's own channel. | The gate is not built. Until a JS job exists, `app/`'s transitive dependencies are unlinted, untested and unaudited in CI, and the first thing to notice a bad one will be a user's machine. The mitigation bounds the blast radius; it does not detect anything. |
| **The app and the CLI are installed through independent channels, and only one channel connects them.** `devteam-app.rb` carries `depends_on formula: "devteam"`, which its own comment describes as making the question "answerable", not answered. winget has no cask-style dependency anywhere under `packaging/winget/` — the word appears once, in a comment — and the three manifests there are for the **CLI** (`DevToolbelt.Devteam`); ADR-0011's channel table promises winget for the app too, and no manifest for it exists. ADR-0011's Risks table also records that the Windows CLI has no decided packaging shape at all (`InstallerType: exe` is "a placeholder, not a decision"). | The resolution order in § 5 is the app's own answer and does not depend on a packager expressing it; step 4 covers a GUI launch that inherits no login-shell `PATH`, and failure is loud and total rather than a silent fallback. | On Windows the resolution order is the *only* thing standing between the app and no CLI, and it is unexercised because neither package exists. A user can also remove or unlink the formula while the app stays installed, at which point a working app becomes the failure screen of § 5 — correct behaviour, and indistinguishable to the user from the app being broken. |
| **A renderer bug cannot corrupt a store, but can misreport one — and the first slice is nothing but reporting.** § 4 puts every invocation in the main process and § 8 wires no mutating command, so the renderer has no write path at all. What it does have is the only path: the user's belief about their projects. | The JSON envelope is pinned for every command by `tests/test_json_contract.py`, and 16 app-facing payloads' key sets by its `AppFacingKeySetContractTest`, so a payload the renderer misreads is at least a payload with a known shape. TypeScript makes a shape change a compile error rather than a blank field. | Nothing compares what a screen renders against what the CLI answered. A misrendered `list` — a bound project shown unbound, a pin shown as the active version — leads a user to a destructive action they take *in the terminal*, where no gate applies. This is the first slice's whole risk surface, and it is unmitigated by anything mechanical. |
| **Nothing on the framework side compels the app to declare or to run the handshake.** ADR-0014 § 3 decided that boundary: the gate binds only a caller that identifies itself, and a caller that declares nothing keeps the entire pre-gate write surface. § 6 is therefore a rule about the app's source, enforced by review. | ADR-0014 § 3 records the reasoning and the reopening condition; declaring on *every* invocation, including read-only ones, means a build that has lost its declaration is detectable from the CLI's own behaviour rather than only from the app's source. | An app build that drops the flag — a refactor, a packaging step that loses an environment variable, a debug branch — silently regains full write access to a store it may not understand, and looks identical from the outside. Reopening this is ADR-0014's decision, not this ADR's, and it is not reopened here. |
| **Every decision above is written ahead of the code it governs.** There was no `app/` directory when this ADR was written, on `86e2f04`. The resolution order, the declaration constant and the read-only slice are stated as decisions, and no test asserts any of them. | ADR-0011's sequencing argument applies here too: retrofitting a refusal path or a spawn rule around a released client means changing behaviour that client already depends on. Deciding first is the cheaper order, and `docs/specs/v4-app-and-distribution.md` marks M4.3 `[UNBUILT]` so nothing reads the criteria as met. | This is the exact failure mode ADR-0011's third risk row names — "the packaging reads as done because it exists" — applied to an ADR instead of a manifest. A reader who finds ADR-0015 `Accepted` may conclude the app follows it. Until `app/` exists and is reviewed against this document, it does not follow anything. |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| **Tauri** | The strongest rejected option, and the argument for it is not weak: 5–10 MB against 100 MB+, lower memory, and an app whose entire job is spawn-and-render is precisely where Electron's ecosystem advantage buys least. Rejected because it adds Rust and a cross-compilation matrix to a repository ADR-0009 deliberately holds at python3 and bash, having rejected a compiled CLI for that same reason — and because the framework's contributors and reviewers are the same people either way. The sunk-cost half of the argument (M4.2's scaffold) is recorded in § 1 as weak: a Tauri build also produces a `.dmg` and a Windows installer. |
| **A native app per platform (SwiftUI + WinUI)** | The best artifact on both platforms and two clients to keep identical — which is the drift ADR-0011 exists to prevent, reintroduced one platform at a time, in two languages neither reviewer group reads. |
| **A local web UI served by the CLI, opened in the user's browser** | No bundle at all and no second runtime. Rejected because it turns the CLI into a long-running local HTTP server with an origin any page in that browser can reach, and the thing behind it mutates a store and lists credential references. Electron's process boundary is the property being bought; a browser tab does not have it. |
| **Svelte or Solid in the renderer** | Smaller output, invisible next to the 100 MB § 1 already accepted, and fewer reviewers here can read it fluently. The constraint is review capacity, not bytes. |
| **A separate repository for the app** | Clean CI separation and an independent release cadence — and it makes a payload change and its client two reviews in two repositories, so ADR-0014 § 2's contributor steps cannot be completed in one commit. `KEEP_ROOT` already means the app costs an installed project nothing, so the separation buys nothing it does not also break. |
| **Bundle a pinned `devteam` inside the app** | Guarantees the app always has a CLI, and guarantees the user's terminal and the app are two different versions of the single source of truth. It is the exact case ADR-0011's second risk row names as "where the check is load-bearing, and the case nothing currently prevents", and ADR-0014's gate would catch it only when the bundled CLI is the *newer* party — a bundled older CLI writing a newer store is caught only because the app declares, which a bundled pairing makes look unnecessary. |
| **Fall back to reading the store directly when no `devteam` resolves** | The obvious way to make the failure screen useful, and it is the second source of truth arriving as a read. A reader needs the path resolver, the layout rules and `is_machine_local_record` — and the moment a screen renders from it, the next screen wants to write. Failing loud and total is the only fallback that cannot grow. |
| **Expose a generic `run(args)` over `contextBridge` and keep the allow-list in the renderer** | One IPC function instead of dozens, and the reachable command set moves into renderer code, where it is a property of assembled strings rather than a reviewable list. `contextIsolation` then protects a renderer that can already ask for `devteam uninstall`. |
| **Derive the declared schemas from `devteam version --json` at startup** | Removes a constant that can go stale, by comparing the store's numbers with themselves — a check that passes always and reports success. A declaration is a statement about the app's own code; any other source makes ADR-0014's gate vacuous for this client. |
| **Ship the first slice with writes, gated behind a preference** | Faster to something users want, and it puts the untested handshake in front of a real store behind a flag somebody will turn on. The flag is also a second code path in the client, which is the structure ADR-0014 § 2 rejected for the contract itself. |

---

> **Amendment — the app's `userData` must never resolve inside the store.** Found while
> fixing the review round, and recorded here rather than only in the changelog because it is
> not deducible from either side on its own. Electron derives `app.getPath('userData')` from
> `productName`, and this app's `productName` is `dev-team-agents` — the same string
> `scripts/lib/devteam/paths.py` uses as `APP_NAME` to derive the store. Both choices are
> individually correct and their collision put Chromium's profile (`Cache`, `Local Storage`,
> `Preferences`, `Trust Tokens`) inside the user's store, next to `core/` and `data/`: a second
> writer in the tree ADR-0011 makes the single source of truth. The fix is one line in
> `src/main/index.ts` — `app.setPath('userData', join(app.getPath('appData'), '<name>-app'))`
> before `whenReady` — and the constraint it encodes is the durable part: **whoever changes
> `productName`, `APP_NAME`, or either platform's store derivation must check the two do not
> resolve to the same directory.** Nothing enforces it; the same collision exists under
> `%APPDATA%` on Windows. Decision § 4's rule that the main process does not read the store
> is what made this a write rather than a read, and therefore worse.
