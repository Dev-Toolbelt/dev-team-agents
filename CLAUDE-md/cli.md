# v3 — Global Store, Project Bind and the `devteam` CLI

Companion to [`CLAUDE.md`](../CLAUDE.md). Decisions behind this layout:
[ADR-0007](../docs/development/adrs/0007-global-core-and-data-store-replacing-per-project-vendored-install.md)
(store split), [ADR-0008](../docs/development/adrs/0008-project-identity-via-committed-project-json-and-three-personal-preference-layers.md)
(identity and preference layers), [ADR-0009](../docs/development/adrs/0009-python3-as-the-devteam-cli-runtime-while-hooks-stay-bash.md)
(python3 CLI). Acceptance criteria: [`docs/specs/v3-global-install.md`](../docs/specs/v3-global-install.md).

**Milestone status.** M1 (store, CLI, identity, bind, versions/pin, migration), M2 (preference
cascade, memory relocation behind a consented upgrade, `context_paths`, store portability), M2.1
(the portable/machine-local store split, [ADR-0013](../docs/development/adrs/0013-portable-and-machine-local-split-of-the-data-store.md))
and M3 (credentials — see § Credentials, [ADR-0010](../docs/development/adrs/0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md))
are implemented. The desktop app, the Homebrew tap and winget are a later milestone. The v2
`install.sh` path keeps working for one deprecation cycle.

---

## The two stores

| Store | Holds | Lifetime |
|-------|-------|----------|
| **core** | `versions/<X.Y.Z>/` (agents, commands, skills, scripts, templates) + the `current` pointer | Disposable — an uninstall may remove it, `devteam update` rebuilds it |
| **data** | `machine-id`, `preferences.json`, `credentials/` (references only), `projects/<project_id>/`, `quarantine/`, `machines/<machine-id>/` (registry, locks, per-project state, `secrets/`, `audit.log`) | Survives uninstall; on Windows it is in the roaming profile, so profile backup covers it |

```
macOS    core  ~/Library/Application Support/dev-team-agents/core
         data  ~/Library/Application Support/dev-team-agents/data
         cache ~/Library/Caches/dev-team-agents
Windows  core  %LOCALAPPDATA%\dev-team-agents\core        data  %APPDATA%\dev-team-agents\data
Linux    core  $XDG_DATA_HOME/dev-team-agents/core        data  $XDG_DATA_HOME/dev-team-agents/data
         cache $XDG_CACHE_HOME/dev-team-agents
```

`$DEVTEAM_HOME` overrides all of it (`<home>/core`, `<home>/data`, `<home>/cache`) and is the seam
the test suite uses — no test touches a real user directory.

**`core/current` is a plain text file, not a symlink.** A symlink there would put the Windows
materialisation failure at the most load-bearing path in the design.

### `data/` is split by what a record says ([ADR-0013](../docs/development/adrs/0013-portable-and-machine-local-split-of-the-data-store.md))

```
data/machine-id                                    this machine's UUID, created once
data/preferences.json                              PORTABLE — the global preference layer
data/projects/<project_id>/preferences.json        PORTABLE — the project preference layer
data/projects/<project_id>/session-summary.md      PORTABLE — the user's own memory
data/credentials/                                  PORTABLE — references only, no values
data/quarantine/<date>/<project_id>/               PORTABLE
data/machines/<machine-id>/registry.json           MACHINE-LOCAL — absolute paths
data/machines/<machine-id>/locks/                  MACHINE-LOCAL — a lock names a pid
data/machines/<machine-id>/projects/<id>/…         MACHINE-LOCAL — bind-manifest.json, state.json,
                                                   and the dot-markers (caches, ETags, day stamps)
```

**Portable = what the user authored or decided. Machine-local = what this machine observed or
built.** `paths.is_machine_local_record(name)` is the single answer to which side a per-project
record belongs on — dot-prefixed names are machine-local as a class, and so are `state.json`,
`bind-manifest.json`, `telemetry-queue.json`, `audit.log` (this machine's own reads, and a growing
record that two machines appending to would need merge semantics for) and the v2
`credentials.local.json` (values, not references). Never re-derive that rule at a call site.

