<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Server Information

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Notifications**: [`Notifications::get_notifications_count`](#notifications-get-notifications-count)
- **Password Strength**: [`PasswdStrength::get_required_strength`](#passwdstrength-get-required-strength)
- **SSH**: [`SSH::get_port`](#ssh-get-port), [`SSH::get_shell`](#ssh-get-shell)
- **cPanel Server Information**: [`ServerInformation::get_information`](#serverinformation-get-information)
- **Variables**: [`Variables::get_server_information`](#variables-get-server-information)
- **WebProsMCP**: [`WebProsMCP::get_connection_config`](#webprosmcp-get-connection-config), [`WebProsMCP::unlink_webpros_account`](#webprosmcp-unlink-webpros-account)

## Notifications

<a id="notifications-get-notifications-count"></a>
### `Notifications::get_notifications_count` — Return server notifications total

`GET /execute/Notifications/get_notifications_count` · RO · since cPanel 54

This function returns the number of server-wide notifications on an account.

**Returns** `data`: integer — The number of server-wide notifications.

```bash
uapi --output=jsonpretty \
  --user=username \
  Notifications \
  get_notifications_count
```

## Password Strength

<a id="passwdstrength-get-required-strength"></a>
### `PasswdStrength::get_required_strength` — Return minimum required password strength

`GET /execute/PasswdStrength/get_required_strength` · RO · since cPanel 11.42

This function retrieves an application's minimum required password strength.

**Parameters**

- `app` · **required** · string (`createacct`, `ftp`, `htaccess`, `mysql`, `passwd`, `pop`, `postgres`, `sshkey`, `webdisk`, `virtual`) · e.g. `webdisk` — The application's name.

**Returns** `data`: object

- `strength` (integer) — The application's minimum password strength.

```bash
uapi --output=jsonpretty \
  --user=username \
  PasswdStrength \
  get_required_strength \
  app='webdisk'
```

## SSH

<a id="ssh-get-port"></a>
### `SSH::get_port` — Return SSH port

`GET /execute/SSH/get_port` · RO · since cPanel 11.42

This function retrieves the server's SSH port.

**Returns** `data`: object

- `port` (integer) — The server's SSH port.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSH \
  get_port
```

<a id="ssh-get-shell"></a>
### `SSH::get_shell` — Return whether cPanel account has shell access

`GET /execute/SSH/get_shell` · RO · since cPanel 11.42

This function returns whether the cPanel account has shell access and the account's shell path.

**Returns** `data`: object

- `has_terminal_access` (boolean) — Whether the cPanel account has shell access.; `true` - Account has shell access.; `false` - Account does not have shell access.
- `shell` (string) — The cPanel account's shell path.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSH \
  get_shell
```

## cPanel Server Information

<a id="serverinformation-get-information"></a>
### `ServerInformation::get_information` — Return service and device status

`GET /execute/ServerInformation/get_information` · RO · since cPanel 82

This function returns the status of each [cPanel service (daemon)](https://go.cpanel.net/ThecPanelWHMServiceDaemons), device, and server health check point on your server.

**Returns** `data`: array of object — An array of objects containing the server's status.

- *(array of objects)*
  - `error` (string) — An error message about why system couldn't read a resource's status file.
  - `name` (string) — The cPanel services, devices, and server health check points on the server.; A valid [cPanel service](https://go.cpanel.net/ThecPanelWHMServiceDaemons).
  - `status` (integer (`1`, `0`) or string (`unknown`)) — Whether the resource is enabled or disabled.; `1` — Enabled.; `0` — Disabled.; `unknown` — The system couldn't determine the resource's status.
  - `type` (string (`device`, `metric`, `service`)) — The type of resource.; `device`; `metric`; `service`
  - `value` (string or string (`up`, `down`, `unknown`)) — The resource's status.; `up`; `down`; `unknown`; The current resource usage.
  - `version` (string) — The resource's software version.

```bash
uapi --output=jsonpretty \
  --user=username \
  ServerInformation \
  get_information
```

## Variables

<a id="variables-get-server-information"></a>
### `Variables::get_server_information` — Return server's configuration settings

`GET /execute/Variables/get_server_information` · RO · since cPanel 86

This function retrieves the configuration settings for the cPanel & WHM server on which an account exists. This is useful, for example, to verify which applications and functionality are available on the account.

**Parameters**

- `name` · optional · string (`default_theme`, `email_filter_storage_directory`, `allow_park_subdomain_on_hostname`, `allow_remote_domains`, `allow_unregistered_domains`, `apache_port`, `apache_ssl_port`, `api_shell`, `awstats_browser_update`, `awstats_reverse_dns`, `cpanel_root_directory`, `database_prefix_required`, …) — The server configuration settings to return. <details> <summary>Click to view information about the available server configuration settings.</summary>; `default_theme` - The cPanel interface's default theme.; `email_filter_storage_directory` - The location of the Exim email filter storage directory.; `allow_park_subdomain_on_hostname` - Whether the system allows users to park subdomains of the server's hostname.; `allow_remote_domains` - Whether the system allows users to create addon domains or aliases that resolve to other servers.; `allow_unregistered_domains` - Whether the system allows users to add domains they didn't register with a domain name registrar.; `apache_port` - The IP address or IP address with a firewall port number that Apache® uses to listen for requests and serve web pages over an unsecured connection.; `apache_ssl_port` - The port or IP address that Apache uses to listen for requests and serve web pages over a secure connection.; `api_shell` - Whether the user can access cPanel's [*API Shell*](https://go.cpanel.net/cpaneldocsAPIShell) interface (*cPanel >> Home >> Advanced >> API Shell*).; `awstats_browser_update` - Whether the user can update their [AWStats](http://awstats.sourceforge.net/) software.; `awstats_reverse_dns` - Whether the AWStats statistical analysis software interprets visitors' domain names as IP addresses.; `cpanel_root_directory` - The cPanel `root` directory.; `database_prefix_required` - Whether the account requires database prefixing.; `display_cpanel_doclinks` - Whether the system displays links to cPanel feature documentation in the cPanel interface.; `dnsadmin_app` - The application that processes DNS management requests.; `empty_trash_days` - The minimum age of files that the system will automatically purge from `.trash` folders in user home directories.; `enable_file_protect` - Whether [EasyApache 4's *FileProtect* option](https://go.cpanel.net/EasyApache4FileprotectOption) is enabled.; `file_upload_maximum_bytes` - The maximum file size, in megabytes (MB), that a user can upload to a server.; `file_upload_must_leave_bytes` - The minimum filesystem quota that the system requires after a file uploads to a server.; `file_usage` - Whether file usage information displays in the cPanel *Home* interface's statistics bar.; `ftp_server` - The FTP server.; `htaccess_check_recurse` - The maximum number of directories deep to look for `.htaccess` files when you change the PHP handler.; `invite_sub` - Whether cPanel account users can send invitations to new Subaccount users via cPanel's [*User Manager*](https://go.cpanel.net/cpaneldocsUserManager) interface (*cPanel >> Home >> Preferences >> User Manager*).; `ipv6_listen` - Whether the `cpsrvd` daemon and other cPanel & WHM services listen on IPv6.; `local_nameserver_type` - The DNS nameserver's type.; `logout_redirect_url` - The logout redirection URL.; `mailbox_storage_format` - The mailbox storage format for new accounts.; `mail_server` - The mailserver type.; `minimum_password_strength` - The minimum strength for cPanel account passwords. ; `minimum_password_strength_mysql` - The minimum strength for MySQL® or MariaDB® passwords.; `mysql_host` - The MySQL or MariaDB hostname or IP address.; `mysql_version` - The MySQL or MariaDB version.; `php_maximum_execution_time` - The number of seconds that a PHP script can run before the system terminates it.; `php_post_maximum_size` - The maximum size, in megabytes (MB), of a POST request.; `php_system_default_version` - The system's default version of PHP.; `php_upload_maximum_filesize` - The maximum file size, in megabytes (MB), that a PHP script may upload.; `php_loader` - The PHP loaders through which the system executes internal PHP scripts.; `php_open_basedir_home` - Whether PHP `open_basedir` protection is enabled on the server.; `phpmyadmin_disable_search_info_schema` - Whether the user can search for the phpMyAdmin information schema.; `docroots_in_public_html_only` - Whether the system restricts users from creating addon domains and subdomains outside of their `public_html` directory.; `require_ssl` - Whether the system requires passwords and other sensitive information use SSL encryption.; `allow_reset_password` - Whether cPanel's [*Reset Password*](https://go.cpanel.net/resetsubaccountpass) feature is enabled for the account.; `allow_reset_password_for_subaccounts` - Whether cPanel's [*Reset Password*](https://go.cpanel.net/resetsubaccountpass) feature is enabled for subaccounts on the account.; `disable_analog` - Whether users can access the [*Analog Stats*](https://go.cpanel.net/cpaneldocsAnalogStats) interface (*cPanel >> Home >> Metrics >> Analog Stats*).; `skip_apache_clients_optimizer` - Whether the Apache Client Optimizer is enabled.; `disable_awstats` - Whether the [AWStats](http://awstats.sourceforge.net/) software is enabled.; `skip_mailbox_warnings_check` - Whether mailbox usage warnings are enabled.; `disable_boxtrapper` - Whether [*BoxTrapper*](https://go.cpanel.net/cpaneldocsBoxTrapper) is enabled.; `skip_bandwidth_limit_check` - Whether the system automatically suspends HTTP service for accounts that exceed their bandwidth limit.; `disable_mailman` - Whether Mailman mailing lists are enabled.; `disable_roundcube` - Whether [Roundcube webmail](https://roundcube.net/) is enabled.; `disable_spamassassin` - Whether the Apache SpamAssassin™ spam filter is enabled.; `disable_spambox` - Whether Apache SpamAssassin's spam box feature is enabled.; `disable_webalizer` - Whether the [Webalizer](https://docs.cpanel.net/cpanel/metrics/webalizer/) statistics program is enabled.; `ssl_default_key_type` - The default SSL/TLS encryption algorithm used by the system.; `use_information_schema` - Whether the system uses the MySQL® `INFORMATION_SCHEMA` view. This view includes disk usage by all MySQL tables in the disk usage totals.; `use_mail_for_mailman_url` - Whether the system prefixes Mailman URLs with the `mail` prefix. For example, `http://mail.domain.com/mailman`.; `is_mod_userdir_enabled` - Whether the [Apache `mod_userdir` Tweak](https://go.cpanel.net/whmdocsApachemod_userdirTweak) is enabled.; `version` - The system's Linux® kernel version. </details> Note:  If you don't use this parameter, this function returns **all** of the server's configuration settings.; To retrieve multiple variables, increment this parameter. For example, `name-1=variable`, `name-2=variable`, `name-3=variable`.

**Returns** `data`: object

- `allow_park_subdomain_on_hostname` (integer (`1`, `0`)) — Whether the system allows users to park subdomains of the server's hostname.; `1` - Allows.; `0` - Doesn't allow.
- `allow_remote_domains` (integer (`1`, `0`)) — Whether the system allows users to create addon domains or aliases that resolve to other servers.; `1` - Allows.; `0` - Doesn't allow.
- `allow_reset_password` (integer (`1`, `0`)) — Whether cPanel's [*Reset Password*](https://go.cpanel.net/resetsubaccountpass) feature is enabled for the account.; `1` - *Reset Password* feature enabled.; `0` - *Reset Password* feature not enabled.
- `allow_reset_password_for_subaccounts` (integer (`1`, `0`)) — Whether cPanel's [*Reset Password*](https://go.cpanel.net/resetsubaccountpass) feature is enabled for subaccounts on the account.; `1` - *Reset Password* feature enabled.; `0` - *Reset Password* feature not enabled.
- `allow_unregistered_domains` (integer (`1`, `0`)) — Whether the system allows users to add domains they didn't register with a domain name registrar.; `1` - Allows.; `0` - Doesn't allow.
- `apache_port` (string) — The IP address or IP address with a firewall port number that Apache uses to listen for requests and serve web pages over an unsecured connection.
- `apache_ssl_port` (string) — The IP address or IP address with a firewall port number that Apache uses to listen for requests and serve web pages over a secure connection.
- `api_shell` (integer (`1`, `0`)) — Whether the user can access cPanel's [*API Shell*](https://go.cpanel.net/cpaneldocsAPIShell) interface (*cPanel >> Home >> Advanced >> API Shell*).; `1` - Can access.; `0` - Can't access.
- `awstats_browser_update` (integer (`1`, `0`)) — Whether the user can update their [AWStats](http://awstats.sourceforge.net/) software.; `1` - Can update.; `0` - Can't update.
- `awstats_reverse_dns` (integer (`1`, `0`)) — Whether the AWStats statistical analysis software interprets visitors' domain names as IP addresses.; `1` - Interprets visitors' domain names as IP addresses.; `0` - Doesn't interpret visitors' domain names as IP address
- `cpanel_root_directory` (string <path>) — The cPanel `root` directory.
- `database_prefix_required` (integer (`1`, `0`)) — Whether the account requires database prefixing.; `1` - Requires database prefixing.; `0` - Doesn't require database prefixing.
- `default_theme` (string) — The cPanel interface's default theme.
- `disable_analog` (integer (`1`, `0`)) — Whether users can access the [*Analog Stats*](https://go.cpanel.net/cpaneldocsAnalogStats) interface (*cPanel >> Home >> Metrics >> Analog Stats*).; `1` - Enabled.; `0` - Not enabled.
- `disable_awstats` (integer (`1`, `0`)) — Whether the [AWStats](http://awstats.sourceforge.net/) software is enabled.; `1` - Enabled.; `0` - Not enabled.
- `disable_boxtrapper` (integer (`1`, `0`)) — Whether [*BoxTrapper*](https://go.cpanel.net/cpaneldocsBoxTrapper) is enabled.; `1` - Enabled.; `0` - Not enabled.
- `disable_mailman` (integer (`1`, `0`)) — Whether Mailman mailing lists are enabled.; `1` - Enabled.; `0` - Not enabled.
- `disable_roundcube` (integer (`1`, `0`)) — Whether [Roundcube webmail](https://roundcube.net/) is enabled.; `1` - Enabled.; `0` - Not enabled.
- `disable_spamassassin` (integer (`1`, `0`)) — Whether the Apache SpamAssassin spam filter is enabled.; `1` - Enabled.; `0` - Not enabled.
- `disable_spambox` (integer (`1`, `0`)) — Whether Apache SpamAssassin's spam box feature is enabled.; `1` - Enabled.; `0` - Not enabled.
- `disable_webalizer` (integer (`1`, `0`)) — Whether the [Webalizer](http://www.webalizer.org/) statistics program is enabled.; `1` - Enabled.; `0` - Not enabled.
- `display_cpanel_doclinks` (integer (`1`, `0`)) — Whether the system displays links to cPanel feature documentation in the cPanel interface.; `1` - Displays documentation links.; `0` - Doesn't display documentation links.
- `dnsadmin_app` (string or string (`dnsadmin`, `auto-detect SSL`)) — The application that processes DNS management requests.; The value is an application's file path, relative to the user's home directory.; `dnsadmin`; `auto-detect SSL`
- `docroots_in_public_html_only` (integer (`1`, `0`)) — Whether the system restricts users from creating addon domains and subdomains outside of their `public_html` directory.; `1` - Restricts users from creating addon domains and subdomains outside of their `public_html` dir
- `email_filter_storage_directory` (string <path>) — The location of the Exim email filter storage directory.
- `empty_trash_days` (string) — The minimum age of files that the system will automatically purge from `.trash` folders in user home directories.
- `enable_file_protect` (integer (`1`, `0`)) — Whether [EasyApache 4's *FileProtect* option](https://go.cpanel.net/EasyApache4FileprotectOption) is enabled.; `1` - Enabled.; `0` - Not enabled.
- `file_upload_maximum_bytes` (integer) — The maximum file size, in megabytes (MB), that a user can upload to a server.
- `file_upload_must_leave_bytes` (integer) — The minimum filesystem quota that the system requires after a file uploads to a server.
- `file_usage` (integer (`1`, `0`)) — Whether file usage information displays in the cPanel *Home* interface's statistics bar.; `1` - Displays file usage information.; `0` - Doesn't display file usage information.
- `ftp_server` (string (`pure-ftpd`, `proftpd`, `disabled`)) — The FTP server.; `pure-ftpd` - The Pure-FTPD server.; `proftpd` - The ProFTPD FTP server.; `disabled` - FTP has been disabled on this server.
- `htaccess_check_recurse` (integer) — The maximum number of directories deep to look for `.htaccess` files when you change the PHP handler.
- `invite_sub` (integer (`1`, `0`)) — Whether cPanel account users can send invitations to new Subaccount users via cPanel's [*User Manager*](https://go.cpanel.net/cpaneldocsUserManager) interface (*cPanel >> Home >> Preferences >> User Manager*).; `1` - Can
- `ipv6_listen` (integer (`1`, `0`)) — Whether the `cpsrvd` daemon and other cPanel & WHM services listen on IPv6.; `1` - Listen on IPv6.; `0` - Don't listen on IPv6.
- `is_mod_userdir_enabled` (integer (`1`, `0`)) — Whether the [Apache `mod_userdir` Tweak](https://go.cpanel.net/whmdocsApachemod_userdirTweak) is enabled.; `1` - Enabled.; `0` - Not enabled.
- `local_nameserver_type` (string (`powerdns`, `bind`, `disabled`)) — The DNS nameserver's type.; `powerdns` - The PowerDNS nameserver.; `bind` - The bind nameserver.; `disabled` - Nameserver's have been disabled on this server.
- `logout_redirect_url` (string <url>) — The logout redirection URL.
- `mail_server` (string (`dovecot`, `disabled`)) — The mailserver type.; `dovecot` - The Dovecot mailserver.; `disabled` - The mailserver is disabled on this system.
- `mailbox_storage_format` (string (`mdbox`, `maildir`)) — The mailbox storage format for new accounts.; `mdbox` - The mdbox storage format.; `maildir` - The maildir storage format.
- `minimum_password_strength` (integer) — The minimum strength for cPanel account passwords.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  Variables \
  get_server_information
```

## WebProsMCP

<a id="webprosmcp-get-connection-config"></a>
### `WebProsMCP::get_connection_config` — Get the WebPros MCP connection configuration

`GET /execute/WebProsMCP/get_connection_config` · RO/RW: unspecified · since 138 · requires plugin `WebProsMCP`

Returns whether the current cPanel user's account is linked to a WebPros Account and the connection snippet for the WebPros MCP.

**Returns** `data`: object

- `is_linked` (integer) — 1 if the current user has a WebPros authentication link, 0 otherwise.
- `link_url` (string) — Session-relative URL used to initiate the WebPros Account link.
- `environment` (string) — 'production' when the baked-in defaults are in effect, or 'overridden' when the overrides file repoints either MCP value.
- `mcp_config` (object) — The MCP connection snippet.
  - `name` (string) — 
  - `type` (string) — 
  - `url` (string) — 
  - `oauth` (object) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  WebProsMCP \
  get_connection_config
```

<a id="webprosmcp-unlink-webpros-account"></a>
### `WebProsMCP::unlink_webpros_account` — Unlink the WebPros Account from this cPanel account

`GET /execute/WebProsMCP/unlink_webpros_account` · RW · since 138 · requires plugin `WebProsMCP`

Removes the current cPanel user's WebPros Account authentication link(s), disconnecting the account from the WebPros MCP. This is not limited to MCP; it also disables WebPros Account login and any other WebPros integration for this cPanel account until the account is linked again. The call is idempotent and succeeds as a no-op when no link exists.

**Returns** `data`: object

- `is_linked` (integer) — Always 0 after a successful call.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebProsMCP \
  unlink_webpros_account
```

