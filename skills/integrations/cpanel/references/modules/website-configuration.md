<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Website Configuration

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Logs**: [`LogManager::delete_archive`](#logmanager-delete-archive), [`LogManager::get_settings`](#logmanager-get-settings), [`LogManager::list_archives`](#logmanager-list-archives), [`LogManager::list_error_logs`](#logmanager-list-error-logs), [`LogManager::set_settings`](#logmanager-set-settings), [`LogManager::view_error_log`](#logmanager-view-error-log)
- **Handler Management**: [`Mime::add_handler`](#mime-add-handler), [`Mime::delete_handler`](#mime-delete-handler), [`Mime::list_handlers`](#mime-list-handlers), [`Mime::redirect_info`](#mime-redirect-info)
- **Mime Type Management**: [`Mime::add_mime`](#mime-add-mime), [`Mime::delete_mime`](#mime-delete-mime), [`Mime::list_mime`](#mime-list-mime)
- **Nova**: [`Nova::account_exists`](#nova-account-exists), [`Nova::add_api_token`](#nova-add-api-token), [`Nova::can_create_domains`](#nova-can-create-domains), [`Nova::create_account`](#nova-create-account), [`Nova::disk_quota_check`](#nova-disk-quota-check), [`Nova::ensure_account`](#nova-ensure-account), [`Nova::get_all_user_nova_info`](#nova-get-all-user-nova-info), [`Nova::get_sso_link`](#nova-get-sso-link), [`Nova::get_tier`](#nova-get-tier), [`Nova::poll_publish`](#nova-poll-publish), [`Nova::publish`](#nova-publish)
- **Sitejet**: [`Sitejet::add_api_token`](#sitejet-add-api-token), [`Sitejet::can_create_domains`](#sitejet-can-create-domains), [`Sitejet::create_account`](#sitejet-create-account), [`Sitejet::create_restore_point`](#sitejet-create-restore-point), [`Sitejet::create_website`](#sitejet-create-website), [`Sitejet::get_all_user_sitejet_info`](#sitejet-get-all-user-sitejet-info), [`Sitejet::get_api_token`](#sitejet-get-api-token), [`Sitejet::get_preview_url`](#sitejet-get-preview-url), [`Sitejet::get_sso_link`](#sitejet-get-sso-link), [`Sitejet::get_templates`](#sitejet-get-templates), [`Sitejet::is_publish_in_progress`](#sitejet-is-publish-in-progress), [`Sitejet::restore_document_root`](#sitejet-restore-document-root), [`Sitejet::set_template`](#sitejet-set-template), [`Sitejet::start_publish`](#sitejet-start-publish)
- **WPX**: [`WPX::change_admin_password`](#wpx-change-admin-password), [`WPX::create_nova_for_wordpress_website`](#wpx-create-nova-for-wordpress-website), [`WPX::create_website`](#wpx-create-website), [`WPX::get_admin_account`](#wpx-get-admin-account), [`WPX::get_credentials`](#wpx-get-credentials), [`WPX::get_site_activity`](#wpx-get-site-activity), [`WPX::get_task_progress`](#wpx-get-task-progress), [`WPX::get_task_status`](#wpx-get-task-status), [`WPX::get_website`](#wpx-get-website), [`WPX::has_reached_quota`](#wpx-has-reached-quota), [`WPX::import_website`](#wpx-import-website), [`WPX::list_websites`](#wpx-list-websites), [`WPX::remove_installation`](#wpx-remove-installation), [`WPX::set_language`](#wpx-set-language)
- **Site Installation**: [`WordPressSite::create`](#wordpresssite-create)
- **Site Information**: [`WordPressSite::retrieve`](#wordpresssite-retrieve)

## Logs

<a id="logmanager-delete-archive"></a>
### `LogManager::delete_archive` — Delete a log archive file

`GET /execute/LogManager/delete_archive` · RW · rollback: clean · since cPanel 136

Delete a specific log archive file from the authenticated user's `~/logs` directory.

**Parameters**

- `file` · **required** · string · e.g. `example.com-Aug-2024.gz` — The log archive filename to delete. Requirements: Must reside in the user's `~/logs` directory.; Must end with `.gz`.; Must not contain path traversal characters.

```bash
uapi --output=jsonpretty \
  --user=username \
  LogManager \
  delete_archive \
  file=example.com-Aug-2024.gz
```

<a id="logmanager-get-settings"></a>
### `LogManager::get_settings` — Retrieve cPanel account's log archival settings

`GET /execute/LogManager/get_settings` · RO · since cPanel 82

This function retrieves the account's log archival settings.

**Returns** `data`: object

- `archive_logs` (integer (`1`, `0`)) — Whether the system archives log files to your home directory.; `1` — Archives the logs.; `0` — Does **not** archive the logs.
- `prune_archive` (integer (`1`, `0`)) — Whether the system removes the previous month's archived log files from your home directory.; `1` — Removes the logs.; `0` — Does **not** remove the logs.
- `retention_days` (integer) — The number of days the system retains archived log files before automatic removal.
- `using_default` (integer (`1`, `0`)) — Whether the user uses the server-wide default retention period.; `1` — Uses the server default.; `0` — Uses a custom retention value.

```bash
uapi --output=jsonpretty \
  --user=username \
  LogManager \
  get_settings
```

<a id="logmanager-list-archives"></a>
### `LogManager::list_archives` — Return cPanel account's archive files list

`GET /execute/LogManager/list_archives` · RO · since cPanel 82

This function returns a list of the user's archive files.

**Returns** `data`: array of object — An array of objects that contain information about the archive files.

- *(array of objects)*
  - `file` (string) — The archive file's name.
  - `mtime` (integer <unix_timestamp>) — The archive file's last modified date.
  - `path` (string) — The archive file's path.

```bash
uapi --output=jsonpretty \
  --user=username \
  LogManager \
  list_archives
```

<a id="logmanager-list-error-logs"></a>
### `LogManager::list_error_logs` — Return domain's PHP error logs

`GET /execute/LogManager/list_error_logs` · RO · since cPanel 138

This function lists the website's PHP error log files with size and last-modified metadata. It does not return file contents.

**Parameters**

- `domain` · **required** · string — A domain owned by the cPanel account.

**Returns** `data`: array of object — An array of objects describing the requested error logs.

- *(array of objects)*
  - `error` (string) — An error message that describes why the system could not return metadata for this log file.
  - `file_id` (string (`php_fpm_error_log`, `docroot_error_log`, `homedir_error_log`)) — The `file_id` value for each log file.; `php_fpm_error_log` — The PHP FPM error log file located in the user's home directory under the `logs/` subdirectory.; `docroot_error_log` — The PHP error log file located in the w
  - `modified_today` (integer (`1`, `0`)) — Whether the log file was last modified today (server local time).; `1` — The file was modified today.; `0` — The file was not modified today.
  - `mtime` (integer) — The log file's last-modified time as a unix timestamp.
  - `path` (string) — The absolute path to the log file.
  - `size` (integer) — The log file's size, in bytes.

```bash
uapi --output=jsonpretty \
  --user=username \
  LogManager \
  list_error_logs \
  domain=example.com
```

<a id="logmanager-set-settings"></a>
### `LogManager::set_settings` — Save cPanel account's log archive settings

`GET /execute/LogManager/set_settings` · RW · rollback: clean · since cPanel 82

This function saves the account's log archive settings. Note: You **must** pass at least one of the `archive_logs`, `prune_archive`, or `retention_days` parameters.

**Parameters**

- `archive_logs` · optional · integer (`0`, `1`) · e.g. `1` — Whether to archive log files to your home directory after the system processes statistics.; `1` — Archive the logs.; `0` — Do **not** archive the logs. Note:  This parameter defaults to the `archive-logs` setting's value in the user's `~/.cpanel-logs` file.; If this file does **not** exist, this parameter defaults to the `default_archive-logs` key's value in the [`cpanel.config`](https://go.cpanel.net/cpanelconfiginvalid) file.
- `prune_archive` · optional · integer (`0`, `1`) · e.g. `1` — Whether to remove the previous month's archived logs from the `~/logs directory` at the end of each month.; `1` — Remove the logs.; `0` — Do **not** remove the logs. Note:  This parameter defaults to the `remove-old-archived-logs` setting's value in the user's `~/.cpanel-logs` file.; If this file doesn't exist, this parameter defaults to the `default_remove-old-archive-logs` key's value in the [`cpanel.config`](https://go.cpanel.net/cpanelconfiginvalid) file.
- `retention_days` · optional · integer · e.g. `30` — The number of days to retain archived log files before automatic removal.; `0` — Retain logs indefinitely.; `-1` — Clear the per-user override and revert to the server default.; Any positive integer — Retain logs for that many days. When not provided, the existing value is preserved.

```bash
uapi --output=jsonpretty \
  --user=username \
  LogManager \
  set_settings \
  archive_logs=1 \
  prune_archive=1 \
  retention_days=30
```

<a id="logmanager-view-error-log"></a>
### `LogManager::view_error_log` — Return PHP error log for a domain

`GET /execute/LogManager/view_error_log` · RO · since cPanel 138

This function reads the trailing lines of a single PHP error log file for a domain owned by the current cPanel user and returns them in chronological order (oldest first).

**Parameters**

- `domain` · **required** · string — A domain owned by the current cPanel user.
- `file_id` · **required** · string (`php_fpm_error_log`, `docroot_error_log`, `homedir_error_log`) — Which of the three well-known log locations to read.; `php_fpm_error_log` — The PHP FPM error log. This file is located in the `logs/` directory within the cPanel account's home directory.; `docroot_error_log` — The PHP error log. This file is located in the domain's document root directory.; `homedir_error_log` — The cPanel account PHP error log. This file is located in the cPanel account's home directory.
- `limit` · optional · integer · default `100` — The number of lines to retrieve from the end of the log file. Note: Values above `5000` are silently capped at `5000`.

**Returns** `data`: object — An object describing the requested log file and its content.

- `file_id` (string (`php_fpm_error_log`, `docroot_error_log`, `homedir_error_log`)) — The identifier of the log file that was read.
- `log_content` (array of string) — The end of the error log file in chronological order.
- `lines_read` (integer) — The number of lines returned in the `log_content` return's value.
- `modified_today` (integer (`1`, `0`)) — Whether the log file was modified today.
- `mtime` (integer) — The log file's last-modified time, in Unix time format.
- `partial` (integer (`1`, `0`)) — Whether the log file contains more lines than the `limit` parameter's value.; `1` — The file exceeds the `limit` parameter's value.; `0` — The file did not exceed the `limit` parameter's value.
- `path` (string) — The absolute path to the log file on disk.
- `size` (integer) — The log file's size, in bytes.

```bash
uapi --output=jsonpretty \
  --user=username \
  LogManager \
  view_error_log \
  domain=example.com \
  file_id=php_fpm_error_log \
  limit=100
```

## Handler Management

<a id="mime-add-handler"></a>
### `Mime::add_handler` — Add web server MIME type handler

`GET /execute/Mime/add_handler` · RW · rollback: clean · since cPanel 11.42

This function creates an Apache MIME type handler for a file extension. Important: When you disable the [Web Server](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `extension` · **required** · string · e.g. `.foo` — The file extension.
- `handler` · **required** · string · e.g. `txt-foo` — The Apache MIME handler.

**Returns** `data`: object (`None`)

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  add_handler \
  extension='.foo' \
  handler='txt-foo'
```

<a id="mime-delete-handler"></a>
### `Mime::delete_handler` — Remove web server MIME type handler

`GET /execute/Mime/delete_handler` · RW · rollback: none · since cPanel 11.42

This function deletes an Apache MIME type handler. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `extension` · **required** · string · e.g. `.foo` — The file extension.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  delete_handler \
  extension='.foo'
```

<a id="mime-list-handlers"></a>
### `Mime::list_handlers` — Return web server's MIME handlers

`GET /execute/Mime/list_handlers` · RO · since cPanel 11.42

This function lists all of Apache's MIME handlers. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `type` · **required** · string (`system`, `user`) · e.g. `user` — Whether to retrieve system or user handlers.

**Returns** `data`: array of object

- *(array of objects)*
  - `extension` (string) — The handler's extension.
  - `handler` (string) — The handler's name.
  - `origin` (string) — The handler's owner.; system; user

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  list_handlers \
  type='user'
```

<a id="mime-redirect-info"></a>
### `Mime::redirect_info` — Return redirect information

`GET /execute/Mime/redirect_info` · RO · since cPanel 11.42

This function retrieves redirect information for a URL or `** All Public Domains **`. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain for which to retrieve redirector information.
- `url` · **required** · string <url> · e.g. `http://redirect.example.com` — The URL for which to retrieve redirector information.

**Returns** `data`: object

- `domain` (string or string <domain>) — The redirect's domain, or `** All Public Domains **`.; A valid domain.; `** All Public Domains **`
- `url` (string <url>) — The redirect's URL.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  redirect_info \
  url='http://redirect.example.com' \
  domain='example.com'
```

## Mime Type Management

<a id="mime-add-mime"></a>
### `Mime::add_mime` — Add MIME type to web server

`GET /execute/Mime/add_mime` · RW · rollback: clean · since cPanel 11.42

This function adds a MIME type to Apache. Important: When you disable the [Web Server](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `extension` · **required** · string · e.g. `.foo` — The file extension.
- `type` · **required** · string <MIME> · e.g. `text/foo` — The MIME type.

**Returns** `data`: object (`None`)

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  add_mime \
  type='text/foo' \
  extension='.foo'
```

<a id="mime-delete-mime"></a>
### `Mime::delete_mime` — Remove MIME type from web server

`GET /execute/Mime/delete_mime` · RW · rollback: none · since cPanel 11.42

This function removes a MIME type from Apache. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `type` · **required** · string · e.g. `text/foo` — The MIME type.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  delete_mime \
  type='text/foo'
```

<a id="mime-list-mime"></a>
### `Mime::list_mime` — Return web server's MIME types

`GET /execute/Mime/list_mime` · RO · since cPanel 11.42

This function lists all of Apache's MIME types. Note: This function does **not** list PHP versions with MIME types when the user or domain enables PHP-FPM. The system displays **only** custom MIME types. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `type` · **required** · string (`system`, `user`) · e.g. `user` — The MIME types to list.; `system` — List the Apache system MIME types.; `user` — List the Apache user MIME types.

**Returns** `data`: array of object

- *(array of objects)*
  - `extension` (string) — The file extension.
  - `origin` (string (`system`, `user`)) — The handler's owner.; `system`; `user`
  - `type` (string) — The MIME type.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  list_mime \
  type='user'
```

## Nova

<a id="nova-account-exists"></a>
### `Nova::account_exists` — Return Nova account status

`GET /execute/Nova/account_exists` · RO · since 110

This function returns whether the cPanel user has been provisioned on the AI App Builder (Nova), that is, whether the cPanel user file carries a Nova API token. Notes:  This function **requires** that your package includes the AI App Builder feature.

**Returns** `data`: integer (`1`, `0`) — Whether the cPanel user has a Nova account.; `1` - The cPanel user has a Nova account.; `0` - The cPanel user does not have a Nova account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  account_exists
```

<a id="nova-add-api-token"></a>
### `Nova::add_api_token` — Add an existing AI App Builder API token

`GET /execute/Nova/add_api_token` · RO/RW: unspecified · since 110

This function adds an existing AI App Builder API token to a cPanel user. Notes:  This function **requires** that your package includes the AI App Builder feature.; You can create an AI App Builder API token with the `Nova::create_account` function. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `api_token` · **required** · string <hexadecimal> · e.g. `d35d8ea651007ccd25f96486cdcdXXXX` — The AI App Builder API token to add.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  add_api_token \
  api_token='d35d8ea651007ccd25f96486cdcdXXXX'
```

<a id="nova-can-create-domains"></a>
### `Nova::can_create_domains` — Return domain creation availability

`GET /execute/Nova/can_create_domains` · RO · since 110

This function returns whether a cPanel account can create new subdomains or addon domains. Notes:  This function **requires** that your package includes the AI App Builder feature.; Creating a new addon domain depends on the creation of subdomains. If the cPanel account has reached its limit for subdomains, you **cannot** create a new addon domain. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Returns** `data`: integer (`1`, `0`) — Whether the cPanel user can create a new subdomain or addon domain.; `1` - The cPanel user can create a new subdomain or addon domain.; `0` - The cPanel user cannot create a new subdomain or addon domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  can_create_domains
```

<a id="nova-create-account"></a>
### `Nova::create_account` — Create AI App Builder API key

`GET /execute/Nova/create_account` · RO/RW: unspecified · since 110

This function creates an AI App Builder API token for a cPanel account. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Returns** `data`: object

- `key` (string <hexadecimal>) — The AI App Builder API token for the cPanel account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  create_account
```

<a id="nova-disk-quota-check"></a>
### `Nova::disk_quota_check` — Return disk quota information

`GET /execute/Nova/disk_quota_check` · RO · since 110

This function checks whether a user has sufficient free space to back up the domain's document root. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `domain` · optional · string · e.g. `example.com` — The domain to use for the AI App Builder website.

**Returns** `data`: object

- `available_space` (integer) — The amount of space available in megabytes (MB).
- `can_backup` (integer (`1`, `0`)) — Whether the document root has enough space to make a backup.; `1` - There is enough space.; `0` - There is not enough space.
- `is_docroot_empty` (integer (`1`, `0`)) — Whether the document root is empty.; `1` - Document root is empty.; `0` - Document root is not empty.
- `required_space` (integer) — The amount of space required in megabytes (MB) for a document root backup.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  disk_quota_check
```

<a id="nova-ensure-account"></a>
### `Nova::ensure_account` — Return Nova account SSO URL

`GET /execute/Nova/ensure_account` · RO/RW: unspecified · since 110

This function ensures that an AI App Builder account exists for the caller, then returns an SSO URL. The system reuses existing accounts. For entitled accounts of any tier, the system usually provisions the account eagerly, asynchronously, during account creation or package upgrades. This function is a fail-safe: it provisions the account on the spot for any entitled caller the eager provisioning hasn't already covered. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `colorScheme` · optional · string (`light`, `dark`, `auto`) · e.g. `light` — The color scheme Meridian is using, so Nova can match it.
- `domain` · optional · string · e.g. `example.com` — The domain to use for the AI App Builder website.
- `promptToken` · optional · string — A base64-encoded prompt token to pre-populate the user's website generation goals. This allows hosting companies to collect user intent before SSO and pass it through to the Nova interface. **Requirements:**; Valid base64 encoding — You can use standard or URL-safe variants.; Maximum 5000 characters after the system decodes it.; Non-empty content — The system ignores empty or whitespace-only prompts. **Example use case:** A hosting company builds a custom landing page that asks, "What kind of website do you want to create?" The user's response is base64-encoded and passed via this parameter, allowing Nova to use it as the initial generation prompt.
- `return_url` · optional · string — Where Nova's "Back to cPanel" control returns the user. Required for a regular account and rejected for a standalone one. Must be an https URL of at most 2048 characters, on the host the request was made to, with the path "/frontend/meridian/index.html" (optionally prefixed by a cPanel session token) and the in-product route in the fragment.

**Returns** `data`: object

- `created` (integer (`1`, `0`)) — Whether the system created a new AI App Builder account.
- `sso_url` (string) — The SSO link to the AI App Builder.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  ensure_account \
  return_url='https://hostname.example.com:2083/frontend/meridian/index.html#/websites'
```

<a id="nova-get-all-user-nova-info"></a>
### `Nova::get_all_user_nova_info` — Return AI App Builder domains

`GET /execute/Nova/get_all_user_nova_info` · RO · since 110

This function returns the AI App Builder domains' information for the cPanel account. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `domain` · optional · string · e.g. `example.com` — The domain to use for the AI App Builder website. When you specify a domain, the function returns information for that domain only. Otherwise, it returns information for every domain on the account.

**Returns** `data`: any

- *(array of objects)*
  - `domain` (string) — The name of the cPanel user's domain.
  - `metadata` (object) — 
    - `company` (string) — The website's company.
    - `cpanelDomainGUID` (string) — The cPanel user's domain.
    - `document_root` (string) — The absolute path to the domain's document root directory.
    - `fullcms` (integer (`1`, `0`)) — Whether the full AI App Builder Content Management System is enabled.; `1` - Full CMS is enabled.; `0` - Full CMS is disabled.
    - `language` (string <ISO-639>) — The language selection for the AI App Builder Content Management System.
    - `latest_publish_date` (integer <unix-timestamp>) — The last successful publication of the AI App Builder domain in Unix time format.
    - `publish_status` (integer (`1`, `0`)) — Whether the AI App Builder domain is published.; `1` - Website is published.; `0` - Website is not published.
    - `session_minted_at` (integer <unix-timestamp>) — When an AI App Builder session was last created for this domain, in Unix time format.
    - `websiteId` (integer) — The website ID of the created website.
  - `quota` (object) — 
    - `available_space` (integer) — The amount of space available in megabytes (MB).
    - `can_backup` (integer (`1`, `0`)) — Whether the document root has enough space to make a backup.; `1` - There is enough space.; `0` - There is not enough space.
    - `is_docroot_empty` (integer (`1`, `0`)) — Whether the document root is empty.; `1` - Document root is empty.; `0` - Document root is not empty.
    - `required_space` (integer) — The amount of space required in megabytes (MB) for a document root backup.
  - `redirection_enabled` (integer (`1`, `0`)) — Whether the domain redirects to another URL.; `1` - Redirects.; `0` - Doesn't redirect.
  - `shared_doc_root` (integer (`1`, `0`)) — Whether the AI App Builder domain shares its document root.; `1` - The document root is shared.; `0` - The document root is not shared.
  - `status` (object) — 
    - `has_nova_published` (integer (`1`, `0`)) — Whether the AI App Builder website is published.; `1` - AI App Builder website is published.; `0` - AI App Builder website is not published.
    - `has_nova_session` (integer (`1`, `0`)) — Whether an AI App Builder session has been started for this domain.
    - `has_nova_website` (integer (`1`, `0`)) — Whether an AI App Builder website exists for this domain.; `1` - An AI App Builder website exists.; `0` - No AI App Builder website exists.
    - `is_nova` (integer (`1`, `0`)) — Whether the domain's document root directory's `index.html` file contains AI App Builder deployed content.; `1` - User has an AI App Builder website.; `0` - User does not have an AI App Builder website.
    - `ssl_status` (integer (`1`, `0`)) — Whether the domain has a valid SSL certificate.; `1` - Domain has a valid SSL certificate.; `0` - Domain does not have a valid SSL certificate or certificate is invalid.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  get_all_user_nova_info
```

<a id="nova-get-sso-link"></a>
### `Nova::get_sso_link` — Return AI App Builder SSO URL

`GET /execute/Nova/get_sso_link` · RO/RW: unspecified · since 110

This function returns an AI App Builder website's SSO URL. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `colorScheme` · optional · string (`light`, `dark`, `auto`) · e.g. `light` — The color scheme Meridian is using, so Nova can match it.
- `domain` · optional · string · e.g. `example.com` — The domain to use for the AI App Builder website.
- `promptToken` · optional · string — A base64-encoded prompt token to pre-populate the user's website generation goals. This allows hosting companies to collect user intent before SSO and pass it through to the Nova interface. **Requirements:**; Valid base64 encoding — You can use standard or URL-safe variants.; Maximum 5000 characters after the system decodes it.; Non-empty content — The system ignores empty or whitespace-only prompts. **Example use case:** A hosting company builds a custom landing page that asks, "What kind of website do you want to create?" The user's response is base64-encoded and passed via this parameter, allowing Nova to use it as the initial generation prompt.
- `return_url` · optional · string — Where Nova's "Back to cPanel" control returns the user. Required for a regular account and rejected for a standalone one. Must be an https URL of at most 2048 characters, on the host the request was made to, with the path "/frontend/meridian/index.html" (optionally prefixed by a cPanel session token) and the in-product route in the fragment.

**Returns** `data`: string — The SSO link to the AI App Builder.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  get_sso_link \
  promptToken='SSB3YW50IHRvIGNyZWF0ZSBhIHBvcnRmb2xpbyB3ZWJzaXRlIGZvciBteSBwaG90b2dyYXBoeSBidXNpbmVzcw=='
```

<a id="nova-get-tier"></a>
### `Nova::get_tier` — Return the user's Nova tier snapshot

`GET /execute/Nova/get_tier` · RO · since 110

This function returns the cPanel user's AI App Builder (Nova) tier snapshot for tier display and upsell. Notes:  This function **requires** that your package includes the AI App Builder feature.; The Meridian theme gates the Nova interface on the `nova` feature itself; this read-only call only feeds tier-aware display.

**Returns** `data`: object — The user's Nova tier snapshot.

- `tier` (string) — The user's effective AI App Builder tier (the AI_APP_BUILDER_TIER value from the cpuser file), or an empty string if none.
- `account_exists` (integer (`1`, `0`)) — Whether the user has been provisioned on Nova.; `1` - The user has a Nova account.; `0` - The user does not have a Nova account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  get_tier
```

<a id="nova-poll-publish"></a>
### `Nova::poll_publish` — Return AI App Builder publication process

`GET /execute/Nova/poll_publish` · RO/RW: unspecified · since 110

This function polls the publishing progress information. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `file_name` · **required** · string · e.g. `/home/cpuser/logs/nova_publish_2024-02-02T16:46:58.log` — The publish process's log file name. Note: This is the full path to the log file.
- `pid` · **required** · integer · e.g. `123456` — The publish action's process ID, as returned by the `publish` function. Note: This value must be a positive integer. The system reports `is_running` as `0` unless this process ID belongs to a running process on this account.

**Returns** `data`: object

- `failed` (integer (`1`, `0`)) — Tracks the publishing process failure status.; `1` - AI App Builder publishing process failed.; `0` - AI App Builder publishing process succeeded.
- `is_running` (integer (`1`, `0`)) — Whether the publishing process is running.; `1` - AI App Builder publishing process is currently running.; `0` - AI App Builder publishing process is not running.
- `log` (array of string) — The publishing log's content as an array of lines.
- `progress` (integer) — Tracks the publishing process completion percentage.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  poll_publish \
  file_name='/home/cpuser/logs/nova_publish_2024-02-02T16:46:58.log' \
  pid='123456'
```

<a id="nova-publish"></a>
### `Nova::publish` — Run AI App Builder domain publication

`GET /execute/Nova/publish` · RO/RW: unspecified · since 110

This function publishes an AI App Builder website to the document root directory for the selected domain. Note: This function **requires** that your package includes the AI App Builder feature. Important: When you disable the AI App Builder feature, the system **disables** this function.

**Parameters**

- `archiveUrl` · **required** · string · e.g. `https://example.com/archive.zip` — URL to download the website archive from.
- `domain` · **required** · string · e.g. `example.com` — The domain to use for the AI App Builder website.
- `signature` · **required** · string · e.g. `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6` — Security signature for request validation.
- `userId` · **required** · string · e.g. `nova_a1b2c3d4e5f6g7h8` — Unique identifier for the website.
- `cleanup` · optional · integer · default `0` · e.g. `1` — Whether to cleanup the domain's `document_root` directory during the publication process.; `1` — Remove previous files in domain's `document_root` directory during the publication process.; `0` — Do **not** remove any files in domain's `document_root` directory during the publication process.

**Returns** `data`: object

- `file_name` (string) — The publish process's log file name.
- `pid` (integer) — The publish action's process ID.
- `user` (string) — The cPanel account's username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Nova \
  publish \
  domain='example.com'
```

## Sitejet

<a id="sitejet-add-api-token"></a>
### `Sitejet::add_api_token` — Add an existing Sitejet API token.

`GET /execute/Sitejet/add_api_token` · RO/RW: unspecified · since 110

This function adds an existing Sitejet API token to a cPanel user. Note: You can create a Sitejet API token with the `Sitejet:create_account` function.

**Parameters**

- `api_token` · **required** · string <hexadecimal> · e.g. `d35d8ea651007ccd25f96486cdcdXXXX` — The Sitejet API token to add.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  add_api_token \
  api_token='d35d8ea651007ccd25f96486cdcdXXXX'
```

<a id="sitejet-can-create-domains"></a>
### `Sitejet::can_create_domains` — Return Domain Availability

`GET /execute/Sitejet/can_create_domains` · RO · since 110

This function returns whether a cPanel account can create new subdomains or addon domains. Note: Creating a new addon domain is dependent on the creation of subdomains. If the cPanel account has reached its limit for subdomains, you cannot create a new addon domain, even if the limit for addon domains has not been reached.

**Returns** `data`: any (`1`, `0`) — Whether the cPanel user can create a new subdomin or addon domain.; `1` - The cPanel user can create a new subdomain or addon domain.; `0` - The cPanel user can not create a new subdomain or addon domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  can_create_domains
```

<a id="sitejet-create-account"></a>
### `Sitejet::create_account` — Generate a Sitejet API key.

`GET /execute/Sitejet/create_account` · RO/RW: unspecified · since 110

This function creates a Sitejet API token for a cPanel account.

**Returns** `data`: object

- `key` (string <hexadecimal>) — The Sitejet API token for the cPanel account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  create_account
```

<a id="sitejet-create-restore-point"></a>
### `Sitejet::create_restore_point` — Create a restore point.

`GET /execute/Sitejet/create_restore_point` · RO/RW: unspecified · since 120

This function creates a restore point for a domain's document root and removes the domain's files.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — A cPanel account's domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  create_restore_point \
  domain='example.com'
```

<a id="sitejet-create-website"></a>
### `Sitejet::create_website` — Create Sitejet domain ID

`GET /execute/Sitejet/create_website` · RO/RW: unspecified · since 110

This function creates a Sitejet ID for the specified domain. Note: A unique Sitejet ID is assigned to each domain on the cPanel account.

**Parameters**

- `company` · **required** · string · e.g. `cPanel` — The name of the company the website represents.
- `domain` · **required** · string · e.g. `example.com` — A cPanel account's domain.
- `assignTo` · optional · string <email> · e.g. `SallySmith@example.com` — Assign website to other user.
- `city` · optional · string · e.g. `Capitol City` — The city where the company or website owner is located.
- `country` · optional · string <ISO-3166> · e.g. `US` — The country where the company or website owner is located.
- `email` · optional · string <email> · e.g. `JohnSmith@example.com` — The email address of the website owner.
- `firstname` · optional · string · e.g. `John` — The first name of the website owner.
- `language` · optional · string <ISO-639> · e.g. `en` — The language to use for the Sitejet Website Builder.
- `lastname` · optional · string · e.g. `Smith` — The last name of the website owner.
- `metadata` · optional · string <encoded JSON> · e.g. `{"Attribute1":9,"Attribute2":3,"Attribute3":5}` — Additional metadata for the website.
- `note` · optional · string · e.g. `This is my website for my business.` — Additional notes about the website.
- `phone` · optional · string · e.g. `000-123-4567` — The phone number of the company or website owner.
- `street` · optional · string · e.g. `1234 Main St` — The street address of the company or website owner.
- `title` · optional · string · e.g. `Example Website` — The website title.
- `zip` · optional · string · e.g. `99999` — The zip code where the company or website owner is located.

**Returns** `data`: object

- `websiteID` (integer) — The website ID of the created website.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  create_website \
  domain='example.com' \
  company='cPanel'
```

<a id="sitejet-get-all-user-sitejet-info"></a>
### `Sitejet::get_all_user_sitejet_info` — Return Sitejet domains

`GET /execute/Sitejet/get_all_user_sitejet_info` · RO/RW: unspecified · since 110

This function returns the Sitejet domains' information for the cPanel account.

**Parameters**

- `domain` · optional · string · e.g. `example.com` — The single domain to return Sitejet information.

**Returns** `data`: any

- *(array of objects)*
  - `domain` (string) — The name of the cPanel user's domain.
  - `metadata` (object) — 
    - `company` (string) — The website's comapany.
    - `cpanelDomainGUID` (string) — The cPanel user's domain.
    - `fullcms` (any (`1`, `0`)) — Whether the full Sitejet Content Management System is enabled.; `1` - Full CMS is enabled.; `0` - Full CMS is disabled.
    - `language` (string <ISO-639>) — The language selection for the Sitejet Content Management System.
    - `latest_publish_date` (integer <unix-timestamp>) — The last successful publication of the Sitejet domain in Unix time format.
    - `publish_status` (integer (`1`, `0`)) — Whether the Sitejet domain is published.; `1` - Website is published.; `0` - Website is not published.
    - `websiteId` (integer) — The website ID of the created website.
  - `quota` (object) — 
    - `available_space` (integer) — The amount of space available in megabytes (MB).
    - `can_backup` (any (`1`, `0`)) — Whether the document root has enough space to make a backup.; `1` - There is enough space.; `0` - There is not enough space.
    - `is_empty_docroot` (any (`1`, `0`)) — Whether the document root is empty.; `1` - Document root is empty.; `0` - Document root is not empty.
    - `required_space` (integer) — The amount of space required in megabytes (MB) for a document root backup.
  - `redirection_enabled` (integer (`1`, `0`)) — Whether the domain redirects to another URL.; 1 - Redirects.; 0 - Doesn't redirect.
  - `shared_doc_root` (integer (`1`, `0`)) — whether the sitejet domain is sharing the document_root.; 1 - document_root is shared.; 0 - document_root is not shared.
  - `is_restore_point_available` (integer (`1`, `0`)) — Whether the sitejet domain has a restore point.; `1` – Restore point is available.; `0` – Restore point is not available.
  - `is_temporary_domain` (integer (`1`, `0`)) — Whether the domain is a temporary domain (for example, cpanel.site).; `1` – Domain is a temporary domain.; `0` – Domain is not a temporary domain.
  - `status` (object) — 
    - `has_sitejet_published` (integer (`1`, `0`)) — Whether the Sitejet website is published.; `1` - Sitejet website is published.; `0` - Sitejet website is not published.
    - `has_sitejet_website` (integer (`1`, `0`)) — Whether the domain's document root diretory contains a Sitejet directory.; `1` - User has created a Sitejet website.; `0` - User has not created a Sitejet website.
    - `is_sitejet` (integer (`1`, `0`)) — Whether the domain's document root diretory's `index.html` file contains Sitejet deployed content.; `1` - User has a Sitejet website.; `0` - User does not have a Sitejet website.
    - `ssl_status` (integer (`1`, `0`)) — Whether the domain has a valid SSL certificate.; `1` - Domain has a valid SSL certificate.; `0` - Domain does not have a valid SSL certificate or certificate is invalid.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  get_all_user_sitejet_info
```

<a id="sitejet-get-api-token"></a>
### `Sitejet::get_api_token` — Return Sitejet API token

`GET /execute/Sitejet/get_api_token` · RO/RW: unspecified · since 110

This function returns the cPanel account's Sitejet API token.

**Returns** `data`: string <hexadecimal> — The cPanel account's Sitejet API token.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  get_api_token
```

<a id="sitejet-get-preview-url"></a>
### `Sitejet::get_preview_url` — Return Sitejet preview URL

`GET /execute/Sitejet/get_preview_url` · RO/RW: unspecified · since 110

This function returns a Sitejet website's preview URL.

**Parameters**

- `websiteId` · **required** · integer · e.g. `123456` — The Sitejet website ID for the domain.

**Returns** `data`: string <URL> — The Sitejet website's preview URL.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  get_preview_url \
  websiteId='123456'
```

<a id="sitejet-get-sso-link"></a>
### `Sitejet::get_sso_link` — Return Sitejet SSO URL

`GET /execute/Sitejet/get_sso_link` · RO/RW: unspecified · since 110

This function returns a Sitejet website's SSO URL.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The cPanel account's Sitejet domain.
- `referrer` · **required** · string — The cPanel interface referral URL.
- `ui_mode` · optional · string (`prompt`, `ai`, `template`) · e.g. `prompt` — Specifies which Sitejet SaaS user interface mode the user will be redirected to.

**Returns** `data`: string — The SSO link to the Sitejet CMS.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  get_sso_link \
  domain='example.com' \
  referrer='https://example.com:2083/cpsess##########/frontend/jupiter/sitejet/index.html%23'
```

<a id="sitejet-get-templates"></a>
### `Sitejet::get_templates` — Return Sitejet templates

`GET /execute/Sitejet/get_templates` · RO/RW: unspecified · since 110 · **DEPRECATED**

This function fetches the list of available Sitejet templates.

**Returns** `data`: any

- *(array of objects)*
  - `createdAt` (string <date-time>) — The templates creation date.
  - `description` (string) — The template's description.
  - `id` (integer) — The template's ID.
  - `image` (string) — The relative path to the template image on the SiteJet CMS website.
  - `name` (string) — The template's name.
  - `previewUrl` (string) — The website's preview URL.
  - `tags` (array of string) — The template's catagory search tags.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  get_templates
```

<a id="sitejet-is-publish-in-progress"></a>
### `Sitejet::is_publish_in_progress` — Check whether a Sitejet publish is running

`GET /execute/Sitejet/is_publish_in_progress` · RO/RW: unspecified · since 110

This function reports whether a Sitejet publish is currently running for a domain, and under which process ID.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The domain for the Sitejet website.

**Returns** `data`: object

- `in_progress` (integer (`1`, `0`)) — - `1` - A publish is currently running for the domain.; `0` - No publish is running for the domain.
- `pid` (integer) — The running publish process's ID.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  is_publish_in_progress \
  domain='example.com'
```

<a id="sitejet-restore-document-root"></a>
### `Sitejet::restore_document_root` — Restore a domain from the restore point.

`GET /execute/Sitejet/restore_document_root` · RO/RW: unspecified · since 120

This function reverts a document root to the restore point.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — A cPanel account's domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  restore_document_root \
  domain='example.com'
```

<a id="sitejet-set-template"></a>
### `Sitejet::set_template` — Update Sitejet template

`GET /execute/Sitejet/set_template` · RO/RW: unspecified · since 110 · **DEPRECATED**

This function sets a Sitejet website's template.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — A cPanel account's domain.
- `templateId` · **required** · string · e.g. `12345` — The Sitejet template's ID.
- `templateName` · **required** · string · e.g. `A great template` — The Sitejet template name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  set_template \
  domain='example.com' \
  templateId='12345'
  templateName='A great template'
```

<a id="sitejet-start-publish"></a>
### `Sitejet::start_publish` — Publish Sitejet domain

`GET /execute/Sitejet/start_publish` · RO/RW: unspecified · since 110

This function publishes a domain's Sitejet website.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The domain for the Sitejet website.
- `cleanup` · optional · integer · e.g. `1` — Whether to cleanup the domain's `document_root` directory during the publication process.; `1` — Remove previous files in domain's `document_root` directory during the publication process.; `0` — Do **not** remove any files in domain's `document_root` directory during the publication process.

**Returns** `data`: object

- `file_name` (string) — **Deprecated.** The publish process's log file name.
- `pid` (integer) — The publish action's process ID.

```bash
uapi --output=jsonpretty \
  --user=username \
  Sitejet \
  start_publish \
  domain='example.com'
```

## WPX

<a id="wpx-change-admin-password"></a>
### `WPX::change_admin_password` — Update WordPress administrator password

`POST /execute/WPX/change_admin_password` · RO/RW: unspecified · since 137

This function sets a new password for a WordPress administrator of an installation that the caller owns. Note:  Over HTTP this function accepts only the `POST` method, and it rejects any request that carries a `password` key in the URL query string. It checks both before it reads the password, so the password cannot reach an access log, a proxy log, or the browser history. The Perl bindings and the `uapi` command-line tool set no request method and no query string, so they are unaffected.; The system passes the password to WordPress through a file that only the caller can read, so it never appears in a process list, in the process environment, or in the WordPress Toolkit logs.; The system applies no password-strength rule of its own. Any non-empty value is accepted.; The system verifies that the caller owns the installation before it changes anything.

**Request body** (`application/x-www-form-urlencoded`)

- `id` (integer) — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.
- `login` (string) — The WordPress administrator login to change.
- `password` (string) — The new WordPress administrator password.

**Returns** `data`: object — Confirmation of the change, and the administrator it applied to.

- `changed` (integer (`1`)) — Always `1`.
- `id` (integer) — The installation id that the system changed.
- `login` (string) — The WordPress administrator login whose password changed.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  change_admin_password \
  id='17' \
  password='EXAMPLE-PASSWORD-PLACEHOLDER'
```

<a id="wpx-create-nova-for-wordpress-website"></a>
### `WPX::create_nova_for_wordpress_website` — Start a Nova for WordPress walkthrough

`POST /execute/WPX/create_nova_for_wordpress_website` · RO/RW: unspecified · since 137

This function starts a Nova for WordPress walkthrough for the specified domain. It creates a cPanel API token and creates a Nova magic link whose callback points directly at UAPI's `import_website` function, then returns the magic link. It does **not** install WordPress. The user is sent straight to Nova for WordPress, which builds the site and publishes it back into the account via UAPI's `import_website` function. Note:  This function requires the `nova-wordpress` entitlement.; This function requires the `mysql` feature, because the WordPress install provisions a MySQL database.; This function also requires the `redirects` feature. An account without it receives a synchronous error before any token is created or any install task is queued.; This function requires the `apitokens` feature, because the walkthrough creates a cPanel API token.; If the domain already has one or more WordPress installations, the function returns a `collision` response listing the existing installations so the caller can prompt the user to remove them and retry.; The function refuses the call when the account has too little free disk space for a WordPress installation. That check runs before the token creation, so a refusal never leaves a live token behind.; Unlike `create_website`, this function does **not** enforce the account's maximum WordPress website count. That limit is a WordPress Toolkit plan constraint, and the Nova walkthrough deliberately does not gate on it.; If the Nova call fails after the token is created, the system revokes the token and returns an error, so a failed walkthrough leaves no live token.

**Request body** (`application/x-www-form-urlencoded`)

- `colorScheme` (string (`light`, `dark`, `auto`, ``)) — The color scheme the caller's interface is using, so Nova for WordPress opens in the same theme.
- `domain` (string) — The domain on which to start the WordPress walkthrough.
- `promptToken` (string) — A base64-encoded website-building prompt that Nova for WordPress opens with, pre-filled.
- `return_url` (string <uri>) — The URL to which Nova returns the user after the walkthrough.

**Returns** `data`: object — On the normal start path the object contains the `magic_link` return value.

- `domain` (string) — The domain, normalized to lowercase.
- `existing_installations` (array of object) — The WordPress installations that already exist on the domain.
  - *(array of objects)*
    - `id` (integer) — The WordPress Toolkit installation id.
    - `url` (string) — The site URL of the existing WordPress installation.
- `magic_link` (string) — The Nova magic link the user follows to continue the walkthrough.
- `status` (string (`collision`)) — This value only returns when the function detects an existing installation on the domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  create_nova_for_wordpress_website \
  domain='example.com'
```

<a id="wpx-create-website"></a>
### `WPX::create_website` — Start a new WordPress installation on a domain

`POST /execute/WPX/create_website` · RO/RW: unspecified · since 137

This function starts a new WordPress installation on a domain that the caller owns. The installation runs in the background, so the function returns as soon as it queues the task. Note:  Poll progress with `get_task_progress` and the returned `install_id` value. That works with a cPanel API token, unlike the `sse_url` stream, which needs an interactive cPanel session.; A domain that already has a WordPress installation is **not** an error. The call succeeds with the `status` field set to `collision` and lists the existing installations, and it queues nothing. To replace the existing site, call `remove_installation` for each entry in the `existing_installations` field, then call this function again.; The `data.status` field reports the outcome of this call. Do not confuse it with the `result.status` field, which reports whether the call itself succeeded.; This function needs the `redirects` and `mysql` features in addition to the `wp-toolkit` feature that the whole module needs. It also refuses the call when the account has too little free disk space, or when the account already holds as many WordPress websites as its plan allows.; The background task can still fail after this function returns, for example when a feature is revoked in the meantime. Read the outcome from `get_task_progress`.

**Request body** (`application/x-www-form-urlencoded`)

- `domain` (string) — The domain to install WordPress on.
- `title` (string) — The WordPress site title.

**Returns** `data`: object — On the normal start path the object contains the `status`, `domain`, `task_id`, `sse_url`, and `install_id` return values.

- `domain` (string) — The domain, normalized to lowercase.
- `existing_installations` (array of object) — The WordPress installations that already exist on the domain.
  - *(array of objects)*
    - `id` (integer) — The WordPress Toolkit installation id.
    - `url` (string) — The site URL of the existing installation.
- `install_id` (string) — The unique correlator for the installation run.
- `sse_url` (string) — The path to the Server-Sent Events stream that reports installation progress.
- `status` (string (`running`, `collision`)) — The outcome of this call.; `running` - The system queued the installation task.
- `task_id` (string) — The queued installation task id.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  create_website \
  domain='example.com'
```

<a id="wpx-get-admin-account"></a>
### `WPX::get_admin_account` — Return WordPress administrator account

`GET /execute/WPX/get_admin_account` · RO/RW: unspecified · since 137

This function returns the WordPress administrator account details for an installation that the caller owns: the administrator logins, the first administrator's display name and email address, and the login URL. The WordPress administration settings form uses it to fill in current values. Note:  The stored WordPress password is never returned. Use `change_admin_password` to set a new one, and `get_credentials` to sign in without a password.; The system verifies that the caller owns the installation before it reads anything.; When the installation has no WordPress administrator, the `current_user_id` field is `null`, the other text fields are empty strings, and the `available_logins` field is an empty array. A failure to read the administrator list is different: it returns a failure status with a message in the `errors` field.; The active WordPress language is not part of this response. Use `set_language` to change it.

**Parameters**

- `id` · **required** · integer — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.

**Returns** `data`: object — The administrator account details for the installation.

- `available_logins` (array of string) — Every WordPress administrator login on the installation.
- `current_display_name` (string) — The first administrator's WordPress display name, or an empty string.
- `current_email` (string) — The first administrator's WordPress email address, or an empty string.
- `current_login` (string) — The first administrator's WordPress login, or an empty string.
- `current_user_id` (integer) — The first administrator's WordPress user id, or `null` when the installation has no administrator.
- `login_url` (string) — The WordPress administrator login URL.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  get_admin_account \
  id='17'
```

<a id="wpx-get-credentials"></a>
### `WPX::get_credentials` — Return single-use WordPress login URL

`GET /execute/WPX/get_credentials` · RO/RW: unspecified · since 137

This function returns a single-use login URL for a WordPress installation that the caller owns. The URL carries a one-time token, so the caller does not need the WordPress administrator password. Note:  Each call mints a new token, so the function is not idempotent and two calls return two different URLs. A token is consumed the first time it is used.; The `login` and `password` fields are always empty. They exist so the response shape stays stable for callers that expect a credential pair. This function never returns a WordPress password.; The system verifies that the caller owns the installation before it mints a token.

**Parameters**

- `id` · **required** · integer — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.
- `panel_return_url` · optional · string <uri> — A cPanel URL to return the user to from the WordPress administration area. When the value passes validation, the system appends it to the login URL and the WordPress administration sidebar shows a link back to cPanel. The value is validated, and an unacceptable value is ignored rather than rejected. It must use the `https` scheme, must be 2048 characters or fewer, must not contain a `userinfo` (`@`) component, and its host must match the cPanel host that serves the request.

**Returns** `data`: object — The single-use login URL, with two always-empty credential fields.

- `login` (string) — Always an empty string.
- `login_url` (string) — The single-use WordPress login URL.
- `password` (string) — Always an empty string.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  get_credentials \
  id='17'
```

<a id="wpx-get-site-activity"></a>
### `WPX::get_site_activity` — Return WordPress installation activity

`GET /execute/WPX/get_site_activity` · RO/RW: unspecified · since 137

This function reports whether the account has done meaningful work on a WordPress installation it owns. A WordPress site goes live the moment it installs, and WordPress sends no event when real setup work finishes. So the system compares the live site to a fresh installation and reports the differences as flags. Note:  The `has_user_activity` field is the summary flag. It is `1` when the `authored_content` or `uploaded_media` field is `1`. The remaining three flags are informational and do not affect it.; This function is expensive. It starts WordPress once to collect every signal, and the system stops the attempt after 30 seconds.; A site whose WordPress cannot start, or that does not answer within the 30-second limit, reports every flag as `0`. This is not an error.; An `id` parameter that does not exist, or that belongs to another account, returns a failure status with a message in the `errors` field. The two cases are indistinguishable.; The system verifies that the caller owns the installation before it reads anything.

**Parameters**

- `id` · **required** · integer — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.

**Returns** `data`: object — The activity flags for the installation.

- `authored_content` (integer (`1`, `0`)) — Whether the site holds content that is not part of a fresh installation, or whether its seed content changed.
- `changed_appearance` (integer (`1`, `0`)) — Whether the site's appearance differs from a fresh installation.
- `extended_functionality` (integer (`1`, `0`)) — Whether the site added functionality beyond a fresh installation.
- `has_user_activity` (integer (`1`, `0`)) — Whether the account has done meaningful work on the site.
- `personalized_identity` (integer (`1`, `0`)) — Whether the site's identity, such as its tagline, logo, or site icon, differs from a fresh installation.
- `uploaded_media` (integer (`1`, `0`)) — Whether the site's media library holds at least one item.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  get_site_activity \
  id='17'
```

<a id="wpx-get-task-progress"></a>
### `WPX::get_task_progress` — Return WordPress task progress

`GET /execute/WPX/get_task_progress` · RO/RW: unspecified · since 137

This function returns the progress of a WordPress installation or import for the supplied `install_id` parameter. Note:  Use this function to read progress with a cPanel API token. The equivalent Server-Sent Events stream (the `sse_url` field) is only available to an interactive cPanel session, not to an API token.; `create_website` and `import_website` return the `install_id` in their normal-start responses. Those are the only two functions that return one. `create_nova_for_wordpress_website` queues no installation task and returns no `install_id` value; a Nova walkthrough gets one when its later `import_website` callback starts the import.; This function is the authoritative source for progress and for success or failure, and it still works after the task finishes, because it reads the run's progress log. `get_task_status` reads the task queue instead, so it can only report whether the task is still queued, and it cannot tell success from failure.

**Parameters**

- `install_id` · **required** · string — The unique correlator for the install or import run. The function that started the task returns it.

**Returns** `data`: object — The latest progress for the run.

- `message` (string) — The most recent human-readable progress or outcome message.
- `percentage` (integer) — The install or import progress, from 0 to 100.
- `status` (string (`unknown`, `running`, `complete`, `failed`)) — The run state.; `unknown` - No progress log exists yet, or the `install_id` value is not the caller's.; `running` - The run is in progress.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  get_task_progress \
  install_id='1784237244-988110-12345'
```

<a id="wpx-get-task-status"></a>
### `WPX::get_task_status` — Return background task status

`GET /execute/WPX/get_task_status` · RO/RW: unspecified · since 137

This function reports whether a queued background task is still in the caller's task queue. It answers only that one question. Note:  This function and `get_task_progress` are a pair, and they are not interchangeable. `get_task_status` takes a `task_id`, reads the task queue, and reports only whether the task is still queued. It cannot tell you whether the work succeeded. `get_task_progress` takes an `install_id` parameter, reads the run's progress log, and is the authoritative source for progress and for success or failure. Prefer `get_task_progress` unless you specifically need to know whether the task is still queued.; A `task_id` parameter that is absent from the queue returns `done`. A finished task, a removed task, a task that never existed, and a task that belongs to another account are indistinguishable, and all four return `done`. There is no not-found failure.; Ownership needs no check: the queue lives in the caller's own home directory, so the caller can only ever see its own tasks.

**Parameters**

- `task_id` · **required** · string — The task id, as returned in the `task_id` field of `create_website` or `import_website`.

**Returns** `data`: object — The queue state of the task.

- `message` (string (`running`, `not found`)) — A fixed, untranslated label that mirrors the `status` field.; `running` - The task is still queued.; `not found` - The task is no longer in the queue.
- `status` (string (`running`, `done`)) — Whether the task is still queued.; `running` - The task is still in the queue.; `done` - The task is not in the queue.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  get_task_status \
  task_id='00000000/63d7f020927f8f'
```

<a id="wpx-get-website"></a>
### `WPX::get_website` — Return WordPress installation

`GET /execute/WPX/get_website` · RO/RW: unspecified · since 137

This function returns a single WordPress installation, addressed by its numeric WordPress Toolkit instance `id` parameter. The returned row is identical to one element of the `list_websites` response, so the same consumer mapping works for both. Note:  This is a lightweight by-id read intended for resolving one installation directly, without listing every installation. A direct lookup is not subject to the brief eventual-consistency lag that can keep a freshly created installation out of `list_websites`.; A valid `id` parameter that does not exist, or that belongs to another account, is **not** an error: the call succeeds with an empty (`null`) `data` field. An installation owned by another account is indistinguishable from one that does not exist.; A missing or non-integer `id` parameter, or a backend failure, returns a failure status with a message in the `errors` field.

**Parameters**

- `id` · **required** · integer — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.

**Returns** `data`: object — The installation row, or `null` when no installation with the given `id` value is owned by the caller.

- `admin_url` (string) — The WordPress administrator login URL.
- `alive` (integer (`1`, `0`)) — Whether the installation is responding.
- `broken` (integer (`1`, `0`)) — Whether WordPress Toolkit reports the installation as broken.
- `documentroot` (string) — The filesystem path to the WordPress root.
- `domain` (string) — The normalized bare hostname of the site.
- `infected` (integer (`1`, `0`)) — Whether WordPress Toolkit reports the installation as infected.
- `outdated_php` (integer (`1`, `0`)) — Whether the installation runs an outdated PHP version.
- `outdated_wp` (integer (`1`, `0`)) — Whether the installation runs an outdated WordPress version.
- `title` (string) — The WordPress site title.
- `unsupported_php` (integer (`1`, `0`)) — Whether the installation runs an unsupported PHP version.
- `unsupported_wp` (integer (`1`, `0`)) — Whether the installation runs an unsupported WordPress version.
- `url` (string) — The public site URL.
- `version` (string) — The WordPress version.
- `wptk_id` (integer) — The WordPress Toolkit instance id.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  get_website \
  id='17'
```

<a id="wpx-has-reached-quota"></a>
### `WPX::has_reached_quota` — Return WordPress disk quota status

`GET /execute/WPX/has_reached_quota` · RO/RW: unspecified · since 137

This function reports whether the caller's disk usage is already at or near the limit that would block a new WordPress installation. The check reserves headroom for the install itself, so it can report `1` before the account has actually exceeded its quota. Note:  The onboarding flow calls this up front, before it offers to install WordPress, so it can explain the refusal instead of failing partway through `create_website`.; This function takes no parameters and has no failure path of its own, beyond the `wp-toolkit` feature that every function in this module needs. A caller that holds the feature always gets a successful status.; `create_website` repeats the same check and refuses with an error when the quota blocks the install.

**Returns** `data`: object — The quota verdict for the caller's account.

- `has_reached_quota` (integer (`1`, `0`)) — Whether the account has too little free disk space for a new WordPress installation.; `1` - The account cannot fit another installation.; `0` - The account has room for another installation.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  has_reached_quota
```

<a id="wpx-import-website"></a>
### `WPX::import_website` — Import an existing WordPress site

`POST /execute/WPX/import_website` · RO/RW: unspecified · since 137

This function imports an existing WordPress site to your cPanel account. The import runs in the background, so the function returns as soon as it queues the task. Note:  This function has the following prerequisites: The `nova-wordpress` entitlement.; The `redirects`, `wp-toolkit`, and `mysql` features.; Because the request carries the source WordPress credentials, use the `POST` method and do not place the `source_password` or `source_user` keys in the URL query string. The system rejects a request that uses another method, or that puts either key in the query string, before it reads the credentials, so they cannot leak into access logs, proxy logs, or browser history.; The background task can still fail after this function returns, for example when a feature is revoked in the meantime. Read the outcome from the `WPX::get_task_progress` function.

**Request body** (`application/x-www-form-urlencoded`)

- `domain` (string) — The destination domain for the import.
- `overwrite` (integer (`1`, `0`)) — Whether to overwrite an existing WordPress installation at the destination.; `1` - Overwrite.; `0` - Do not overwrite.
- `password_type` (string (`admin`, `application`)) — The password type supplied in the `source_password` parameter.; `admin` - A WordPress administrator user password.; `application` - A service account password for a third-party integration.
- `source_password` (string) — The WordPress user's password for the source site.
- `source_url` (string <uri>) — The URL of the source WordPress site to import.
- `source_user` (string) — The WordPress username for the source site.

**Returns** `data`: object — On the normal start path the object contains the `status`, `domain`, `task_id`, `sse_url`, and `install_id` return values.

- `domain` (string) — The destination domain, normalized to lowercase.
- `existing_installations` (array of object) — The WordPress installations that already exist on the domain.
  - *(array of objects)*
    - `id` (integer) — The WordPress Toolkit installation id.
    - `url` (string) — The site URL of the existing installation.
- `install_id` (string) — The unique correlator for the import run.
- `sse_url` (string) — The path to the Server-Sent Events stream that reports import progress.
- `status` (string (`running`, `collision`)) — The outcome of this call.; `running` - The system queued the import task.
- `task_id` (string) — The queued import task id.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  import_website \
  source_url='https://subdomain.example.net' \
  source_user='admin_abcd' \
  source_password='EXAMPLE-PASSWORD-PLACEHOLDER' \
  domain='example.com'
```

<a id="wpx-list-websites"></a>
### `WPX::list_websites` — Return WordPress installations

`GET /execute/WPX/list_websites` · RO/RW: unspecified · since 137

This function returns the caller's WordPress installations. Each row is identical in shape to the `get_website` response `data`, so the same consumer mapping works for both. Note:  Ownership is enforced by filesystem path: only installations under the caller's home directory are returned.; Each row carries the installation's health as flat flags (`alive`, `broken`, `infected`, `outdated_php`, `outdated_wp`, `unsupported_php`, `unsupported_wp`), taken directly from WordPress Toolkit.

**Returns** `data`: object — The installations and summary counts.

- `domains` (array of object) — The caller's WordPress installations.
  - *(array of objects)*
    - `admin_url` (string) — The WordPress administrator login URL.
    - `alive` (integer (`1`, `0`)) — Whether the installation is responding.
    - `broken` (integer (`1`, `0`)) — Whether WordPress Toolkit reports the installation as broken.
    - `documentroot` (string) — The filesystem path to the WordPress root.
    - `domain` (string) — The normalized bare hostname of the site.
    - `infected` (integer (`1`, `0`)) — Whether WordPress Toolkit reports the installation as infected.
    - `outdated_php` (integer (`1`, `0`)) — Whether the installation runs an outdated PHP version.
    - `outdated_wp` (integer (`1`, `0`)) — Whether the installation runs an outdated WordPress version.
    - `title` (string) — The WordPress site title.
    - `unsupported_php` (integer (`1`, `0`)) — Whether the installation runs an unsupported PHP version.
    - `unsupported_wp` (integer (`1`, `0`)) — Whether the installation runs an unsupported WordPress version.
    - `url` (string) — The public site URL.
    - `version` (string) — The WordPress version.
    - `wptk_id` (integer) — The WordPress Toolkit instance id.
- `info` (object) — Summary counts for the result set.
  - `disk_quota_reached` (integer (`1`, `0`)) — Whether the account has reached the disk quota that blocks a new install.
  - `results` (integer) — The number of installations returned.
  - `total` (integer) — The total number of installations.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  list_websites
```

<a id="wpx-remove-installation"></a>
### `WPX::remove_installation` — Delete a WordPress installation permanently

`POST /execute/WPX/remove_installation` · RO/RW: unspecified · since 137

This function permanently deletes a WordPress installation that the caller owns. It removes the site's files and its database. Note:  This action cannot be undone. There is no recycle bin, and the system keeps no copy of the files or the database.; The onboarding flow calls this to clear an existing installation before it retries `create_website`. When `create_website` reports a `collision`, call this function once for each entry in the `existing_installations` field, then call `create_website` again.; This function is not idempotent. A second call for the same `id` parameter fails, because the installation no longer exists.; The system verifies that the caller owns the installation before it deletes anything. An installation that belongs to another account is indistinguishable from one that does not exist.

**Request body** (`application/x-www-form-urlencoded`)

- `id` (integer) — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.

**Returns** `data`: object — Confirmation that the system deleted the installation.

- `id` (integer) — The installation id that the system deleted.
- `removed` (integer (`1`)) — Always `1`.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  remove_installation \
  id='17'
```

<a id="wpx-set-language"></a>
### `WPX::set_language` — Update WordPress installation language

`POST /execute/WPX/set_language` · RO/RW: unspecified · since 137

This function sets the active WordPress language for an installation that the caller owns. The system installs the translation files if the site does not already have them, then activates the locale. Note:  The system verifies that the caller owns the installation before it changes anything.; `get_admin_account` does not report the active language. There is no function that reads it back.

**Request body** (`application/x-www-form-urlencoded`)

- `id` (integer) — The WordPress Toolkit installation id, as returned in the `wptk_id` field of `list_websites`.
- `language` (string) — The WordPress locale to activate, for example `en_US`, `de_DE`, or `pt_BR`.

**Returns** `data`: object — The installation and the locale that is now active.

- `id` (integer) — The installation id that the system changed.
- `language` (string) — The locale that is now active.

```bash
uapi --output=jsonpretty \
  --user=username \
  WPX \
  set_language \
  id='17' \
  language='de_DE'
```

## Site Installation

<a id="wordpresssite-create"></a>
### `WordPressSite::create` — Install WordPress site

`GET /execute/WordPressSite/create` · RW · rollback: none · since cPanel 11.42

This function installs a WordPress site for cPanel user's primary domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressSite \
  create
```

## Site Information

<a id="wordpresssite-retrieve"></a>
### `WordPressSite::retrieve` — Return WordPress site information

`GET /execute/WordPressSite/retrieve` · RO · since cPanel 11.42

This function retrieves the installation status and detailed information of the WordPress site for cPanel user's primary domain.

**Returns** `data`: any — An object that contains the installation status and information for the WordPress site.

- *(array of objects)*
  - `details` (object) — Detailed information of the WordPress site.
  - `install_status` (string) — Installation status of the WordPress site.

```bash
uapi --output=jsonpretty \
  --user=username \
  WordPressSite \
  retrieve
```

