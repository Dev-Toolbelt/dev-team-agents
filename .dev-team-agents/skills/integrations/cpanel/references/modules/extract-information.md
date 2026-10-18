<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Extract Information

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **ExtractInfo**: [`ExtractInfo::finish`](#extractinfo-finish), [`ExtractInfo::progress`](#extractinfo-progress), [`ExtractInfo::start`](#extractinfo-start)

## ExtractInfo

<a id="extractinfo-finish"></a>
### `ExtractInfo::finish` — Remove extract progress record

`GET /execute/ExtractInfo/finish` · RO/RW: unspecified · since 136 · requires plugin `ExtractInfo`

This function clears the run-state marker that the `ExtractInfo::start` function wrote. Note: After it runs, the `ExtractInfo::progress` function reports the state `none`. This function is idempotent and succeeds whether or not a marker exists. Call it after the `Fileman::fileop` function with `op=extract` finishes, whether that operation succeeded or failed.

**Returns** `data`: object

- `cleared` (boolean) — Always true on success.

```bash
uapi --output=jsonpretty \
  --user=username \
  ExtractInfo \
  finish
```

<a id="extractinfo-progress"></a>
### `ExtractInfo::progress` — Return archive extraction progress

`GET /execute/ExtractInfo/progress` · RO/RW: unspecified · since 136 · requires plugin `ExtractInfo`

This function returns progress information for an archive extraction that the `ExtractInfo::start` function began. Note: When no run is active, the `state` return value is `none` and the other return values are `0` or null.

**Returns** `data`: object

- `currentBytes` (integer) — Bytes the destination directory has grown by since the baseline that the `ExtractInfo::start` function recorded.
- `elapsedSeconds` (integer) — Seconds since the run started.
- `percent` (number) — Completion percent, from 0 to 99.
- `startedAtEpoch` (integer) — Start epoch recorded by the `ExtractInfo::start` function.
- `state` (string (`inprogress`, `timeout`, `none`)) — Current run state.; `inprogress` - A run is active and within the timeout.; `timeout` - A run has passed the timeout ceiling.; `none` - Nothing is running.
- `totalBytes` (integer) — The uncompressed archive size recorded at start.
- `totalBytesEstimated` (integer) — Whether the `totalBytes` return value is an estimate rather than an exact size.; `1` - The value is an estimate.

```bash
uapi --output=jsonpretty \
  --user=username \
  ExtractInfo \
  progress
```

<a id="extractinfo-start"></a>
### `ExtractInfo::start` — Start extract progress tracking

`GET /execute/ExtractInfo/start` · RO/RW: unspecified · since 136 · requires plugin `ExtractInfo`

This function starts progress tracking for a File Manager extract operation. Note:  The `Fileman::fileop` function with `op=extract` is a single synchronous call to `tar` that reports no progress of its own. This function brackets that call from the outside so that a caller can show real progress.; Call this function first, then call the `Fileman::fileop` function to perform the extract, poll the `ExtractInfo::progress` function while it runs, and call the `ExtractInfo::finish` function when it completes.; The function records the archive's total uncompressed byte size and a baseline snapshot of the destination directory's disk usage, then writes a run-state marker.; This function returns immediately and extracts nothing itself.

**Parameters**

- `archive` · **required** · string · e.g. `/home/user/backups/backup-8.18.2026_12-53-12.tar.gz` — The file path to the backup archive. It must resolve within the cPanel account's home directory.
- `directory` · **required** · string · e.g. `/home/user/restored/backup-8.18.2026_12-53-12` — The destination directory where you want to extract the archive. It must resolve within the cPanel account's home directory.

**Returns** `data`: object

- `started` (boolean) — Always true on success.

```bash
uapi --output=jsonpretty \
  --user=username \
  ExtractInfo \
  start \
  archive='/home/user/backups/backup-8.18.2026_12-53-12.tar.gz' \
  directory='/home/user/restored/backup-8.18.2026_12-53-12'
```

