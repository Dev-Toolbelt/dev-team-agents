# Machine Identity in a Roaming Profile

**Origin:** M2.1 split — portable and machine-local records | 2026-09-27
**Tags:** machine-id, roaming profile, Windows, ADR-0007, data store, network mount, VM clone, disk image

> A per-machine ID stored in a roaming data directory does not identify a machine, because roaming profiles replicate between machines by OS policy.

---

## What it is

ADR-0007 deliberately placed the data store on Windows in `%APPDATA%` — the **roaming** profile — because it survives uninstall and the OS backs it up by policy. This is a feature: an exported store can move between machines as a backup or to pre-seed a new developer's setup.

The machine-id records which machine wrote a bind manifest or a state marker, so the store can say "this registry entry came from the laptop, not the desktop." But a roaming profile replicates to every machine the user logs into, so if the ID is stored there unchanged, two machines answer with one identity — the store cannot tell them apart.

## How it works

On first use, `paths.machine_id()` creates a machine-id file in the data store. It **records both the id and the hostname** (from `socket.gethostname()` or `DEVTEAM_HOSTNAME`) at the time of creation. On subsequent reads, it checks whether the recorded hostname matches the current machine's hostname:

- **Match** → same machine, return the id
- **Mismatch** → the store travelled (exported and restored, or accessed from another machine), re-issue a new id for this machine. The old id's subtree (`data/machines/<old-id>/`) stays put, inert — nothing is deleted

The same logic applies to:
- A disk image cloned and booted on two machines
- A VM snapshot restored multiple times
- `$DEVTEAM_HOME` on a shared network mount accessed from multiple hosts

## Gotchas

- The hostname must be **stable** across reboots — most systems have this, but containers, VMs set to `localhost`, or dynamically-assigned names in cloud deployments may not
- A hostname collision (two machines with the same hostname on the same network) will not be detected — the name is used only as a match check, not as a unique identifier
- Reading `paths.machine_id(create=False)` returns the recorded id even when the hostname does not match; it does not re-issue a new one. This is deliberate for diagnostics and read-only callers
- The first machine to boot after a roaming-profile sync will get the multi-machine ID, and will re-issue a local one on second read. Subsequent machines will each take a new ID in turn

## References

- ADR-0007: [Global core and data store replacing per-project vendored install](../../development/adrs/0007-global-core-and-data-store-replacing-per-project-vendored-install.md)
- ADR-0013: [Portable and machine-local split of the data store](../../development/adrs/0013-portable-and-machine-local-split-of-the-data-store.md)
- `scripts/lib/devteam/paths.py`: `machine_id()`, `_reissue_machine_id()`
