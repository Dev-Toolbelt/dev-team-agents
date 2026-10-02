<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — PostgreSQL

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **PostgreSQL Database Management**: [`Postgresql::create_database`](#postgresql-create-database), [`Postgresql::delete_database`](#postgresql-delete-database), [`Postgresql::get_restrictions`](#postgresql-get-restrictions), [`Postgresql::list_databases`](#postgresql-list-databases), [`Postgresql::rename_database`](#postgresql-rename-database)
- **PostgreSQL User Management**: [`Postgresql::create_user`](#postgresql-create-user), [`Postgresql::delete_user`](#postgresql-delete-user), [`Postgresql::grant_all_privileges`](#postgresql-grant-all-privileges), [`Postgresql::list_users`](#postgresql-list-users), [`Postgresql::rename_user`](#postgresql-rename-user), [`Postgresql::rename_user_no_password`](#postgresql-rename-user-no-password), [`Postgresql::revoke_all_privileges`](#postgresql-revoke-all-privileges), [`Postgresql::set_password`](#postgresql-set-password), [`Postgresql::update_privileges`](#postgresql-update-privileges)

## PostgreSQL Database Management

<a id="postgresql-create-database"></a>
### `Postgresql::create_database` — Create PostgreSQL database

`GET /execute/Postgresql/create_database` · RW · rollback: none · since cPanel 11.42

This function creates a PostgreSQL® database. Important: When you disable the [PostgreSQL role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `database` — The database's name. **Note**: If database prefixing is enabled, this parameter **must** include the database prefix for the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  create_database \
  name='database'
```

<a id="postgresql-delete-database"></a>
### `Postgresql::delete_database` — Delete PostgreSQL database

`GET /execute/Postgresql/delete_database` · RW · rollback: none · since cPanel 54

This function deletes a PostgreSQL® database. Important: When you disable the [Postgres role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `database` — The database's name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  delete_database \
  name='database'
```

<a id="postgresql-get-restrictions"></a>
### `Postgresql::get_restrictions` — Return PostgreSQL name length restrictions

`GET /execute/Postgresql/get_restrictions` · RO · since cPanel 11.42

This function retrieves the PostgreSQL® user and database name length restrictions. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

- `max_database_name_length` (integer) — The maximum length of a database name.
- `max_username_length` (integer) — The maximum length of a database username.
- `prefix` (string) — If database prefixing is enabled, this return outputs the database prefix.

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  get_restrictions
```

<a id="postgresql-list-databases"></a>
### `Postgresql::list_databases` — Return PostgreSQL databases

`GET /execute/Postgresql/list_databases` · RO · since cPanel 84

This function lists an account's PostgreSQL® databases. Important: When you disable the [*Postgres* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `database` (string) — The database name.
  - `disk_usage` (integer) — The disk space that the database uses, in bytes.
  - `users` (array of string) — An array of database usernames.

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  list_databases
```

<a id="postgresql-rename-database"></a>
### `Postgresql::rename_database` — Update PostgreSQL database name

`GET /execute/Postgresql/rename_database` · RW · rollback: none · since cPanel 11.42

This function renames a PostgreSQL® database. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `newname` · **required** · string · e.g. `database2` — The database's new name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.
- `oldname` · **required** · string · e.g. `database` — The database's current name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  rename_database \
  oldname='database' \
  newname='database2'
```

## PostgreSQL User Management

<a id="postgresql-create-user"></a>
### `Postgresql::create_user` — Create PostgreSQL user

`GET /execute/Postgresql/create_user` · RW · rollback: none · since cPanel 11.42

This function creates a PostgreSQL® database user. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `dbuser` — The database user's name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.
- `password` · **required** · string · e.g. `123456luggage` — The new user's password.

**Returns** `data`: integer

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  create_user \
  name='dbuser' \
  password='123456luggage'
```

<a id="postgresql-delete-user"></a>
### `Postgresql::delete_user` — Delete PostgreSQL user

`GET /execute/Postgresql/delete_user` · RW · rollback: none · since cPanel 84

This function deletes a PostgreSQL® user. Important: When you disable the [PostgreSQL role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `example` — The PostgreSQL user's name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  delete_user \
  name='example'
```

<a id="postgresql-grant-all-privileges"></a>
### `Postgresql::grant_all_privileges` — Enable all user privileges on PostgreSQL database

`GET /execute/Postgresql/grant_all_privileges` · RW · rollback: none · since cPanel 11.42

This function grants all privileges for a PostgreSQL® database to a database user. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `database` · **required** · string · e.g. `example_database` — The database's name. **Note** If database prefixing is enabled, this value **must** include the database prefix for the account.
- `user` · **required** · string · e.g. `example_dbuser` — The database user's name. **Note** If database prefixing is enabled, this value **must** include the database prefix for the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  grant_all_privileges \
  user='example_dbuser' \
  database='example_database'
```

<a id="postgresql-list-users"></a>
### `Postgresql::list_users` — Return PostgreSQL users

`GET /execute/Postgresql/list_users` · RO · since cPanel 84

This function lists an account's PostgreSQL® database users. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of string — An array of strings which are PostgreSQL database usernames.

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  list_users
```

<a id="postgresql-rename-user"></a>
### `Postgresql::rename_user` — Update PostgreSQL username

`GET /execute/Postgresql/rename_user` · RW · rollback: none · since cPanel 11.42

This function renames a PostgreSQL® database user. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `newname` · **required** · string · e.g. `dbuser2` — The database user's new name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.
- `oldname` · **required** · string · e.g. `dbuser` — The database user's current name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.
- `password` · **required** · string · e.g. `123456luggage` — The database user's new password.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  rename_user \
  oldname='dbuser' \
  newname='dbuser2' \
  password='123456luggage'
```

<a id="postgresql-rename-user-no-password"></a>
### `Postgresql::rename_user_no_password` — Update PostgreSQL username without password

`GET /execute/Postgresql/rename_user_no_password` · RW · rollback: none · since cPanel 11.42

This function renames a PostgreSQL® database user. Warning:  If you rename a PostgreSQL user, you **must** set the password for the database user. This is required because of the md5 hash that PostgreSQL creates to store user passwords.; We **strongly** recommend that you use the `Postgresql::rename_user function` instead of this one. Important: When you disable the  [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `newname` · **required** · string · e.g. `dbuser2` — The database user's new name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.
- `oldname` · **required** · string · e.g. `dbuser` — The database user's current name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  rename_user_no_password \
  oldname='dbuser' \
  newname='dbuser2'
```

<a id="postgresql-revoke-all-privileges"></a>
### `Postgresql::revoke_all_privileges` — Remove PostgreSQL user privileges

`GET /execute/Postgresql/revoke_all_privileges` · RW · rollback: none · since cPanel 11.42

This function revokes all privileges for a PostgreSQL® database from a database user. Important: When you disable the [*PostgreSQL* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `database` · **required** · string · e.g. `example_database` — The database's name. **Note** If database prefixing is enabled, this value **must** include the database prefix for the account.
- `user` · **required** · string · e.g. `example_dbuser` — The database user's name. **Note** If database prefixing is enabled, this value **must** include the database prefix for the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  revoke_all_privileges \
  user='example_dbuser' \
  database='example_database'
```

<a id="postgresql-set-password"></a>
### `Postgresql::set_password` — Update PostgreSQL user password

`GET /execute/Postgresql/set_password` · RW · rollback: none · since cPanel 11.42

This function changes a PostgreSQL® database user's password. Important: When you disable the [Postgres role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `password` · **required** · string · e.g. `12345luggage` — The user's new password.
- `user` · **required** · string · e.g. `dbuser` — The database user's name. Note: If database prefixing is enabled, this parameter **must** include the database prefix for the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  set_password \
  user='dbuser' \
  password='12345luggage'
```

<a id="postgresql-update-privileges"></a>
### `Postgresql::update_privileges` — Update PostgreSQL® privileges

`GET /execute/Postgresql/update_privileges` · RW · rollback: none · since cPanel 84

This function synchronizes PostgreSQL® database user privileges on an account. Some versions of PostgreSQL are ANSI SQL-92 compliant and do not support recursive grants, wildcard grants, or future grants. If you use phpPgAdmin, or manually create new tables, and you want multiple PostgreSQL users to access your PostgreSQL tables, you may either call this API function or click _Synchronize Grants_ in the _PostgreSQL Databases_ interface (_Home >> Databases >> PostgreSQL Databases_) after you add a table. Important: When you disable the [PostgreSQL role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Postgresql \
  update_privileges
```

