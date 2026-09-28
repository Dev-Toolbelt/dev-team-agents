# ADR-0013: Portable and machine-local split of the data store

**Date:** 2026-09-27  
**Status:** Accepted  
**Deciders:** Repository owner, software-architect

## Context

[ADR-0007](0007-global-core-and-data-store-replacing-per-project-vendored-install.md) created one
durable `data/` store and recorded, as a known limitation, that it is not portable even though it
holds memory that is: "registry.json and bind-manifest.json hold absolute paths from the exporting
machine." That limitation was written down rather than fixed.

The question that forced it was whether a future synchronisation mechanism is possible at all. Ten
projects on one machine need no sync today, and none is being built — but the architecture has to be
ready for one. So the store was inventoried to find what actually blocks it:

```
data/registry.json                            → absolute paths
data/projects/<id>/bind-manifest.json         → absolute paths
data/projects/<id>/state.json                 → session id, installed version, last update check
data/projects/<id>/session-summary.md         → portable
data/projects/<id>/preferences.json           → portable
data/preferences.json                         → portable
data/quarantine/…                             → portable by content, but see below
```

Exactly **two** record types carry absolute paths, and one more — `state.json` — carries facts that
are true only of the machine that wrote them: `installed_version` is the version of *this* machine's
core store, and `session_id`, `session_head` and `last_update_check` are observations of this
machine's sessions. Everything else is what the user authored.

The inventory read `quarantine/` as portable, and that reading is what made the first cut of this
decision unsafe: whatever the *content* is, the directory is where retired machine-local records are
deposited — `devteam upgrade` moves the whole legacy `user-data/` there, `credentials.local.json`
included. Portability of content and inclusion in a portable export turn out to be two questions,
and this store needs a third class for the records where the answers differ.

Two things make the timing decisive:

1. **v3 is unreleased.** No user is on layout 2 yet. Changing the shape now costs one relocation of
   the repository's own store; changing it after release costs a *second* consented layout migration
   on top of the one ADR-0012 just introduced.
2. **A machine id cannot be assigned retroactively.** Once two machines have written records into a
   shared tree with no identity on them, nothing can say afterwards which machine wrote which.

The storage engine was never the blocker, which is why this ADR does not pick one. SQLite, a
key-value store or JSON files would each face the same problem: a record that names
`/Users/alice/Code/app` is meaningless on the machine that has `D:\work\app`.

## Decision

**Split `data/` by what a record says, not by how it is stored.**

Records the user **authored or decided** are portable and stay at the top of the store. Records this
machine **observed or built** move under `data/machines/<machine-id>/`.

```
data/
├── machine-id                                  ← {id, created_on}: UUID + the host that
│                                                 recorded it. O_EXCL on first write;
│                                                 re-issued when the host does not match
├── preferences.json                            ← portable
├── projects/<project_id>/
│   ├── preferences.json                        ← portable
│   └── session-summary.md                      ← portable
├── credentials/                                ← portable — references only (ADR-0010)
├── quarantine/                                 ← portable by content, never exported by
│                                                 default (see the export bullet below)
└── machines/<machine-id>/
    ├── registry.json                           ← machine-local: absolute paths
    ├── locks/                                  ← machine-local: a lock names a pid
    └── projects/<project_id>/
        ├── bind-manifest.json                  ← machine-local: absolute paths
        ├── state.json                          ← machine-local: this machine's observations
        └── .<markers>                           ← machine-local: caches, ETags, day stamps
```

