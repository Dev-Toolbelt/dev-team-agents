<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Directory Management

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Directory Indexes**: [`DirectoryIndexes::get_indexing`](#directoryindexes-get-indexing), [`DirectoryIndexes::list_directories`](#directoryindexes-list-directories), [`DirectoryIndexes::set_indexing`](#directoryindexes-set-indexing)
- **Directory Privacy**: [`DirectoryPrivacy::add_user`](#directoryprivacy-add-user), [`DirectoryPrivacy::configure_directory_protection`](#directoryprivacy-configure-directory-protection), [`DirectoryPrivacy::delete_user`](#directoryprivacy-delete-user), [`DirectoryPrivacy::is_directory_protected`](#directoryprivacy-is-directory-protected), [`DirectoryPrivacy::list_directories`](#directoryprivacy-list-directories), [`DirectoryPrivacy::list_users`](#directoryprivacy-list-users)
- **Directory Protection**: [`DirectoryProtection::list_directories`](#directoryprotection-list-directories)

## Directory Indexes

<a id="directoryindexes-get-indexing"></a>
### `DirectoryIndexes::get_indexing` — Return directory indexing settings

`GET /execute/DirectoryIndexes/get_indexing` · RO · since cPanel 88

This function returns the directory indexing settings for a directory on the cPanel account and its subdirectories.

**Parameters**

- `dir` · **required** · string · e.g. `/home/example/example.com` — The directory for which to check the indexing type.

**Returns** `data`: string — The directory's indexing type.; standard  The directory uses directory indexing with standard formatting.; disabled  The directory doesn't use directory indexing.; inherit  The directory uses the system's default setting

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryIndexes \
  get_indexing \
  dir='/home/example/example.com'
```

<a id="directoryindexes-list-directories"></a>
### `DirectoryIndexes::list_directories` — Return subdirectories directory indexing settings

`GET /execute/DirectoryIndexes/list_directories` · RO · rollback: none · since cPanel 88

This function returns the [directory indexing](https://go.cpanel.net/cpaneldocsIndexes) settings of the subdirectories in a directory.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The absolute path of the directory for which to return indexing information.

**Returns** `data`: object

- `children` (array of object) — Subdirectories and their indexing information.
  - *(array of objects)*
    - `path` (string <path>) — The subdirectory's absolute path.
    - `state` (object) — The subdirectory's indexing information.
- `current` (object) — The user's current directory and its indexing information.
  - `path` (string <path>) — The current directory's absolute path.
  - `state` (object) — The current directory's indexing information.
- `home` (object) — The user's home directory and its indexing information.
  - `path` (string <path>) — The home directory's absolute path.
  - `state` (object) — An object containing the home directory's indexing information.
- `parent` (object) — The current directory’s parent directory and its indexing information.
  - `path` (string <path>) — The parent directory's absolute path.
  - `state` (object) — The parent directory's indexing information.

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryIndexes \
  list_directories \
  dir='/home/example/example.com'
```

<a id="directoryindexes-set-indexing"></a>
### `DirectoryIndexes::set_indexing` — Update directory indexing settings

`GET /execute/DirectoryIndexes/set_indexing` · RW · rollback: clean · since cPanel 88

This function configures the [directory indexing](https://go.cpanel.net/cpaneldocsIndexes) settings for a directory on the cPanel account.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The directory for which to manage directory indexing.
- `type` · **required** · string (`standard`, `disabled`, `inherit`, `fancy`) · e.g. `inherit` — The type of directory indexing.; `standard` — The directory uses directory indexing with standard formatting.; `disabled` — The directory doesn't use directory indexing.; `inherit` — The directory uses the system's default settings.; `fancy` — The directory uses directory indexing with Apache FancyIndexing directive. The directory will include additional information such as file size and the date of the file's last update.

**Returns** `data`: string (`standard`, `disabled`, `inherit`, `fancy`) — The directory's indexing type.; `standard` — The directory uses directory indexing with standard formatting.; `disabled` — The directory doesn't use directory indexing.; `inherit` — The directory uses the system's defaul

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryIndexes \
  set_indexing \
  dir='/home/example/example.com' \
  type='inherit'
```

## Directory Privacy

<a id="directoryprivacy-add-user"></a>
### `DirectoryPrivacy::add_user` — Add authorized user for protected directory

`GET /execute/DirectoryPrivacy/add_user` · RW · rollback: none · since cPanel 88

This function adds a user who can access a protected directory on the cPanel account.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The directory to add users to.
- `password` · **required** · string · e.g. `123456luggage` — The password for the user.
- `user` · **required** · string · e.g. `example1` — The username of the user who can access the directory.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryPrivacy \
  add_user \
  dir='/home/example/example.com' \
  user='example1' \
  password='123456luggage'
```

<a id="directoryprivacy-configure-directory-protection"></a>
### `DirectoryPrivacy::configure_directory_protection` — Enable or disable protected directory

`GET /execute/DirectoryPrivacy/configure_directory_protection` · RW · rollback: clean · since cPanel 88

This function enables or disables password protection for a directory on the cPanel account.

**Parameters**

- `authname` · **required** · string · e.g. `protectandserve` — The name of the directory protection authorization instance. Note: **Only** use this parameter when you enable password protection.
- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The absolute or relative directory path for which to enable or disable password protection.
- `enabled` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to enable password protection for the directory.; `1` - Enable.; `0` - Disable.

**Returns** `data`: object

- `auth_name` (string) — The authentication resource name.
- `auth_type` (string (`Basic`, `None`)) — The directory's authentication type.; `Basic`; `None`
- `passwd_file` (string <path>) — The path to the directory's password file.
- `protected` (integer (`0`, `1`)) — Whether the directory uses password protection.; `1` - Protected.; `0` - **Not** protected.

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryPrivacy \
  configure_directory_protection \
  dir='/home/example/example.com' \
  enabled='1' \
  authname='protectandserve'
```

<a id="directoryprivacy-delete-user"></a>
### `DirectoryPrivacy::delete_user` — Delete authorized user for protected directory

`GET /execute/DirectoryPrivacy/delete_user` · RW · rollback: none · since cPanel 88

This function deletes a user who can access a protected directory on the cPanel account.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The absolute directory path on the cPanel account from which to remove a user.
- `user` · **required** · string <username> · e.g. `example1` — The username to remove from the directory.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryPrivacy \
  delete_user \
  dir='/home/example/example.com' \
  user='example1'
```

<a id="directoryprivacy-is-directory-protected"></a>
### `DirectoryPrivacy::is_directory_protected` — Return whether directory uses password protection

`GET /execute/DirectoryPrivacy/is_directory_protected` · RO · rollback: none · since cPanel 88

This function confirms whether a directory uses password protection.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The absolute directory path on the cPanel account to check for password protection.

**Returns** `data`: object

- `auth_name` (string) — The authentication resource name.
- `auth_type` (string (`Basic`, `None`)) — The directory's authentication type.; `Basic`; `None`
- `passwd_file` (string <path>) — The path to the directory's password file.
- `protected` (integer (`0`, `1`)) — Whether the directory uses password protection.; `1` - Protected.; `0` - **Not** protected.

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryPrivacy \
  is_directory_protected \
  dir='/home/example/example.com'
```

<a id="directoryprivacy-list-directories"></a>
### `DirectoryPrivacy::list_directories` — Return privacy status of subdirectories

`GET /execute/DirectoryPrivacy/list_directories` · RO · rollback: none · since cPanel 88

This function returns the privacy status of the subdirectories in a directory.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The directory path for which to return the subdirectories' privacy information.

**Returns** `data`: object

- `children` (array of object) — An array of objects containing subdirectories and their privacy information.
  - *(array of objects)*
    - `path` (string <path>) — The subdirectory's directory path.
    - `state` (object) — The subdirectory's privacy information.
- `current` (object) — The user's current directory and its privacy information.
  - `path` (string <path>) — The current directory's path.
  - `state` (object) — The current subdirectory's privacy information.
- `home` (object) — The user's home directory and its privacy information.
  - `path` (string <path>) — The home directory's absolute path.
  - `state` (object) — The home directory's privacy information.
- `parent` (object) — The parent directory of the current directory and its privacy information.
  - `path` (string <path>) — The parent directory's absolute directory path.
  - `state` (object) — The parent directory's privacy information.

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryPrivacy \
  list_directories \
  dir='/home/example/example.com'
```

<a id="directoryprivacy-list-users"></a>
### `DirectoryPrivacy::list_users` — Return authorized users for protected directory

`GET /execute/DirectoryPrivacy/list_users` · RO · rollback: none · since cPanel 88

This function returns the users who can access a password-protected directory on the cPanel account.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The password-protected directory for which to return authorized users.

**Returns** `data`: array of string — list of users who can access the directory.

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryPrivacy \
  list_users \
  dir='/home/example/example.com'
```

## Directory Protection

<a id="directoryprotection-list-directories"></a>
### `DirectoryProtection::list_directories` — Return Directory Protection settings

`GET /execute/DirectoryProtection/list_directories` · RO · rollback: none · since cPanel 88

This function returns the [leech protection](https://go.cpanel.net/cpaneldocsLeechProtection) settings of the subdirectories in a directory.

**Parameters**

- `dir` · **required** · string <path> · e.g. `/home/example/example.com` — The absolute or relative file path in the user's `home` directory for which to return leech protection information.

**Returns** `data`: object

- `children` (array of object) — A list of subdirectories and their leech protection information.
  - *(array of objects)*
    - `path` (string <path>) — The subdirectory's absolute directory path.
    - `state` (object) — A object containing the subdirectory's leech protection information.
- `current` (object) — The user's current directory and its leech protection information.
  - `path` (string <path>) — The current directory's absolute file path.
  - `state` (object) — An object containing the current directory's leech protection information.
- `home` (object) — The user's `home` directory and its leech protection information.
  - `path` (string <path>) — The `home` directory's absolute directory path.
  - `state` (object) — A object containing the `home` directory's leech protection information.
- `parent` (object) — The parent directory of the current directory and its leech protection information.
  - `path` (string <path>) — The parent directory's absolute directory path.
  - `state` (object) — An object containing the parent directory's leech protection information.

```bash
uapi --output=jsonpretty \
  --user=username \
  DirectoryProtection \
  list_directories \
  dir='/home/example/example.com'
```

