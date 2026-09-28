---
touches: [] # CLI/tooling change — none of backend, frontend, database or mobile is involved
depends_on: []
---

## Spec — v3 global install, project bind and version pinning (milestone M1)

### User Story
As a developer running dev-team-agents across many projects, I want one installation on my
machine that each project binds to, so that an update is applied once instead of once per
project, and so that a project can stay on a known version while others move.

### Context
Until v2 the framework was vendored into every project (325 files committed per repository) and
updated N times for N projects. ADR-0007 splits the installation into a versioned **core** and a
durable **data** store; ADR-0008 gives each project a committed identity and resolves
preferences on write; ADR-0009 makes the CLI python3. This spec covers milestone **M1** only:
store, CLI, identity, bind, versions/pin, and migration of an existing v2 install. Memory
relocation and the preference cascade arrived in M2/M2.1 and are asserted below; credentials
arrived in M3 and are specified separately in [`v3-credentials.md`](v3-credentials.md); the client
contract, the distribution channels and the desktop app are M4, specified separately in
[`v4-app-and-distribution.md`](v4-app-and-distribution.md) and only partly built.

### Acceptance Criteria

**Scenario: store paths follow the platform, and `$DEVTEAM_HOME` overrides them**
- Given `$DEVTEAM_HOME` is unset
- When the CLI resolves its directories on macOS
- Then core lives under `~/Library/Application Support/dev-team-agents/core`, data under
  `.../dev-team-agents/data`, and cache under `~/Library/Caches/dev-team-agents`
- And on Windows core and cache resolve under `%LOCALAPPDATA%` while data resolves under `%APPDATA%`
- And when `$DEVTEAM_HOME` is set, `core/`, `data/` and `cache/` resolve beneath it on every platform

**Scenario: binding a project creates no copy of the framework**
- Given a git project with no dev-team-agents install and a populated core version
- When the developer runs `devteam bind` in that project
- Then `.dev-team-agents/project.json` is created with a `schema`, a new `project_id` and
  `context_paths: ["docs"]`
- And the provider artifacts for each requested provider exist in the project
- And no copy of `agents/`, `commands/` or `skills/` exists inside the project
- And the project appears in `registry.json` with its path, providers, mode and null pin

**Scenario: a bound project can reach the framework by a project-relative path**
- Given a project bound in `link` or `copy` mode
- When any shipped command or skill resolves `.dev-team-agents/core/scripts/…` or
  `.dev-team-agents/core/templates/…`
- Then the path exists and resolves into the version that project is bound to
- And `bash .dev-team-agents/core/scripts/new-adr.sh "<title>"` creates an ADR

**Scenario: binding registers the hook dispatchers**
- Given a project being bound for a provider that uses them
- When the bind completes
- Then `.claude/settings.json` carries one entry each for `SessionStart`, `Stop`, `PreCompact`
  and `PreToolUse`, pointing through the core pointer
- And every other key in that file is unchanged
- And a second bind neither duplicates an entry nor rewrites an unrelated one
- And `unbind` removes those four entries and leaves the file and its other keys in place

**Scenario: binding is idempotent**
- Given a project already bound
- When `devteam bind` runs again with the same arguments
- Then the existing `project_id` is preserved, not regenerated
- And the registry entry is updated rather than duplicated
- And the `.gitignore` managed block contains each entry exactly once

**Scenario: bind artifacts are gitignored between managed markers**
- Given a project being bound
- When bind writes `.gitignore`
- Then every bind artifact path sits between the managed begin and end markers
- And content outside those markers is left byte-identical
- And a second bind rewrites only the block

**Scenario: a project without native symlink support falls back to copy, visibly**
- Given a platform or filesystem where creating a symlink fails
- When `devteam bind` runs
- Then the artifacts are materialised as copies
- And `registry.json` records `mode: "copy"` for that project
- And `devteam list` shows the mode, so the fallback is never silent