> **Amended by ADR-0010's implementation (M3).** The inventory in Context above was taken before
> credentials were built, and it classified neither of the two records that milestone adds. Both are
> **machine-local**, and the tree above should be read as carrying them:
>
> ```
> data/credentials/                                 ← PORTABLE: references only, no value
> data/machines/<machine-id>/secrets/               ← machine-local: values at rest
> data/machines/<machine-id>/projects/<pid>/audit.log ← machine-local: reads on THIS machine
> ```
>
> - **`audit.log`** is in `paths.MACHINE_LOCAL_RECORDS`. It is an observation, not something the
>   user authored — it records credential reads that happened on this host — so it lands on the
>   machine side by the same rule as `state.json`. The stronger reason is that it is a *growing*
>   record: two machines appending to one portable log would need merge semantics nothing here has,
>   and a trail that silently interleaves two hosts is worse than two separate ones. It is written as
>   append-only JSONL, one `json.dumps` per `os.write` on an `O_APPEND` descriptor, which is the
>   format this ADR's own closing paragraph asks a growing log to use — and the contrast with
>   `session-summary.md`, still prepend-at-top markdown, is recorded under Remaining gaps below.
>   Global-layer reads (no bound project) use the scope `global`, which cannot collide with a
>   `project_id` because those are UUID4.
> - **The value store** at `machine_dir() / "secrets"` is machine-local and deliberately **not**
>   beside `data/credentials/`. The reference layer is portable *precisely because* it holds no
>   value, which makes exporting it routine — and a value store adjacent to a routinely-exported
>   directory ends up in the first archive somebody takes. Separating the subtrees means the
>   classification does the work rather than an author remembering an exclusion, which is the same
>   argument the `credentials.local.json` bullet below already makes for the v2 file. A keychain or
>   DPAPI value is not in this directory at all on macOS; DPAPI writes one `0600` JSON envelope per
>   secret here, and the last-resort `insecure` backend writes one `insecure.json`.
>
> Neither record changes the export predicate: both are caught by
> `paths.is_machine_local_record` / `path_is_machine_local` at every path depth, so no new exclusion
> was added and none has to be remembered — which is what the `devteam_record_class` row in
> `docs/development/reuse-guidelines.md` exists to keep true.

Consequences of the line, each deliberate:

- **The machine id identifies a machine, not a store.** `machine-id` records the id **and the host
  that created it**, and a mismatch re-issues a new id rather than adopting the recorded one. This
  is not defensive coding: ADR-0007 deliberately places `data/` in the Windows **roaming** profile
  because that is the tree the user must not lose, and a roaming profile is replicated between
  machines by policy — so without the host check, the layout this design documents would
  *guarantee* two machines answering with one id. A restored disk image, a VM clone and a shared
  `$DEVTEAM_HOME` on a network mount are the same failure. On re-issue nothing is deleted: the
  previous machine's subtree stays where it is, inert and unread.
- **A project carries two pointers, because layout 2 has two directories.**
  `.dev-team-agents/state-dir` names the machine-local directory, because `scripts/lib/state.sh`
  resolves `state.json` through it and nothing else. `.dev-team-agents/memory-dir` names the
  portable one, because `skills/shared/project-context/SKILL.md` step 4 reads
  `<memory-dir>/session-summary.md` — the framework's own context contract is a reader, so the
  second pointer was never speculative. Both are regenerated projections: every path that changes
  where either directory resolves must call `project.write_pointers`, including the relocation
  below.
- **Dot-prefixed names are machine-local as a class.** Every one of them is a cache, an ETag, a
  once-per-day stamp or a session marker. A class rule beats an enumeration that the next marker
  silently escapes.
- **`credentials.local.json` is machine-local.** Its *values* are secrets, and a secret that travels
  with a portable export is a secret in one more place. This is also the direction ADR-0010 already
  takes: references are portable precisely because they hold no value, and the values live in a
  per-machine keychain.
- **`devteam export` is portable by default**; `--all` keeps the machine subtree for a backup of
  *this* machine and excludes only `locks/`. The default excludes `machine-id`, `machines/`,
  `locks/`, `quarantine/`, and any machine-local record **matched by basename at every path depth** —
  not by first component, which is the check a review found insufficient. A portable archive
  restored elsewhere is completed by running `devteam bind` in each project: the committed
  `project.json` reconnects the project to its memory, and the registry and manifests are rebuilt
  locally. That round trip — `project.json` + portable records ⇒ a working bind — is the property
  this ADR exists to establish.
- **`quarantine/` is portable by content but never part of a portable export.** It is an unbounded
  recovery bin, and it is where both `devteam upgrade` and the relocation deposit retired
  machine-local records — secrets included. It is therefore `paths.LOCAL_ONLY_STORE_ENTRIES`: a
  third class, neither machine-local nor exportable. `--all` takes it, because that mode is a backup
  of this machine and the user already has the content.
