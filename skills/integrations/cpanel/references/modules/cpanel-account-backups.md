<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — cPanel Account Backups

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Backup**: [`Backup::fullbackup_to_ftp`](#backup-fullbackup-to-ftp), [`Backup::fullbackup_to_homedir`](#backup-fullbackup-to-homedir), [`Backup::fullbackup_to_scp_with_key`](#backup-fullbackup-to-scp-with-key), [`Backup::fullbackup_to_scp_with_password`](#backup-fullbackup-to-scp-with-password), [`Backup::list_backups`](#backup-list-backups)
- **File Restoration**: [`Backup::restore_databases`](#backup-restore-databases), [`Backup::restore_email_filters`](#backup-restore-email-filters), [`Backup::restore_email_forwarders`](#backup-restore-email-forwarders), [`Backup::restore_files`](#backup-restore-files), [`Restore::directory_listing`](#restore-directory-listing), [`Restore::get_users`](#restore-get-users), [`Restore::query_file_info`](#restore-query-file-info), [`Restore::restore_file`](#restore-restore-file)

## Backup

<a id="backup-fullbackup-to-ftp"></a>
### `Backup::fullbackup_to_ftp` — Back up cPanel account via FTP

`GET /execute/Backup/fullbackup_to_ftp` · RW · rollback: none · since cPanel 78

This function creates a full backup to the remote server via File Transfer Protocol (FTP). The system creates a file in the `backup-MM.DD.YYYY_HH-mm-ss.tar.gz` filename format.

**Parameters**

- `host` · **required** · string <hostname> or string <ipv4> · e.g. `example.com` — The remote server's hostname or IP address.
- `password` · **required** · string · e.g. `luggage123456` — The remote server account's password.
- `username` · **required** · string · e.g. `username` — The remote server account's username.
- `directory` · optional · string · e.g. `/public_ftp` — The directory on the remote server that will store the backup. Note:  This value defaults to the remote server account's default login directory.; Enter the directory relative to the FTP user's login directory. For example, enter `/public_ftp` not `/home/username/public_ftp`.
- `email` · optional · string <email> · e.g. `username@example.com` — The email address to receive a confirmation email when the backup completes. Note: The system does **not** provide confirmation if you do **not** pass this parameter.
- `homedir` · optional · string (`include`, `skip`) · default `include` · e.g. `include` — How to manage the home directory in the backup.; `include` — Include the home directory in the backup.; `skip` — Omit the home directory from the backup.
- `port` · optional · integer · default `21` · e.g. `21` — The port number to use during the transfer.
- `variant` · optional · string (`active`, `passive`) · default `active` · e.g. `active` — Whether to use the `active` or `passive` FTP variant to connect to the remote server. For more information about FTP variants, read our How to [Enable FTP Passive Mode](https://go.cpanel.net/HowtoEnableFTPPassiveMode) documentation.; `active` — The FTP server responds to the connection attempt and returns a connection request from a different port to the FTP client.; `passive` — The FTP client initiates connection attempts.

**Returns** `data`: object

- `pid` (string) — The backup's process identifier.

```bash
uapi --output=jsonpretty \
  --user=username \
  Backup \
  fullbackup_to_ftp \
  username='username' \
  password='luggage123456' \
  host='example.com'
```

<a id="backup-fullbackup-to-homedir"></a>
### `Backup::fullbackup_to_homedir` — Back up cPanel account to home directory

`GET /execute/Backup/fullbackup_to_homedir` · RW · rollback: none · since cPanel 78

This function creates a full backup to the user's home directory. The system creates a file in the `backup-MM.DD.YYYY_HH-mm-ss_username.tar.gz` filename format.

**Parameters**

- `email` · optional · string <email> · e.g. `username@example.com` — The email address to receive a confirmation email when the backup process completes. Note: The system does **not** provide confirmation if you do not pass this parameter.
- `homedir` · optional · string (`include`, `skip`) · default `include` · e.g. `include` — How to manage the home directory in the backup.; `include` — Include the home directory in the backup.; `skip` — Omit the home directory from the backup.

**Returns** `data`: object

- `pid` (string) — The backup's process identifier.

```bash
uapi --output=jsonpretty \
  --user=username \
  Backup \
  fullbackup_to_homedir
```

<a id="backup-fullbackup-to-scp-with-key"></a>
### `Backup::fullbackup_to_scp_with_key` — Back up cPanel account via SCP with SSH key

`GET /execute/Backup/fullbackup_to_scp_with_key` · RW · rollback: none · since cPanel 78

This function creates a full backup to a remote server with a private SSH key via the secure copy protocol (scp) command. The system creates a file in the `backup-MM.DD.YYYY_HH-mm-ss_username.tar.gz` filename format.

**Parameters**

- `host` · **required** · string <hostname> or string <ipv4> · e.g. `example.com` — The remote server's hostname or IP address.
- `key_name` · **required** · string · e.g. `examplesshkey` — The SSH key's name. Notes:  To generate a private SSH key, use the UAPI `SSL::generate_key` function.; To import an existing SSH key, use the cPanel API 2 `SSH::importkey` function.
- `key_passphrase` · **required** · string · e.g. `123456luggage` — The SSH key's password.
- `directory` · optional · string · e.g. `/user` — The directory on the remote server that will store the backup. Note: This parameter defaults to the remote server account's default login directory.
- `email` · optional · string <email> · e.g. `username@example.com` — The email address to receive a confirmation email when the backup completes. Note: The system does **not** provide confirmation if you do not pass this parameter.
- `homedir` · optional · string (`include`, `skip`) · default `include` · e.g. `include` — How to manage the home directory in the backup.; `include` — Include the home directory in the backup.; `skip` — Omit the home directory from the backup.
- `port` · optional · integer · default `22` · e.g. `22` — The port to use during the transfer.

**Returns** `data`: object

- `pid` (string) — The backup's process identifier.

```bash
uapi --output=jsonpretty \
  --user=username \
  Backup \
  fullbackup_to_scp_with_key \
  host='example.com' \
  key_name='examplesshkey' \
  key_passphrase='123456luggage'
```

<a id="backup-fullbackup-to-scp-with-password"></a>
### `Backup::fullbackup_to_scp_with_password` — Back up cPanel account via SCP with password

`GET /execute/Backup/fullbackup_to_scp_with_password` · RW · rollback: none · since cPanel 78

This function creates a full backup to a remote server via the secure copy protocol (`scp`) command with a password. The system creates a file in the `backup-MM.DD.YYYY_HH-mm-ss.tar.gz` filename format.

**Parameters**

- `host` · **required** · string <hostname> or string <ipv4> · e.g. `example.com` — The remote server's hostname or IP address.
- `password` · **required** · string · e.g. `luggage123456` — The remote server account's password.
- `username` · **required** · string · e.g. `username` — The remote server account's username.
- `directory` · optional · string · e.g. `/user` — The directory on the remote server that will store the backup. Note: This parameter defaults to the remote server account's default login directory.
- `email` · optional · string <email> · e.g. `username@example.com` — The email address to receive a confirmation email when the backup completes. Note: The system does **not** provide confirmation if you do **not** pass this parameter.
- `homedir` · optional · string (`include`, `skip`) · default `include` · e.g. `include` — How to manage the home directory in the backup.; `include` — Include the home directory in the backup.; `skip` — Omit the home directory from the backup.
- `port` · optional · integer · default `22` · e.g. `22` — The port to use during the transfer.

**Returns** `data`: object

- `pid` (string) — The backup's process identifier.

```bash
uapi --output=jsonpretty \
  --user=username \
  Backup \
  fullbackup_to_scp_with_password \
  host='example.com' \
  username='username' \
  password='luggage123456'
```

<a id="backup-list-backups"></a>
### `Backup::list_backups` — Return backup files

`GET /execute/Backup/list_backups` · RO · since cPanel 11.42

This function lists the account's backup files.

**Returns** `data`: array of string <ISO-8601 Date> — An array of the account's backup files.

```bash
uapi --output=jsonpretty \
  --user=username \
  Backup \
  list_backups
```

## File Restoration

<a id="backup-restore-databases"></a>
### `Backup::restore_databases` — Restore databases

`POST /execute/Backup/restore_databases` · RW · rollback: none · since cPanel 84

This function restores a database's backup files. Important: When the [MySQL Client role](https://go.cpanel.net/howtouseserverprofiles#roles) is disabled, the system also **disables** this function. Note: You **must** pass either the `file` **or** `backup` parameter.

**Parameters**

- `backup` · optional · string — The database backup file to restore. Important: **Only** pass this parameter to restore files already on the server. Note: To restore multiple database backup files, increment the parameter name. For example: `backup-1`, `backup-2`, and `backup-3`.
- `timeout` · optional · integer · default `7200` · e.g. `3600` — The maximum number of seconds to try to restore the file.; `0` - The system will not time out the file restoration.
- `verbose` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return additional information from the `/usr/local/cpanel/logs/cpbackup` log file.; `1` - Return additional information.; `0` - Do **not** return additional information.

**Request body** (`multipart/form-data`)

- `file` (string <binary>) — 

**Returns** `data`: object

- `log_id` (string) — The log file's restoration identification (ID).
- `log_path` (string <path>) — The filepath to the backup restoration's log file.
- `messages` (array of string) — An array of statements about the database's restoration.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  Backup \
  restore_databases
```

<a id="backup-restore-email-filters"></a>
### `Backup::restore_email_filters` — Restore email filters

`POST /execute/Backup/restore_email_filters` · RW · rollback: none · since cPanel 86

This function restores an account's email filters. Important: When the [Receive Mail role](https://go.cpanel.net/howtouseserverprofiles#roles) is disabled, the system also **disables** this function. Note: You **must** use the `backup` parameter when you call this function in one of the following formats: As part of a `multipart/form-data` request body to upload and restore a backup file to the server.; As a query parameter to restore an existing file on the server.

**Parameters**

- `backup` · optional · string — The email filter file to restore. Important: **Only** pass this parameter to restore email filter files that already exist on the server. Note: To restore multiple email filter files, increment the parameter name. For example: `backup-1`, `backup-2`, and `backup-3`.
- `timeout` · optional · integer · default `7200` · e.g. `3600` — The maximum number of seconds to try to restore the file.; `0` - The system will not time out the file restoration.
- `verbose` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return additional information from the `/home/cpuser/.cpanel/logs/restore-email-filters` log files.; `1` - Return additional information.; `0` - Do not return additional information.

**Request body** (`multipart/form-data`)

- `backup` (string <binary>) — 

**Returns** `data`: object

- `log_id` (string) — The log file's restoration identification (ID).
- `log_path` (string <path>) — The filepath to the backup restoration's log file.
- `messages` (array of string) — An array of statements about the database's restoration.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  Backup \
  restore_email_filters
```

<a id="backup-restore-email-forwarders"></a>
### `Backup::restore_email_forwarders` — Restore email forwarders

`POST /execute/Backup/restore_email_forwarders` · RW · rollback: none · since cPanel 86

This function restores an account's email forwarders. Important: When the [Receive Mail role](https://go.cpanel.net/howtouseserverprofiles#roles) is disabled, the system also **disables** this function. Note: You **must** use the `backup` parameter when you call this function in one of the following formats: As part of a `multipart/form-data` request body to upload and restore a backup file to the server. For more information about this structure, read Mozilla's [POST Method](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST) documentation.; As a query parameter to restore an existing file on the server.

**Parameters**

- `backup` · optional · string — The email forwarder file to restore. Important: **Only** pass this parameter to restore email forwarder files that already exist on the server. Note: To restore multiple email filter files, increment the parameter name. For example: `backup-1`, `backup-2`, and `backup-3`.
- `timeout` · optional · integer · default `7200` · e.g. `3600` — The maximum number of seconds to try to restore the file.; `0` - The system will not time out the file restoration.
- `verbose` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return additional information from the `/home/cpuser/.cpanel/logs/restore-email-forwarders` log files.; `1` - Return additional information.; `0` - Do not return additional information.

**Request body** (`multipart/form-data`)

- `backup` (string <binary>) — 

**Returns** `data`: object

- `log_id` (string) — The log file's restoration identification (ID).
- `log_path` (string <path>) — The filepath to the backup restoration's log file.
- `messages` (array of string) — An array of statements about the database's restoration.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  Backup \
  restore_email_forwarders
```

<a id="backup-restore-files"></a>
### `Backup::restore_files` — Restore files

`POST /execute/Backup/restore_files` · RW · rollback: none · since cPanel 86

This function restores an account's files. Important: When the [File Storage role](https://go.cpanel.net/howtouseserverprofiles#roles) is disabled, the system also **disables** this function. Note: You **must** use the `backup` parameter when you call this function in one of the following formats: As part of a `multipart/form-data` request body to upload and restore a backup file to the server. For more information about this structure, read Mozilla's [POST Method](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST) documentation.; As a query parameter to restore an existing file on the server.

**Parameters**

- `backup` · optional · string — The backup file to restore. Important: **Only** pass this parameter to restore backup files that already exist on the server. Note: To restore multiple backup files, increment the parameter name. For example: `backup-1`, `backup-2`, and `backup-3`.
- `directory` · optional · string <path> · e.g. `/home/user/example` — The directory to which to restore the file. The default is the user's `home` directory.
- `timeout` · optional · integer · default `172800` · e.g. `7200` — The maximum number of seconds to try to restore the file.; `0` - The system will not time out the file restoration.
- `verbose` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return additional information from the `/home/cptest/.cpanel/logs/restorefiles` log files.; `1` - Return additional information.; `0` - Do not return additional information.

**Request body** (`multipart/form-data`)

- `backup` (string <binary>) — 

**Returns** `data`: object

- `log_id` (string) — The log file's restoration identification (ID).
- `log_path` (string <path>) — The filepath to the backup restoration's log file.
- `messages` (array of string) — An array of statements about the database's restoration.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  Backup \
  restore_files
```

<a id="restore-directory-listing"></a>
### `Restore::directory_listing` — Return backups in home directory

`GET /execute/Restore/directory_listing` · RO · since cPanel 68

This function lists all of the backup files and directories in the user's home directory. Important: When you disable the [File Storage role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `path` · **required** · string · e.g. `/public_html/` — A path to a subdirectory within the user's home directory, or any level below it. Note: The value of this parameter **must** begin and end with a forward slash (`/`) for security purposes.

**Returns** `data`: array of object — An object that contains information about a specific item stored in the backup.

- *(array of objects)*
  - `conflict` (integer (`0`, `1`)) — Whether a difference exists between the `type` and `onDiskType` returns.; `1` - Conflict exists.; `0` - **No** conflict exists.
  - `exists` (integer (`0`, `1`)) — Whether the file exists in the user's directory or **only** in the backup.; `1` - File exists in the user's directory.; `0` - File exists **only** in the backup.
  - `name` (string) — The name of the file or directory.
  - `onDiskType` (string (`dir`, `file`, `symlink`, `unknown`)) — The item type stored on the disk.; `dir` - A directory.; `file` - A file.; `symlink` - A symlink.; `unknown` - An unknown file type.
  - `type` (string (`dir`, `file`, `symlink`, `unknown`)) — The item type stored in the backup.; `dir` - A directory.; `file` - A file.; `symlink` - A symlink.; `unknown` - An unknown file type.

```bash
uapi --output=jsonpretty \
  --user=username \
  Restore \
  directory_listing \
  path='/public_html/'
```

<a id="restore-get-users"></a>
### `Restore::get_users` — Return cPanel accounts with backup metadata

`GET /execute/Restore/get_users` · RO · since cPanel 72

This function lists a reseller's users that have existing backup metadata. Note: When you disable the [File Storage role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of string <username> — An array of reseller account names.

```bash
uapi --output=jsonpretty \
  --user=username \
  Restore \
  get_users
```

<a id="restore-query-file-info"></a>
### `Restore::query_file_info` — Return backup storage locations

`GET /execute/Restore/query_file_info` · RO · since cPanel 68

This function lists all of an item's backup locations. An item can be a file, a directory, or a symlink. Important: When you disable the [File Storage role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `path` · **required** · string <path> · e.g. `/public_html/index.php` — A file, directory, or symlink in the user's directory tree. Note: The value of this parameter **must** begin with a forward slash (`/`).
- `exists` · optional · integer (`1`, `0`) · default `0` · e.g. `0` — Whether to show the `exist` return, which indicates whether the item exists in the local disk or only in the backup.; `1` — Show the `exist` return's value.; `0` — Do **not** show the `exists` return's value.

**Returns** `data`: array of object — An array of objects containing the item's details.

- *(array of objects)*
  - `backupDate` (string <ISO-8601 Date>) — The date when the system created the backup.
  - `backupID` (string or string (`incremental`) or string (`weekly/incremental`, `monthly/incremental`) or string <ISO-8601 Date>) — The backup's identification.; A date, in `YYYY-MM-DD` format.; `incremental` — An incremental daily backup.; The backup frequency (`weekly` or `monthly`) , a slash character (`/`), and the value `incremental`.; The backu
  - `backupType` (string (`compressed`, `incremental`, `uncompressed`)) — The backup type.; `compressed` —  A compressed tar file.; `incremental` — A full tree of files and directories.; `uncompressed` — An uncompressed tar file.
  - `exists` (integer (`1`, `0`)) — Whether the item (a file, a directory, or a symlink) exists in the local disk or only in the backup.; `1` — The item exists in the local disk.; `0` — The item exists only in the backup.
  - `fileSize` (integer) — The size, in bytes, of the file in the backup.
  - `mtime` (integer <unix_timestamp>) — The file's last modification time.
  - `path` (string <path>) — The identical file path value that the system passed in the function.
  - `type` (string (`dir`, `file`, `symlink`, `unknown`)) — The item type stored in the backup.; `dir` — A directory.; `file` — A file.; `symlink` — A symlink.; `unknown` — An unknown file type.

```bash
uapi --output=jsonpretty \
  --user=username \
  Restore \
  query_file_info \
  path='/public_html/index.php'
```

<a id="restore-restore-file"></a>
### `Restore::restore_file` — Restore file or directory

`GET /execute/Restore/restore_file` · RW · rollback: none · since cPanel 68

This function restores a file or directory from a backup to the file or directory's original location. Important: When you disable the [File Storage role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `backupID` · **required** · string or string (`incremental`) or string (`weekly/incremental`, `monthly/incremental`) or string <ISO-8601 Date> · e.g. `weekly/2017-07-03` — The backup's identification.; `YYYY-MM-DD` — Restore a daily backup from the specified backup date.; `incremental` — Restore a daily incremental backup.; `weekly/YYYY-MM-DD` — Restore a weekly backup from the specified backup date.; `monthly/YYYY-MM-DD` — Restore a monthly backup from the specified backup date.; `weekly/incremental` — Restore a weekly incremental backup.; `monthly/incremental` — Restore a monthly incremental backup.
- `overwrite` · **required** · integer (`1`, `0`) · e.g. `1` — Whether to overwrite the file or directory on the disc with its backup replacement.; `1` — Overwrite the file or directory.; `0` — Do **not** overwrite the file or directory.
- `path` · **required** · string <path> · e.g. `/public_html/index.php` — The absolute file or directory's path, within a backup, that you wish to restore. Important:  The value of this parameter **must** begin with a forward slash (/).; You **must** parse filenames properly to prevent a cross-site scripting (XSS) attack.

**Returns** `data`: object — An object containing the status of the operation.

- `success` (integer (`1`, `0`)) — Whether the `overwrite` parameter succeeded.; `1` — Success.; `0` — Failure.

```bash
uapi --output=jsonpretty \
  --user=username \
  Restore \
  restore_file \
  backupID='weekly/2017-07-03' \
  path='/public_html/index.php' \
  overwrite='1'
```

