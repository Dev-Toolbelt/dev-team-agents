<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Statistics

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Domain Statistics**: [`Stats::get_bandwidth`](#stats-get-bandwidth), [`Stats::get_site_errors`](#stats-get-site-errors), [`Stats::get_stats_daily`](#stats-get-stats-daily), [`Stats::list_sites`](#stats-list-sites), [`Stats::list_stats_by_domain`](#stats-list-stats-by-domain)
- **Weblog Settings**: [`StatsManager::get_configuration`](#statsmanager-get-configuration), [`StatsManager::save_configuration`](#statsmanager-save-configuration)

## Domain Statistics

<a id="stats-get-bandwidth"></a>
### `Stats::get_bandwidth` — Return bandwidth statistics for all domains

`GET /execute/Stats/get_bandwidth` · RO · since cPanel 84

This function retrieves a list of bandwidth records for the domains on a cPanel account. Note: This function also returns the bandwidth use of a [distributed cPanel account](https://docs.cpanel.net/knowledge-base/cpanel-product/cpanel-glossary#distributed-cpanel-account). Warning: This function requires the _Bandwidth Stats_ feature. To enable this feature, use WHM's [_Feature Manager_](https://go.cpanel.net/whmdocsFeatureManager) interface (_WHM >> Home >> Packages >> Feature Manager_).

**Parameters**

- `timezone` · optional · string · e.g. `America/Chicago` — The timezone in which to report the data, in [Olson tz format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). Note: This parameter defaults to the server's timezone.

**Returns** `data`: array of object

- *(array of objects)*
  - `bytes` (integer) — The domain's bandwidth usage, in bytes.
  - `domain` (string <domain>) — The domain for which to display bandwidth statistics.
  - `month_start` (integer <unix_timestamp>) — The beginning of the report window.
  - `protocol` (string (`http`, `imap`, `smtp`, `pop3`, `ftp`)) — The protocol for which to provide data.; `http`; `imap`; `smtp`; `pop3`; `ftp`

```bash
uapi --output=jsonpretty \
  --user=username \
  Stats \
  get_bandwidth
```

<a id="stats-get-site-errors"></a>
### `Stats::get_site_errors` — Return specified domain access log

`GET /execute/Stats/get_site_errors` · RO · since cPanel 84

This function returns entries from a domain's error log.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain for which to return error log entries.
- `log` · optional · string (`error`, `suexec`) · e.g. `suexec` — The [Apache log file](https://go.cpanel.net/cpanellogfiles) to query. This parameter defaults to error.; `error` - The `/var/log/apache2/error_log` file.; `suexec` - The `/var/log/apache2/suexec_log` file.
- `maxlines` · optional · integer · default `300` · e.g. `250` — The number of lines to retrieve from the error log.

**Returns** `data`: array of object

- *(array of objects)*
  - `date` (integer <unix_timestamp>) — The date that the system recorded the error.
  - `entry` (string) — The error log entry.

```bash
uapi --output=jsonpretty \
  --user=username \
  Stats \
  get_site_errors \
  domain='example.com'
```

<a id="stats-get-stats-daily"></a>
### `Stats::get_stats_daily` — Return daily AwStats statistics for a domain

`GET /execute/Stats/get_stats_daily` · RO · since cPanel 132

This function returns the daily AwStats statistics for a domain.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain to retrieve statistics for. Must be owned by the current cPanel user.

**Returns** `data`: object

- `domain` (string) — The domain associated with the returned daily stats.
- `stats` (object) — A map of date strings (YYYY-MM-DD) to daily statistics.

```bash
uapi --output=jsonpretty \
  --user=username \
  Stats \
  get_stats_daily \
  domain='example.com'
```

<a id="stats-list-sites"></a>
### `Stats::list_sites` — Return Analog statistics for all domains

`GET /execute/Stats/list_sites` · RO · since cPanel 84

This function displays the Analog statistics for the domains on a cPanel account.

**Parameters**

- `engine` · **required** · string (`webalizer`, `analog`) · e.g. `webalizer` — The statistics engine.; `webalizer`; `analog`
- `traffic` · optional · string (`http`, `ftp`) · default `http` · e.g. `http` — The web traffic type.; `http`; `ftp`

**Returns** `data`: array of object

- *(array of objects)*
  - `all_domains` (integer (`0`, `1`)) — Whether the statistics file's filepath is for all the domains on a cPanel account.; `1` - All domains.; `0` - An individual domain.
  - `domain` (string <domain>) — The domain for which to display statistics.
  - `path` (string <path>) — The filepath to the statistics file.
  - `ssl` (integer (`0`, `1`)) — Whether the function generates statistics from SSL requests.; `1` - Generates statistics for SSL requests.; `0` - Generates statistics for non-SSL requests.

```bash
uapi --output=jsonpretty \
  --user=username \
  Stats \
  list_sites \
  engine='webalizer'
```

<a id="stats-list-stats-by-domain"></a>
### `Stats::list_stats_by_domain` — Return Analog statistics for specified domain

`GET /execute/Stats/list_stats_by_domain` · RO · since cPanel 84

This function returns a domain's Analog statistics.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain from which to retrieve statistics.
- `engine` · **required** · string (`analog`) · e.g. `analog` — The statistics engine. `analog` is the only possible value.
- `ssl` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to return statistics from SSL requests.; `1` - Return statistics for SSL requests.; `0` - Return statistics for non-SSL requests.

**Returns** `data`: array of object

- *(array of objects)*
  - `date` (integer <unix_timestamp>) — The current date and time.
  - `url` (string) — The URL of the file from which the system generates statistics reports.

```bash
uapi --output=jsonpretty \
  --user=username \
  Stats \
  list_stats_by_domain \
  engine='analog' \
  domain='example.com'
```

## Weblog Settings

<a id="statsmanager-get-configuration"></a>
### `StatsManager::get_configuration` — Returns weblog analyzers' configuration

`GET /execute/StatsManager/get_configuration` · RO · since 90

This function lists the configuration of the web log anayzers for each domain on the cPanel account. Important: When you disable the WebServer role the system disables this function. For more information, read our How to Use [Server Profiles documentation](https://docs.cpanel.net/knowledge-base/general-systems-administration/how-to-use-server-profiles/). **Note** Additional web log analyzer configuration such as if the user can edit their own configuration is provided in the metadata section of the return.

**Returns** `data`: array of object — A list of domains and the status of each of the web log analyzers available in cPanel for that domain.

- *(array of objects)*
  - `analyzers` (array of object) — List of log analyzer configuration objects for this domain.
    - *(array of objects)*
      - `enabled` (integer (`1`, `0`)) — Whether the analyzer is turned on or off for the domain.; `1` - the analyzer is enabled.; `0` - the analyzer is disabled.
      - `enabled_by_user` (integer (`1`, `0`)) — Whether the analyzer is turned on or off for the domain specifically by this user.; `1` - the analyzer is enabled by the user.; `0` - the analyzer is disabled by the user.
      - `name` (string (`analog`, `awstats`, `webalizer`)) — Name of the analyzer.
  - `domain` (string) — The domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  StatsManager \
  get_configuration
```

<a id="statsmanager-save-configuration"></a>
### `StatsManager::save_configuration` — Save current user's weblog analyzers configuration

`POST /execute/StatsManager/save_configuration` · RW · rollback: none · since 90

This function saves the users choice about which web log anayzers are enabled for each domain on their cPanel users account. If the log anayzers are controlled by the reseller or root account, the user cannot manage which log analyzers are enabled or disabled. Important: When you disable the WebServer role the system disables this function. For more information, read our How to Use Server Profiles documentation.

**Request body** (`application/json`)

- `changes` (array of object) — 
  - *(array of objects)*
    - `analyzers` (array of object) — List of log analyzer configuration objects.
    - `domain` (string) — Domain you want to configure.

**Returns** `data`: array of object — A list of domains and the status of each of the web log analyzers available in cPanel for that domain.

- *(array of objects)*
  - `analyzers` (array of object) — List of log analyzer configuration objects for this domain
    - *(array of objects)*
      - `available` (integer (`1`, `0`)) — Whether the analyzer is turned on or off for the whole server.; `1` - the analyzer is enabled on the server.; `0` - the analyzer is disabled on the server.
      - `enabled` (integer (`1`, `0`)) — Whether the analyzer is turned on or off for the domain.; `1` - the analyzer is enabled.; `0` - the analyzer is disabled.
      - `locked` (integer (`1`, `0`)) — Whether the analyzer can be turned on or off for the domain by the cPanel user.; `1` - the analyzer can be managed by the cPanel user.; `0` - the analyzer cannot be managed by the cPanel user.
      - `name` (string (`analog`, `awstats`, `webalizer`)) — Name of the analyzer.
  - `domain` (string) — The domain.

```bash
echo '{"changes":[{"analyzers":[{"enabled":"1","name":"awstats"},{"enabled":"0","name":"analog"},{"enabled":"0","name":"webalizer"}],"domain":"domain.com"}]}' | \
uapi --input=json --output=jsonpretty \
  --user=username \
  StatsManager \
  save_configuration
```