- **The archive lands in `cache_dir()/exports/` and is written `0600`.** Not the current working
  directory: that is the bound repository, where an archive of the data store is one `git add -A`
  away from being committed. The path is printed either way. The manifest also stopped naming the
  absolute data directory, which disclosed the OS username and home layout to whoever received it.
- **A portable import keeps the receiving machine's own records, and inherits no consent.**
  Promoting a portable archive verbatim would take the live registry out of the active store, and
  every bound project would read as unbound — so `machine-id` and `machines/` are carried across
  before promotion. The consent keys (`telemetry`, `auto_update`) are **stripped** from an incoming
  `preferences.json`, because the backfill only adds keys that are *missing*: an imported file
  saying `true` would have enabled telemetry on a machine whose owner was never asked. Removing them
  makes the cascade resolve both to `consent-withheld`, which is what "never asked" looks like.
  Every member is validated by `update.safe_members` — including a symlink's or hardlink's
  `linkname` — because `filter="data"` does not exist on the declared python floor, where
  `extractall` defaults to `fully_trusted`.
- **`store.adopt_machine_layout()` relocates a pre-split store once**, from `cli.main`, before any
  command reads the registry. Idempotent; promotes each file with `os.replace`, so a record is at the
  old path or the new one and never neither; and quarantines rather than overwriting when the
  destination is already occupied, because only the user can say which of two registries is current.
  It then **rewrites each bound project's two pointers**, because moving `state.json` out from under
  `.dev-team-agents/state-dir` without repointing it made `state_get` return an empty string for
  every key — installed version, session id, health-check marker — silently, with no error anywhere.
  This is a relocation inside the app's own store: it is not the project-facing structure change
  ADR-0012 governs, and it moves no *content* into or out of a project. It does refresh two
  regenerated projections there, which every `bind` and `sync` already rewrites.

**No synchronisation is being built, and none is implied.** This ADR makes one possible; it does not
start one. When it is built, the portable subtree is the candidate for syncing, the machine subtree
never is, and growing logs should be append-only (JSONL) so two machines' appends merge instead of
colliding. A derived index — SQLite or otherwise — belongs in `cache/`, rebuildable from the records,
and never becomes the source of truth.

## Consequences

### Positive
- `export`/`import` no longer depend on a warning in a manifest being read: the records that cannot
  survive the trip are the ones that no longer travel, and the classification is applied
  mechanically at every path depth. This is **not** correctness by construction, and claiming it was
  hid a real defect. The classification is *allow-portable-by-default* — `MACHINE_LOCAL_RECORDS`,
  `LOCAL_ONLY_STORE_ENTRIES` and the dot-prefix class are enumerations, and anything outside them
  travels whatever it holds. What the construction does guarantee is narrower and still worth
  having: no enumerated class escapes by being nested one directory deeper, and one predicate
  decides both what the archive holds and what the report counts.
- The machine id exists from the first write, which is the only time it can be created honestly, and
  it is recorded together with the host that created it — the part that lets a store which travelled
  be recognised rather than trusted.
- **Two machines write into separate subtrees even when they can both reach the same store.** The id
  is not the store's; a store opened on a host other than the one in the record yields a new id and
  a new subtree, so the roaming profile, the VM clone and the shared `$DEVTEAM_HOME` stop being
  silent single-identity cases. The residual case is two hosts that report the *same* name — two
  clones of one image before either is renamed, or a default hostname — where the records do still
  land in one subtree and one file. That is narrower than the original claim, which was simply
  false: "never in the same file" was a property of the tree shape, and the tree shape is keyed by
  an id that a shared store handed to both machines.
- **A portable archive carries no `credentials.local.json` and no quarantined copy of one.** Stated
  precisely, because the earlier wording ("secrets no longer ride along") was false as shipped:
  `devteam upgrade` quarantines the whole legacy `user-data/` directory, secrets included, and
  `quarantine/` was portable and included in the default export — a reviewer extracted a plaintext
  database password from a default archive. What now holds: `credentials.local.json` is
  machine-local at every depth, `quarantine/` is excluded from a default export outright, and the
  archive itself is `0600`. What this does **not** cover: classification is
  allow-portable-by-default, so a secret the user keeps under a name the enumerations do not list —
  `secrets.yml`, `api-keys.json`, a token pasted into `session-summary.md` — is portable and will
  travel. (A dot-prefixed name would be caught, but only incidentally: that class exists for caches
  and markers, not as a secrets policy.) `--all` carries everything but `locks/` by design,
  quarantine included.
