<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Website Backups

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **WebsiteBackup**: [`WebsiteBackup::create_backup`](#websitebackup-create-backup), [`WebsiteBackup::delete_backup`](#websitebackup-delete-backup), [`WebsiteBackup::disk_quota_check`](#websitebackup-disk-quota-check), [`WebsiteBackup::extract_backup`](#websitebackup-extract-backup), [`WebsiteBackup::list_backups`](#websitebackup-list-backups), [`WebsiteBackup::list_operations`](#websitebackup-list-operations), [`WebsiteBackup::operation_status`](#websitebackup-operation-status), [`WebsiteBackup::restore_backup`](#websitebackup-restore-backup)

## WebsiteBackup

<a id="websitebackup-create-backup"></a>
### `WebsiteBackup::create_backup` — Start a backup of a website's files and databases

`POST /execute/WebsiteBackup/create_backup` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function starts a backup of the document root of the `domain` parameter and returns an `operationId` return value immediately. Note:  A detached background process writes the archive, so a large backup never holds the request open.; Pass the `operationId` return value to the `WebsiteBackup::operation_status` function to poll progress and read the terminal state. The `WebsiteBackup::list_operations` function recovers the id if the client loses it.; Pre-flight checks run synchronously and fail this call. The account must own the domain, no other backup or restore may be running for the account, each named database must be a safe single path component, and the estimated archive must fit in the remaining disk quota.; The function records anything that goes wrong after it backgrounds the work in the operation log, and reports it through the `WebsiteBackup::operation_status` function.; The operation runs under a two-hour wall-clock cap. Exceeding that cap fails the operation.; This function requires the account's `backup` feature and is unavailable to demo (shared) accounts.

**Request body** (`application/x-www-form-urlencoded`)

- `database` (array of string) — A database to include in the archive.
- `domain` (string) — The website to back up.
- `email` (string) — Address to notify when the backup finishes.

**Returns** `data`: object — The identifier of the background operation this call started.

- `operationId` (string) — Identifier of the detached operation that performs the work.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  create_backup \
  domain=example.com \
  database=user_wordpress \
  database=user_store \
  email=user@example.com
```

<a id="websitebackup-delete-backup"></a>
### `WebsiteBackup::delete_backup` — Delete one or more website backups

`POST /execute/WebsiteBackup/delete_backup` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function deletes the named website backups, removing each archive and its sidecar manifest. Note:  This is a synchronous delete. It starts no operation and nothing needs polling.; The call returns one row per requested id rather than failing as a whole, so a partially successful batch reports each outcome individually.; The call itself fails only when the whole batch is unusable, meaning the `ids` parameter carried no non-empty value at all.; This function returns an array, so UAPI's generic `api.filter_*`, `api.sort_*` and `api.paginate_*` parameters apply, and a caller-supplied sort replaces the default ordering of the `data` return value.; This function requires the account's `backup` feature and is unavailable to demo (shared) accounts.

**Request body** (`application/x-www-form-urlencoded`)

- `ids` (array of string) — Identifier of a backup to delete, as returned by the `WebsiteBackup::list_backups` function.

**Returns** `data`: array of object — One row per **non-empty** requested id.

- *(array of objects)*
  - `error` (string) — Why this id could not be deleted.
  - `id` (string) — The requested backup id this row reports on.
  - `ok` (integer (`1`, `0`)) — Outcome for this id.; `1` - The function deleted the archive and its manifest.; `0` - The delete failed.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  delete_backup \
  ids=example.com-2026.08.18_12-53-12 \
  ids=example.com-2026.08.11_09-04-55
```

<a id="websitebackup-disk-quota-check"></a>
### `WebsiteBackup::disk_quota_check` — Validate website backup disk quota

`GET /execute/WebsiteBackup/disk_quota_check` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function estimates whether a backup of the `domain` parameter fits in the account's remaining disk quota. Note:  The function compares an estimate of the document root's size against the quota the account has left and returns both figures alongside a single verdict, so a caller can warn before starting a backup that would fail.; The estimate is advisory. The `WebsiteBackup::create_backup` function re-checks the quota itself and refuses if the backup no longer fits.; This function is not cheap. It runs `du` over the whole document root, bounded only by a one-hour timeout. Call it when the backup dialog opens, not on a timer.; This function requires the account's `backup` feature.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The website whose backup size to estimate. Note: The account must own this domain.

**Returns** `data`: object — The quota verdict and the two figures it was derived from.

- `availableBytes` (integer) — Bytes of quota the account has left.
- `estimatedBytes` (integer) — Estimated size in bytes of the website files to be archived.
- `ok` (integer (`1`, `0`)) — Whether the estimated backup fits.; `1` - The backup is expected to fit, or the account is unlimited.; `0` - The estimate exceeds the remaining quota.
- `unlimited` (integer (`1`, `0`)) — Whether the account is unconstrained by a disk quota.; `1` - No quota applies, or quotas are not enabled on the server.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  disk_quota_check \
  domain=example.com
```

<a id="websitebackup-extract-backup"></a>
### `WebsiteBackup::extract_backup` — Start extracting a backup's files to a folder

`POST /execute/WebsiteBackup/extract_backup` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function starts copying the website files of the `domain` parameter out of the named backup into a folder under the account's home directory, and returns an `operationId` return value immediately. Note:  Poll the `WebsiteBackup::operation_status` function with the returned id for progress and the terminal state. The `WebsiteBackup::list_operations` function recovers the id if the client loses it.; The extraction is non-destructive. It never overwrites an existing file and never activates anything. It only places a copy of the archived document root under the named folder.; Because nothing live is touched, the per-account backup lock does not gate it and it may run alongside another operation.; Both the folder creation and the extraction run confined to the account's jail wherever the account is normally confined, so a jailed account cannot redirect the write outside its jail.; Pre-flight checks run synchronously and fail this call. The account must own the domain, the archive must exist, and the expanded archive must fit on disk.; The operation runs under a two-hour wall-clock cap.; This function requires the account's `backup` feature and is unavailable to demo (shared) accounts.

**Request body** (`application/x-www-form-urlencoded`)

- `domain` (string) — The website whose files to extract from the backup.
- `id` (string) — Identifier of the backup to extract from, as returned by the `WebsiteBackup::list_backups` function.
- `path` (string) — Destination folder for the extracted files, relative to the account's home directory.

**Returns** `data`: object — The identifier of the background operation this call started.

- `operationId` (string) — Identifier of the detached operation that performs the work.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  extract_backup \
  domain=example.com \
  id=example.com-2026.08.18_12-53-12 \
  path=backup-restore/example.com
```

<a id="websitebackup-list-backups"></a>
### `WebsiteBackup::list_backups` — Return website backups

`GET /execute/WebsiteBackup/list_backups` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function returns the website backups that cover the `domain` parameter, newest first. Note:  The function reads the JSON sidecar manifests under the account's `website_backups` directory and returns one row per manifest that covers the domain, either as the manifest's own domain or as a member of its site list.; The function lists only backups that already exist. The `WebsiteBackup::list_operations` and `WebsiteBackup::operation_status` functions report an operation that is still in flight.; The function skips a manifest that it cannot read rather than failing the call.; This function returns an array, so UAPI's generic `api.filter_*`, `api.sort_*` and `api.paginate_*` parameters apply, and a caller-supplied sort replaces the default ordering of the `data` return value.; This function requires the account's `backup` feature.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The website whose backups to list. Note: The account must own this domain.

**Returns** `data`: array of object — The backups covering the requested domain, newest first.

- *(array of objects)*
  - `createdMs` (integer) — Epoch milliseconds at which the backup was created.
  - `databaseNames` (array of string) — The databases dumped into this archive, so a restore can offer a per-database picker.
  - `id` (string) — Identifier of the backup, in the form `<domain>-<YYYY.MM.DD_HH-MM-SS>`.
  - `includesDatabases` (integer (`1`, `0`)) — Whether the archive holds any database dumps.; `1` - The archive includes databases.; `0` - The archive is website files only.
  - `name` (string) — Display name of the backup.
  - `relativePath` (string) — Path of the archive relative to the account's home directory.
  - `sites` (array of string) — The domains this archive covers.
  - `sizeBytes` (integer) — Size of the archive in bytes.
  - `source` (string (`user`, `system`)) — Who created the backup.; `user` - The account created it.
  - `status` (string) — State of the archive itself.
  - `type` (string (`website`)) — Always `website`.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  list_backups \
  domain=example.com
```

<a id="websitebackup-list-operations"></a>
### `WebsiteBackup::list_operations` — Return running backup operations

`GET /execute/WebsiteBackup/list_operations` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function returns the backup, restore and extract operations still running for the `domain` parameter, most recently updated first. Note:  A client that lost the operation identifier it was polling, after a page reload for example, can use this function to reattach its progress display. The work itself runs in a detached daemon and survives the reload. Only the caller's in-memory id is lost.; Each row is the shape the `WebsiteBackup::operation_status` function returns, plus the `operationId` return value needed to resume polling.; The function lists only operations that can still finish. It omits a terminal operation, meaning one that is `ready` or `failed`, because the `WebsiteBackup::list_backups` function reflects a completed backup. It also omits a non-terminal log whose daemon is no longer alive, which is a job that crashed without writing a terminal frame and can never complete.; This function returns an array, so UAPI's generic `api.filter_*`, `api.sort_*` and `api.paginate_*` parameters apply, and a caller-supplied sort replaces the default ordering of the `data` return value.; This function requires the account's `backup` feature.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The website whose running operations to list. Note: The account must own this domain.

**Returns** `data`: array of object — The still-running operations for the requested domain.

- *(array of objects)*
  - `domain` (string) — The website the operation is running against.
  - `extractPath` (string) — For an `extract` operation, the home-relative destination folder the caller named in the `path` parameter of the `WebsiteBackup::extract_backup` function.
  - `kind` (string (`create`, `restore`, `extract`)) — Which function started the operation.; `create` - The `WebsiteBackup::create_backup` function.; `restore` - The `WebsiteBackup::restore_backup` function.; `extract` - The `WebsiteBackup::extract_backup` function.
  - `operationId` (string) — Identifier to resume polling this operation through the `WebsiteBackup::operation_status` function.
  - `progressPct` (number) — Completion percentage, from 0 to 100.
  - `startedAtMs` (integer) — Epoch milliseconds at which the operation started.
  - `status` (string (`inProgress`)) — Always `inProgress`, because this function does not list terminal operations.
  - `subStatus` (string) — Localized description of the step the operation is currently on.
  - `title` (string) — Localized, user-facing title of the operation, for example `Backing up “example.com”`.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  list_operations \
  domain=example.com
```

<a id="websitebackup-operation-status"></a>
### `WebsiteBackup::operation_status` — Return backup operation status

`GET /execute/WebsiteBackup/operation_status` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function reads the per-operation log for the `operationId` parameter and returns its rolled-up status. Note:  This is the poll endpoint for the asynchronous `WebsiteBackup::create_backup`, `WebsiteBackup::restore_backup` and `WebsiteBackup::extract_backup` functions, each of which returns the id to poll.; A client should keep polling until the `status` return value is no longer `inProgress`. If it loses the id, the `WebsiteBackup::list_operations` function returns the running operations for a domain.; The function reads the log without opening it for append, so polling a live operation never disturbs it.; A job killed mid-write leaves a truncated final frame, and the function still reports every complete frame, including the terminal one.; An unknown or malformed `operationId` fails the call.; This function requires the account's `backup` feature.

**Parameters**

- `operationId` · **required** · string · e.g. `2026-08-18T12:53:12Z.1` — Identifier of the operation to read. Note: The `WebsiteBackup::create_backup`, `WebsiteBackup::restore_backup`, `WebsiteBackup::extract_backup` and `WebsiteBackup::list_operations` functions return this identifier.

**Returns** `data`: object — The operation's rolled-up status.

- `error` (string) — Localized, user-facing description of why the operation failed.
- `kind` (string (`create`, `restore`, `extract`)) — Which function started the operation.; `create` - The `WebsiteBackup::create_backup` function.; `restore` - The `WebsiteBackup::restore_backup` function.; `extract` - The `WebsiteBackup::extract_backup` function.
- `progressPct` (number) — Completion percentage, from 0 to 100.
- `startedAtMs` (integer) — Epoch milliseconds at which the operation started.
- `status` (string (`inProgress`, `ready`, `failed`)) — Rolled-up state of the operation.; `inProgress` - The background child has not yet written a terminal frame.; `ready` - The operation finished successfully.; `failed` - The operation ended in an error.
- `subStatus` (string) — Localized description of the step the operation is currently on.
- `title` (string) — Localized, user-facing title of the operation, for example `Backing up “example.com”`.
- `warnings` (array of string) — Localized descriptions of non-critical problems noted while the operation ran.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  operation_status \
  operationId=2026-08-18T12:53:12Z.1
```

<a id="websitebackup-restore-backup"></a>
### `WebsiteBackup::restore_backup` — Start an in-place restore of a website backup

`POST /execute/WebsiteBackup/restore_backup` · RO/RW: unspecified · since 138 · requires plugin `WebsiteBackup`

This function starts an in-place restore of the `domain` parameter from the named backup and returns an `operationId` return value immediately. Note:  The work runs in a detached background process. Poll the `WebsiteBackup::operation_status` function with the returned id for progress and the terminal state, or recover the id from the `WebsiteBackup::list_operations` function after a page reload.; By default the function restores the document root as a merge. The archive's files overwrite their counterparts, missing files are added, and files created since the backup are kept. The `clean` parameter selects a snapshot restore instead.; Database restoration is opt-out, controlled by the `restore_databases` parameter, and the `database` parameter names the subset to restore.; The function resets a restored database to exactly its backed-up state, dropping its existing objects and re-importing the dump, so objects created after the backup do not survive. It takes a rollback snapshot first, so a failed restore returns the database to its previous contents and reports failure rather than destroying live data.; Pre-flight checks run synchronously and fail this call. The account must own the domain, the archive must exist, each named database must be recorded in the archive's manifest, no other backup or restore may be running for the account, and the expanded archive must fit on disk.; The operation runs under a six-hour wall-clock cap.; This function requires the account's `backup` feature and is unavailable to demo (shared) accounts.

**Request body** (`application/x-www-form-urlencoded`)

- `clean` (integer) — Send the integer `1` to restore the website files as a snapshot, which rebuilds the document root from the archive and removes anything added since the backup.
- `database` (array of string) — A database from the archive to restore.
- `domain` (string) — The website to restore in place.
- `id` (string) — Identifier of the backup to restore, as returned by the `WebsiteBackup::list_backups` function.
- `restore_databases` (integer) — Send the integer `0` to restore website files only and leave every database untouched.

**Returns** `data`: object — The identifier of the background operation this call started.

- `operationId` (string) — Identifier of the detached operation that performs the work.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebsiteBackup \
  restore_backup \
  domain=example.com \
  id=example.com-2026.08.18_12-53-12 \
  clean=1 \
  database=user_wordpress \
  database=user_store
```

