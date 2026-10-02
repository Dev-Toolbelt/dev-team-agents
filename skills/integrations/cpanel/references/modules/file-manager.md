<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — File Manager

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Trash**: [`Trash::remove`](#trash-remove), [`Trash::usage`](#trash-usage)

## Trash

<a id="trash-remove"></a>
### `Trash::remove` — Delete item from Trash

`POST /execute/Trash/remove` · RO/RW: unspecified · since 136 · requires plugin `Trash`

This function permanently deletes a single item from the `.trash` directory in the current cPanel account's home directory. Note: Unlike the `Fileman::fileop` function with `op=unlink`, this function uses a non-safe recursive delete, so it removes permission-locked entries instead of skipping them silently and reporting them as deleted. Such an entry might be a `0444` file or a `0555` subdirectory preserved from a backup. If the target is already absent, the function reports an idempotent success rather than an error. On success, it also prunes the stale line for the removed item, if there is one, from the trash's restore map.

**Parameters**

- `path` · **required** · string · e.g. `/.trash/backup-7.14.2026_16-35-25` — The path of the item to permanently delete. Note: This parameter must resolve strictly within the `.trash` directory in the account's home directory. A leading slash is read relative to the home directory, so `/.trash/backup-7.14.2026_16-35-25` is the expected form. The function resolves symlinks and `..` traversal before it runs that confinement check, and the trash directory itself can never be the target.

**Returns** `data`: object

- `alreadyGone` (boolean) — True when the target was already absent, which the function reports as an idempotent success.
- `removed` (boolean) — Always true on success.

```bash
uapi --output=jsonpretty \
  --user=username \
  Trash \
  remove \
  path=/.trash/backup-7.14.2026_16-35-25_alonglonglon
```

<a id="trash-usage"></a>
### `Trash::usage` — Report the disk space used by the trash directory

`GET /execute/Trash/usage` · RO/RW: unspecified · since 136 · requires plugin `Trash`

Report the current apparent size of the trash directory's contents. Returns whether the trash exists, the total apparent bytes calculated by summing each entry's lstat size, and the number of items in the trash. Excludes the root-level .trash_restore bookkeeping file. Does not walk the account's home directory or follow symbolic links outside the trash. even on large accounts.

**Returns** `data`: object

- `bytes` (integer) — Total apparent size of the trash contents, calculated by summing each entry's lstat size in bytes.
- `exists` (integer) — Whether the trash directory exists.
- `items` (integer) — Number of items in the trash, excluding the .trash_restore bookkeeping file.

```bash
uapi --output=jsonpretty \
  --user=username \
  Trash \
  usage
```