- ADR-0007's recorded limitation is resolved rather than carried.

### Negative
- One more level of nesting in the store, and two per-project directories instead of one. A reader
  has to know which of the two a record lives in; `paths.is_machine_local_record()` for a name and
  `paths.path_is_machine_local()` for a path are the single answer, and no caller may re-derive it.
  Registered as `devteam_record_class` in `docs/development/reuse-guidelines.md`, because the two
  defects that shipped — an export filter and the upgrade's own router — both re-derived it from a
  first path component and both read as ordinary path handling.
- A portable restore needs a `devteam bind` per project. That is more steps than an archive that
  "just works" — but the archive that just worked only did so on the machine it came from.
- Two pointer files per project instead of one, and both must be rewritten by every path that
  changes where either directory resolves. The original decision here was **wrong and is reversed**:
  the portable pointer was skipped on the reasoning that "a pointer with no reader is a surface that
  drifts", but it had a reader from the start — `skills/shared/project-context/SKILL.md` step 4 is
  the framework's own context-loading contract, and it reads the session summary through a pointer.
  Repointing `state-dir` at the machine subtree without adding `memory-dir` left every agent looking
  for the episodic layer in a directory that has no summary. The reasoning failed because it counted
  readers in the CLI and the bash hooks, and the largest class of reader in this framework is an
  agent following a skill.

### Remaining gaps

Recorded because the review surfaced them and this decision does **not** close them:

- **`preferences.json` is classified as one file, and it is not one kind of record.**
  `qa_browser` and `worktree_docker_isolate` assert *this machine's* tooling — a browser that is
  installed here, a Docker daemon that runs here — and they travel with a portable export like any
  other preference. Only the consent keys are handled specially, and only on import. The honest
  position is that the split is per-file and this file is mixed; a per-key classification is the
  fix, and it is not built.
- **`session-summary.md` is prepend-at-top markdown**, which contradicts this ADR's own guidance
  that a growing log should be append-only (JSONL) so two machines' appends merge instead of
  colliding. It is also the largest growing record in the portable subtree — the one a future sync
  would hit first. Changing its format is a change to what every agent writes, not a store change,
  so it is not in scope here.
- **No record carries a revision or a timestamp of its own.** A future sync needs one to decide
  which side of a divergence is newer; today the only ordering available is the filesystem's mtime,
  which does not survive an archive round trip reliably. Adding it is cheap now and cheaper than
  reconstructing it later, but it is not part of this decision.

### Neutral
- `data/locks` from a pre-split store is left in place rather than moved: a lock may be held right
  now by a process that will look for it at the old path, and locks are regenerated anyway.
- `devteam path` and `devteam doctor` both report the machine id, so the extra nesting is visible
  rather than something to deduce from the tree. Both resolve it with `create=False` and mint
  nothing: a diagnostic that creates an identity as a side effect of being asked a question reports
  on a world it just made, and a second run would see a different one. `doctor` reports another
  machine's record set as a **warn**, not as `ok` — inert is not the same as expected, and a second
  record set means the store is shared or was restored from elsewhere.

