<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Web Server Management

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **PHP Settings**: [`LangPHP::php_get_domain_handler`](#langphp-php-get-domain-handler), [`LangPHP::php_get_impacted_domains`](#langphp-php-get-impacted-domains), [`LangPHP::php_get_installed_versions`](#langphp-php-get-installed-versions), [`LangPHP::php_get_system_default_version`](#langphp-php-get-system-default-version), [`LangPHP::php_get_vhost_versions`](#langphp-php-get-vhost-versions), [`LangPHP::php_ini_get_user_basic_directives`](#langphp-php-ini-get-user-basic-directives), [`LangPHP::php_ini_get_user_content`](#langphp-php-ini-get-user-content), [`LangPHP::php_ini_get_user_paths`](#langphp-php-ini-get-user-paths), [`LangPHP::php_ini_set_user_basic_directives`](#langphp-php-ini-set-user-basic-directives), [`LangPHP::php_ini_set_user_content`](#langphp-php-ini-set-user-content), [`LangPHP::php_set_vhost_versions`](#langphp-php-set-vhost-versions)
- **ModSecurity**: [`ModSecurity::disable_all_domains`](#modsecurity-disable-all-domains), [`ModSecurity::disable_domains`](#modsecurity-disable-domains), [`ModSecurity::enable_all_domains`](#modsecurity-enable-all-domains), [`ModSecurity::enable_domains`](#modsecurity-enable-domains), [`ModSecurity::has_modsecurity_installed`](#modsecurity-has-modsecurity-installed), [`ModSecurity::list_domains`](#modsecurity-list-domains)
- **NginxCaching**: [`NginxCaching::clear_cache`](#nginxcaching-clear-cache), [`NginxCaching::disable_cache`](#nginxcaching-disable-cache), [`NginxCaching::enable_cache`](#nginxcaching-enable-cache), [`NginxCaching::reset_cache_config`](#nginxcaching-reset-cache-config)
- **Application Manager**: [`PassengerApps::disable_application`](#passengerapps-disable-application), [`PassengerApps::edit_application`](#passengerapps-edit-application), [`PassengerApps::enable_application`](#passengerapps-enable-application), [`PassengerApps::ensure_deps`](#passengerapps-ensure-deps), [`PassengerApps::list_applications`](#passengerapps-list-applications), [`PassengerApps::register_application`](#passengerapps-register-application), [`PassengerApps::unregister_application`](#passengerapps-unregister-application)
- **Web Apps**: [`WebApp::configure`](#webapp-configure), [`WebApp::delete`](#webapp-delete), [`WebApp::deploy`](#webapp-deploy), [`WebApp::fetch_logs`](#webapp-fetch-logs), [`WebApp::get_available`](#webapp-get-available), [`WebApp::has_feature`](#webapp-has-feature), [`WebApp::list`](#webapp-list), [`WebApp::redeploy`](#webapp-redeploy), [`WebApp::redeploy`](#webapp-redeploy), [`WebApp::restart`](#webapp-restart), [`WebApp::set_mode`](#webapp-set-mode), [`WebApp::stage`](#webapp-stage), [`WebApp::stage`](#webapp-stage), [`WebApp::start`](#webapp-start), [`WebApp::stop`](#webapp-stop)

## PHP Settings

<a id="langphp-php-get-domain-handler"></a>
### `LangPHP::php_get_domain_handler` — Return PHP version's handler

`GET /execute/LangPHP/php_get_domain_handler` · RO · since cPanel 68

This function returns a PHP version's assigned PHP handler. Note: This document **only** applies to systems that run EasyApache 4. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system disables this function. For more information, read our How to Use Server Profiles documentation.

**Parameters**

- `type` · **required** · string (`home`, `vhost`) · e.g. `vhost` — The type of `php.ini` file.; `home`; `vhost` Important:  If you set this parameter to `vhost`, you **must** also include the vhost parameter.; If you set this parameter to `home`, the system returns the system default PHP handler.
- `vhost` · optional · string <domain> · e.g. `clearly.com` — The name of a virtual host. Important: If the `type` value is `vhost`, you **must** use this parameter.

**Returns** `data`: object

- `php_handler` (string) — The virtual host's PHP handler.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_get_domain_handler \
  type='vhost'
```

<a id="langphp-php-get-impacted-domains"></a>
### `LangPHP::php_get_impacted_domains` — Return domains that shared PHP configuration

`GET /execute/LangPHP/php_get_impacted_domains` · RO · since cPanel 62

This function lists domains that obtain their PHP version from a specified PHP configuration. Note: This document **only** applies to systems that run EasyApache 4. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — A domain on the system. Note:  You must pass either the `system_default` or `domain` parameters, or both.; You can pass this parameter multiple times.; You **cannot** pass the name of a parked domain.
- `system_default` · optional · integer (`1`, `0`) · e.g. `1` — Whether to return domains that inherit the system's default PHP version.; `1` - Return domains that inherit the system's default PHP version.; `0` - Do **not** return domains that inherit the system's default PHP version. Note: If you pass this parameter with a false value and do **not** also pass the domain parameter, the function returns an error.

**Returns** `data`: object

- `domains` (array of string) — The domains that obtain their PHP version from the PHP configuration.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_get_impacted_domains
```

<a id="langphp-php-get-installed-versions"></a>
### `LangPHP::php_get_installed_versions` — Return installed PHP versions

`GET /execute/LangPHP/php_get_installed_versions` · RO · since cPanel 11.52

This function lists the system's PHP versions. Note: This document **only** applies to systems that run EasyApache 4. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: object

- `versions` (array of string) — The available PHP versions.; `ea-php72`; `ea-php73`; `ea-php74`; Any custom PHP package name.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_get_installed_versions
```

<a id="langphp-php-get-system-default-version"></a>
### `LangPHP::php_get_system_default_version` — Return default PHP version

`GET /execute/LangPHP/php_get_system_default_version` · RO · since cPanel 11.52

This function lists the system’s default PHP version. **Important**: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

- `version` (string) — The system’s default PHP version.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_get_system_default_version
```

<a id="langphp-php-get-vhost-versions"></a>
### `LangPHP::php_get_vhost_versions` — Return virtual host's PHP version

`GET /execute/LangPHP/php_get_vhost_versions` · RO · since cPanel 11.52

This function returns the PHP version of every virtual host that a reseller controls. You can get the version of a single virtual host by providing an optional `vhost` name. Note: This document **only** applies to systems that run EasyApache 4. Important: When you disable the [Web Server role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `vhost` · optional · string · e.g. `your-domain.test` — The PHP Virtual Hostname.

**Returns** `data`: array of object — An array of objects of the virtual host's suspended status, versions, virtual hosts, and accounts.

- *(array of objects)*
  - `account` (string <username>) — The account's name.
  - `account_owner` (string <username>) — The account's owner.
  - `documentroot` (string <path>) — The virtual host's document root.
  - `homedir` (string <path>) — The virtual host's home directory.
  - `main_domain` (integer (`1`, `0`)) — Whether the virtual host is the primary domain.
  - `php_fpm` (integer (`0`, `1`)) — Whether FPM is enabled on the virtual host.; `1` - PHP-FPM enabled.; `0` - PHP-FPM **not** enabled.
  - `php_fpm_pool_parms` (object) — An object containing the domain's PHP-FPM parameters.
    - `pm_max_children` (integer) — The maximum number of child pages per pool.
    - `pm_max_requests` (integer) — The maximum number of requests per pool.
    - `pm_process_idle_timeout` (integer) — A specified time of idleness before the system kills an FPM child process.
  - `phpversion_source` (array of object) — How the virtual host determines its PHP version.
    - *(array of objects)*
      - `domain` (string <domain>) — The domain the virtual host inherits its PHP version from.
      - `system_default` (integer (`1`)) — Whether the virtual host uses the system's default PHP version.; `1` - Uses the system default PHP version.
  - `version` (string) — The virtual host's PHP version.; `ea-php72`; `ea-php73`; `ea-php74`; Any custom PHP package name.
  - `vhost` (string <domain>) — The virtual host's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_get_vhost_versions
```

<a id="langphp-php-ini-get-user-basic-directives"></a>
### `LangPHP::php_ini_get_user_basic_directives` — Return basic PHP directives

`GET /execute/LangPHP/php_ini_get_user_basic_directives` · RO · since cPanel 11.52

This function lists a virtual host's basic PHP directives. The Basic Mode section of cPanel's [MultiPHP INI Editor](https://go.cpanel.net/cPanelMultiPHPINI)  interface (Home >> Software >> MultiPHP INI Editor) also lists these directives. Note: This document **only** applies to systems that run EasyApache 4 with MultiPHP enabled. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `type` · **required** · string (`home`, `vhost`) · e.g. `vhost` — The type of `php.ini` file.; `home`; `vhost` Important: If you set this parameter to `vhost`, you **must** also include the `vhost` parameter.
- `vhost` · optional · string <domain> · e.g. `clearly.com` — The name of a virtual host. Important: If the type value is `vhost`, you **must** use this parameter.

**Returns** `data`: object

- `directives` (array of object) — An array of the available directives in the `php.ini` file of the selected user's PHP version.
  - *(array of objects)*
    - `default_value` (boolean or integer or number or string) — The directive's default value.
    - `info` (string) — The purpose of the directive.
    - `key` (string) — The directive's name.
    - `php_ini_mode` (string (`PHP_INI_SYSTEM`, `PHP_INI_PERDIR`, `PHP_INI_ALL`, `PHPINI_ONLY`)) — The directive's [PHP_INI mode](http://php.net/manual/en/configuration.changes.modes.php).; `PHP_INI_SYSTEM`; `PHP_INI_PERDIR`; `PHP_INI_ALL`; `PHPINI_ONLY`
    - `type` (string (`string`, `boolean`, `integer`, `float`)) — The type of value that the directive uses.; `string`; `boolean`; `integer`; `float`
    - `value` (string) — The directive's current value.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_ini_get_user_basic_directives \
  type='vhost'
```

<a id="langphp-php-ini-get-user-content"></a>
### `LangPHP::php_ini_get_user_content` — Return virtual host's php.ini content

`GET /execute/LangPHP/php_ini_get_user_content` · RO · since cPanel 11.52

This function returns the contents of a virtual host's `php.ini` file. Note: This document **only** applies to systems that run EasyApache 4 with MultiPHP enabled. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `type` · **required** · string · e.g. `vhost` — The type of `php.ini` file.; `home`; `vhost` Important: If you set this parameter to `vhost`, you **must** also include the `vhost` parameter.
- `vhost` · optional · string <domain> · e.g. `clearly.com` — The name of a virtual host. Important: If the type value is `vhost`, you **must** use this parameter.

**Returns** `data`: object

- `content` (string) — The contents of the requested user's `php.ini` file.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_ini_get_user_content \
  type='vhost'
```

<a id="langphp-php-ini-get-user-paths"></a>
### `LangPHP::php_ini_get_user_paths` — Return php.ini file paths

`GET /execute/LangPHP/php_ini_get_user_paths` · RO · since cPanel 11.52

This function lists the `php.ini` file paths for the user's home directory and virtual host document roots. Note: This document **only** applies to systems that run EasyApache 4 with MultiPHP enabled. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: object

- `paths` (array of object) — An array of objects of `php.ini` file information.
  - *(array of objects)*
    - `account` (string) — The account's name.
    - `documentroot` (string) — The virtual host's document root.
    - `homedir` (string) — The home directory.
    - `main_domain` (integer (`1`, `0`)) — Whether the virtual host is the account's primary domain.; `1` - Primary domain.; `0` - **Not** the primary domain.
    - `path` (string) — The name of the virtual host's `php.ini` file.
    - `type` (string (`home`, `vhost`)) — The record's type.; `home`; `vhost`
    - `version` (string) — The default PHP version.; `ea-php##`, where `##` represents the major and minor versions of PHP (for example, `ea-php72` represents PHP 7.2).; Any custom PHP package name.
    - `vhost` (string <domain>) — The name of the virtual host.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_ini_get_user_paths
```

<a id="langphp-php-ini-set-user-basic-directives"></a>
### `LangPHP::php_ini_set_user_basic_directives` — Update basic PHP directives

`GET /execute/LangPHP/php_ini_set_user_basic_directives` · RW · rollback: none · since cPanel 11.52

This function sets the values of any basic PHP directive. The *Basic Mode* section of cPanel's [*MultiPHP INI Editor*](https://go.cpanel.net/whmdocsMultiPHPINIEditor) interface (*WHM >> Home >> Software >> MultiPHP INI Editor*) lists these directives. Note: This document **only** applies to systems that run EasyApache 4 with MultiPHP enabled. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `directive` · **required** · string — The name of a PHP directive and its value. Note:  To change the directive's value for multiple PHP directives, increment the parameter name. For example, the `directive-1`, `directive-2`, and `directive-3` parameters.; You **must** format values as `<directive>:<value>`
- `type` · **required** · string (`home`, `vhost`) · e.g. `vhost` — The type of `php.ini` file.; `home`; `vhost` Important: If you set this parameter to `vhost`, you **must** also include the `vhost` parameter.
- `vhost` · optional · string <domain> · e.g. `clearly.com` — The name of a virtual host. Important: If the `type` value is `vhost`, you **must** use this parameter.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_ini_set_user_basic_directives \
  type='vhost' \
  directive='allow_url_fopen:0'
```

<a id="langphp-php-ini-set-user-content"></a>
### `LangPHP::php_ini_set_user_content` — Update virtual host's php.ini content

`GET /execute/LangPHP/php_ini_set_user_content` · RW · rollback: none · since cPanel 11.52

This function changes the contents of a virtual host's `php.ini` file. Note: This document **only** applies to systems that run EasyApache 4 with MultiPHP enabled. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `content` · **required** · string — The content of the `php.ini` file to change.
- `type` · **required** · string (`host`, `vhost`) · e.g. `vhost` — The type of `php.ini` file.; `home`; `vhost` Important: If you set this parameter to `vhost`, you **must** also include the `vhost` parameter.
- `vhost` · optional · string <domain> · e.g. `clearly.com` — The name of a virtual host. Important: If the type value is `vhost` , you **must** use this parameter.

**Returns** `data`: object — This value will always be `null`.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_ini_set_user_content \
  type='vhost' \
  content='%5BPHP%5D%0D%0A%3B+About+php.ini%0D%0A%3B+php.ini+is+responsible+for+configuring+many+of+the+aspects+of+PHP%27s+behavior.%0D%0Apcre.backtrack_limit%3D100000'
```

<a id="langphp-php-set-vhost-versions"></a>
### `LangPHP::php_set_vhost_versions` — Update virtual host's PHP version

`GET /execute/LangPHP/php_set_vhost_versions` · RW · rollback: none · since cPanel 11.52

This function sets a virtual host's PHP version. Note: This document **only** applies to systems that run EasyApache 4. Important: When you disable the [WebServer role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `version` · **required** · string · e.g. `ea-php72` — The PHP version of a virtual host.
- `vhost` · **required** · string <domain> — The virtual host's name. Note: To change the PHP version of multiple virtual hosts, duplicate or increment the parameter name. For example, `vhost-1`, `vhost-2`, and `vhost-3`.

**Returns** `data`: object

- `vhosts` (array of string <domain>) — The names of the changed virtual hosts.

```bash
uapi --output=jsonpretty \
  --user=username \
  LangPHP \
  php_set_vhost_versions \
  version='ea-php72' \
  vhost='example.com'
```

## ModSecurity

<a id="modsecurity-disable-all-domains"></a>
### `ModSecurity::disable_all_domains` — Disable ModSecurity for all domains

`GET /execute/ModSecurity/disable_all_domains` · RW · rollback: none · since cPanel 11.46

This function disables ModSecurity™ on a cPanel account's domains. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string <domain>) — An array of domains that your changes to a selected domain affect.
  - `domain` (string <domain>) — The cPanel account's domain.
  - `enabled` (integer (`0`, `1`)) — Whether ModSecurity is enabled on the account.; `1` - Enabled.; `0` - Disabled.
  - `exception` (string) — An exception error message.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `sub`)) — The domain type.; `main` - A main domain.; `sub` - A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  ModSecurity \
  disable_all_domains
```

<a id="modsecurity-disable-domains"></a>
### `ModSecurity::disable_domains` — Disable ModSecurity for selected domains

`GET /execute/ModSecurity/disable_domains` · RW · rollback: none · since cPanel 11.46

This function disables ModSecurity™ on specified domains. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domains` · **required** · string · e.g. `example.com,dallas.example.com,galveston.example.com` — A comma-separated list of domains that the cPanel account owns. Important: The authenticated cPanel account **must** own these domains.

**Returns** `data`: array of object or object

- *variant: array*
  - *(array of objects)*
    - `dependencies` (array of string <domain>) — An array of domains that your changes to a selected domain affect.
    - `domain` (string <domain>) — The cPanel account's domain.
    - `enabled` (integer (`0`, `1`)) — Whether ModSecurity is enabled on the domain.; `1` - Enabled.; `0` - Disabled.
    - `exception` (string) — An exception error message.
    - `searchhint` (string) — A comma-separated list of domain-related search terms.
    - `type` (string (`main`, `sub`)) — The domain type.; `main` - A main domain.; `sub` - A subdomain.
- *variant: object*
  - `no_domains_provided` (integer (`1`)) — Indicates caller error on API call.
- *variant: object*
  - `invalid_domains` (array of string) — List of invalid domains provided by caller.
  - `invalid_domains_provided` (integer (`1`)) — Indicates caller error on API call.

```bash
uapi --output=jsonpretty \
  --user=username \
  ModSecurity \
  disable_domains \
  domains='example.com,dallas.example.com,galveston.example.com'
```

<a id="modsecurity-enable-all-domains"></a>
### `ModSecurity::enable_all_domains` — Enable ModSecurity for all domains

`GET /execute/ModSecurity/enable_all_domains` · RW · rollback: none · since cPanel 11.46

This function enables ModSecurity™ on a cPanel account's domains. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles#roles), the system **disables** this function

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string <domain>) — An array of domains that your changes to a selected domain affect.
  - `domain` (string <domain>) — The cPanel account's domain.
  - `enabled` (integer (`0`, `1`)) — Whether ModSecurity is enabled on the account.; `1` - Enabled.; `0` - Disabled.
  - `exception` (string) — An exception error message.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `sub`)) — The domain type.; `main` - A main domain.; `sub` - A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  ModSecurity \
  enable_all_domains
```

<a id="modsecurity-enable-domains"></a>
### `ModSecurity::enable_domains` — Enable ModSecurity for selected domains

`GET /execute/ModSecurity/enable_domains` · RW · rollback: none · since cPanel 11.46

This function enables ModSecurity™ for specified domains. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domains` · **required** · string · e.g. `example.com,dallas.example.com,galveston.example.com` — A comma-separated list of domains for which to enable ModSecurity. Important: The authenticated cPanel account **must** own these domains.

**Returns** `data`: array of object or object

- *variant: array*
  - *(array of objects)*
    - `dependencies` (array of string <domain>) — An array of domains that your changes to a selected domain affect.
    - `domain` (string <domain>) — The cPanel account's domain.
    - `enabled` (integer (`0`, `1`)) — Whether ModSecurity is enabled on the domain.; `1` - Enabled.; `0` - Disabled.
    - `exception` (string) — An exception error message.
    - `searchhint` (string) — A comma-separated list of domain-related search terms.
    - `type` (string (`main`, `sub`)) — The domain type.; `main` - A main domain.; `sub` - A subdomain.
- *variant: object*
  - `no_domains_provided` (integer (`1`)) — Indicates caller error on API call.
- *variant: object*
  - `invalid_domains` (array of string) — List of invalid domains provided by caller.
  - `invalid_domains_provided` (integer (`1`)) — Indicates caller error on API call.

```bash
uapi --output=jsonpretty \
  --user=username \
  ModSecurity \
  enable_domains \
  domains='example.com,dallas.example.com,galveston.example.com'
```

<a id="modsecurity-has-modsecurity-installed"></a>
### `ModSecurity::has_modsecurity_installed` — Return ModSecurity installation status

`GET /execute/ModSecurity/has_modsecurity_installed` · RO · since cPanel 11.46

This function checks whether ModSecurity™ is installed on a server. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: object

- `installed` (integer (`0`, `1`)) — Whether ModSecurity is installed on the server.; `1` - Installed.; `0` - Not installed.

```bash
uapi --output=jsonpretty \
  --user=username \
  ModSecurity \
  has_modsecurity_installed
```

<a id="modsecurity-list-domains"></a>
### `ModSecurity::list_domains` — Return ModSecurity domains' status

`GET /execute/ModSecurity/list_domains` · RO · since cPanel 11.46

This function returns ModSecurity's™ status for a cPanel account's domains. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `dependencies` (array of string <domain>) — An array of domains that your changes to a selected domain affect.
  - `domain` (string <domain>) — The cPanel account's domain.
  - `enabled` (integer (`0`, `1`)) — Whether ModSecurity is enabled for the account.; `1` - Enabled.; `0` - Disabled.
  - `searchhint` (string) — A comma-separated list of domain-related search terms.
  - `type` (string (`main`, `sub`)) — The domain type.; `main` - A main domain.; `sub` - A subdomain.

```bash
uapi --output=jsonpretty \
  --user=username \
  ModSecurity \
  list_domains
```

## NginxCaching

<a id="nginxcaching-clear-cache"></a>
### `NginxCaching::clear_cache` — Delete NGINX cache contents.

`GET /execute/NginxCaching/clear_cache` · RW · rollback: none · since cPanel 100

This function clears the user's NGINX cache. Note:  You can **only** use this function if you installed the `ea-nginx` package.

**Returns** `data`: any

```bash
uapi --output=jsonpretty \
  --user=username \
  NginxCaching \
  clear_cache
```

<a id="nginxcaching-disable-cache"></a>
### `NginxCaching::disable_cache` — Disable the user's NGINX cache

`GET /execute/NginxCaching/disable_cache` · RW · rollback: none · since cPanel 100

This function disables the user's NGINX cache. Note:  You can **only** use this function if you installed the `ea-nginx` package.

**Returns** `data`: any

```bash
uapi --output=jsonpretty \
  --user=username \
  NginxCaching \
  disable_cache
```

<a id="nginxcaching-enable-cache"></a>
### `NginxCaching::enable_cache` — Enable the user's NGINX cache

`GET /execute/NginxCaching/enable_cache` · RW · rollback: none · since cPanel 100

This function enables the user's NGINX cache. Note:  You can **only** use this function if you installed the `ea-nginx` package.

**Returns** `data`: any

```bash
uapi --output=jsonpretty \
  --user=username \
  NginxCaching \
  enable_cache
```

<a id="nginxcaching-reset-cache-config"></a>
### `NginxCaching::reset_cache_config` — Reset the user's NGINX cache configuration

`GET /execute/NginxCaching/reset_cache_config` · RW · rollback: none · since cPanel 100

This function resets the user's NGINX caching configuration. Note:  You can **only** use this function if you installed the `ea-nginx` package.

**Returns** `data`: any

```bash
uapi --output=jsonpretty \
  --user=username \
  NginxCaching \
  reset_cache_config
```

## Application Manager

<a id="passengerapps-disable-application"></a>
### `PassengerApps::disable_application` — Disable Passenger application

`GET /execute/PassengerApps/disable_application` · RW · rollback: none · since cPanel 66

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. Use `WebApp::stop` instead of this function for applications deployed with Web Apps. Use `PassengerApps` only to manage applications already registered with Application Manager. This function disables a Passenger application on an account. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `slippers` — The application to disable.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  disable_application \
  name='slippers'
```

<a id="passengerapps-edit-application"></a>
### `PassengerApps::edit_application` — Update Passenger application settings

`GET /execute/PassengerApps/edit_application` · RW · rollback: none · since cPanel 66

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. Use `WebApp::configure` instead of this function for applications deployed with Web Apps. Use `PassengerApps` only to manage applications already registered with Application Manager. This function edits a Passenger application for an account. **Note**: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `Ruby Slippers` — The application’s current name.
- `clear_envvars` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to clear the application’s environment variables.
- `deployment_mode` · optional · string (`production`, `development`) · e.g. `production` — The new server environment in which to run the application. If you do not use this parameter, the function does not change the application’s server environment.; `development` — Sets the application to run in a development environment.; `production` — Sets the application to run in a production environment.
- `domain` · optional · string <domain> · e.g. `toto.com` — The application’s new domain. If you do not use this parameter, the function does not change the application’s domain.
- `enabled` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to enable the application and generate the web server configuration for it.; `1` — Enable the application and generate the web server configuration.; `0` — Don’t enable the application and generate the web server configuration.
- `envvar_name` · optional · array of string · e.g. `["SCARECROW", "TINMAN", "LION"]` — New set of environment variables for the application. **Important**: The function replaces all current environment variables with the variables that you pass in this parameter. **Note**: For each `envvar_name` parameter you send you **must** include an `envvar_value` parameter.
- `envvar_value` · optional · array of string · e.g. `["brain", "heart", "courage"]` — Each environment variable’s value. **Note**: For each `envvar_name` parameter you send you **must** include an `envvar_value` parameter.
- `new_name` · optional · string · e.g. `Little Dog` — The application’s new name. If you do not use this parameter, the function does not change the application's name.
- `path` · optional · string <path> · e.g. `/home/dorothy/littledog` — The application’s new filepath. If you do not use this parameter, the function does not change the application’s filepath.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  edit_application \
  name='Ruby Slippers'
```

<a id="passengerapps-enable-application"></a>
### `PassengerApps::enable_application` — Enable Passenger application

`GET /execute/PassengerApps/enable_application` · RW · rollback: none · since cPanel 66

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. Use `WebApp::start` instead of this function for applications deployed with Web Apps. Use `PassengerApps` only to manage applications already registered with Application Manager. This function enables a Passenger application and generates the Apache configuration on an account. Important: When you disable the [Web Server role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `slippers` — The Passenger application to enable on the account.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  enable_application \
  name='slippers'
```

<a id="passengerapps-ensure-deps"></a>
### `PassengerApps::ensure_deps` — Install Passenger application dependencies

`GET /execute/PassengerApps/ensure_deps` · RW · rollback: none · since cPanel 80

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. `WebApp::deploy` installs an application's dependencies automatically as part of the deploy, so there is no separate dependency-install call for Web Apps. Use `PassengerApps` only to manage applications already registered with Application Manager. This function installs the dependencies for a Passenger application. **Note**: This function starts the installation process. This may take a long time to complete. **Important**: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `app_path` · **required** · string <path> · e.g. `/home/example/my-app/` — The application’s filepath.
- `type` · **required** · string (`gem`, `npm`, `pip`) · e.g. `npm` — The application’s type.; `gem` — Ensure ruby gems in the application’s `Gemfile` file.; `npm` — Ensure node packages in the application’s `package.json` file.; `pip` — Ensure python pips in the application’s `requirements.txt` file.

**Returns** `data`: object

- `sse_url` (string <url-path>) — The SSE URI to track the progress of the process.
- `task_id` (string) — The task id of the SSE process.

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  ensure_deps \
  type='npm' \
  app_path='/home/example/my-app/'
```

<a id="passengerapps-list-applications"></a>
### `PassengerApps::list_applications` — Return Passenger applications

`GET /execute/PassengerApps/list_applications` · RO · since cPanel 66

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. Use `WebApp::list` instead of this function for applications deployed with Web Apps. Use `PassengerApps` only to manage applications already registered with Application Manager. This function lists an account’s Passenger applications. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object — An object describing each application.

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  list_applications
```

<a id="passengerapps-register-application"></a>
### `PassengerApps::register_application` — Register Passenger application

`GET /execute/PassengerApps/register_application` · RW · rollback: none · since cPanel 66

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. For a new application, use `WebApp::stage` and `WebApp::deploy` instead of this function. Use `PassengerApps` only to manage applications already registered with Application Manager. This function registers a Passenger application for an account. **Important**: This function **only** registers an application. It does **not** create the application. You **must** create an application **before** you register the application. For an example of how to do this, read our [How to Create Ruby Web Applications](https://go.cpanel.net/howtocreaterubyapps) documentation.; When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `dorothy.com` — The domain for which to register the application.
- `name` · **required** · string · e.g. `Name of Application` — The application’s name.
- `path` · **required** · string <path> · e.g. `/slippers` — The application’s filepath relative to the user’s home directory.
- `base_uri` · optional · string <url-path> · default `/` · e.g. `/ruby` — The application’s base URI.
- `deployment_mode` · optional · string (`production`, `development`) · default `production` · e.g. `production` — The type of server environment in which to run the application.; `development` — Sets the application to run in a development environment.; `production` — Sets the application to run in a production environment.
- `enabled` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to enable the application and generate the web server configuration for it.; `1` — Enable the application and generate the web server configuration.; `0` — Don’t enable the application and generate the web server configuration.
- `envvar_name` · optional · array of string · e.g. `["SHOES", "TINMAN"]` — Environment variables that the application needs. **Note**: For each `envvar_name` parameter you send, you **must** include an `envvar_value` parameter. This parameter's value can only contain letters, numbers, underscores, and dashes, and cannot begin with a number. This parameter's value must also not exceed 256 characters.
- `envvar_value` · optional · array of string · e.g. `["ruby", "heart"]` — Each environment variable’s value. **Note**: For each `envvar_name` parameter you send, you **must** include an `envvar_value` parameter. An environment variable value must contain 1024 or fewer ASCII-printable characters.

**Returns** `data`: object — An object describing the newly-registered application.

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  register_application \
  name='Name of Application' \
  path='/slippers' \
  domain='dorothy.com'
```

<a id="passengerapps-unregister-application"></a>
### `PassengerApps::unregister_application` — Unregister Passenger application

`GET /execute/PassengerApps/unregister_application` · RW · rollback: none · since cPanel 66

**Note**: Web Apps (`WebApp`) is the newer, recommended feature for deploying web applications; it deploys container-based applications and supersedes Application Manager. Use `WebApp::delete` instead of this function for applications deployed with Web Apps. Use `PassengerApps` only to manage applications already registered with Application Manager. This function unregisters a [Passenger application](https://go.cpanel.net/cpaneldocsApplicationManager) on an account. Note:  This function **only** unregisters an application. It does **not** delete the application. You **must** manually delete the application from your system.; When you disable the [Web Server role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `name` · **required** · string · e.g. `slippers` — The application to unregister.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  PassengerApps \
  unregister_application \
  name='slippers'
```

## Web Apps

<a id="webapp-configure"></a>
### `WebApp::configure` — Update an application's configuration.

`GET /execute/WebApp/configure` · RO/RW: unspecified · since cPanel 138

This function updates an application's configuration. Only the parameters you pass change; omitted parameters keep their current values. Important: The `env` parameter uses **replace-all** semantics — the value you pass becomes the application's complete set of environment variables. To change one variable, read the current set first and resubmit it with your change applied. `env_text` is the same operation with the same semantics, for a caller pasting a whole `.env` file instead of assembling an object; pass one or the other, never both.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).
- `appdir` · optional · string · e.g. `packages/web` — The application root, relative to the top of the source, for a source whose application does not live at the top level (for example, `packages/web` in a monorepo). Pass an empty value to reset the root back to the source top. Changing this value re-runs the preflight against the new root, which re-detects the application's `framework` and `category` and re-seeds the suggested build defaults (any value you pass explicitly in the same call takes precedence). When it changes, the response also carries the `confidence` and `defaults` from the re-detection. This parameter must be a relative path inside the source.
- `build_command` · optional · string · e.g. `npm run build` — The command that builds the application. Pass an empty value to clear it, so the deploy falls back to the detected default.
- `deployname` · optional · string · e.g. `my-app` — The name (slug) used to name the deployment. When omitted, the deployment is named after the application.
- `domain` · optional · string <domain> · e.g. `my-app.example.com` — The domain to bind the application to: a new subdomain of a domain the account owns, or the application's own already-materialized domain. A domain already claimed by another application is always rejected. A domain the account already uses for something else — the main domain, an addon domain, a manually created subdomain — is rejected unless `use_existing_domain` confirms it. See the `domain_in_use`, `domain_unavailable`, and `domain_temporary` `error_category` values. Pass an empty value to regenerate the application's default `<name>.<main domain>`.
- `env` · optional · string <json> · e.g. `{"NODE_ENV":"production","API_KEY":"abc123"}` — A JSON-encoded object of the application's environment variables. Warning: This **replaces all** existing environment variables with the set you provide. The values are written to the application's own `.env` file, which the container reads at startup. That file lives in the application's source tree, so setting values is refused unless the repository keeps it out of version control — see the `env_not_editable` `error_category` and the `env_editable` field on the application. An empty object clears the environment, which is allowed even then, because a clear removes values rather than publishing them. **Limits:** at most 16384 bytes of JSON and 64 variables. A name must match `[A-Za-z_][A-Za-z0-9_]*` and be at most 128 characters. A value must be a single value (not an object or a list), at most 4096 characters, and free of control characters. `PORT` is reserved by the system and is rejected.
- `env_text` · optional · string · e.g. `# deployment
NODE_ENV=production
API_KEY=abc123` — The raw contents of a `.env` file, for a caller pasting a whole file rather than assembling an object. Mutually exclusive with `env`; passing both is an error. Warning: This **replaces all** existing environment variables, exactly as `env` does. The text is read the way podman's `--env-file` reads it, so what is accepted here is what the container would have loaded from the same bytes: leading whitespace is trimmed, blank lines and lines beginning with `#` are ignored, the first `=` separates the name from the value, and the rest of the line is taken verbatim — no quote stripping and no trimming, so `A="b"` has the value `"b"` including the quotes. A name repeated on a later line takes that later value. A line with no `=` is rejected rather than copied from the server's own environment. The resulting variables are held to the same limits as `env`, and are refused for the same repository reasons. Text that yields no variables clears the environment, which is allowed even then, exactly as an empty `env` object is.
- `mode` · optional · string (`production`, `development`) · e.g. `production` — The run mode for `server` category applications.
- `output_dir` · optional · string · e.g. `dist` — The directory, relative to the application root, that the build writes its output to.
- `runtime_tag` · optional · string · e.g. `22` — The runtime version tag to run the application under. Use `WebApp::get_available` to list the valid tags.
- `startup_command` · optional · string · e.g. `npm run start` — The command that starts the application's server process. Only meaningful for the `server` category. Pass an empty value to clear it, so the deploy falls back to the adapter default. Clearing both this and `build_command` on a non-static application leaves it undeployable: the deploy then fails with a `requires_build` `error_category`.
- `use_existing_domain` · optional · integer (`0`, `1`) · e.g. `1` — Confirms that the application may be served at a domain the account already uses. The application is proxied over that domain, so whatever its document root serves — an existing website, and any files added to it later — stops being reachable until the application is deleted. Other configuration on a domain already in use (rewrites, handlers) may also take precedence and keep the application from being served, which is why a fresh, unused `<name>.<domain>` is the ideal target. See https://go.cpanel.net/docroot2proxy. Only meaningful alongside `domain`, and only kept while that domain is unchanged: pointing the application at a different domain requires confirming again. Omitting the parameter does not withdraw a confirmation already given — it leaves the standing one in place, so resending `domain` to change something else needs no reconfirmation. There is no way to withdraw a confirmation for a domain that still exists (sending `0` is refused with `domain_unavailable`); point the application at a different domain instead, which releases the reverse-proxy include on the domain being left so it serves its own document root again. It is recorded only when the domain already exists and the application did not create it; for one the application will create, or already created, the domain is the application's own, so there is nothing to take over and the application object reports `0`. It does not allow a domain another application already has, nor a domain the system cannot create.

**Returns** `data`: object — The application with its updated configuration.

- `build_command` (string) — The application's configured build command, or `null` if it has no build step.
- `category` (string (`static`, `server`, `other`)) — The application's category.
- `confidence` (string (`high`, `low`, `none`)) — How confident the preflight detection is.
- `container_name` (string) — The name of the deployed container backing this application, or `null` while it is only staged.
- `defaults` (object) — Suggested configuration values for the detected framework.
  - `build_command` (string) — The suggested build command, or `null` if no build step is needed.
  - `output_dir` (string) — The suggested build output directory, or `null` if not applicable.
  - `runtime_tag` (string) — The suggested runtime version tag.
  - `startup_command` (string) — The suggested startup command, or `null` for `static` applications.
- `deployed` (boolean) — Whether a deploy has put the application live.
- `deployname` (string) — The name used to name the deployment, or `null` when it defaults to the application name.
- `domain` (string <domain>) — The domain the application is bound to.
- `env` (object) — The application's environment variables.
- `env_editable` (boolean) — Whether the environment may be set for this application.
- `env_status` (string (`ok`, `tracked`, `not_ignored`)) — Why the environment is not editable, or `ok` when it is.
- `framework` (string) — The application's detected or user-selected framework, or `null` if unknown.
- `last_deploy` (object) — Information about the most recent deploy, or `null` if the application has never deployed.
  - `deploy_id` (string) — The unique identifier of the deploy.
  - `result` (string (`success`, `failed`)) — The result of the deploy.
  - `timestamp` (string <date-time>) — When the deploy finished, in ISO 8601 format.
- `mode` (string (`production`, `development`)) — The application's run mode.
- `name` (string) — The application's name (slug), unique across the account.
- `package_manager` (string (`npm`, `yarn`, `pnpm`, `bun`)) — The package manager the deploy uses to install dependencies and run scripts.
- `runtime` (string) — The application's runtime identifier.
- `runtime_tag` (string) — The runtime version tag.
- `source` (object) — The application's source information.
  - `branch` (string) — The Git branch, or `null` for ZIP sources.
  - `type` (string (`zip`, `git`)) — The source type.; `zip` — An uploaded archive.; `git` — A Git repository.
  - `url` (string) — The Git repository URL, or `null` for ZIP sources.
- `staged` (boolean) — Whether the application's source is present in the staging area.
- `startup_command` (string) — The application's configured startup command, or `null` for a `static` application (which has no running process to start).
- `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's current status.; `created` — Registered but never deployed.; `deploying` — A deploy is in progress.; `running` — The application is live.; `stopped` — The application is stopped.; `errored` — The last a
- `url` (string <url>) — The application's live HTTPS URL.
- `use_existing_domain` (integer) — Whether the application was confirmed onto a domain the account already used, replacing what that domain served.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  configure \
  name='my-app' \
  env='{"NODE_ENV":"production","API_KEY":"abc123"}' \
  build_command='npm run build' \
  startup_command='npm run start' \
  runtime_tag='22'
```

<a id="webapp-delete"></a>
### `WebApp::delete` — Delete an application.

`GET /execute/WebApp/delete` · RO/RW: unspecified · since cPanel 138

This function deletes an application: it stops the application's running process and removes its container, moves the application's directory aside to a `.bak` sibling (kept for verification or rollback rather than deleted), and removes the application from the account's registry. Deleting an application cannot be undone, so it requires an explicit confirmation: `verify` must be `1` to proceed. A `verify` of `0` makes no changes and returns a confirmation-required error. The application's domain is not affected; subdomains are managed independently. On failure, the `metadata.error_category` field carries a machine-readable failure category. **Important**: The `verify` parameter is **required** and has no default. You must set it to `1` to confirm this irreversible operation.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).
- `verify` · **required** · integer (`0`, `1`) · e.g. `1` — Confirmation that this irreversible deletion should proceed.; `1` — Confirm and delete: the container is torn down and the application's directory is moved aside to `<name>.bak` (kept for verification or rollback, not hard-deleted).; `0` — Make no changes; the call returns a confirmation-required error. This parameter is **required** and has no default.

**Returns** `data`: object

- `removed` (integer (`1`)) — Whether the application was removed.; `1` — Removed.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  delete \
  name='my-app' \
  verify='1'
```

<a id="webapp-deploy"></a>
### `WebApp::deploy` — Deploy an application.

`GET /execute/WebApp/deploy` · RO/RW: unspecified · since cPanel 138

Web Apps is the recommended feature for deploying new web applications; prefer it over the older Application Manager (`PassengerApps`) feature for new deployments. This function deploys an application: it installs dependencies, runs the build, and promotes the result to the live environment. **Note**: This function starts an asynchronous task and returns immediately. Stream the returned `sse_url` for live progress, or poll the task. While the task runs, the application's status is `deploying`. When the task finishes the status transitions to `running` on success or `errored` on failure. Use `WebApp::list` to read the current status and inspect `last_deploy` for the outcome and any failure category. **Important**: This function is idempotent. If you call it while a deploy for the same application is already running, it returns the in-flight task's identifiers instead of starting a new deploy. If this call fails before the task is dispatched (for example, when the application does not exist), `metadata.error_category` carries a machine-readable failure category. Build and runtime failures occur inside the background task and are recorded asynchronously in `last_deploy.error_category`, which is accessible via `WebApp::list`.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Returns** `data`: object

- `deploy_id` (string) — The unique identifier of this deploy.
- `sse_url` (string <url-path>) — The SSE URL to stream the deploy's progress.
- `task_id` (string) — The task id of the SSE process.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  deploy \
  name='my-app'
```

<a id="webapp-fetch-logs"></a>
### `WebApp::fetch_logs` — Fetch an application's runtime or build logs.

`GET /execute/WebApp/fetch_logs` · RO/RW: unspecified · since cPanel 138

This function fetches an application's runtime or build logs. It returns the most recent lines from the log the container persists on disk. It returns a static tail; live streaming of new lines is not yet available.

**Parameters**

- `log_type` · **required** · string (`app`, `build`) · e.g. `app` — The type of log to fetch.; `app` — The application's runtime output (stdout and stderr).; `build` — The output of the build step.
- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).
- `deploy_id` · optional · string · e.g. `dp-20260612-0001` — Limit the output to a specific deploy's logs. Only meaningful when `log_type` is `build`. This parameter defaults to the most recent deploy.
- `lines` · optional · integer · e.g. `100` — The maximum number of log lines to return, counted from the end of the log.

**Returns** `data`: object

- `lines` (array of string) — The requested log lines, oldest first.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  fetch_logs \
  name='my-app' \
  log_type='app' \
  lines='100'
```

<a id="webapp-get-available"></a>
### `WebApp::get_available` — List available application runtimes and limits.

`GET /execute/WebApp/get_available` · RO/RW: unspecified · since cPanel 138

This function returns the account's application capacity: the account-wide application pool, and — per App Type enabled on the server — the runtime's supported version tags and their package managers and the account's current per-type usage. Call this function first to determine what kinds of applications the account can deploy.

**Returns** `data`: object

- `account` (object) — The account-wide application capacity, shared across all App Types.
  - `apps` (object) — The account's total application allowance, applied across all App Types together.
- `runtimes` (object) — The App Types enabled on the server, keyed by runtime identifier (for example, `nodejs`).

```bash
uapi --output=jsonpretty --user=username WebApp get_available
```

<a id="webapp-has-feature"></a>
### `WebApp::has_feature` — Report whether the Web Apps feature is available.

`GET /execute/WebApp/has_feature` · RO/RW: unspecified · since cPanel 138

This function reports whether the Web Apps feature is available to the current account, so an interface can decide whether to surface it. It is available when the server has the feature enabled, the account's package feature list includes the feature, and the account is allowed at least one application.

**Returns** `data`: object

- `has_feature` (integer (`0`, `1`)) — Whether the Web Apps feature is available to the account.; `1` — Available.; `0` — Not available.

```bash
uapi --output=jsonpretty --user=username WebApp has_feature
```

<a id="webapp-list"></a>
### `WebApp::list` — List the account's web applications.

`GET /execute/WebApp/list` · RO/RW: unspecified · since cPanel 138

This function lists the account's web applications and their current state.

**Returns** `data`: array of object — The account's web applications.

- *(array of objects)*
  - `build_command` (string) — The application's configured build command, or `null` if it has no build step.
  - `category` (string (`static`, `server`, `other`)) — The application's category.
  - `container_name` (string) — The name of the deployed container backing this application, or `null` while it is only staged.
  - `deployed` (boolean) — Whether a deploy has put the application live.
  - `deployname` (string) — The name used to name the deployment, or `null` when it defaults to the application name.
  - `domain` (string <domain>) — The domain the application is bound to.
  - `env` (object) — The application's environment variables.
  - `env_editable` (boolean) — Whether the environment may be set for this application.
  - `env_status` (string (`ok`, `tracked`, `not_ignored`)) — Why the environment is not editable, or `ok` when it is.
  - `framework` (string) — The application's detected or user-selected framework, or `null` if unknown.
  - `last_deploy` (object) — Information about the most recent deploy, or `null` if the application has never deployed.
    - `deploy_id` (string) — The unique identifier of the deploy.
    - `result` (string (`success`, `failed`)) — The result of the deploy.
    - `timestamp` (string <date-time>) — When the deploy finished, in ISO 8601 format.
  - `mode` (string (`production`, `development`)) — The application's run mode.
  - `name` (string) — The application's name (slug), unique across the account.
  - `package_manager` (string (`npm`, `yarn`, `pnpm`, `bun`)) — The package manager the deploy uses to install dependencies and run scripts.
  - `runtime` (string) — The application's runtime identifier.
  - `runtime_tag` (string) — The runtime version tag.
  - `source` (object) — The application's source information.
    - `branch` (string) — The Git branch, or `null` for ZIP sources.
    - `type` (string (`zip`, `git`)) — The source type.; `zip` — An uploaded archive.; `git` — A Git repository.
    - `url` (string) — The Git repository URL, or `null` for ZIP sources.
  - `staged` (boolean) — Whether the application's source is present in the staging area.
  - `startup_command` (string) — The application's configured startup command, or `null` for a `static` application (which has no running process to start).
  - `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's current status.; `created` — Registered but never deployed.; `deploying` — A deploy is in progress.; `running` — The application is live.; `stopped` — The application is stopped.; `errored` — The last a
  - `url` (string <url>) — The application's live HTTPS URL.
  - `use_existing_domain` (integer) — Whether the application was confirmed onto a domain the account already used, replacing what that domain served.

```bash
uapi --output=jsonpretty --user=username WebApp list
```

<a id="webapp-redeploy"></a>
### `WebApp::redeploy` — Redeploy an application, pulling source updates first.

`GET /execute/WebApp/redeploy` · RO/RW: unspecified · since cPanel 138

This function redeploys an already-deployed application. For Git-sourced applications, it pulls the latest changes from the configured branch before deploying. Otherwise it behaves exactly like `WebApp::deploy`. **Note**: This function starts an asynchronous task and returns immediately. Stream the returned `sse_url` for live progress, or poll the task. While the task runs, the application's status is `deploying`. When the task finishes the status transitions to `running` on success or `errored` on failure. Use `WebApp::list` to read the current status and inspect `last_deploy` for the outcome and any failure category. **Important**: This function is idempotent. If you call it while a deploy for the same application is already running, it returns the in-flight task's identifiers instead of starting a new deploy. If this call fails before the task is dispatched (for example, when the application does not exist), `metadata.error_category` carries a machine-readable failure category. Build and runtime failures occur inside the background task and are recorded asynchronously in `last_deploy.error_category`, which is accessible via `WebApp::list`. When the source's selected SSH key is currently passphrase-protected, the pull cannot happen inside the asynchronous task -- its arguments are serialized to disk, and a passphrase must never persist there -- so this function requires `sshkeypass`, validates it, and runs the pull synchronously (adding to this call's latency) before queuing the rest of the pipeline, which never needs the key. A currently passphrase-protected selected SSH key cannot be unlocked on this GET operation -- use POST with `sshkeypass` in the request body instead.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Returns** `data`: object

- `deploy_id` (string) — The unique identifier of this deploy.
- `sse_url` (string <url-path>) — The SSE URL to stream the deploy's progress.
- `task_id` (string) — The task id of the SSE process.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  redeploy \
  name='my-app'
```

<a id="webapp-redeploy"></a>
### `WebApp::redeploy` — Redeploy an application, pulling source updates first.

`POST /execute/WebApp/redeploy` · RO/RW: unspecified · since cPanel 138

This function redeploys an already-deployed application. For Git-sourced applications, it pulls the latest changes from the configured branch before deploying. Otherwise it behaves exactly like `WebApp::deploy`. **Note**: This function starts an asynchronous task and returns immediately. Stream the returned `sse_url` for live progress, or poll the task. While the task runs, the application's status is `deploying`. When the task finishes the status transitions to `running` on success or `errored` on failure. Use `WebApp::list` to read the current status and inspect `last_deploy` for the outcome and any failure category. **Important**: This function is idempotent. If you call it while a deploy for the same application is already running, it returns the in-flight task's identifiers instead of starting a new deploy. If this call fails before the task is dispatched (for example, when the application does not exist), `metadata.error_category` carries a machine-readable failure category. Build and runtime failures occur inside the background task and are recorded asynchronously in `last_deploy.error_category`, which is accessible via `WebApp::list`. When the source's selected SSH key is currently passphrase-protected, the pull cannot happen inside the asynchronous task -- its arguments are serialized to disk, and a passphrase must never persist there -- so this function requires `sshkeypass`, validates it, and runs the pull synchronously (adding to this call's latency) before queuing the rest of the pipeline, which never needs the key. GET is also available, without a request body, when the source's selected SSH key is not currently passphrase-protected.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Request body** (`application/x-www-form-urlencoded`)

- `sshkeypass` (string) — The one-off passphrase to unlock the source's selected SSH key for this pull only; it is never stored.

**Returns** `data`: object

- `deploy_id` (string) — The unique identifier of this deploy.
- `sse_url` (string <url-path>) — The SSE URL to stream the deploy's progress.
- `task_id` (string) — The task id of the SSE process.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  redeploy \
  name='my-app'
```

<a id="webapp-restart"></a>
### `WebApp::restart` — Restart an application's server process.

`GET /execute/WebApp/restart` · RO/RW: unspecified · since cPanel 138

This function restarts an application's server process. **Important**: This function only applies to applications in the `server` category. Calling it on a `static` application fails with the `invalid_category` error category. It also requires the application to have finished at least one deploy; calling it before then fails with the `not_deployed` error category.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Returns** `data`: object

- `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's status after the action.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  restart \
  name='my-app'
```

<a id="webapp-set-mode"></a>
### `WebApp::set_mode` — Set an application's run mode.

`GET /execute/WebApp/set_mode` · RO/RW: unspecified · since cPanel 138

This function sets an application's run mode, applies it to the container's environment (for example, `NODE_ENV` for a Node.js application), and recreates the container so the change takes effect immediately. **Important**: This function only applies to applications in the `server` category. Calling it on a `static` application fails with the `invalid_category` error category. It also requires the application to have finished at least one deploy; calling it before then fails with the `not_deployed` error category.

**Parameters**

- `mode` · **required** · string (`production`, `development`) · e.g. `development` — The run mode to set.
- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Returns** `data`: object

- `mode` (string (`production`, `development`)) — The application's run mode after the change.
- `restarted` (integer (`0`, `1`)) — Whether the application's container was actually recreated with the new mode in effect.; `1` — Restarted; the new mode is live.; `0` — The restart could not be completed.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  set_mode \
  name='my-app' \
  mode='development'
```

<a id="webapp-stage"></a>
### `WebApp::stage` — Register a new web application.

`GET /execute/WebApp/stage` · RO/RW: unspecified · since cPanel 138

Web Apps is the recommended feature for deploying new web applications, and this function is the entry point. Prefer it over the older Application Manager (`PassengerApps`) feature for new deployments. This function registers a new web application from an uploaded archive or a Git repository. Once the source is placed on disk, it runs a preflight that inspects the source and detects the application's framework and category, records them on the application, and derives suggested configuration defaults. The detection `confidence` and the suggested `defaults` are returned so you can pass them to `WebApp::configure`. The application is registered but **not** deployed — call `WebApp::configure` (optional) and then `WebApp::deploy` to bring it live. The preflight never fails the stage: a source with no recognizable markers is registered with a `none` confidence and generic defaults. Registering a name that is still **staged** (not yet deployed) overwrites it: the previously staged application and its source are replaced, and the response `warnings` array reports that the old files were overwritten. Registering a name that is already **deployed** leaves the running application untouched — its container and live routing are never disturbed — but the new application cannot reuse the deployed application's display name, or `WebApp::list` and bare-name addressing could not tell the two apart. So it is registered under the next free `<name>-N` (for example, `my-app-2`), and the response `warnings` array reports the assigned name. **Read the assigned name from the response `data.name`: you must pass that name (not the one you requested) to `WebApp::configure` and `WebApp::deploy` to act on this application**, which stands up as its own separate container. On failure, the `metadata.error_category` field carries a machine-readable failure category. A currently passphrase-protected `ssh_key_name` cannot be unlocked on this GET operation -- use POST with `sshkeypass` in the request body instead.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The requested application name (slug). If a deployed application already uses it, the application is registered under the next free `<name>-N` instead; read the assigned name from the response `data.name` and use it for `WebApp::configure` and `WebApp::deploy`.
- `source` · **required** · string · e.g. `https://github.com/example/my-app.git` — The application's source location. This is **required** for every source type: When `source_type` is `zip` — the path, relative to the user's home directory, of a previously uploaded source archive: a ZIP or tar file (for example, `uploads/my-app.zip` or `uploads/my-app.tar.gz`).; When `source_type` is `git` — the Git repository URL to clone (for example, `https://github.com/example/my-app.git`). **Security note:** This source is built and run on the server. Only use uploaded archives or Git repositories from a trusted origin. Do not embed credentials (such as a username and password or an access token) in the Git URL — they are stored in plaintext. To clone a private repository, use a Git SSH URL that you have an SSH key configured for.
- `source_type` · **required** · string (`zip`, `git`) · e.g. `git` — The application's source type.; `zip` — An archive (ZIP or tar — `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`, `.tar.xz`) previously uploaded with `Fileman::upload_files`.; `git` — A Git repository.
- `appdir` · optional · string · e.g. `packages/web` — The application root, relative to the top of the cloned repository or extracted archive, for a source whose application does not live at the top level (for example, `packages/web` in a monorepo). The preflight inspects this directory to detect the framework. This parameter must be a relative path inside the source. When omitted, it defaults to the source root, unless the manifest is found in a single top-level subdirectory (as in a repository zip), in which case that subdirectory is used automatically.
- `branch` · optional · string · e.g. `main` — The Git branch to clone. Only meaningful when `source_type` is `git`. This parameter defaults to the repository's default branch.
- `mode` · optional · string (`production`, `development`) · e.g. `production` — The run mode for `server` category applications. This parameter defaults to `production`.
- `parent` · optional · string <domain> · e.g. `shop.example.com` — The parent domain to serve the application under. The application's domain becomes `<assigned name>.<parent>` — read it back from the response `data.domain` rather than composing it, since the assigned name may differ from the requested `name`. This is the parent domain only, not the whole served domain. The account must own the parent itself; owning only the domain above it is not sufficient. Omit this parameter — or pass an empty value — to serve the application under the account's main domain.
- `runtime` · optional · string (`nodejs`) · e.g. `nodejs` — The runtime that backs the application. This parameter defaults to the system default runtime (`nodejs`).
- `ssh_key_name` · optional · string · e.g. `github-test` — The name of one of the account's existing SSH keys (Security's "Manage SSH Keys") to use for the clone. Only meaningful for a `git@...` SSH source URL; invalid with `source_type` `zip`, or with an `https://` source. This lets the clone use a key that has real access to the repository even when it is not stored under one of ssh's default identity filenames. When this key is currently passphrase-protected, also provide `sshkeypass`.

**Returns** `data`: object — The newly registered application.

- `build_command` (string) — The application's configured build command, or `null` if it has no build step.
- `category` (string (`static`, `server`, `other`)) — The application's category.
- `confidence` (string (`high`, `low`, `none`)) — How confident the preflight detection is.; `high` — Strong framework markers found.; `low` — Partial markers found; verify the defaults before deploying.; `none` — No recognizable markers; the defaults are generic.
- `container_name` (string) — The name of the deployed container backing this application, or `null` while it is only staged.
- `defaults` (object) — Suggested configuration values for the detected framework.
  - `build_command` (string) — The suggested build command, or `null` if no build step is needed.
  - `output_dir` (string) — The suggested build output directory, or `null` if not applicable.
  - `runtime_tag` (string) — The suggested runtime version tag.
  - `startup_command` (string) — The suggested startup command, or `null` for `static` applications.
- `deployed` (boolean) — Whether a deploy has put the application live.
- `domain` (string <domain>) — The domain the application is bound to, composed as the assigned name under the requested `parent` — or under the account's main domain when `parent` was omitted.
- `env` (object) — The application's environment variables.
- `env_editable` (boolean) — Whether the environment may be set for this application.
- `env_status` (string (`ok`, `tracked`, `not_ignored`)) — Why the environment is not editable, or `ok` when it is.
- `framework` (string) — The application's detected or user-selected framework, or `null` if unknown.
- `last_deploy` (object) — Information about the most recent deploy, or `null` if the application has never deployed.
  - `deploy_id` (string) — The unique identifier of the deploy.
  - `result` (string (`success`, `failed`)) — The result of the deploy.
  - `timestamp` (string <date-time>) — When the deploy finished, in ISO 8601 format.
- `mode` (string (`production`, `development`)) — The application's run mode.
- `name` (string) — The application's assigned name (slug), unique across the account.
- `package_manager` (string (`npm`, `yarn`, `pnpm`, `bun`)) — The package manager the deploy uses to install dependencies and run scripts.
- `runtime` (string) — The application's runtime identifier.
- `runtime_tag` (string) — The runtime version tag.
- `source` (object) — The application's source information.
  - `branch` (string) — The Git branch, or `null` for ZIP sources.
  - `ssh_key_name` (string) — The name of the SSH key used for the clone, or `null` when none was selected or the source is not Git.
  - `type` (string (`zip`, `git`)) — The source type.; `zip` — An uploaded archive.; `git` — A Git repository.
  - `url` (string) — The Git repository URL, or `null` for ZIP sources.
- `staged` (boolean) — Whether the application's source is present in the staging area.
- `startup_command` (string) — The application's configured startup command, or `null` for a `static` application (which has no running process to start).
- `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's current status.; `created` — Registered but never deployed.; `deploying` — A deploy is in progress.; `running` — The application is live.; `stopped` — The application is stopped.; `errored` — The last a
- `url` (string <url>) — The application's live HTTPS URL.
- `use_existing_domain` (integer) — Whether the application was confirmed onto a domain the account already used, replacing what that domain served.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  stage \
  name='my-app' \
  source_type='git' \
  source='https://github.com/example/my-app.git' \
  branch='main'
```

<a id="webapp-stage"></a>
### `WebApp::stage` — Register a new web application.

`POST /execute/WebApp/stage` · RO/RW: unspecified · since cPanel 138

Web Apps is the recommended feature for deploying new web applications, and this function is the entry point. Prefer it over the older Application Manager (`PassengerApps`) feature for new deployments. This function registers a new web application from an uploaded archive or a Git repository. Once the source is placed on disk, it runs a preflight that inspects the source and detects the application's framework and category, records them on the application, and derives suggested configuration defaults. The detection `confidence` and the suggested `defaults` are returned so you can pass them to `WebApp::configure`. The application is registered but **not** deployed — call `WebApp::configure` (optional) and then `WebApp::deploy` to bring it live. The preflight never fails the stage: a source with no recognizable markers is registered with a `none` confidence and generic defaults. Registering a name that is still **staged** (not yet deployed) overwrites it: the previously staged application and its source are replaced, and the response `warnings` array reports that the old files were overwritten. Registering a name that is already **deployed** leaves the running application untouched — its container and live routing are never disturbed — but the new application cannot reuse the deployed application's display name, or `WebApp::list` and bare-name addressing could not tell the two apart. So it is registered under the next free `<name>-N` (for example, `my-app-2`), and the response `warnings` array reports the assigned name. **Read the assigned name from the response `data.name`: you must pass that name (not the one you requested) to `WebApp::configure` and `WebApp::deploy` to act on this application**, which stands up as its own separate container. On failure, the `metadata.error_category` field carries a machine-readable failure category. GET is also available, without a request body, for calls that do not need to unlock a passphrase-protected `ssh_key_name`.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The requested application name (slug). If a deployed application already uses it, the application is registered under the next free `<name>-N` instead; read the assigned name from the response `data.name` and use it for `WebApp::configure` and `WebApp::deploy`.
- `source` · **required** · string · e.g. `https://github.com/example/my-app.git` — The application's source location. This is **required** for every source type: When `source_type` is `zip` — the path, relative to the user's home directory, of a previously uploaded source archive: a ZIP or tar file (for example, `uploads/my-app.zip` or `uploads/my-app.tar.gz`).; When `source_type` is `git` — the Git repository URL to clone (for example, `https://github.com/example/my-app.git`). **Security note:** This source is built and run on the server. Only use uploaded archives or Git repositories from a trusted origin. Do not embed credentials (such as a username and password or an access token) in the Git URL — they are stored in plaintext. To clone a private repository, use a Git SSH URL that you have an SSH key configured for.
- `source_type` · **required** · string (`zip`, `git`) · e.g. `git` — The application's source type.; `zip` — An archive (ZIP or tar — `.tar`, `.tar.gz`/`.tgz`, `.tar.bz2`, `.tar.xz`) previously uploaded with `Fileman::upload_files`.; `git` — A Git repository.
- `appdir` · optional · string · e.g. `packages/web` — The application root, relative to the top of the cloned repository or extracted archive, for a source whose application does not live at the top level (for example, `packages/web` in a monorepo). The preflight inspects this directory to detect the framework. This parameter must be a relative path inside the source. When omitted, it defaults to the source root, unless the manifest is found in a single top-level subdirectory (as in a repository zip), in which case that subdirectory is used automatically.
- `branch` · optional · string · e.g. `main` — The Git branch to clone. Only meaningful when `source_type` is `git`. This parameter defaults to the repository's default branch.
- `mode` · optional · string (`production`, `development`) · e.g. `production` — The run mode for `server` category applications. This parameter defaults to `production`.
- `parent` · optional · string <domain> · e.g. `shop.example.com` — The parent domain to serve the application under. The application's domain becomes `<assigned name>.<parent>` — read it back from the response `data.domain` rather than composing it, since the assigned name may differ from the requested `name`. This is the parent domain only, not the whole served domain. The account must own the parent itself; owning only the domain above it is not sufficient. Omit this parameter — or pass an empty value — to serve the application under the account's main domain.
- `runtime` · optional · string (`nodejs`) · e.g. `nodejs` — The runtime that backs the application. This parameter defaults to the system default runtime (`nodejs`).
- `ssh_key_name` · optional · string · e.g. `github-test` — The name of one of the account's existing SSH keys (Security's "Manage SSH Keys") to use for the clone. Only meaningful for a `git@...` SSH source URL; invalid with `source_type` `zip`, or with an `https://` source. This lets the clone use a key that has real access to the repository even when it is not stored under one of ssh's default identity filenames. When this key is currently passphrase-protected, also provide `sshkeypass`.

**Request body** (`application/x-www-form-urlencoded`)

- `sshkeypass` (string) — The one-off passphrase to unlock `ssh_key_name` for this clone only; it is never stored.

**Returns** `data`: object — The newly registered application.

- `build_command` (string) — The application's configured build command, or `null` if it has no build step.
- `category` (string (`static`, `server`, `other`)) — The application's category.
- `confidence` (string (`high`, `low`, `none`)) — How confident the preflight detection is.; `high` — Strong framework markers found.; `low` — Partial markers found; verify the defaults before deploying.; `none` — No recognizable markers; the defaults are generic.
- `container_name` (string) — The name of the deployed container backing this application, or `null` while it is only staged.
- `defaults` (object) — Suggested configuration values for the detected framework.
  - `build_command` (string) — The suggested build command, or `null` if no build step is needed.
  - `output_dir` (string) — The suggested build output directory, or `null` if not applicable.
  - `runtime_tag` (string) — The suggested runtime version tag.
  - `startup_command` (string) — The suggested startup command, or `null` for `static` applications.
- `deployed` (boolean) — Whether a deploy has put the application live.
- `domain` (string <domain>) — The domain the application is bound to, composed as the assigned name under the requested `parent` — or under the account's main domain when `parent` was omitted.
- `env` (object) — The application's environment variables.
- `env_editable` (boolean) — Whether the environment may be set for this application.
- `env_status` (string (`ok`, `tracked`, `not_ignored`)) — Why the environment is not editable, or `ok` when it is.
- `framework` (string) — The application's detected or user-selected framework, or `null` if unknown.
- `last_deploy` (object) — Information about the most recent deploy, or `null` if the application has never deployed.
  - `deploy_id` (string) — The unique identifier of the deploy.
  - `result` (string (`success`, `failed`)) — The result of the deploy.
  - `timestamp` (string <date-time>) — When the deploy finished, in ISO 8601 format.
- `mode` (string (`production`, `development`)) — The application's run mode.
- `name` (string) — The application's assigned name (slug), unique across the account.
- `package_manager` (string (`npm`, `yarn`, `pnpm`, `bun`)) — The package manager the deploy uses to install dependencies and run scripts.
- `runtime` (string) — The application's runtime identifier.
- `runtime_tag` (string) — The runtime version tag.
- `source` (object) — The application's source information.
  - `branch` (string) — The Git branch, or `null` for ZIP sources.
  - `ssh_key_name` (string) — The name of the SSH key used for the clone, or `null` when none was selected or the source is not Git.
  - `type` (string (`zip`, `git`)) — The source type.; `zip` — An uploaded archive.; `git` — A Git repository.
  - `url` (string) — The Git repository URL, or `null` for ZIP sources.
- `staged` (boolean) — Whether the application's source is present in the staging area.
- `startup_command` (string) — The application's configured startup command, or `null` for a `static` application (which has no running process to start).
- `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's current status.; `created` — Registered but never deployed.; `deploying` — A deploy is in progress.; `running` — The application is live.; `stopped` — The application is stopped.; `errored` — The last a
- `url` (string <url>) — The application's live HTTPS URL.
- `use_existing_domain` (integer) — Whether the application was confirmed onto a domain the account already used, replacing what that domain served.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  stage \
  name='my-app' \
  source_type='git' \
  source='https://github.com/example/my-app.git' \
  branch='main'
```

<a id="webapp-start"></a>
### `WebApp::start` — Start an application's server process.

`GET /execute/WebApp/start` · RO/RW: unspecified · since cPanel 138

This function starts an application's server process. **Important**: This function only applies to applications in the `server` category. Calling it on a `static` application fails with the `invalid_category` error category. It also requires the application to have finished at least one deploy; calling it before then fails with the `not_deployed` error category.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Returns** `data`: object

- `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's status after the action.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  start \
  name='my-app'
```

<a id="webapp-stop"></a>
### `WebApp::stop` — Stop an application's server process.

`GET /execute/WebApp/stop` · RO/RW: unspecified · since cPanel 138

This function stops an application's server process. **Important**: This function only applies to applications in the `server` category. Calling it on a `static` application fails with the `invalid_category` error category. It also requires the application to have finished at least one deploy; calling it before then fails with the `not_deployed` error category.

**Parameters**

- `name` · **required** · string · e.g. `my-app` — The application's unique name (slug).

**Returns** `data`: object

- `status` (string (`created`, `deploying`, `running`, `stopped`, `errored`)) — The application's status after the action.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebApp \
  stop \
  name='my-app'
```