**Scenario: a plain re-bind does not change a pin**
- Given a project pinned to a version
- When `devteam bind` runs again with no `--pin`
- Then the pin is unchanged and the project still resolves to the pinned version
- And only `devteam pin --release` clears it

**Scenario: retiring an artifact never destroys content**
- Given a project bound in `copy` or `vendored` mode, with a file the user added inside an
  artifact directory
- When `devteam sync`, `devteam bind` or `devteam unbind` retires that directory
- Then the directory is moved into `data/quarantine/<date>/<project_id>/`
- And the user's file is readable at its quarantined location
- And a symlink artifact is simply unlinked, since `sync` recreates it

**Scenario: a path resolving outside the project is refused**
- Given a project where `.claude` or `.dev-team-agents` is a symlink pointing elsewhere
- When any command would write or remove an artifact through it
- Then the command fails with a conflict and writes nothing outside the project

**Scenario: a linked worktree is not a fork**
- Given a bound repository whose `project.json` is committed, and a linked worktree of it
- When the worktree is bound
- Then it reuses the same `project_id` and the registry still holds one entry
- And the entry lists the worktree, and `sync` refreshes both checkouts
- And unbinding the worktree leaves the shared ignore block intact for the other checkout

**Scenario: one update, every project**
- Given three bound projects, none pinned, all following `current`
- When a new version is installed into the core and `current` is moved to it
- And `devteam sync --all` runs
- Then all three projects resolve to the new version
- And each registry entry records the new sync time

**Scenario: a pinned project does not move**
- Given two bound projects, one pinned to the previous version
- When `current` moves to a new version and `devteam sync --all` runs
- Then the unpinned project resolves to the new version
- And the pinned project still resolves to its pinned version
- And `devteam list` reports the drift between them

**Scenario: releasing a pin returns the project to `current`**
- Given a pinned project
- When `devteam pin --release` runs for it and the project is synced
- Then the project resolves to `current`

**Scenario: pinned versions are never garbage-collected**
- Given a version that is neither `current` nor pinned by any project, and a second version pinned by one project
- When `devteam store gc` runs
- Then the unreferenced version is removed
- And the pinned version and `current` remain

**Scenario: a moved project is reconciled by its identity**
- Given a bound project whose directory has been moved to a new path
- When `devteam doctor` runs from the new path
- Then the registry path is updated to the new location for the same `project_id`
- And no second registry entry is created
- And the project's data directory is unchanged

**Scenario: the same identity at two paths is reported, not merged**
- Given two directories carrying the same `project_id` (a fork of the repository)
- When `devteam doctor` runs
- Then it reports the collision and names both paths
- And it does not merge, delete or silently re-point either entry

**Scenario: migrating a v2 install previews before it acts**
- Given a project with a vendored v2 install at `.dev-team-agents/` containing `agents/` and `scripts/`
- When `devteam migrate` runs without an explicit apply flag
- Then the planned actions are printed and nothing on disk changes

**Scenario: migrating a v2 install preserves memory and knowledge**
- Given the same project, and `devteam migrate --apply`
- When the migration completes
- Then `.dev-team-agents/user-data/` is still present and unmodified
- And `docs/` is untouched
- And the vendored framework directories have been **moved** into a dated quarantine under the data store, not deleted
- And the project is bound and appears in `registry.json`
- And the report states that the vendored tree was tracked by git and must be removed from the index by an explicit commit

**Scenario: every command answers machine-readably**
- Given any subcommand, including one rejected for bad arguments
- When it is invoked with `--json`
- Then stdout is a single valid JSON document and carries an `ok` field
- And `ok` is false whenever the command reports a problem, including a `warn`-level one
- And human-formatted text appears on stdout only without `--json`
- And a usage error exits 2, an environment error exits 3, and a conflict or lock failure exits 4
- And a command that ran but reported an unfixed problem exits 1 — `doctor` with any finding,
  and `sync` or `update` with any per-project failure

**Scenario: concurrent writes to the store do not interleave**
- Given two processes mutating `registry.json` at the same time
- When both complete
- Then the file is valid JSON containing both mutations
- And no partially written file is ever observable