## Risks

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **One store, two machines, one identity.** The design invites it: ADR-0007 puts `data/` in the Windows roaming profile, and `$DEVTEAM_HOME` on a network mount is a documented layout. Two machines sharing one id interleave their absolute paths in one `registry.json`, and nothing afterwards can say which entry belongs to which machine. | `machine-id` records the creating host; a mismatch re-issues a new id and a new subtree, leaving the other one inert. `devteam doctor` warns whenever it finds a record set that is not this machine's. | The check is only as good as the hostname. Two clones of one image, or two hosts on a default name, report the same name and share a subtree. `machine_host()` also honours `$DEVTEAM_HOSTNAME`, `$COMPUTERNAME` and `$HOSTNAME` before asking the OS, so the check rests on a value a user or a CI image can set. And a user who merely renames their machine gets a new id and an orphaned previous subtree — nothing is lost, but `devteam bind` has to run again per project. None of these is detected automatically; `doctor`'s warning is the only signal. |
| **A project pointer goes stale under a relocation**, and fails silently: `state_get` returns an empty string for every key rather than erroring, so the installed version, the session id and the health-check marker all read as absent. This already happened. | The relocation calls `project.write_pointers` for every bound project it can resolve. `devteam doctor` checks **both** pointers against what the project's layout resolves to and **rewrites** a missing or stale one in place — the same additive repair it already performs on a moved registry entry, because reporting and waiting is what let a stale pointer hand every hook an empty `state.json` until someone happened to run `devteam sync`. | The repair only runs where `doctor` runs. A project whose directory is missing or whose `project.json` is unreadable is skipped by the relocation on purpose, so it stays stale until `doctor` or `sync` next runs there — and a bash hook that fires before either reads the stale pointer. Nothing detects the condition at hook time. |
| **A record travels that should not have**, because classification is allow-portable-by-default and the enumerations are not a secrets policy. | `credentials.local.json` and the dot class are machine-local at every path depth; `quarantine/` is excluded from a default export; the archive is `0600`; one predicate decides both the archive and the count. | A user-authored file under an unlisted name is exported. `--all` exports quarantine by design. There is no scan of record *contents*, and adding one is not proposed — it would be a heuristic making a security promise. |
| **A hostile archive on import.** `filter="data"` does not exist on the declared python floor, where `extractall` defaults to `fully_trusted`. | `update.safe_members` validates every member's `name`, rejects device and fifo members, and validates a symlink's or hardlink's `linkname` — absolute or escaping targets are refused. `filter="data"` is still passed where it exists. | `import` and `update` now share one implementation of the guard rather than keeping a copy each — the copy is how `linkname` went unchecked here. Any future extractor that grows its own loop reintroduces the defect, and no regex can see an absent call — the same shape as the `devteam_record_class` row in `docs/development/reuse-guidelines.md`, which covers the classification helpers but not this one. |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Leave it as ADR-0007 recorded it and revisit when sync is built | The machine id cannot be assigned retroactively, and after release the change becomes a second consented layout migration for every user. Cost now: one relocation. |
| Make paths relative to a per-machine root variable | Only fixes the two path-bearing records and leaves `state.json` mixing machine observations with portable memory. Also turns every read into a resolution step that can fail. |
| Pick a database (SQLite) and let it own the problem | The engine is not what blocks portability — absolute paths are. A synced SQLite file with absolute paths in it is exactly as unusable, and it adds a write-concurrency model that JSON-plus-lock already handles. |
| Split only `registry.json` and `bind-manifest.json` | Leaves `state.json` portable, so a future sync would ping-pong `installed_version` between machines running different versions — the one field that must never be shared. |
| Keep `credentials.local.json` portable, since it is the user's own file | It holds values, not references. Making secrets the payload of a routine export is the wrong default, and ADR-0010 already moves values off the filesystem. |
| Derive the machine id from an OS machine identifier — `/etc/machine-id`, `IOPlatformUUID`, `MachineGuid` | It is the more precise answer and it was rejected on cost and coverage, not on principle. It is three per-platform code paths to maintain and to keep testable behind `$DEVTEAM_HOME`, against one `socket.gethostname()` for all three. Coverage is worse where this store is most exposed: a container has no `/etc/machine-id` on many images and shares the host's when the file is bind-mounted, which is exactly the CI and devcontainer case; `IOPlatformUUID` needs a subprocess into `ioreg`; and `MachineGuid` is a registry read that a cloned Windows image reproduces verbatim unless sysprep ran — the VM-clone case this check exists for. A recorded UUID plus a host check gets the same outcome for the cases that actually occur, and fails visibly (a new id, a `doctor` warning) rather than silently. Worth revisiting if the residual same-hostname case is ever observed. |
| Fail loudly, or refuse to run, when the recorded host does not match | An error on every invocation for a user whose machine was simply renamed, and there is nothing for them to do about it. Re-issuing is the recoverable action: nothing is deleted, the previous subtree stays readable, and one `devteam bind` per project restores the state. `doctor` is where the condition is surfaced. |
