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
relocation, the preference cascade, credentials and the desktop app are later milestones.

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

### Out of Scope
- Moving project memory (`session-summary.md`, `state.json`) into the data store — later milestone
- The preference cascade and its resolved projection — later milestone
- Credential storage, `devteam cred`, and the PreToolUse guard — later milestone
- The Electron app, the Homebrew tap and the winget package — later milestone
- Making the harness write root (`docs/`) configurable; only additional read-only context paths are planned, and not in M1
- Linux as a release target

### Dependencies
- **Depends on**: ADR-0007, ADR-0008, ADR-0009
- **Blocks**: memory relocation, preference cascade, credentials, desktop app

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

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