**Scenario: a project declares which layout it is on**
- Given a project being bound for the first time
- When it has no in-project memory directory
- Then it is created on the current layout and no upgrade is offered
- And when it does have one, it is created on layout 1 and an upgrade is reported

**Scenario: nothing relocates memory except the upgrade command**
- Given a bound project on layout 1
- When `devteam bind`, `devteam sync`, `devteam update` or `devteam migrate` runs
- Then the in-project memory is untouched
- And each of them reports that an upgrade is available

**Scenario: the upgrade previews, verifies, and retires rather than deletes**
- Given a project on layout 1 with memory files, including nested ones
- When `devteam upgrade` runs without `--apply`
- Then nothing on disk changes
- And when it runs with `--apply`, every file is copied to the data store and verified by sha256
- And only then is the original directory moved to quarantine
- And `layout` becomes 2, the state pointer names the new directory, and the managed `.gitignore`
  block drops its `user-data` entries
- And a second run is refused, and a populated destination aborts before anything is copied

**Scenario: preferences resolve in three personal layers**
- Given the shipped defaults, a global layer and a project layer
- When any of them sets a key
- Then the later layer wins and `devteam prefs list` names the layer each value came from
- And a consent key that no layer sets resolves to `false`, reported as `consent-withheld`
- And the merged result is written to one file the agents read, which no agent merges

**Scenario: extra knowledge folders are read-only**
- Given `context_paths` listing a folder beyond the default write root
- When context is loaded for a task
- Then that folder is read when the task's subject matter is there, and never written to

**Scenario: the data store separates what the user authored from what this machine observed**
- Given a bound project
- Then the registry, the bind manifest and `state.json` live under `data/machines/<machine-id>/`
- And every caller that has to decide which subtree a record belongs in asks
  `paths.is_machine_local_record` / `paths.path_is_machine_local` rather than re-deriving it
- And a portable export carries no record naming an absolute path from the exporting machine: it
  excludes `machine-id`, `machines/`, `locks/` and `quarantine/`, plus any machine-local record
  matched by basename at **every** path depth
- And `data/quarantine/` is *not* asserted to be free of absolute paths — it is in the portable
  subtree and the upgrade and the relocation both retire absolute-path records into it, which is
  exactly why the default export excludes it and `--all` is the only mode that carries it
- And reading the same store as a different machine yields no registry entries and no manifest,
  while the portable preferences and memory are unchanged
- And a store written before the split is relocated once, before any command reads the registry,
  moving no content into or out of any project

**Scenario: the machine identity is re-issued when the store is opened on another host**
- Given a data store whose `machine-id` record names the host that created it
- When the same store is opened on a host with a different name — a roaming profile, a shared
  `$DEVTEAM_HOME`, a restored image or a VM clone
- Then a new id is issued and recorded with the new host, and this machine's records go under its
  own `machines/<new-id>/`
- And the previous machine's subtree is left in place, unread and unmodified
- And `devteam doctor` reports every other record set it finds as a `warn`, not as `ok`
- And `$DEVTEAM_MACHINE_ID` overrides the recorded id, and is rejected unless it is a lowercase UUID

**Scenario: `devteam path` and `devteam doctor` create nothing**
- Given a data store with no `machine-id` recorded yet
- When `devteam path` or `devteam doctor` runs
- Then no identity is minted, no machine subtree is created, and the report says the identity is
  unassigned
- And running either twice in a row reports the same store both times

**Scenario: an import does not inherit the sending machine's consent**
- Given an archive whose `preferences.json` sets `telemetry` or `auto_update`
- When it is imported
- Then those keys are stripped from the incoming layer before it is promoted
- And the cascade resolves both to `false`, reported as `consent-withheld`
- And the import result names which keys were withheld
- And every member of the archive is validated before extraction — including a symlink or hardlink
  `linkname` — on the declared python floor, not only where `filter="data"` exists

