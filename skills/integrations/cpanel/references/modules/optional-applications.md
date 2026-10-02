<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Optional Applications

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Calendar and Contacts Server**: [`CCS::add_delegate`](#ccs-add-delegate), [`CCS::list_delegates`](#ccs-list-delegates), [`CCS::list_users`](#ccs-list-users), [`CCS::remove_delegate`](#ccs-remove-delegate), [`CCS::update_delegate`](#ccs-update-delegate)
- **Calendar and Contacts (DAV)**: [`CPDAVD::add_delegate`](#cpdavd-add-delegate), [`CPDAVD::list_delegates`](#cpdavd-list-delegates), [`CPDAVD::list_users`](#cpdavd-list-users), [`CPDAVD::manage_collection`](#cpdavd-manage-collection), [`CPDAVD::remove_delegate`](#cpdavd-remove-delegate), [`CPDAVD::update_delegate`](#cpdavd-update-delegate), [`DAV::disable_shared_global_addressbook`](#dav-disable-shared-global-addressbook), [`DAV::enable_shared_global_addressbook`](#dav-enable-shared-global-addressbook), [`DAV::get_calendar_contacts_config`](#dav-get-calendar-contacts-config), [`DAV::has_shared_global_addressbook`](#dav-has-shared-global-addressbook), [`DAV::is_dav_service_enabled`](#dav-is-dav-service-enabled), [`DAV::is_horde_enabled`](#dav-is-horde-enabled)
- **Antivirus Protection (ClamAV)**: [`ClamScanner::check_disinfection_status`](#clamscanner-check-disinfection-status), [`ClamScanner::disinfect_files`](#clamscanner-disinfect-files), [`ClamScanner::get_scan_paths`](#clamscanner-get-scan-paths), [`ClamScanner::get_scan_status`](#clamscanner-get-scan-status), [`ClamScanner::list_infected_files`](#clamscanner-list-infected-files), [`ClamScanner::start_scan`](#clamscanner-start-scan)
- **WordPress Manager Backups**: [`WordPressBackup::any_running`](#wordpressbackup-any-running), [`WordPressBackup::cancel`](#wordpressbackup-cancel), [`WordPressBackup::cleanup`](#wordpressbackup-cleanup), [`WordPressBackup::get_available_backups`](#wordpressbackup-get-available-backups), [`WordPressBackup::is_running`](#wordpressbackup-is-running), [`WordPressBackup::start`](#wordpressbackup-start), [`WordPressRestore::any_running`](#wordpressrestore-any-running), [`WordPressRestore::cleanup`](#wordpressrestore-cleanup), [`WordPressRestore::start`](#wordpressrestore-start)

## Calendar and Contacts Server

<a id="ccs-add-delegate"></a>
### `CCS::add_delegate` — Add calendar delegation

`GET /execute/CCS/add_delegate` · RW · rollback: none · since cPanel 90 · requires package `cpanel-ccs-calendarserver`

This function delegates a user's calendar to another user. Note: You **must** install the [Calendar and Contacts Server](https://go.cpanel.net/CalendarAndContactsServer) cPanel plugin to access this API function.

**Parameters**

- `delegatee` · **required** · string <email> · e.g. `delegatee@cptest.test` — The user to whom you wish to delegate the calendar.
- `delegator` · **required** · string <email> · e.g. `delegator@cptest.test` — The calendar's owner.
- `readonly` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether the delegatee will only have read-only access on the calendar.; `1` - Read-only access.; `0` - Full access.

```bash
uapi --output=jsonpretty \
  --user=username \
  CCS \
  add_delegate \
  delegator='delegator@cptest.test' \
  delegatee='delegatee@cptest.test'
```

<a id="ccs-list-delegates"></a>
### `CCS::list_delegates` — List cPanel account's calendar delegates

`GET /execute/CCS/list_delegates` · RO · since cPanel 90

This function lists all [calendar delegates](https://docs.cpanel.net/cpanel/email/calendar-delegation/) on the cPanel account. Note: You **must** install the [Calendar and Contacts Server](https://go.cpanel.net/CalendarAndContactsServer) cPanel plugin to access this API function.

**Returns** `data`: array of object — An array of objects that contain Calendars and Contacts Server calendar delegation information.

- *(array of objects)*
  - `delegatee` (string <email>) — The user with delegation rights.
  - `delegator` (string <email>) — The calendar's owner.
  - `read_only` (integer (`1`, `0`)) — Whether the delegatee has read-only access on the calendar.; `1` - Read-only access.; `0` - Full access.

```bash
uapi --output=jsonpretty \
  --user=username \
  CCS \
  list_delegates
```

<a id="ccs-list-users"></a>
### `CCS::list_users` — List cPanel account's calendar users

`GET /execute/CCS/list_users` · RO · since cPanel 90

This function lists all calendar users on the cPanel account. Note: You **must** install the [Calendar and Contacts Server](https://go.cpanel.net/CalendarAndContactsServer) cPanel plugin to access this API function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  CCS \
  list_users
```

<a id="ccs-remove-delegate"></a>
### `CCS::remove_delegate` — Remove calendar delegation

`GET /execute/CCS/remove_delegate` · RW · rollback: none · since cPanel 90

This function removes a delegate from another user's calendar. Note: You **must** install the [Calendar and Contacts Server](https://go.cpanel.net/CalendarAndContactsServer) cPanel plugin to access this API function.

**Parameters**

- `delegatee` · **required** · string <email> · e.g. `user2@example.com` — The user from whom you wish to remove delegation rights.
- `delegator` · **required** · string <email> · e.g. `user1@example.com` — The calendar's owner.

```bash
uapi --output=jsonpretty \
  --user=username \
  CCS \
  remove_delegate \
  delegator='user1@example.com' \
  delegatee='user2@example.com'
```

<a id="ccs-update-delegate"></a>
### `CCS::update_delegate` — Update calendar delegation

`GET /execute/CCS/update_delegate` · RW · rollback: none · since cPanel 90

This function updates the delegation of a user's calendar to another user. Note: You **must** install the [Calendar and Contacts Server](https://go.cpanel.net/CalendarAndContactsServer) cPanel plugin to access this API function.

**Parameters**

- `delegatee` · **required** · string <email> · e.g. `user2@example.com` — The user to whom you delegated the calendar.
- `delegator` · **required** · string <email> · e.g. `user1@example.com` — The calendar's owner.
- `readonly` · optional · integer · default `0` · e.g. `1` — Whether the delegatee will only have read-only access on the calendar.; `1` - Read-only access.; `0` - Full access.

```bash
uapi --output=jsonpretty \
  --user=username \
  CCS \
  update_delegate \
  delegator='user1@example.com' \
  delegatee='user2@example.com'
```

## Calendar and Contacts (DAV)

<a id="cpdavd-add-delegate"></a>
### `CPDAVD::add_delegate` — Share a calendar

`GET /execute/CPDAVD/add_delegate` · RW · rollback: none · since cPanel 120

This function adds a share for the specified calendar.

**Parameters**

- `calendar` · **required** · string · e.g. `calendar` — The calendar to share.
- `delegatee` · **required** · string · e.g. `second@example.com` — The person to whom you will share the calendar.
- `delegator` · **required** · string · e.g. `first@example.com` — The owner of the calendar, who wishes to share it to another user.
- `readonly` · optional · integer (`0`, `1`) · e.g. `1` — If set, the provided access will be read-only.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the sharing succeeded.; `1` — Shared.; `0` — **Not** shared.

```bash
uapi --output=jsonpretty \
  --user=username \
  CPDAVD \
  add_delegate \
  delegator='first@example.com' \
  delegatee='second@example.com' \
  calendar='calendar'
```

<a id="cpdavd-list-delegates"></a>
### `CPDAVD::list_delegates` — List calendar sharing.

`GET /execute/CPDAVD/list_delegates` · RO · since cPanel 120

This function lists the sharing configuration in calendars for this account.

**Returns** `data`: array of object

- *(array of objects)*
  - `calendar` (string) — The calendar id.
  - `calname` (string) — The name of the calendar.
  - `delegatee` (string) — The person to whom the owner of the calendar shared it.
  - `delegator` (string) — The owner of the calendar.
  - `readonly` (integer (`0`, `1`)) — If set to `1`, the `delegatee` only has read access to the calendar.

```bash
uapi --output=jsonpretty \
  --user=username \
  CPDAVD \
  list_delegates
```

<a id="cpdavd-list-users"></a>
### `CPDAVD::list_users` — List CalDAV and CardDAV users

`GET /execute/CPDAVD/list_users` · RO · since cPanel 120

This function lists the users that are available for use with CalDAV and CardDAV

**Returns** `data`: array of object

```bash
uapi --output=jsonpretty \
  --user=username \
  CPDAVD \
  list_users
```

<a id="cpdavd-manage-collection"></a>
### `CPDAVD::manage_collection` — Manage a calendar, task list, or address book

`GET /execute/CPDAVD/manage_collection` · RW · rollback: none · since cPanel 120

This function creates, updates, or deletes a collection.

**Parameters**

- `account` · **required** · string · e.g. `user@example.com` — The owner of the calendar.
- `action` · **required** · string (`create`, `update`, `delete`) · e.g. `delete` — The action to perform (create, update, or delete a collection).
- `collection_type` · **required** · string (`calendar`, `tasks`, `addressbook`) · e.g. `calendar` — The collection type.
- `calendar-color` · optional · string · e.g. `#ee5555` — The color of the calendar, if applicable.
- `description` · optional · string · e.g. `This is my calendar.` — The description of the collection.
- `name` · optional · string · e.g. `My Calendar` — The name of the collection. Required when creating a collection.
- `path` · optional · string · e.g. `/calendars/user@example.com/mycalendar` — The path to the collection. Required for the `update` and `delete` actions, which use it to identify an existing collection. Optional for `create`, where omitting it autogenerates a path of the form `<collection_type>-<uuid>`.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the operation succeeded.; `1` — Operation succeeded.; `0` — Operation did **not** succeed.

```bash
uapi --output=jsonpretty \
  --user=username \
  CPDAVD \
  manage_collection \
  account='user@example.com' \
  action='delete' \
  path='/calendars/user@example.com/mycalendar' \
  collection_type='calendar'
```

<a id="cpdavd-remove-delegate"></a>
### `CPDAVD::remove_delegate` — Remove a share.

`GET /execute/CPDAVD/remove_delegate` · RW · rollback: none · since cPanel 120

This function removes a share for the specified calendar.

**Parameters**

- `calendar` · **required** · string · e.g. `calendar` — The calendar that was shared.
- `delegatee` · **required** · string · e.g. `second@example.com` — The person to whom the calendar was shared.
- `delegator` · **required** · string · e.g. `first@example.com` — The owner of the calendar, who wishes to remove the sharing.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the sharing removal succeeded.; `1` — Removed.; `0` — **Not** removed.

```bash
uapi --output=jsonpretty \
  --user=username \
  CPDAVD \
  remove_delegate \
  delegator='first@example.com' \
  delegatee='second@example.com' \
  calendar='calendar'
```

<a id="cpdavd-update-delegate"></a>
### `CPDAVD::update_delegate` — Update calendar sharing.

`GET /execute/CPDAVD/update_delegate` · RW · rollback: none · since cPanel 120

This function updates a share for the specified calendar.

**Parameters**

- `calendar` · **required** · string · e.g. `calendar` — The calendar to share.
- `delegatee` · **required** · string · e.g. `second@example.com` — The person to whom you will share the calendar.
- `delegator` · **required** · string · e.g. `first@example.com` — The owner of the calendar, who wishes to change the details of the sharing.
- `readonly` · optional · integer (`0`, `1`) · e.g. `1` — If set, the provided access will be read-only.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the sharing succeeded.; `1` — Shared.; `0` — **Not** shared.

```bash
uapi --output=jsonpretty \
  --user=username \
  CPDAVD \
  update_delegate \
  delegator='first@example.com' \
  delegatee='second@example.com' \
  calendar='calendar'
```

<a id="dav-disable-shared-global-addressbook"></a>
### `DAV::disable_shared_global_addressbook` — Disable global address book

`GET /execute/DAV/disable_shared_global_addressbook` · RW · rollback: none · since cPanel 54

This function disables the shared global address book for the current cPanel account's webmail accounts.

**Parameters**

- `name` · optional · string · e.g. `user` — cPanel account username or a Webmail user's email address. If you do **not** specify a user, this parameter defaults to the currently-authenticated user.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the global address book is shared.; `1` — Shared.; `0` — **Not** shared.

```bash
uapi --output=jsonpretty \
  --user=username \
  DAV \
  disable_shared_global_addressbook
```

<a id="dav-enable-shared-global-addressbook"></a>
### `DAV::enable_shared_global_addressbook` — Enable global address book

`GET /execute/DAV/enable_shared_global_addressbook` · RW · rollback: none · since cPanel 54

This function enables the shared global address book for the current cPanel account's webmail accounts.

**Parameters**

- `name` · optional · string · e.g. `user` — cPanel account username or a Webmail user's email address. If you do **not** specify a user, this parameter defaults to the currently-authenticated user.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the global address book is shared.; 1 — Shared.; 0 — **Not** shared.

```bash
uapi --output=jsonpretty \
  --user=username \
  DAV \
  enable_shared_global_addressbook
```

<a id="dav-get-calendar-contacts-config"></a>
### `DAV::get_calendar_contacts_config` — Return CalDAV and CardDAV connection information

`GET /execute/DAV/get_calendar_contacts_config` · RO · since cPanel 11.50

This function returns the connection information to set up the CalDAV and CardDAV clients.

**Parameters**

- `user` · optional · string <email> or string <username> — A cPanel account or valid email account user. If you do **not** include this parameter, the function defaults to the current authenticated user.

**Returns** `data`: object

- `activesync` (object) — Configuration details for ActiveSync.
  - `enabled` (integer (`1`, `0`)) — Whether the server has ActiveSync enabled.; `1` — Enabled.; `0` — **Not** enabled.
  - `port` (integer) — The port number the system uses for secure ActiveSync connections.
  - `server` (string <domain>) — The fully qualified domain name to connect to.
  - `user` (string) — The cPanel user or email account user to whom the returned connection information pertains.
- `no_ssl` (object) — A list of non-SSL connection configurations.
  - `calendars` (array of object) — An array of objects containing the user's calendars.
  - `contacts` (array of object) — An array of objects containing the user's address books.
  - `free_busy` (string <url>) — The absolute URL path and HTTP port to the user's CalDAV `free-busy-query` connection.
  - `full_server` (string <url>) — The absolute URL path and HTTP port to the user's CalDAV and CardDAV connection information.
  - `port` (integer) — The port number that the system uses for non-SSL connections.
  - `server` (string <url>) — The short server connection string that includes a domain name and a port that uses the HTTP protocol.
- `ssl` (object) — A list of SSL connection configurations.
  - `calendars` (array of object) — An array of objects containing the user's calendars.
  - `contacts` (array of object) — An array of objects containing the user's address books.
  - `free_busy` (string <url>) — The absolute URL path and HTTPS port to the user's CalDAV `free-busy-query` connection.
  - `full_server` (string <url>) — The absolute URL path and HTTPS port to the user's CalDAV and CardDAV connection information.
  - `is_self_signed` (integer (`1`, `0`)) — Whether the server uses a self-signed certificate.; `1` — Self-signed.; `0` — **Not** self-signed.
  - `port` (integer) — The port number that the system uses for SSL connections.
  - `server` (string <url>) — The short server connection string that includes a domain name and a port that uses the HTTPS protocol.
- `user` (string) — The cPanel user or email account user to whom the returned connection information pertains.

```bash
uapi --output=jsonpretty \
  --user=username \
  DAV \
  get_calendar_contacts_config
```

<a id="dav-has-shared-global-addressbook"></a>
### `DAV::has_shared_global_addressbook` — Return whether global address book is enabled

`GET /execute/DAV/has_shared_global_addressbook` · RO · since cPanel 54

This function checks whether the shared global address book is enabled on the current cPanel account's webmail accounts.

**Parameters**

- `name` · optional · string · e.g. `user` — cPanel account user name or a Webmail user's email address. If you do **not** specify a user, this parameter defaults to the currently-authenticated user.

**Returns** `data`: object

- `shared` (integer (`0`, `1`)) — Whether the global address book is enabled.; `1` — Enabled.; `0` — **Not** enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  DAV \
  has_shared_global_addressbook
```

<a id="dav-is-dav-service-enabled"></a>
### `DAV::is_dav_service_enabled` — Return whether DAV is enabled

`GET /execute/DAV/is_dav_service_enabled` · RO · since cPanel 11.50

This function checks whether the DAV service is enabled.

**Returns** `data`: object

- `enabled` (integer (`0`, `1`)) — Whether the DAV service is enabled.; `1` — Enabled.; `0` — Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  DAV \
  is_dav_service_enabled
```

<a id="dav-is-horde-enabled"></a>
### `DAV::is_horde_enabled` — Return whether Horde is enabled

`GET /execute/DAV/is_horde_enabled` · RO · since cPanel 11.50

This function checks whether Horde is enabled. Since Horde is no longer installed with the product, the return value will only ever be 0.

**Returns** `data`: object

- `enabled` (integer (`0`)) — Whether Horde is enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  DAV \
  is_horde_enabled
```

## Antivirus Protection (ClamAV)

<a id="clamscanner-check-disinfection-status"></a>
### `ClamScanner::check_disinfection_status` — Request disinfection process status

`GET /execute/ClamScanner/check_disinfection_status` · RO · since 94

This function checks the status of the previously queued disinfection of infected files. Note: You must run the APIs in this order: 1. Run [`ClamScanner::start_scan`](https://go.cpanel.net/ClamScanner-start-scan) to start the virus scan. 2. Run [`ClamScanner::get_scan_status`](https://go.cpanel.net/ClamScanner-get-scan-status) in a loop until the scan is finished. 3. Run [`ClamScanner::list_infected_files`](https://go.cpanel.net/ClamScanner-list-infected-files) to get a report of the complete list of infected files. 4. Decide how you want to handle each infected file. 5. Run [`ClamScanner::disinfect_files`](https://go.cpanel.net/ClamScanner-disinfect-files) to queue the disinfection of the files. 6. Run [`ClamScanner::check_disinfection_status`](https://go.cpanel.net/ClamScanner-check-disinfection-status) in a loop until you get a done status. If you want to display the progress, you can render the `ClamScanner::check_disinfection_status` returned 'result{data}{details}' array where the `type` is `step`. Each `step` record indicates the action taken on a specific file in the set being processed.

**Parameters**

- `last_id` · optional · integer · e.g. `10` — The unique `id` of the message you last received from this same log. The API will return only the records after the specified `last_id`. If this parameter is not provided, the entire log is returned. Note: For improved performance, we recommend applications include the last record ID (last_id) from a previous call to this API, so only messages since the previous API call are returned.

**Returns** `data`: object

- `details` (array of object) — The list of events recorded in the log.
  - *(array of objects)*
    - *variant: object*
      - `file` (string) — The absolute path to the file.
      - `id` (number) — The task processing order.
      - `message` (string) — Optional message that may include more information about errors.
      - `state` (string (`deleted`, `error`, `mailbox-cleansed`, `no-action`, `quarantined`)) — The state of the step.
      - `type` (string (`step`)) — * `step` - Record about a single file being processes.
    - *variant: object*
      - `id` (number) — The task processing order.
      - `message` (string) — Optional message that may include more information about errors and warnings.
      - `state` (string (`error`, `warning`)) — The state of the issue.
      - `type` (string (`issue`)) — * `issue` - Record that the disinfection is complete for all files indicated.
    - *variant: object*
      - `id` (number) — The task processing order.
      - `message` (string) — Optional message that may include more information about errors.
      - `state` (string (`error`, `info`, `success`)) — The state of the step.
      - `type` (string (`done`)) — * `done` - Record that the disinfection is complete for all files indicated.
- `log` (string) — Path to the disinfection log file.
- `status` (string (`done`, `queued`, `running`)) — * `done` - The disinfection is finished.; `none` - There is no disinfection scheduled.; `queued` - The disinfection is queued.; `running` - The disinfection is in progress.

```bash
uapi --output=jsonpretty \
  --user=username \
  ClamScanner \
  check_disinfection_status
```

<a id="clamscanner-disinfect-files"></a>
### `ClamScanner::disinfect_files` — Start disinfecting files with viruses

`POST /execute/ClamScanner/disinfect_files` · RW · rollback: none · since 94

This function applies the disinfection option selected by the user for each infected file. Note: You must run the APIs in this order: 1. Run [`ClamScanner::start_scan`](https://go.cpanel.net/ClamScanner-start-scan) to start the virus scan. 2. Run [`ClamScanner::get_scan_status`](https://go.cpanel.net/ClamScanner-get-scan-status) in a loop until the scan is finished. 3. Run [`ClamScanner::list_infected_files`](https://go.cpanel.net/ClamScanner-list-infected-files) to get a report of the complete list of infected files. 4. Decide how you want to handle each infected file. 5. Run [`ClamScanner::disinfect_files`](https://go.cpanel.net/ClamScanner-disinfect-files) to queue the disinfection of the files. 6. Run [`ClamScanner::check_disinfection_status`](https://go.cpanel.net/ClamScanner-check-disinfection-status) in a loop until you get a done status.

**Request body** (`application/json`)

- `actions` (object) — The user provides the actions to perform on each specific infected file found in the scan.

**Returns** `data`: object

- `log` (string) — Path to the disinfection log file.
- `task_id` (string) — The Task Queue system's task ID number.

```bash
echo '{"home/unsure":"ignore","home/virus1":"delete","home/virus2":"quarantine"}' | uapi --user=username --input=json --output=jsonpretty ClamScanner disinfect_files
```

<a id="clamscanner-get-scan-paths"></a>
### `ClamScanner::get_scan_paths` — Return virus scan types

`GET /execute/ClamScanner/get_scan_paths` · RO · since cPanel 94

This function gets the available local paths that a cPanel account is permitted to scan. **Note**: The system determines the available scan types based on what the system administrator has set in WHM's [Configure ClamAV®](https://go.cpanel.net/configureclamavscanner) page. **Note**: You must run the APIs in this order: 1. Run [`ClamScanner::start_scan`](https://go.cpanel.net/ClamScanner-start-scan) to start the virus scan. 2. Run [`ClamScanner::get_scan_status`](https://go.cpanel.net/ClamScanner-get-scan-status) in a loop until the scan is finished. 3. Run [`ClamScanner::list_infected_files`](https://go.cpanel.net/ClamScanner-list-infected-files) to get a report of the complete list of infected files. 4. Decide how you want to handle each infected file. 5. Run [`ClamScanner::disinfect_files`](https://go.cpanel.net/ClamScanner-disinfect-files) to queue the disinfection of the files. 6. Run [`ClamScanner::check_disinfection_status`](https://go.cpanel.net/ClamScanner-check-disinfection-status) in a loop until you get a done status.

**Returns** `data`: object

- `id` (string (`home`, `mail`, `public_html`, `public_ftp`)) — The type of path; `home` — The cPanel account's entire home directory.; `mail` — The cPanel account's email directory.; `public_html` — The cPanel account's web directory.; `public_ftp` — The cPanel account's FTP directo
- `message` (string) — Short description of the path

```bash
uapi --output=jsonpretty \
  --user=username \
  ClamScanner \
  get_scan_paths
```

<a id="clamscanner-get-scan-status"></a>
### `ClamScanner::get_scan_status` — Request virus scan status

`GET /execute/ClamScanner/get_scan_status` · RO · since cPanel 94

This function gets the status of a ClamAV® scan on a directory. **Note**: You must run the APIs in this order: 1. Run [`ClamScanner::start_scan`](https://go.cpanel.net/ClamScanner-start-scan) to start the virus scan. 2. Run [`ClamScanner::get_scan_status`](https://go.cpanel.net/ClamScanner-get-scan-status) in a loop until the scan is finished. 3. Run [`ClamScanner::list_infected_files`](https://go.cpanel.net/ClamScanner-list-infected-files) to get a report of the complete list of infected files. 4. Decide how you want to handle each infected file. 5. Run [`ClamScanner::disinfect_files`](https://go.cpanel.net/ClamScanner-disinfect-files) to queue the disinfection of the files. 6. Run [`ClamScanner::check_disinfection_status`](https://go.cpanel.net/ClamScanner-check-disinfection-status) in a loop until you get a done status.

**Returns** `data`: object

- `current_file` (string) — The current file being scanned.
- `infected_files` (array of string) — List of files scanned and found to be infected.
- `scan_complete` (integer (`0`, `1`)) — Whether the last scan has completed.; `1` - scan has completed.; `0` - scan has **not** completed.
- `scanned_file_count` (integer) — The number of files already scanned.
- `scanned_file_size` (integer) — The number of bytes of data scanned.
- `time_started` (string) — The epoch timestamp of the beginning of the last scan.
- `total_file_count` (integer) — The total number of files found to scan.
- `total_file_size_MiB` (integer) — The total number of megabytes of data found to scan.

```bash
uapi --output=jsonpretty \
  --user=username \
  ClamScanner \
  get_scan_status
```

<a id="clamscanner-list-infected-files"></a>
### `ClamScanner::list_infected_files` — Return infected file list

`GET /execute/ClamScanner/list_infected_files` · RO · since cPanel 94

This function lists infected files from a ClamAV® virus scan. **Note**: You must run the APIs in this order: 1. Run [`ClamScanner::start_scan`](https://go.cpanel.net/ClamScanner-start-scan) to start the virus scan. 2. Run [`ClamScanner::get_scan_status`](https://go.cpanel.net/ClamScanner-get-scan-status) in a loop until the scan is finished. 3. Run [`ClamScanner::list_infected_files`](https://go.cpanel.net/ClamScanner-list-infected-files) to get a report of the complete list of infected files. 4. Decide how you want to handle each infected file. 5. Run [`ClamScanner::disinfect_files`](https://go.cpanel.net/ClamScanner-disinfect-files) to queue the disinfection of the files. 6. Run [`ClamScanner::check_disinfection_status`](https://go.cpanel.net/ClamScanner-check-disinfection-status) in a loop until you get a done status.

**Returns** `data`: array of object

- *(array of objects)*
  - `file` (string <path>) — An absolute path to the infected file on the system.
  - `virus_type` (string) — A virus type.

```bash
uapi --output=jsonpretty \
  --user=username \
  ClamScanner \
  list_infected_files
```

<a id="clamscanner-start-scan"></a>
### `ClamScanner::start_scan` — Start virus scan

`GET /execute/ClamScanner/start_scan` · RW · rollback: none · since cPanel 94

This function starts a ClamAV® scan on a directory. **Note**: You must run the APIs in this order: 1. Run [`ClamScanner::start_scan`](https://go.cpanel.net/ClamScanner-start-scan) to start the virus scan. 2. Run [`ClamScanner::get_scan_status`](https://go.cpanel.net/ClamScanner-get-scan-status) in a loop until the scan is finished. 3. Run [`ClamScanner::list_infected_files`](https://go.cpanel.net/ClamScanner-list-infected-files) to get a report of the complete list of infected files. 4. Decide how you want to handle each infected file. 5. Run [`ClamScanner::disinfect_files`](https://go.cpanel.net/ClamScanner-disinfect-files) to queue the disinfection of the files. 6. Run [`ClamScanner::check_disinfection_status`](https://go.cpanel.net/ClamScanner-check-disinfection-status) in a loop until you get a done status.

**Parameters**

- `scan_type` · **required** · any (`home`, `mail`, `public_html`, `public_ftp`) · e.g. `home` — The type of directory to scan.; `home` — User's entire home directory; `mail` — User's email directory; `public_html` — User's web directory; `public_ftp` — User's ftp directory

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  ClamScanner \
  start_scan \
  scan_type='home'
```

## WordPress Manager Backups

<a id="wordpressbackup-any-running"></a>
### `WordPressBackup::any_running` — Return all WordPress sites' backup status

`GET /execute/WordPressBackup/any_running` · RO · since WordPress Manager 3.0

This function checks for any active WordPress® site backups on the cPanel account. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Returns** `data`: object

- `any_running` (integer (`0`, `1`)) — Whether any backups are in progess.; `1` - Backups are in progress.; `0` - No backups are in progress.
- `sites` (array of object) — An array that contains each site with a backup in progress.
  - *(array of objects)*
    - `id` (string) — The WordPress site's unique ID.
    - `site` (string) — The WordPress site's URL.
    - `type` (string) — The type of process that is active.
- `sse_url` (string) — The SSE service URL that the system uses to monitor the backup progress.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressBackup \
  any_running
```

<a id="wordpressbackup-cancel"></a>
### `WordPressBackup::cancel` — Stop WordPress site backup

`GET /execute/WordPressBackup/cancel` · RW · rollback: none · since WordPress Manager 3.0

This function cancels a WordPress® site backup. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `site` · **required** · any <domain> or any <url-path> — The WordPress site's URL without the protocol prefix.

**Returns** `data`: object

- `ok` (integer (`0`, `1`)) — Whether the system cancelled an active backup.; `1` — Backup cancelled.; `0` — Could not cancel the backup or no active backup in progress.
- `site` (any <domain> or any <url-path>) — The site's URL without the protocol prefix.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressBackup \
  cancel \
  site='example.com'
```

<a id="wordpressbackup-cleanup"></a>
### `WordPressBackup::cleanup` — Delete WordPress backup temporary files

`GET /execute/WordPressBackup/cleanup` · RW · rollback: none · since WordPress Manager 3.0

This function releases any system resources from a previous WordPress® site backup. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `site` · **required** · string · e.g. `example.com/wordpress` — The WordPress site's URL **without** the protocol prefix.

**Returns** `data`: object

- `ok` (integer (`0`, `1`)) — Whether the system released the system resources.; `1` - Resources released.; `0` - Backup in progress.
- `site` (string) — The site's URL **without** the protocol prefix.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressBackup \
  cleanup \
  site='example.com/wordpress'
```

<a id="wordpressbackup-get-available-backups"></a>
### `WordPressBackup::get_available_backups` — Return WordPress site backups

`GET /execute/WordPressBackup/get_available_backups` · RO · since WordPress Manager 3.0

This function retrieves a list of available WordPress® site backups of a single site. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `site` · **required** · string · e.g. `example.com/wordpress` — The WordPress site's URL **without** the protocol prefix.

**Returns** `data`: object

- `available` (array of object) — An array of objects containing a list of the WordPress site's backups.
  - *(array of objects)*
    - `date` (integer <unix_timestamp>) — The date and time the system created the backup.
    - `file` (string) — The backup's file name with the `tar.zip` extension.
    - `path` (string) — The absolute path to the backup file.
    - `site` (string) — The site's URL **without** the protocol prefix.
- `dir` (string) — The absolute path to the backup directory.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressBackup \
  get_available_backups \
  site='example.com/wordpress'
```

<a id="wordpressbackup-is-running"></a>
### `WordPressBackup::is_running` — Return WordPress site backup status

`GET /execute/WordPressBackup/is_running` · RO · since WordPress Manager 3.0

This function checks for an active WordPress® site backup. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `site` · **required** · string · e.g. `example.com

example.com/wordpress` — The WordPress site's URL **without** `http://`.

**Returns** `data`: object

- `action_id` (string) — The unique ID of the backup process.
- `is_running` (integer (`0`, `1`)) — Whether a backup is active.; `1` - Backup in progress.; `0` - No backup in progress.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressBackup \
  is_running \
  site='example.com

example.com/wordpress'
```

<a id="wordpressbackup-start"></a>
### `WordPressBackup::start` — Backup WordPress site

`GET /execute/WordPressBackup/start` · RW · rollback: none · since WordPress Manager 3.0

This function starts a single WordPress® site backup. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `site` · **required** · any <domain> or any <url-path> — The WordPress site's URL without the protocol prefix.

**Returns** `data`: object

- `backup_id` (string) — The unique ID of the backup process.
- `site` (any <domain> or any <url-path>) — The WordPress site's URL without the protocol prefix.
- `sse_url` (string <url-path>) — The SSE path **without** the protocol, hostname, or port that the system uses to monitor the backup progress.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressBackup \
  start \
  site='example.com'
```

<a id="wordpressrestore-any-running"></a>
### `WordPressRestore::any_running` — Return WordPress site restore status

`GET /execute/WordPressRestore/any_running` · RO · since WordPress Manager 3.0

This function returns whether a WordPress® site backup restoration is in progress. Note:  You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.; The output of this function changes, depending on the state of the backup restoration.

**Returns** `data`: object

- `items` (object) — 
  - *variant: object*
    - `any_running` (integer (`1`)) — Whether the system is processing a backup restoration.; `1` - Restoration in progress.
    - `sites` (array of object) — Information about the site that the system is actively restoring.
  - *variant: object*
    - `any_running` (integer (`0`)) — Whether the system is processing a backup restoration.; `0` - No restoration in progress.
    - `last_outcome` (object) — The status of the last backup restoration.
    - `sites` (object) — Information about the site that the system is actively restoring.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressRestore \
  any_running
```

<a id="wordpressrestore-cleanup"></a>
### `WordPressRestore::cleanup` — Delete restored WordPress site's temporary files

`GET /execute/WordPressRestore/cleanup` · RW · rollback: none · since WordPress Manager 3.0

This function cleans up any temporary system resources after a WordPress® site backup restoration. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `site` · **required** · string — The WordPress site's URL **without** the protocol prefix.

**Returns** `data`: integer (`0`, `1`) — Whether the system cleaned up the temporary system resources.; `1` - Successful.; `0` - Unsuccessful.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressRestore \
  cleanup \
  site='example.com'
```

<a id="wordpressrestore-start"></a>
### `WordPressRestore::start` — Restore WordPress site

`GET /execute/WordPressRestore/start` · RW · rollback: none · since WordPress Manager 3.0

This function starts a single WordPress® site backup restoration. Note: You **must** install the [WordPress Manager](https://go.cpanel.net/wordpressmanager) cPanel plugin to access this API function.

**Parameters**

- `backup_path` · **required** · string <path> — The file path to the backup archive.
- `site` · **required** · string — The WordPress site's URL to restore.

**Returns** `data`: object

- `restore_id` (string) — The unique identifier for the restoration operation.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressRestore \
  start \
  site='example.com' \
  backup_path='/home/example/wordpress-backups/example.com__2018-11-13T11:11:31-0600.tar.gz'
```

