# v3 — Global Store, Project Bind and the `devteam` CLI

Companion to [`CLAUDE.md`](../CLAUDE.md). Decisions behind this layout:
[ADR-0007](../docs/development/adrs/0007-global-core-and-data-store-replacing-per-project-vendored-install.md)
(store split), [ADR-0008](../docs/development/adrs/0008-project-identity-via-committed-project-json-and-three-personal-preference-layers.md)
(identity and preference layers), [ADR-0009](../docs/development/adrs/0009-python3-as-the-devteam-cli-runtime-while-hooks-stay-bash.md)
(python3 CLI),
[ADR-0014](../docs/development/adrs/0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md)
(store schemas as the normative write gate, and the `json_contract` deprecation policy).
Acceptance criteria: [`docs/specs/v3-global-install.md`](../docs/specs/v3-global-install.md).

**Milestone status.** M1 (store, CLI, identity, bind, versions/pin, migration), M2 (preference
cascade, memory relocation behind a consented upgrade, `context_paths`, store portability), M2.1
(the portable/machine-local store split, [ADR-0013](../docs/development/adrs/0013-portable-and-machine-local-split-of-the-data-store.md))
and M3 (credentials — see § Credentials, [ADR-0010](../docs/development/adrs/0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md))
are implemented. **M4 is partially done:** `devteam catalog`, the `compat` block in `version --json`,
the `--json` contract test sweep, and the client write gate (§ The client write gate) are in place.
The desktop app, signed release channels (Homebrew, winget), and full M4 are not yet available. The v2
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
record that two machines appending to would need merge semantics for), the v2
`credentials.local.json` (values, not references), and the notification queue
`notifications.jsonl` with its `notifications-seen.json` (what this machine's hooks noticed and this
machine's app has shown). Never re-derive that rule at a call site.

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
<project>/.dev-team-agents/scripts        link to the resolved version's scripts/ (a copy in copy mode)
<project>/.dev-team-agents/templates      link to the resolved version's templates/ (a copy in copy mode)
<project>/.dev-team-agents/resolved/      generated: preferences.json (the cascade's projection)
<project>/.dev-team-agents/state-dir      generated: one line, absolute path of the machine-local state directory
<project>/.dev-team-agents/memory-dir     generated: one line, absolute path of the portable memory directory
<project>/.dev-team-agents/user-data/     project memory — layout 1 only; gone after `devteam upgrade`
<project>/.claude/settings.json           hook dispatchers, merged — project-owned, committed
<project>/.claude/… .opencode/… .codex/…  bind artifacts — excluded, regenerated by sync
```

**The `scripts` and `templates` links are what make project-relative framework paths work.** The
framework's own text names 138 of them (`.dev-team-agents/scripts/new-adr.sh`,
`…/templates/plan-template.md`, the reuse and design-token lints the Stop hook runs); the links sit
at exactly that path, so nothing is rewritten and `settings.json`'s hook path is the one a v2 install
used. Only these two trees: nothing shipped reads agents, commands or skills through
`.dev-team-agents/` — Claude Code finds those under `.claude/`. They replaced a single `core`
pointer to the whole version, which put every reference one directory too deep; `sync` retires a
leftover `core` and rewrites `core/scripts/hooks` entries in place. `tests/test_runtime_links.py`
binds this repository's real tree and fails on any cited path that does not resolve. A real
directory at either path is a v2 tree: `bind` and `sync` refuse with exit 4 and point at `migrate`.
The v2 tools that now resolve there (`update.sh`, `rollback.sh`, `fix-symlinks.sh`) refuse to run
in a bound project (`scripts/lib/bound-project-guard.sh`) and name the `devteam` command instead.

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

**`link` is the mode to recommend a user** — it is the only one where a `devteam update` to the
store reaches every bound project with no further action. `copy` and `vendored` both need an
explicit `devteam sync` (per project) after each update to pick up the change; a user on one of
those modes who skips that step keeps running the version they bound at. This is a recommendation
for a human choosing among the four, not a change to the CLI's own default: `--mode` still
defaults to `auto`, and `auto` already resolves to `link` on any filesystem that supports it — a
plain `devteam bind` on macOS or Linux gets the recommended behaviour without the caller having to
know that. Only a caller for whom `link` is not viable (Windows without symlink privilege, or a
project that intentionally wants `vendored`) has a reason to override it. The app's bind dialog
mirrors this: it pre-selects `link` and labels it recommended, but a user can still choose another
mode.

## Commands

| Command | Does |
|---------|------|
| `devteam path` | Resolved store locations |
| `devteam version` | Installed versions and the active one |
| `devteam catalog` | Read-only browse — counts, and per-kind listings; see § Catalog below |
| `devteam store list \| install --from <tree> \| use <v> \| gc [--apply]` | Manage the versioned core; `gc` previews by default and never removes `current` or a pinned version |
| `devteam bind [path] [--provider …] [--mode …] [--pin <v>]` | Bind a project; idempotent. **Refuses a v2 vendored install with exit 4** and points at `migrate` — binding over one left the vendored tree tracked in git. `--mode vendored` is exempt, and `sync` never refuses: the check is in the command, not in `bind()` |
| `devteam unbind [path]` | Remove artifacts, keeping `project.json` and `user-data/` |
| `devteam list` | Bound projects, mode, resolved version, pin drift |
| `devteam sync [path] [--all]` | Rebuild artifacts from the store |
| `devteam pin <v> \| --release` | Hold a project on a version, or return it to `current` |
| `devteam update [--ref vX.Y.Z] [--check]` | Fetch a release, activate it, sync every unpinned project |
| `devteam migrate [path] [--apply]` | v2 vendored install → bind. Previews unless `--apply`. Reports, never runs, the `git rm -r --cached` the user owes: `git_tracked` (the vendored trees) and `git_tracked_artifacts` (committed links a bind replaced with machine-local ones) |
| `devteam prefs list \| get <key> \| set <key> <value> [--scope project] \| unset <key>` | Read and write the preference layers; `list` names the layer each value came from |
| `devteam cred list \| get <key> \| set <key> \| unset <key> \| import <file> \| check \| backends` | Manage credential references and values; see § Credentials below |
| `devteam upgrade [path] [--apply]` | Move this project's memory into the store. Previews unless `--apply`; **nothing moves on any other command** |
| `devteam export [--to <path>] [--all]` / `devteam import <archive> [--force]` | Move the data store to another machine; portable by default, `--all` includes this machine's registry and manifests |
| `devteam uninstall [--purge --yes]` | Remove the core; `--purge` also deletes the data store and needs `--yes` |
| `devteam notifications list [--project <id>] [--unseen]` | Live notifications across bound projects: what the hooks queued (`scripts/hooks/lib/notify.sh`), minus the expired, each with `seen` (ADR-0017) |
| `devteam notifications ack <id>… \| --all [--project <id>]` | Mark notifications seen. Writes `notifications-seen.json` under a lock; **never rewrites the queue** a hook may be appending to |
| `devteam notifications watch [--interval <s>]` | Stream the unseen backlog, then each new record, until stdin closes or SIGTERM. `--json` is JSON Lines — see § The `--json` contract |
| `devteam doctor [path] [--reassign-identity]` | Diagnose store and bind; reconcile a moved project; report a stale layout, a v2 tree left behind by a bind, and machine-local bind artifacts git still tracks (`bind.MACHINE_LOCAL_KINDS` — `settings` is exempt, it is the project's own file). The same allowlist decides what `bind` writes into `.git/info/exclude`, so `.claude/settings.json` is never hidden from `git add` |

## The `--json` contract

`--json` is accepted before or after the subcommand. stdout then carries exactly one JSON document
with an `ok` field; human text is suppressed and warnings stay on stderr. This is **public API**
defined in [ADR-0011](../docs/development/adrs/0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) —
the desktop app is a client of the CLI, so an output shape change is a breaking change. The contract
is swept across every subcommand by `tests/test_json_contract.py`, which discovers commands from the
real parser rather than a hardcoded list, ensuring new or changed commands are caught before release.

| Exit | Meaning |
|------|---------|
| 0 | success |
| 1 | findings — ran and reported a problem it did not fix |
| 2 | usage error (bad arguments, unknown subcommand, **a malformed client declaration** — see § The client write gate) |
| 3 | environment error (no store, no version, unreadable directory, **a store whose one-time layout migration a declared client may not perform**) |
| 4 | conflict (lock timeout, identity collision, refusing to overwrite, a declared client refused a mutating command — see § The client write gate) |

This table and the module docstring of `scripts/lib/devteam/errors.py` are two halves of one contract:
the docstring names the same declared-client cases on 2, 3 and 4, and the reasoning for each sits with
the function that raises it (`compat.refusal` for 4, `compat.migration_required` for 3). If you change
one, change the other in the same commit — and see ADR-0014 § 2, which makes *changing which exit code
an existing outcome uses* a `json_contract` obligation.

**Exception: `devteam notifications watch --json` is JSON Lines.** It runs until its stdin closes
(or SIGTERM) and writes one compact JSON document per line, each carrying `ok`: every unseen
`notification` already queued, then `ready`, then each new `notification`, a `heartbeat` every
30 s, and `end` (with `reason`: `stdin-closed`, `sigterm`, `interrupted`) last. No final document
follows. It is excluded from the bulk contract sweep and pinned by `tests/test_notifications.py`
against a real stream instead.

**Exception: `devteam cred get` refuses `--json`.** The value is written to stdout and nothing else, so wrapping it in a document would put a secret somewhere a client is likely to log. Use `devteam cred list --json` for the references instead.

## Catalog

`devteam catalog` is a read-only browse surface for the framework's agents, skills, and commands
in the version the project is bound to.

**Three deliberate behaviors:**

1. **It reads from the bound version, never from the working tree.** If you stand in a project with a
   pin or a stale checkout, catalog shows what that pin resolves to. This is load-bearing for the desktop
   app, which must never report the harness in two different states depending on where the user was
   standing when they asked.
2. **It creates nothing, including not minting a machine identity.** Same discipline as `devteam path`
   and `devteam doctor` — read-only commands leave the store untouched.
3. **Malformed files are flagged, never fatal.** A skill with invalid YAML in the frontmatter is
   listed as `malformed` with its path, so the user can locate and fix it. A catalog that exits on
   one bad file is useless for finding the bad file.

**Subcommands:**

- `devteam catalog` — Summary: installed version, project identity, counts per kind, and malformed counts
- `devteam catalog agents|skills|commands` — Every entry of that kind, with name/tier/model/path/description
- `devteam catalog show <name>` — One entry's metadata plus body; resolves a bare name across all three kinds. When a name is ambiguous, lists the candidates instead

**Flags:**

- `--path <dir>` — Read from a different project (default: current one)
- `--json` — Output JSON with entries in their full structure

**Payload shapes (JSON output):**

- `devteam catalog`: `{version, project_id, counts: {agents, skills, commands}, malformed: {agents, skills, commands}}`
- `devteam catalog agents|skills|commands`: `{version, project_id, <kind>: [{name, tier, model, description, path, version}, …], count}`
- `devteam catalog show`: adds `kind` and `body` to the entry

## Compatibility block in `version`

`devteam version --json` now includes a `compat` block that reports the JSON contract version and
the store schema numbers:

Keys are alphabetical because `output.py` dumps with `sort_keys=True`. This is a real emission,
captured from `devteam version --json` against a throwaway store — **`store_schemas` carries every
shape the store has, and a client that is silent about one of them is treated as not understanding
it** (see the write gate below), so an example listing a subset would teach the opposite rule:

```json
{
  "compat": {
    "json_contract": 1,
    "min_app_version": null,
    "store_schemas": {
      "bind_manifest": 1,
      "credentials": 1,
      "project": 1,
      "project_layout": 2,
      "registry": 1
    }
  },
  "core": "/path/to/core",
  "current": null,
  "installed": [],
  "ok": true
}
```

A client (the desktop app, for example) reads this before writing to the store: if it does not
understand a schema number in `store_schemas`, it downgrades to read-only mode. `min_app_version`
is `null` until a desktop release ships; it will then carry the minimum app version that understands
the current contract. This is ADR-0011's "compatibility is declared, not assumed" — the alternative
is inferring compatibility from the framework's release version, which moves for reasons that have
nothing to do with the contract.

## The client write gate

`devteam compat` *answers* "may this client write?". The gate is what makes that answer **binding** for
a caller that identified itself. Decided in
[ADR-0014](../docs/development/adrs/0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md);
the reasoning behind each judgment call is recorded in `scripts/lib/devteam/compat.py` beside the code
and is not restated here.

**Declaring.** Two seams, both naming a JSON file holding the same object `devteam compat
--client-file` accepts — every shape `store_schemas` reports, since an omitted one counts as
unsupported:

| Seam | Form |
|------|------|
| `--client-schemas <PATH>` | global — accepted before or after the subcommand, like `--json` |
| `DEVTEAM_CLIENT_SCHEMAS` | the same path in the environment, exported once for a client session |

**The flag wins over the variable.** The flag is on the invocation in front of you; the variable is
ambient and inherited, so a wrapper that exported it once must not override what this call says about
itself. An empty or whitespace-only variable is treated as *unset*, not as an empty declaration —
`export DEVTEAM_CLIENT_SCHEMAS=` is a shell saying "no value", and reading it as `{}` would refuse
every write in that session.

**An empty flag is the opposite case: `--client-schemas ""` is exit 2, not the anonymous path.** The
asymmetry is deliberate. A shell cannot distinguish an absent variable from an empty one, so empty means
unset *there and only there*; a flag with an empty value is a caller that passed a value and got it
wrong — almost always `--client-schemas "$SCHEMAS"` with `SCHEMAS` unset, the ordinary idiom a client
wrapper has. Downgrading that to silence would drop the gate on exactly the invocation that meant to
declare. Asserted in both directions by `tests/test_client_gate.py::EmptyFlagValueIsNotSilenceTest`,
including against `compat.client_declaration` itself so the rule is pinned as a rule and not only as an
exit code.

One parser (`compat.parse_client_schemas` / `compat.load_client_schemas`)
serves both seams **and** `devteam compat`'s own `--client`/`--client-file`, so the two cannot disagree
about what a valid declaration is. A bare `devteam compat` with no `--client`/`--client-file` falls back
to the same seam, so an exported declaration gets a `may_write` without restating the file.

**Every rejection names the seam that carried the path**, not just the path: `--client-schemas …`,
`--client-file …` or `DEVTEAM_CLIENT_SCHEMAS …`. A client whose wrapper exported the variable three
layers up has to be told which seam is at fault rather than handed a path it never typed. Asserted for
all three seams by `tests/test_client_gate.py::…test_a_declaration_file_names_the_seam_that_carried_it`.

**A malformed declaration is a malformed question — exit 2 on every seam, including `devteam compat`.**
`json.loads` has two failure modes that are not `JSONDecodeError` and `Path.read_text` one that is not
`OSError`: a file that is not valid UTF-8, and input nested too deeply to parse. Both are `UsageError`
now, so `devteam compat --client-file <undecodable-or-too-deep>` is **exit 2**; it was exit 3 before,
reached through `cli.main`'s catch-all as *"unexpected UnicodeDecodeError / RecursionError"*, which is a
crash reported as an environment problem. Exactly one document still goes out on stdout under `--json`,
and no traceback reaches the shell — `tests/test_client_gate.py::UnreadableDeclarationIsADocumentNotATracebackTest`
asserts both on all three seams plus `devteam compat`, and exercises `cli.main`'s remaining catch-all
directly so the net itself is not the untested part.

**When it runs.** A declaration is resolved — and therefore validated — on every invocation that
carries one, including a read-only one: a corrupt declaration file is a broken client installation, and
reporting it on the first call rather than on the first *write* removes the window in which the gate
silently is not there. The refusal itself applies only to a **mutating** command, and it happens in
`cli.main` after the parse and **before `store.adopt_machine_layout()`**, which is itself a store
mutation — so a refused command leaves the store byte-identical. That ordering is not a comment any
more: `tests/test_client_gate.py::PreSplitStoreTest` fabricates a pre-split store and asserts the store
is byte-identical after a refusal, for `bind` and then across the whole of `compat.MUTATING`. Before it
existed, moving the gate block below `adopt_machine_layout()` left every test green.

| Caller | Mutating command | Read-only command |
|--------|------------------|-------------------|
| declares nothing | runs | runs |
| declares, understands every shape | runs | runs |
| declares, is behind on or silent about a shape | **refused, exit 4** | runs — except on a store that has not been relocated, see below |
| declaration file missing, empty, malformed, not UTF-8 or nested too deeply | usage error, exit 2 | usage error, exit 2 |

A client *ahead* of the store is not refused — an older store read by a newer client is the direction
that works.

**Exit 4, not 1.** `devteam compat` exits 1 for an incompatible client because there the negative is a
*finding*: the question ran and answered. A refused write ran nothing, and exit 1 in this CLI always
means "ran and reported a problem it did not fix". Exit 2 stays reserved for a malformed question,
which is what a broken declaration file already raises; exit 3 says the environment cannot support the
command, and for a refused **write** the environment is fine — the client is the party that is behind.
Exit 3 does have one declared-client use, and it is the opposite case: a read-only command whose
*environment* is not ready, described below.

The refusal is an ordinary error document, and its `details` carry the comparison so a client branches
on data rather than on the wording of a sentence. Below is a **real emission**, not an illustration:
`devteam bind --json --client-schemas client-schemas.json` in a throwaway store, against a declaration
naming three of the store's five shapes and one of those a version behind
(`{"project": 1, "project_layout": 2, "registry": 0}`). Keys are alphabetical because the emitter dumps
with `sort_keys=True` (`output.py`), so this is the on-the-wire order, not a tidied one:

```json
{
  "details": {
    "client_schemas": {
      "project": 1,
      "project_layout": 2,
      "registry": 0
    },
    "command": "bind",
    "declaration_source": "client-schemas.json",
    "declared_by": "--client-schemas",
    "may_write": false,
    "store_schemas": {
      "bind_manifest": 1,
      "credentials": 1,
      "project": 1,
      "project_layout": 2,
      "registry": 1
    },
    "unsupported": {
      "bind_manifest": {
        "client": null,
        "store": 1
      },
      "credentials": {
        "client": null,
        "store": 1
      },
      "registry": {
        "client": 0,
        "store": 1
      }
    }
  },
  "error": "bind would write to this store, and the client declared via --client-schemas does not understand 3 shape(s) it uses: bind_manifest (store=1, client=(not declared)), credentials (store=1, client=(not declared)), registry (store=1, client=0)",
  "exit_code": 4,
  "hint": "Upgrade the client, or run `devteam compat --client-file client-schemas.json` for the full comparison. Read-only commands still work. Dropping the declaration is not a fix — it only hides the mismatch.",
  "ok": false
}
```

Read what that payload is actually saying, because a shorter example would teach the wrong rule. The
store carries **five** shapes (`project`, `project_layout`, `registry`, `bind_manifest`, `credentials`).
This declaration named three, so `unsupported` has **three** entries, not one: `registry` is a version
behind, and `bind_manifest` and `credentials` were never mentioned — silence is not a claim of support,
so both are reported with `"client": null` and render as `client=(not declared)` in the human message.
A client that declares a subset is refused for every shape it left out.

`declaration_source` is the path exactly as the caller passed it — relative here, because the invocation
passed a relative path. `declared_by` names the seam actually used, so a client whose wrapper three
layers up exported `DEVTEAM_CLIENT_SCHEMAS` is told about the variable rather than about a flag it never
passed. This refusal always sets `hint`, so a client parsing `details` should expect it — but `hint` is a
*conditional* key of the error envelope generally (`errors.DevteamError.payload()` emits it only when
set), never a fixed key of any command. The seven `details` keys are the pinned part, held by
`tests/test_client_gate.py::RefusalDetailsAreThePinnedContractTest` in both directions — it fails on an
added key as loudly as on a removed one, and prints the two sets so the next reader decides rather than
silences.

**The one-time machine-layout relocation is suppressed for an incompatible client, and one read-only
command is refused instead — exit 3.** `store.adopt_machine_layout()` moves a pre-ADR-0013 store's
machine-local records to the split paths. It **writes `registry` and `bind_manifest`** — precisely the
shapes an incompatible client just declared it cannot read — so it does not run on that caller's behalf.
A terminal invocation, any anonymous caller and any *compatible* declaration still perform it, so no
store is stranded by this.

With the relocation skipped, a read-only command answers against the layout actually on disk. Every
read-only command answers the same on both layouts **except `devteam list`**, which is why
`compat.NEEDS_MACHINE_LAYOUT` holds exactly that one entry. `paths.registry_file()` resolves only the
post-split path, so `list` read no registry at all and reported *every* bound project as unbound — exit
0, `projects: []`, no error anywhere, the same silent failure mode as the stranded `state-dir` pointer
that made `state_get` return an empty string for every key. The other read-only commands resolve through
the project's own pointers or through the core store rather than through the registry, so the layout
never reaches their answer.

**That membership was measured, not reasoned about.**
`tests/test_client_gate.py::PreSplitStoreTest.test_a_read_only_command_answers_the_pre_split_truth_or_is_refused`
runs every leaf of `compat.READ_ONLY` twice under the same incompatible declaration — once on the split
store, once after de-splitting — and requires each to answer identically or be refused, then asserts the
refused set **equals** `compat.NEEDS_MACHINE_LAYOUT`. A command that starts reading the registry fails
there rather than joining the wrong side quietly. (`cred get` is the one exclusion, and not for
convenience: it appends an audit line, so two runs differ by construction, and it refuses `--json` by
design so there is no document to compare.)

So `list` under an incompatible declaration on a pre-split store is **exit 3, not 4**. Nothing is being
refused *as a write* — this caller is entitled to read, and ADR-0011's rule is that an incompatible
client degrades to read-only. What is not ready is the **environment**: the store is in a shape this
command cannot read, and the one thing that would fix it is a write the caller said it cannot
understand. A clear refusal beats a wrong answer, because a client told `projects: []` would offer to
bind a project that is already bound. `compat.migration_required` raises it, carrying the refusal's seven
`details` keys **plus `machine_layout_pending: true`**, and its `hint` names the fix that does not
require upgrading the client: run any `devteam` command from a terminal without a declaration. The hint's
own escape hatches — `devteam compat`, `version` and `path` — are asserted to answer on a pre-split
store, so the guidance is not a dead end for the caller it is written for.

**Where the classification lives.** `compat.MUTATING` and `compat.READ_ONLY` in
`scripts/lib/devteam/compat.py` — 19 and 16 entries, covering all 35 parser leaves — keyed by the same
path tuples `tests/test_json_contract.py`'s discovery walk produces, with the reason beside every
entry. `compat.is_mutating()` **fails closed**: a command in neither table counts as mutating, so
forgetting to classify a new one cannot open a hole. `tests/test_client_gate.py` (52 tests) walks the real
parser and fails on any unclassified leaf, any leaf in both tables, and any entry naming a command that no
longer exists. A third, much smaller table sits beside them — `compat.NEEDS_MACHINE_LAYOUT`, one entry,
described above — and its membership is swept rather than trusted.

Six entries are judgment calls rather than readings of a name. Five of them carry their reason in the
table; the sixth is noted below because it does not:

- `cred get` is **read-only**. Its audit line is the framework's own record *about* the caller, not one
  of the shapes `store_schemas()` declares; gating it would turn a write gate into a read denial and
  replace its documented `--json` exit-2 refusal with an exit 4.
- `doctor` is **mutating** — it repairs directory pointers and can reassign identity.
- `export` is **mutating** — it creates a restorable archive of shapes the declaring client just said
  it cannot read.
- `store gc` and `migrate` are **mutating** by what the command can do, not by which flag one
  invocation passed — both say exactly that in the table, because both are read-only without `--apply`.
- `upgrade` is **mutating** for the same per-command reason, and its table entry does **not** state it —
  it reads only "relocates this project's memory into the store". It is also gated on `--apply`, so a
  reader comparing it against `store gc` and `migrate` finds the rationale missing from the one entry
  where the flag is most likely to invite re-deciding it from the invocation.

**An anonymous caller keeps its full write access.** No detection, no warning, no log entry: the gate
binds only callers that identify themselves, and omitting the declaration is a complete bypass. That is
deliberate — an anonymous invocation is byte-for-byte a human at a terminal, and the human's CLI is the
one thing this gate may not touch. ADR-0014 § 3 records the boundary, why identification is not
authentication, and the two conditions that would justify reopening it.

## Credentials

Credential **references** (purpose, scope, backend) are portable and reviewed — stored in `data/credentials/global.json` (shared across projects) or `data/credentials/<project_id>.json` (per-project, overrides global). Values stay out of git entirely: the macOS `security` keychain, Windows DPAPI, or a machine-local encrypted store. See [ADR-0010](../docs/development/adrs/0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md).

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
a stale layout and stop. The one file `bind` and `sync` do take out of `user-data/` is
`preferences.json`, because the cascade never read it there: its declared, well-typed keys are copied into
the project layer, read back, and the file is moved to quarantine (`imported-preferences`). A value the
project layer already holds wins; unknown or ill-typed keys are reported, not imported. The result is
`preferences_import` in the `bind`/`sync` payload — `null` when there was no file — with `imported`,
`unchanged`, `conflicts`, `ignored`, `quarantined` and `problem`. A file that is not a JSON object, or a
write that does not read back, is left in place with `problem` set. The upgrade is copy → verify by sha256 → retire the original to quarantine,
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