`devteam export` archives the portable subtree by default (excludes `machine-id`, `machines/`,
`locks/`, `quarantine/`, and every machine-local record at any depth); `--all` includes the
machine subtree for a full-machine backup. Default destination is `$cache/exports/<stamp>.tar.gz`
with mode `0600` (owner-only). A portable archive restored elsewhere is completed with
`devteam bind` per project — the committed `project.json` reconnects it to its memory, and the
registry and manifests are rebuilt locally. An import that carries no machine subtree keeps the
receiving machine's own `machine-id` and `machines/`, or every bound project there would read as
unbound. `devteam import` strips the consent keys (`telemetry`, `auto_update`) from any incoming
`preferences.json`.

`store.adopt_machine_layout()` relocates a store written before the split, once, from `cli.main`
before any command reads the registry. **No synchronisation exists or is implied** — the split is
what makes one possible later.

## What a bound project contains

```
<project>/.dev-team-agents/project.json   COMMITTED — schema, project_id, layout, context_paths
<project>/.dev-team-agents/core           pointer to the resolved core version
<project>/.dev-team-agents/resolved/      generated: preferences.json (the cascade's projection)
<project>/.dev-team-agents/state-dir      generated: one line, absolute path of the machine-local state directory
<project>/.dev-team-agents/memory-dir     generated: one line, absolute path of the portable memory directory
<project>/.dev-team-agents/user-data/     project memory — layout 1 only; gone after `devteam upgrade`
<project>/.claude/settings.json           hook dispatchers, merged — project-owned, committed
<project>/.claude/… .opencode/… .codex/…  bind artifacts — excluded, regenerated by sync
```

**The `core` pointer is what makes project-relative framework paths work.** 116 shipped
references resolve through it (`.dev-team-agents/core/scripts/…`, `…/core/templates/…`),
including `CLAUDE.md`'s own `new-adr.sh` invocation. It is a symlink in `link` mode and a copy in
`copy` mode, and it is recorded in the manifest like any other artifact.

**The bind registers the four hook dispatchers** (`SessionStart`, `Stop`, `PreCompact`,
`PreToolUse`) by merging into the project's own `.claude/settings.json`; a stale v2 path is
rewritten in place rather than duplicated, and `unbind` removes only those entries. Without them
the session banner, session-summary enforcement, orphan-skill scan, agent lint and ADR-gap check
do not run in that project at all.

**Files the installers merge into** — `.claude/settings.json`, `.opencode/opencode.json`,
`AGENTS.md` — belong to the project. They are neither ignored nor removed; the project commits
them.

Bind artifacts cannot be committed: they carry an absolute path into one developer's store. They are
excluded through **`.git/info/exclude`**, which is local to the clone — a bind links one entry per
skill (152 today), and writing those into a shared `.gitignore` would add ~155 generated lines to a
product repository. `.gitignore` gets only the short project-level block (memory, resolved
preferences, markers, `.worktrees/`), between managed markers.

## Bind modes

| Mode | Artifacts | Default where | Notes |
|------|-----------|---------------|-------|
| `link` | symlinks into `core/versions/<v>` | macOS, Linux | `devteam update` re-points every project at once |
| `copy` | real copies, refreshed by `sync` | Windows without native symlink support | Recorded in `registry.json`, so the fallback is never silent |
| `vendored` | full tree in the project, relative links — v2 behaviour | opt-in | CI, containers, air-gapped, repos that must ship the harness |

`auto` probes for symlink support rather than guessing from the platform name. An explicit
`--mode=link` on a filesystem that cannot do it **fails** instead of silently downgrading.

## Commands

| Command | Does |
|---------|------|
| `devteam path` | Resolved store locations |
| `devteam version` | Installed versions and the active one |
| `devteam store list \| install --from <tree> \| use <v> \| gc [--apply]` | Manage the versioned core; `gc` previews by default and never removes `current` or a pinned version |
| `devteam bind [path] [--provider …] [--mode …] [--pin <v>]` | Bind a project; idempotent |
| `devteam unbind [path]` | Remove artifacts, keeping `project.json` and `user-data/` |
| `devteam list` | Bound projects, mode, resolved version, pin drift |
| `devteam sync [path] [--all]` | Rebuild artifacts from the store |
| `devteam pin <v> \| --release` | Hold a project on a version, or return it to `current` |
| `devteam update [--ref vX.Y.Z] [--check]` | Fetch a release, activate it, sync every unpinned project |
| `devteam migrate [path] [--apply]` | v2 vendored install → bind. Previews unless `--apply` |
| `devteam prefs list \| get <key> \| set <key> <value> [--scope project] \| unset <key>` | Read and write the preference layers; `list` names the layer each value came from |
| `devteam cred list \| get <key> \| set <key> \| unset <key> \| import <file> \| check \| backends` | Manage credential references and values; see § Credentials below |
| `devteam upgrade [path] [--apply]` | Move this project's memory into the store. Previews unless `--apply`; **nothing moves on any other command** |
| `devteam export [--to <path>] [--all]` / `devteam import <archive> [--force]` | Move the data store to another machine; portable by default, `--all` includes this machine's registry and manifests |
| `devteam uninstall [--purge --yes]` | Remove the core; `--purge` also deletes the data store and needs `--yes` |
| `devteam doctor [path] [--reassign-identity]` | Diagnose store and bind; reconcile a moved project; report a stale layout |

