<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — MySQL and MariaDB

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Remote Databases**: [`Mysql::add_host`](#mysql-add-host), [`Mysql::add_host_note`](#mysql-add-host-note), [`Mysql::delete_host`](#mysql-delete-host), [`Mysql::get_host_notes`](#mysql-get-host-notes)
- **Database Management**: [`Mysql::check_database`](#mysql-check-database), [`Mysql::create_database`](#mysql-create-database), [`Mysql::delete_database`](#mysql-delete-database), [`Mysql::dump_database_schema`](#mysql-dump-database-schema), [`Mysql::list_databases`](#mysql-list-databases), [`Mysql::rename_database`](#mysql-rename-database), [`Mysql::repair_database`](#mysql-repair-database), [`Mysql::setup_db_and_user`](#mysql-setup-db-and-user)
- **User Management**: [`Mysql::create_user`](#mysql-create-user), [`Mysql::delete_user`](#mysql-delete-user), [`Mysql::get_privileges_on_database`](#mysql-get-privileges-on-database), [`Mysql::get_restrictions`](#mysql-get-restrictions), [`Mysql::list_routines`](#mysql-list-routines), [`Mysql::list_users`](#mysql-list-users), [`Mysql::rename_user`](#mysql-rename-user), [`Mysql::revoke_access_to_database`](#mysql-revoke-access-to-database), [`Mysql::set_password`](#mysql-set-password), [`Mysql::set_privileges_on_database`](#mysql-set-privileges-on-database), [`Mysql::update_privileges`](#mysql-update-privileges)
- **Database Information**: [`Mysql::get_server_information`](#mysql-get-server-information), [`Mysql::locate_server`](#mysql-locate-server)

## Remote Databases

<a id="mysql-add-host"></a>
### `Mysql::add_host` — Enable remote MySQL host access

`GET /execute/Mysql/add_host` · RW · rollback: none · since cPanel 11.52

This function authorizes a remote MySQL® host to access the account's databases. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `host` · **required** · string or string <domain> or string <ipv4> — The remote MySQL server's hostname or IP address. You may use the following IP address formats: `192.168.1.6` — IP address.; `192.168.%.%` — Range with the percent (%) symbol as a wildcard.; `192.168.0.0/16` — Range in CIDR format.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  add_host \
  host='192.168.1.6'
```

<a id="mysql-add-host-note"></a>
### `Mysql::add_host_note` — Add remote MySQL host note

`GET /execute/Mysql/add_host_note` · RW · rollback: none · since cPanel 74

This function adds a note about a remote MySQL® server. Important:  If you attempt to add a note to an unauthorized remote MySQL server, the function will fail.; When you **disable** the [MySQL role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `host` · **required** · string or string <domain> or string <ipv4> — The remote MySQL server's hostname or IP address. You may use the following IP address formats: `192.168.1.6` — IP address.; `192.168.%.%` — Range with the percent (%) symbol as a wildcard.; `192.168.0.0/16` — Range in CIDR format.
- `note` · **required** · string · e.g. `A remote mysql server for storing my data` — note that describes the remote MySQL server.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  add_host_note \
  host='192.168.1.6' \
  note='A remote mysql server for storing my data'
```

<a id="mysql-delete-host"></a>
### `Mysql::delete_host` — Disable remote MySQL host access

`GET /execute/Mysql/delete_host` · RW · rollback: none · since cPanel 11.52

This function removes a remote MySQL® host's access to the account's databases. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is not already configured, the system **disables** this function.

**Parameters**

- `host` · **required** · string · e.g. `remote.example.com` — The remote MySQL server's hostname, IP Address, or IP address range. Note: You may use the following IP address formats: 192.168.1.6 — IP address. 192.168.%.% — Range with the percent (%) symbol as a wildcard. 192.168.0.0/16 — Range in CIDR format.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  delete_host \
  host='remote.example.com'
```

<a id="mysql-get-host-notes"></a>
### `Mysql::get_host_notes` — Return remote MySQL host notes

`GET /execute/Mysql/get_host_notes` · RO · since cPanel 74

This function returns the notes associated with the account's remote MySQL® hosts. Important: When you disable the [*MySQL/MariaDB* role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Returns** `data`: object — The keys are remote MySQL hostnames or IP addresses and values are their corresponding notes.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  get_host_notes
```

## Database Management

<a id="mysql-check-database"></a>
### `Mysql::check_database` — Validate MySQL database integrity

`GET /execute/Mysql/check_database` · RW · rollback: none · since cPanel 54

This function checks for errors in all of the tables in a MySQL® database. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `example_test` — The database's name.

**Returns** `data`: array of object — An array that contains a response message for each of a database's tables in sequence.

- *(array of objects)*
  - `msg_text` (string) — The message's contents.
  - `msg_type` (string (`status`, `error`, `info`, `note`, `warning`)) — The type of message.; `status`; `error`; `info`; `note`; `warning` Note: For more information, read [MySQL's `CHECK TABLE` documentation](http://dev.mysql.com/doc/refman/5.7/en/check-table.html).
  - `table` (string) — The table's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  check_database \
  name='example_test'
```

<a id="mysql-create-database"></a>
### `Mysql::create_database` — Create MySQL database

`GET /execute/Mysql/create_database` · RW · rollback: none · since cPanel 11.44

This function creates a MySQL® database. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/howtouseserverprofiles#roles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `newdb` — The new database's name.
- `prefix-size` · optional · integer (`8`, `16`) · default `16` · e.g. `16` — The desired prefix size.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  create_database \
  name='newdb'
```

<a id="mysql-delete-database"></a>
### `Mysql::delete_database` — Delete MySQL database

`GET /execute/Mysql/delete_database` · RW · rollback: none · since cPanel 11.52

This function deletes a MySQL® database. Important: when you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles#roles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `example` — The database's name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  delete_database \
  name='example'
```

<a id="mysql-dump-database-schema"></a>
### `Mysql::dump_database_schema` — Return MySQL database schema

`GET /execute/Mysql/dump_database_schema` · RO · since cPanel 82

This function returns a string that you can give to MySQL® to recreate a particular database’s schema. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** configured, the system **disables** this function.

**Parameters**

- `dbname` · **required** · string · e.g. `username_example_db` — The database's name.

**Returns** `data`: string — The string to give to MySQL.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  dump_database_schema \
  dbname='username_example_db'
```

<a id="mysql-list-databases"></a>
### `Mysql::list_databases` — Return MySQL databases

`GET /execute/Mysql/list_databases` · RO · since cPanel 82

This function lists an account's MySQL® databases. Important: When you disable the [*MySQL/MariaDB* role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** configured, the system **disables** this function.

**Returns** `data`: array of object — Information about the database.

- *(array of objects)*
  - `database` (string) — The database name.
  - `disk_usage` (integer) — The disk space that the database uses, in bytes.
  - `users` (array of string) — A list of database usernames.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  list_databases
```

<a id="mysql-rename-database"></a>
### `Mysql::rename_database` — Update MySQL database name

`GET /execute/Mysql/rename_database` · RW · rollback: none · since cPanel 11.44

This function renames a MySQL® database. MySQL does not allow you to rename a database. When cPanel & WHM "renames" a database, the system performs the following steps: 1. The system creates a new database. 2. The system moves data from the old database to the new database. 3. The system recreates grants and stored code in the new database. 4. The system deletes the old database and its grants. Warning:  It is potentially dangerous to rename a MySQL database. We **strongly** recommend that you perform a backup of the database before you attempt to rename it.; If any of the first three steps fail, the system returns an error and attempts to restore the database's original state. If the restoration process fails, the API function's error response describes these additional failures.; In rare cases, the system creates the second database successfully, but fails to delete the old database or grants. The system treats the rename action as a success; however, the API function returns warnings that describe the failure to delete the old database or grants. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `newname` · **required** · string · e.g. `newlyrenamed` — The database's new name. Important:  If database prefixing is enabled, you **must** prefix this value with the account prefix and an underscore (`_`). For example, for the `dbuser` database on the user cPanel account, pass in a value of `user_dbuser`.; The maximum length of the database name is 64 characters. However, due to the method that cPanel & WHM uses to store MySQL database names, each underscore character requires two characters of that limit. Therefore, if you enable database prefixing, the maximum length of the database name is 63 characters, which includes both the database prefix and the underscore character. Each additional underscore requires another two characters of that limit.
- `oldname` · **required** · string · e.g. `mydb` — The database's current name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  rename_database \
  oldname='mydb' \
  newname='newlyrenamed'
```

<a id="mysql-repair-database"></a>
### `Mysql::repair_database` — Repair MySQL database tables

`GET /execute/Mysql/repair_database` · RW · rollback: none · since cPanel 54

This function repairs all of the tables in a MySQL® database. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `example_db` — The database's name.

**Returns** `data`: array of object — An array of objects containing a response message for each of a database's table in sequence.

- *(array of objects)*
  - `msg_text` (string) — The message's contents.
  - `msg_type` (string (`status`, `error`, `info`, `note`, `warning`)) — The type of message.; `status`; `error`; `info`; `note`; `warning` Note: For more information, read [MySQL's REPAIR TABLE](http://dev.mysql.com/doc/refman/5.7/en/repair-table.html) documentation.
  - `table` (string) — The table's name in the database.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  repair_database \
  name='example_db'
```

<a id="mysql-setup-db-and-user"></a>
### `Mysql::setup_db_and_user` — Create a randomly named MySQL username/database set.

`GET /execute/Mysql/setup_db_and_user` · RW · rollback: none · since cPanel 11.116

This function creates a randomly named MySQL® database and user. This allows a 3rdparty tool to create its own DB without needing any knowledge of cPanel internals such as quotas or other limits. These will simply be passed back as an error. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/howtouseserverprofiles#roles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `prefix` · optional · string · e.g. `wp` — An optional string to prepend to the randomly generated database name. This is in addition to the cPanel user which will appear prior to this. The prefix should be 6 characters or less and be only alphanumeric characters. WARNING: longer prexies lead to less entropy in the random username. Keep it short if you can!

**Returns** `data`: object

- `database` (string <database name>) — The randomized name of the database created.
- `database_user` (string <database username>) — The randomized username assigned to the database.
- `database_user_password` (string <password>) — A randomly generated password intended to be maximally randomized.
- `hostname` (string <hostname>) — The hostname to connect to from within the server to connect to the MySQL server
- `port` (string <unix-port>) — The port to connect to from within the server to connect to the MySQL server

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  setup_db_and_user \
  prefix='wp'
```

## User Management

<a id="mysql-create-user"></a>
### `Mysql::create_user` — Create MySQL user

`GET /execute/Mysql/create_user` · RW · rollback: none · since cPanel 11.44

This function creates a MySQL® database user. Important: When you **disable** the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is not already configured, the system disables this function.

**Parameters**

- `name` · **required** · string · e.g. `dbuser` — A valid database username. Important: ==== To learn more about database username limits, check your database type: MySQL 5.6 ---- MySQL version 5.6 limits the database username to 16 characters. The server uses the first nine characters of this limit for the database prefix. The database prefix uses the cPanel account's username and an underscore (`_`). The server only applies the first eight characters of the cPanel account's username. For example: A `db_` database prefix allows MySQL usernames of up to 13 characters.; An `example_` database prefix allows MySQL usernames of up to eight characters. MySQL 5.7+ ---- MySQL versions 5.7 and later limit the database username to 32 characters. The server uses the first nine characters of this limit for the database prefix. The database prefix uses the cPanel account's username and an underscore (`_`). The server only applies the first eight characters of the cPanel account's username. For example: A `db_` database prefix allows MySQL usernames of up to 29 characters.; An `example_` database prefix allows MySQL usernames of up to 24 characters. MariaDB ---- MariaDB limits the database username to 47 characters. The server uses the first nine characters of this limit for the database prefix. The database prefix uses the cPanel account's username and an underscore (`_`). The server only applies the first eight characters of the cPanel account's username. For example: A `db_` database prefix allows MariaDB usernames of up to 44 characters.; An `example_` database prefix allows MariaDB usernames of up to 39 characters.
- `password` · **required** · string · e.g. `12345luggage` — The new user's password.
- `prefix-size` · optional · integer (`8`, `16`) · default `16` · e.g. `16` — The desired prefix size.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  create_user \
  name='dbuser' \
  password='12345luggage'
```

<a id="mysql-delete-user"></a>
### `Mysql::delete_user` — Delete MySQL user

`GET /execute/Mysql/delete_user` · RW · rollback: none · since cPanel 11.52

This function deletes a MySQL® user. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is not already configured, the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `example` — The MySQL user's name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  delete_user \
  name='example'
```

<a id="mysql-get-privileges-on-database"></a>
### `Mysql::get_privileges_on_database` — Return MySQL user privileges

`GET /execute/Mysql/get_privileges_on_database` · RO · since cPanel 11.44

This function lists a MySQL® database user's privileges. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is not already configured, the system disables this function.

**Parameters**

- `database` · **required** · string · e.g. `mydb` — The database name.
- `user` · **required** · string · e.g. `dbuser` — The database user's name. Important: If database prefixing is enabled, you **must** prefix this value with the account prefix and an underscore (`_`). For example, for the `dbuser` user on the `user` cPanel account, pass in a value of `user_dbuser`.

**Returns** `data`: array of string — An array of privileges.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  get_privileges_on_database \
  user='dbuser' \
  database='mydb'
```

<a id="mysql-get-restrictions"></a>
### `Mysql::get_restrictions` — Return MySQL name length restrictions

`GET /execute/Mysql/get_restrictions` · RO · since cPanel 11.44

This function lists a MySQL® database's name, username length restrictions, and database prefix. Important: When you disable the [*MySQL/MariaDB* role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Returns** `data`: object

- `max_database_name_length` (integer) — The maximum length of a MySQL database name.
- `max_username_length` (integer) — The maximum length of a MySQL database user's name.
- `prefix` (string) — The account's database prefix, if database prefixing is enabled.; If database prefixing is enabled, a string of up to the first eight characters of the cPanel account username, and an underscore (_).; If database prefixi

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  get_restrictions
```

<a id="mysql-list-routines"></a>
### `Mysql::list_routines` — Return MySQL user routines

`GET /execute/Mysql/list_routines` · RO · since cPanel 82

This function returns a database user's MySQL® routines. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** configured, the system **disables** this function.

**Parameters**

- `database_user` · optional · string · e.g. `db_user` — The database user for whom to return MySQL routines. If you don't specify a database user, this function returns the MySQL routines for all database users.

**Returns** `data`: array of string — An array of MySQL routines.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  list_routines
```

<a id="mysql-list-users"></a>
### `Mysql::list_users` — Return MySQL users

`GET /execute/Mysql/list_users` · RO · since cPanel 82

This function lists an account's MySQL® database users. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** configured, the system **disables** this function.

**Returns** `data`: array of object — An array of database information objects.

- *(array of objects)*
  - `databases` (array of string) — An array of databases that belong to the database user.
  - `shortuser` (string) — The short version of the database username.
  - `user` (string) — The database username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  list_users
```

<a id="mysql-rename-user"></a>
### `Mysql::rename_user` — Update MySQL username

`GET /execute/Mysql/rename_user` · RW · rollback: none · since cPanel 11.44

This function renames a MySQL® database user. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `newname` · **required** · string · e.g. `mynewusername` — The user's new name. Important: ==== To learn more about database username limits, check your database type: MySQL 5.6 ---- MySQL version 5.6 limits the database username to 16 characters. The server uses the first nine characters of this limit for the database prefix. The database prefix uses the cPanel account's username and an underscore (`_`). The server only applies the first eight characters of the cPanel account's username. For example: A `db_` database prefix allows MySQL usernames of up to 13 characters.; An `example_` database prefix allows MySQL usernames of up to eight characters. MySQL 5.7+ ---- MySQL versions 5.7 and later limit the database username to 32 characters. The server uses the first nine characters of this limit for the database prefix. The database prefix uses the cPanel account's username and an underscore (`_`). The server only applies the first eight characters of the cPanel account's username. For example: A `db_` database prefix allows MySQL usernames of up to 29 characters.; An `example_` database prefix allows MySQL usernames of up to 24 characters. MariaDB ---- MariaDB limits the database username to 47 characters. The server uses the first nine characters of this limit for the database prefix. The database prefix uses the cPanel account's username and an underscore (`_`). The server only applies the first eight characters of the cPanel account's username. For example: A `db_` database prefix allows MariaDB usernames of up to 44 characters.; An `example_` database prefix allows MariaDB usernames of up to 39 characters.
- `oldname` · **required** · string · e.g. `dbuser` — The user's current name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  rename_user \
  oldname='dbuser' \
  newname='mynewusername'
```

<a id="mysql-revoke-access-to-database"></a>
### `Mysql::revoke_access_to_database` — Remove MySQL user privileges

`GET /execute/Mysql/revoke_access_to_database` · RW · rollback: none · since cPanel 11.44

This function revokes a MySQL® database user's privileges. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `database` · **required** · string · e.g. `mydb` — The database's name.
- `user` · **required** · string · e.g. `dbuser` — The database user's name. Important: If database prefixing is enabled, you **must** prefix this value with the account prefix and an underscore (`_`). For example, for the `dbuser` user on the `user` cPanel account, pass in a value of `user_dbuser`.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  revoke_access_to_database \
  user='dbuser' \
  database='mydb'
```

<a id="mysql-set-password"></a>
### `Mysql::set_password` — Update MySQL user password

`GET /execute/Mysql/set_password` · RW · rollback: none · since cPanel 11.44

This function sets a MySQL® database user's password. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) and remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `password` · **required** · string · e.g. `12345luggage` — The user's new password.
- `user` · **required** · string · e.g. `dbuser` — The MySQL database user.

**Returns** `data`: object

- `failures` (array of object) — An array of the function's error messages.
  - *(array of objects)*
    - `error` (string) — The error message.
    - `host` (string <domain>) — The hostname that reported the error.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  set_password \
  user='dbuser' \
  password='12345luggage'
```

<a id="mysql-set-privileges-on-database"></a>
### `Mysql::set_privileges_on_database` — Update MySQL user privileges

`GET /execute/Mysql/set_privileges_on_database` · RW · rollback: none · since cPanel 11.44

This function sets a MySQL® database user's privileges. Important: When you disable the [*MySQL/MariaDB* role](https://go.cpanel.net/serverroles), **and** remote MySQL is **not** already configured, the system **disables** this function.

**Parameters**

- `database` · **required** · string · e.g. `cpuser_dbname` — The database's name. Important: If database prefixing is enabled, you **must** prefix this value with the account prefix and an underscore (`_`). For example, for the `db` database on the `user` cPanel account, pass in a value of `user_db`.
- `user` · **required** · string · e.g. `cpuser_dbuser` — The database user's name. Important: If database prefixing is enabled, you **must** prefix this value with the account prefix and an underscore (`_`). For example, for the `dbuser` user on the `user` cPanel account, pass in a value of `user_dbuser`.
- `privileges` · optional · string · e.g. `DELETE,UPDATE,CREATE,ALTER` — * `ALL PRIVILEGES`; A comma-separated list of one or more of the following individual privileges: `ALTER`; `ALTER ROUTINE`; `CREATE`; `CREATE ROUTINE`; `CREATE TEMPORARY TABLES`; `CREATE VIEW`; `DELETE`; `DROP`; `EVENT`; `EXECUTE`; `INDEX`; `INSERT`; `LOCK TABLES`; `REFERENCES`; `SELECT`; `SHOW VIEW`; `TRIGGER`; `UPDATE` Note:  This list replaces, rather than adds to, the existing privilege list.; In browser-based and command line calls, separate multiple values with `%2C` and replace spaces with `%20`.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  set_privileges_on_database \
  user='cpuser_dbuser' \
  database='cpuser_dbname'
```

<a id="mysql-update-privileges"></a>
### `Mysql::update_privileges` — Update MySQL® privileges

`GET /execute/Mysql/update_privileges` · RW · rollback: none · since cPanel 82

This function updates privileges for all MySQL® databases and users on an account. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** configured, the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  update_privileges
```

## Database Information

<a id="mysql-get-server-information"></a>
### `Mysql::get_server_information` — Return MySQL server host information and version

`GET /execute/Mysql/get_server_information` · RO · since cPanel 54

This function returns information about the account's MySQL® host. Important: When you disable the [MySQL role](https://go.cpanel.net/serverroles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Returns** `data`: object

- `host` (string <domain> or string <ipv4>) — The MySQL server's hostname or IP address.
- `is_remote` (integer (`0`, `1`)) — Whether the host is a remote MySQL server.; `1` - Remote host.; `0` - Local host.
- `version` (string) — The MySQL server's version.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  get_server_information
```

<a id="mysql-locate-server"></a>
### `Mysql::locate_server` — Return MySQL server host information

`GET /execute/Mysql/locate_server` · RO · since cPanel 11.52

This function returns information about the account's MySQL® host. Important: When you disable the [MySQL/MariaDB role](https://go.cpanel.net/serverroles#roles) **and** remote MySQL is **not** already configured, the system **disables** this function.

**Returns** `data`: object

- `is_remote` (integer (`0`, `1`)) — Whether the host is a remote MySQL server.; `1` - Remote host.; `0` - Local host.
- `remote_host` (string <domain> or string <ipv4>) — The remote MySQL server's hostname or IP address.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mysql \
  locate_server
```

