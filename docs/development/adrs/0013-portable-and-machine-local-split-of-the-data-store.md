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
data/quarantine/…                             → portable
```

Exactly **two** record types carry absolute paths, and one more — `state.json` — carries facts that
are true only of the machine that wrote them: `installed_version` is the version of *this* machine's
core store, and `session_id`, `session_head` and `last_update_check` are observations of this
machine's sessions. Everything else is what the user authored.

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
├── machine-id                                  ← UUID, created once, O_EXCL
├── preferences.json                            ← portable
├── projects/<project_id>/
│   ├── preferences.json                        ← portable
│   └── session-summary.md                      ← portable
├── credentials/                                ← portable — references only (ADR-0010)
├── quarantine/                                 ← portable
└── machines/<machine-id>/
    ├── registry.json                           ← machine-local: absolute paths
    ├── locks/                                  ← machine-local: a lock names a pid
    └── projects/<project_id>/
        ├── bind-manifest.json                  ← machine-local: absolute paths
        ├── state.json                          ← machine-local: this machine's observations
        └── .<markers>                           ← machine-local: caches, ETags, day stamps
```

Consequences of the line, each deliberate:

- **`.dev-team-agents/state-dir` points at the machine subtree.** `scripts/lib/state.sh` resolves
  `state.json` through that pointer and nothing else, so the pointer follows `state.json`. A second
  pointer for the portable directory is **not** written: nothing reads it yet, and a pointer with no
  reader is a surface that drifts.
- **Dot-prefixed names are machine-local as a class.** Every one of them is a cache, an ETag, a
  once-per-day stamp or a session marker. A class rule beats an enumeration that the next marker
  silently escapes.
- **`credentials.local.json` is machine-local.** Its *values* are secrets, and a secret that travels
  with a portable export is a secret in one more place. This is also the direction ADR-0010 already
  takes: references are portable precisely because they hold no value, and the values live in a
  per-machine keychain.
- **`devteam export` is portable by default**; `--all` keeps the machine subtree for a backup of
  *this* machine. A portable archive restored elsewhere is completed by running `devteam bind` in
  each project: the committed `project.json` reconnects the project to its memory, and the registry
  and manifests are rebuilt locally. That round trip — `project.json` + portable records ⇒ a working
  bind — is the property this ADR exists to establish.
- **A portable import keeps the receiving machine's own records.** Promoting a portable archive
  verbatim would take the live registry out of the active store, and every bound project would read
  as unbound. `machine-id` and `machines/` are carried across before promotion.
- **`store.adopt_machine_layout()` relocates a pre-split store once**, from `cli.main`, before any
  command reads the registry. Idempotent; promotes each file with `os.replace`, so a record is at the
  old path or the new one and never neither; and quarantines rather than overwriting when the
  destination is already occupied, because only the user can say which of two registries is current.
  This is a relocation inside the app's own store — it is not the project-facing structure change
  ADR-0012 governs, and it moves nothing inside a project.

**No synchronisation is being built, and none is implied.** This ADR makes one possible; it does not
start one. When it is built, the portable subtree is the candidate for syncing, the machine subtree
never is, and growing logs should be append-only (JSONL) so two machines' appends merge instead of
colliding. A derived index — SQLite or otherwise — belongs in `cache/`, rebuildable from the records,
and never becomes the source of truth.

## Consequences

### Positive
- `export`/`import` are correct by construction rather than by a warning in a manifest: the paths
  that cannot survive the trip are the ones that no longer travel.
- The machine id exists from the first write, which is the only time it can be created honestly.
- Two machines' records cannot collide, because they are never in the same file.
- Secrets no longer ride along in a portable archive.
- ADR-0007's recorded limitation is resolved rather than carried.

### Negative
- One more level of nesting in the store, and two per-project directories instead of one. A reader
  has to know which of the two a record lives in; `paths.is_machine_local_record()` is the single
  answer, and no caller may re-derive it.
- A portable restore needs a `devteam bind` per project. That is more steps than an archive that
  "just works" — but the archive that just worked only did so on the machine it came from.
- The second per-project directory has no bash pointer, so a hook that needs the portable directory
  (the session-summary readers, still reading the in-project path) will need one added. That gap
  predates this change and is not closed by it.

### Neutral
- `data/locks` from a pre-split store is left in place rather than moved: a lock may be held right
  now by a process that will look for it at the old path, and locks are regenerated anyway.
- `devteam path` and `devteam doctor` both report the machine id, so the extra nesting is visible
  rather than something to deduce from the tree.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Leave it as ADR-0007 recorded it and revisit when sync is built | The machine id cannot be assigned retroactively, and after release the change becomes a second consented layout migration for every user. Cost now: one relocation. |
| Make paths relative to a per-machine root variable | Only fixes the two path-bearing records and leaves `state.json` mixing machine observations with portable memory. Also turns every read into a resolution step that can fail. |
| Pick a database (SQLite) and let it own the problem | The engine is not what blocks portability — absolute paths are. A synced SQLite file with absolute paths in it is exactly as unusable, and it adds a write-concurrency model that JSON-plus-lock already handles. |
| Split only `registry.json` and `bind-manifest.json` | Leaves `state.json` portable, so a future sync would ping-pong `installed_version` between machines running different versions — the one field that must never be shared. |
| Keep `credentials.local.json` portable, since it is the user's own file | It holds values, not references. Making secrets the payload of a routine export is the wrong default, and ADR-0010 already moves values off the filesystem. |