**Scenario: the relocation refreshes the pointers it invalidates**
- Given a pre-split store and a bound project on the current layout
- When the relocation moves that project's `state.json` into the machine subtree
- Then `.dev-team-agents/state-dir` and `.dev-team-agents/memory-dir` are rewritten to the machine
  and portable directories the records now live in
- And a project whose directory is gone, or whose `project.json` is unreadable, is skipped rather
  than failing the relocation
- And `devteam doctor` checks both pointers against what the layout resolves to, and rewrites a
  missing or stale one in place rather than only reporting it

**Scenario: the data store can move to another machine**
- Given a populated data store
- When it is exported and imported on another machine
- Then every project's memory and preferences are present, and the archive carries no absolute path
  from the exporting machine
- And running `devteam bind` in each project restores its registry entry and manifest under the
  receiving machine's own identity
- And `devteam export --all` instead carries this machine's registry and manifests, for a backup
  of this machine
- And an import that carries no machine subtree keeps the receiving machine's own registry
- And the import refuses to overwrite a populated store unless forced, and rejects an unsafe archive
- And `devteam uninstall` keeps the data store unless `--purge --yes` is given

### Out of Scope
- Any synchronisation mechanism — no daemon, no cloud, no conflict resolution. ADR-0013 makes one
  possible; nothing in this spec starts one, and `export`/`import` stay explicit and manual
- Credential storage, `devteam cred`, and the PreToolUse guard — **built in M3, specified in
  [`v3-credentials.md`](v3-credentials.md)**, which owns those criteria. Out of scope *here*, not
  unbuilt: this spec asserts nothing about them, and a change to that surface is checked against
  that spec
- Retiring `state.json:installed_version` and repointing its four readers — later milestone;
  the bind stamps the key so they report the truth in the meantime
- The Electron app, the Homebrew tap and the winget package — **milestone M4, specified in
  [`v4-app-and-distribution.md`](v4-app-and-distribution.md)**, which owns those criteria. That
  milestone is **partially done**: the client contract the app depends on is built and tested
  (`devteam catalog`, the `compat` block on `version --json`, and a `--json` sweep across every
  command discovered from the parser), and the Homebrew formula and cask, the winget manifests and
  the release workflow exist as **unverified scaffolding** — nothing has been published, installed,
  brew-audited or accepted anywhere, and the app itself is not built. Out of scope *here* either
  way: this spec asserts nothing about them, and each criterion in that spec is marked met,
  unverifiable-without-credentials, or unbuilt
- Making the harness write root (`docs/`) configurable; only additional read-only context paths are planned, and not in M1
- Linux as a release target

### Dependencies
- **Depends on**: ADR-0007, ADR-0008, ADR-0009, ADR-0012, ADR-0013
- **Blocks**: [`v3-credentials.md`](v3-credentials.md) (M3, now built),
  [`v4-app-and-distribution.md`](v4-app-and-distribution.md) (M4, partially built — contract yes,
  channels and app no)

### Amendment Log
- 2026-09-27 | implementation | Bind artifacts are excluded through `.git/info/exclude`, not
  `.gitignore`; `.gitignore` keeps only the short, project-level managed block (memory, resolved
  preferences, markers, `.worktrees/`). | A bind links one entry per skill — 152 in the current
  tree — and those are per-developer, per-clone paths. Writing them into the committed
  `.gitignore` would add ~155 generated lines to every product repository for information no
  teammate needs. `.git/info/exclude` is local to the clone, which is exactly the scope of a
  bind. The scenario "bind artifacts are gitignored between managed markers" still holds; the
  file it holds in is the local exclude.
- 2026-09-27 | review | Added the `core` pointer, hook-dispatcher, pin-preservation,
  quarantine, containment, worktree and exit-code scenarios above. | The M1 review found that
  the bind produced provider content but neither the in-project runtime root that 116 shipped
  references need nor the hook dispatchers that make the framework self-enforcing; that three
  code paths deleted user content instead of quarantining it; that no write path checked
  containment; and that a plain re-bind silently released a pin. Each was invisible to the
  criteria as written, so the criteria were wrong, not just the code.