## The `--json` contract

`--json` is accepted before or after the subcommand. stdout then carries exactly one JSON document
with an `ok` field; human text is suppressed and warnings stay on stderr. This is public API — the
desktop app is a client of the CLI (ADR-0011), so an output shape change is a breaking change.

| Exit | Meaning |
|------|---------|
| 0 | success |
| 1 | findings — ran and reported a problem it did not fix |
| 2 | usage error |
| 3 | environment error (no store, no version, unreadable directory) |
| 4 | conflict (lock timeout, identity collision, refusing to overwrite) |

**Exception: `devteam cred get` refuses `--json`.** The value is written to stdout and nothing else, so wrapping it in a document would put a secret somewhere a client is likely to log. Use `devteam cred list --json` for the references instead.

## Credentials

Credential **references** (purpose, scope, backend) are portable and reviewed — stored in `data/credentials/global.json` (shared across projects) or `data/credentials/<project_id>.json` (per-project, overrides global). Values stay out of git entirely: the macOS `security` keychain, Windows DPAPI, or a machine-local encrypted store. See [ADR-0010](../docs/development/adrs/0010-credential-references-and-the-secret-backend-cascade.md).

### Commands

| Command | What it does | Flags |
|---------|------|-------|
| `devteam cred list` | Every declared credential — references only, never a value | `--path <dir>`, `--global` |
| `devteam cred get <key>` | Print one value on stdout and nothing else — use this for the sanctioned read path (audited) | `--path <dir>`, `--global`, `--agent <name>` |
| `devteam cred set <key>` | Declare a credential and store the value; reads from stdin (never argv) | `--path <dir>`, `--global`, `--purpose <text>` (required), `--scope <agents>` (comma-separated), `--backend <name>` |
| `devteam cred unset <key>` | Remove a reference; the value stays unless `--forget-value` is passed | `--path <dir>`, `--global`, `--forget-value` |
| `devteam cred import <file>` | Migrate a v2 `credentials.local.json` into references and move the file to quarantine | `--path <dir>`, `--global` |
| `devteam cred check` | Report references with no stored value, or any credential on an insecure backend | `--path <dir>`, `--global` |
| `devteam cred backends` | Which secret stores this machine has available (and why, if any are unavailable) | none |

Shared flags (on all but `backends`): `--path <dir>` targets a different project directory (default: the current one); `--global` acts on the global layer instead of the project's.

### Store layout

**Portable** (in archives by default; reviewed in git):

```
data/credentials/global.json                    References used across projects
data/credentials/<project_id>.json              References for one project (overrides global)
```

**Machine-local** (never in archives; never in git):

```
data/machines/<machine-id>/secrets/             Where a backend keeps values on disk (mode 0600, last resort)
data/machines/<machine-id>/projects/<id>/audit.log   Append-only read audit trail — machine-local because two machines appending to one log would need merge semantics we do not have
```

When a reference exists but its value is missing, `devteam cred check` reports it; `devteam cred get` fails cleanly.

### Backends

| Backend | Availability | Behavior |
|---------|--------------|----------|
| `keychain` | macOS only, via `security` CLI | System keychain; service `dev-team-agents`, account `devteam/<project_id>/<key>`. Encrypted by OS. |
| `dpapi` | Windows only, via ctypes | Windows Data Protection API; key derivation from machine identity. Implemented but unverified on real hardware — testers needed. |
| `insecure` | All platforms (fallback only) | **Not encrypted.** A mode-0600 JSON file at `data/machines/<machine-id>/secrets/`. Last resort when no native store is available. `devteam cred check` reports every value on this backend. Never use in production; suitable for test/CI environments where the value lifetime is seconds. |

