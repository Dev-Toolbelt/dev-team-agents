<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Backup Information

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **BackupInfo**: [`BackupInfo::list`](#backupinfo-list), [`BackupInfo::progress`](#backupinfo-progress), [`BackupInfo::reset`](#backupinfo-reset)

## BackupInfo

<a id="backupinfo-list"></a>
### `BackupInfo::list` — Return cPanel account backups

`GET /execute/BackupInfo/list` · RO/RW: unspecified · since 136 · requires plugin `BackupInfo`

This function returns one entry for each cPanel account backup archive in the current cPanel account's home directory. Note: The function derives each archive's status from the on-disk marker file that cPanel writes while a backup runs. It is the single source of truth for the list of available backups.

**Returns** `data`: array of object

- *(array of objects)*
  - `fullpath` (string) — The archive file name.
  - `mtime` (integer) — Archive modification time, epoch seconds.
  - `name` (string) — The archive file name.
  - `sizeBytes` (integer) — Size of the `.tar.gz` archive in bytes.
  - `startedAtEpoch` (integer) — Start epoch read from the marker file while a run is active.
  - `status` (string (`ready`, `inprogress`, `timeout`)) — Archive status derived from the marker file.; `ready` - No marker file is present.; `inprogress` - A marker file is present and the run is within the timeout.; `timeout` - A marker file is present and the run stalled pas

```bash
uapi --output=jsonpretty \
  --user=username \
  BackupInfo \
  list
```

<a id="backupinfo-progress"></a>
### `BackupInfo::progress` — Return account backup progress

`GET /execute/BackupInfo/progress` · RO/RW: unspecified · since 136 · requires plugin `BackupInfo`

This function returns progress information for a cPanel account backup. Note: When the `PkgAcct::Create` hook is installed, that hook anchors the run's start and finish, and the function reports `complete` only after it confirms the published archive in the home directory, along with the archive's exact final size. A run that never publishes an archive is therefore never reported as complete. Without the hook, the function falls back to the on-disk marker file. When no run is active, the `state` return value is `none` and the other return values are `0` or null. When the function cannot determine the account's disk usage, the `estimatedTotalBytes` and `estimatedPercent` return values are `0` even while a run is active.

**Returns** `data`: object

- `currentBytes` (integer) — Current size in bytes of the growing `.tar.gz` archive.
- `elapsedSeconds` (integer) — Seconds since the run started.
- `estimatedPercent` (number) — Completion percent, from 0 to 100.
- `estimatedTotalBytes` (integer) — Estimated final archive size in bytes.
- `finishedAtEpoch` (integer) — The finish time, in epoch seconds.
- `startedAtEpoch` (integer) — The start time, in epoch seconds.
- `state` (string (`inprogress`, `timeout`, `complete`, `none`)) — The current run state.; `inprogress` - A run is active or finalizing.; `timeout` - A run is active but has passed the timeout ceiling.; `complete` - The published archive is confirmed in the home directory.
- `stateSource` (string (`hook`, `marker`, `none`)) — Origin of the `state` value.; `hook` - The authoritative `PkgAcct::Create` record, which gives a definitive start and finish.; `marker` - The estimated fallback derived from the on-disk marker file.; `none` - Nothing is 

```bash
uapi --output=jsonpretty \
  --user=username \
  BackupInfo \
  progress
```

<a id="backupinfo-reset"></a>
### `BackupInfo::reset` — Remove backup progress record

`GET /execute/BackupInfo/reset` · RO/RW: unspecified · since 136 · requires plugin `BackupInfo`

This function clears the authoritative run-state record, so that the `BackupInfo::progress` function stops reporting a `complete` state that persists across polls. Note: After a reset, the `BackupInfo::progress` function reflects only live state. It reports `inprogress` while a run is genuinely active and `none` otherwise. This function is idempotent and succeeds whether or not a record exists.

**Returns** `data`: object

- `cleared` (boolean) — Always true on success.

```bash
uapi --output=jsonpretty \
  --user=username \
  BackupInfo \
  reset
```