- 2026-09-27 | M2 | Added the layout, upgrade, preference-cascade, context-path and store-portability
  scenarios; moved memory relocation and the preference cascade out of Out of Scope. | M2 implements
  them. Memory relocation landed behind an explicit `devteam upgrade` rather than as a side effect of
  `sync`, which changed the shape of the criteria: the guarantee worth asserting is that **no other
  command moves it**, not merely that it ends up in the store. Recorded in ADR-0012.
- 2026-09-27 | M2.1 | Split the data store into a portable subtree and `data/machines/<machine-id>/`,
  and made `devteam export` portable by default. | The inventory of a populated store found exactly
  two record types carrying absolute paths (`registry.json`, `bind-manifest.json`) plus `state.json`
  carrying this machine's own observations, while memory and preferences were already portable — so
  the criterion "the registry and every project's memory are present" after an import was asserting
  the wrong thing: a registry full of another machine's paths is worse than no registry. What a
  restore must guarantee is that `project.json` plus the portable records rebuild the bind. Done now
  because v3 is unreleased and a machine id cannot be assigned retroactively; after release it would
  be a second consented layout migration. Recorded in ADR-0013, which amends ADR-0007.
- 2026-09-27 | review | A five-agent review of M2.1 found two CRITICAL defects and a
  plaintext-credential leak, none of them visible to the criteria as written. (1) `import` routed
  its members through a filter that never inspected `linkname`, and relied on `filter="data"` —
  which does not exist on the declared python floor (3.9), where `extractall` defaults to
  `fully_trusted`: on the interpreter the CLI is required to support, a symlink or hardlink member
  was an arbitrary write and a read-any-file primitive. (2) The relocation moved `state.json` out
  from under `.dev-team-agents/state-dir` without repointing it, so `state_get` returned an empty
  string for every key — installed version, session id, health-check marker — silently, with no
  error anywhere. (3) `devteam upgrade` quarantines the whole legacy `user-data/` directory,
  `credentials.local.json` included, and `quarantine/` was both portable and included in the
  default export: a reviewer extracted a plaintext database password from a default archive. | The
  criteria said the portable subtree names no absolute path and that the relocation moves nothing
  inside a project. Both were false, and being false is how the defects passed: quarantine *is* in
  the portable subtree and *does* hold absolute-path records, and a regenerated pointer is
  something the relocation must move. The criteria now assert what the export excludes rather than
  what a subtree contains, assert that the relocation refreshes the pointers it invalidates, and
  add the machine re-issue, consent-withholding, archive-member validation, and the
  `path`/`doctor`-create-nothing guarantees that had no criterion at all.
- 2026-09-28 | software-architect | Moved credentials, `devteam cred` and the PreToolUse guard out of
  Out of Scope as unbuilt, and pointed at the new [`v3-credentials.md`](v3-credentials.md) instead of
  absorbing them here. | M3 built them. They stay out of *this* spec's criteria on purpose: this spec
  is about the store, the bind and versioning, and folding ~15 credential scenarios into it would mean
  one document whose scope is "v3", which is not a boundary anyone can check a change against. The
  line in Out of Scope now says which spec owns them rather than that they do not exist — a stale
  "later milestone" reads as "not built" and is how a reviewer concludes a surface is unspecified.
- 2026-09-28 | software-architect | Pointed the Electron-app / Homebrew / winget Out of Scope entry at
  the new [`v4-app-and-distribution.md`](v4-app-and-distribution.md), and stated that M4 is *partially*
  done — the client contract is built and tested, the packaging is unverified scaffolding, the app does
  not exist. | Same reasoning as the M3 entry above, with one addition that matters more here: M4 was
  split, so "later milestone" is now wrong in both directions. It understates the contract, which is
  built and green, and it would overstate the channels if the entry simply said M4 shipped. The pointer
  names the owning spec; the marked criteria in that spec carry the distinction, and none of it moves
  into this spec's own criteria.

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