A value is stored on the first-available backend by default; `--backend` on `devteam cred set` overrides the probed default. When a backend becomes unavailable (e.g., upgrading to a different OS), values stay on the machine that wrote them — move them across machines with `devteam export --all` → `devteam import`. A reference without a value is not an error; it documents what a project needs even if the value has not been set yet.

### Special behaviors

**Stdin rule:** `devteam cred set` reads the value from stdin, never from a command-line argument. A value in `argv` is in the process table for every other user on the machine, and in the shell history of the user running the command. Interactively, it prompts without echo; non-interactively, pipe it: `printf %s "$TOKEN" | devteam cred set mykey --purpose "an API key"`.

**Scope field:** `--scope` restricts which agents can read the value via `devteam cred get --agent <name>`. Agents not listed get a clear error; comma-separated, no spaces. The scope is **hygiene and auditability, not a sandbox** — an agent with Bash can read anything the user can read. Its value is auditing read paths and reporting scope violations in the audit log.

**`credentials.local.json` migration:** The v2 plaintext file is opt-in, never scanned for. `devteam cred import /path/to/credentials.local.json` reads it, migrates values to the secret store, writes references to the reference layer, and moves the original file to quarantine — a one-way, confirmed operation. Non-secret fields (TTL thresholds, notification prefs) are kept as plain values in the reference layer.

## Layout, memory and preferences

`project.json` carries **`layout`**, distinct from `schema`: `schema` is the file's format, `layout`
is where the project's own state lives. `1` means `.dev-team-agents/user-data/` (every v2 and M1
project); `2` means the data store — portable memory in `data/projects/<project_id>/` and machine-local state
in `data/machines/<machine-id>/projects/<project_id>/`. A bind that finds no `user-data/` creates the
project on the current layout, so a new project is clean from the start. `devteam upgrade` splits the
v2 directory between the two as it copies.

**Nothing relocates memory except `devteam upgrade`.** `bind`, `sync`, `update` and `migrate` report
a stale layout and stop. The upgrade is copy → verify by sha256 → retire the original to quarantine,
and it refuses a populated destination before copying anything. See
[ADR-0012](../docs/development/adrs/0012-project-layout-version-and-a-consented-structure-upgrade.md).

`.dev-team-agents/state-dir` holds the absolute path of the state directory so `scripts/lib/state.sh`
resolves it in one file read — a CLI call would put a python subprocess inside every hook. It names
the **machine-local** directory (`project.state_dir()`), because `state.json` is what reads through
it; `project.memory_dir()` is the portable sibling and has no pointer, since nothing in bash reads
it yet.

**Preferences cascade in three personal layers** (defaults → global → project) and are resolved on
write into `.dev-team-agents/resolved/preferences.json`. Agents read that one file; nothing merges at
read time. Canonical contract: `skills/shared/user-preferences/SKILL.md`. `context_paths` is **not**
a preference — it is committed topology in `project.json`, read per
`skills/shared/project-context/SKILL.md` § Context Loading Order.

## Rules for contributors

- **No-Destruction Rule** — canonical home `skills/shared/setup-health-check/SKILL.md`, including
  the one named exception this CLI has (a symlink artifact is unlinked, since `sync` regenerates
  it). Implemented by `scripts/lib/devteam/quarantine.py`; every real file or directory goes to
  `data/quarantine/<date>/<project_id>/`. `require_inside` in `bind.py` must be called before
  every write and every removal — three separate data-loss defects were one missing call to it.
- **Every store mutation takes a lock** (`scripts/lib/devteam/lock.py`) and writes through
  `jsonio.write_json_atomic` — two sessions in two bound projects mutate the same registry.
- **Standard library only**, and **python 3.9 or newer** — the floor is enforced in
  `scripts/cli/devteam` and tested as its own CI matrix leg. No third-party dependency, no
  virtualenv, no lockfile.
- **Path containment is compared component-wise on resolved paths** (`_is_inside` in `bind.py`).
  `startswith` on unresolved paths is wrong twice: `/var` vs `/private/var` on macOS, and a
  sibling named `core-backup` reading as inside `core`.
- **Tests are the gate.** `python3 -m unittest discover -s tests -t tests`, run by
  `.github/scripts/ci/03-python.sh` as a blocking CI step. `tests/` is stripped from the package.
