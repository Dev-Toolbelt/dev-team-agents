<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Retrieve bandwidth information

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Bandwidth**: [`Bandwidth::get_enabled_protocols`](#bandwidth-get-enabled-protocols), [`Bandwidth::get_retention_periods`](#bandwidth-get-retention-periods), [`Bandwidth::query`](#bandwidth-query)

## Bandwidth

<a id="bandwidth-get-enabled-protocols"></a>
### `Bandwidth::get_enabled_protocols` — Return services monitored in bandwidth data

`GET /execute/Bandwidth/get_enabled_protocols` · RO · since cPanel 76

This function returns a list of the server's enabled protocols.

**Returns** `data`: array of string (`ftp`, `http`, `imap`, `pop3`, `smtp`) — The bandwidth protocols that the server records.; `ftp`; `imap`; `pop3`; `smtp`; `http` — This value includes all web traffic for the 80 and 443 ports.

```bash
uapi --output=jsonpretty \
  --user=username \
  Bandwidth \
  get_enabled_protocols
```

<a id="bandwidth-get-retention-periods"></a>
### `Bandwidth::get_retention_periods` — Return bandwidth retention period

`GET /execute/Bandwidth/get_retention_periods` · RO · since cPanel 11.52

This function retrieves the retention periods for bandwidth data.

**Returns** `data`: array of object

- *(array of objects)*
  - `interval` (string (`daily`, `hourly`, `5min`)) — The interval in which the system reports bandwidth data.; `daily`; `hourly`; `5min`
  - `retention` (integer <unix_timestamp>) — The retention period for bandwidth data.

```bash
uapi --output=jsonpretty \
  --user=username \
  Bandwidth \
  get_retention_periods
```

<a id="bandwidth-query"></a>
### `Bandwidth::query` — Return cPanel account's bandwidth usage report

`GET /execute/Bandwidth/query` · RO · since cPanel 11.52

This function queries an account's bandwidth data and returns a report. Note: This function also returns the bandwidth use of a [distributed cPanel account](https://go.cpanel.net/cPanelGlossary#distributed-cpanel-account).

**Parameters**

- `grouping` · **required** · string (`domain`, `protocol`) or string (`year`, `year_month`, `year_month_day`, `year_month_day_hour`, `year_month_day_hour_minute`) — How to group the data in the report, in pipe-separated format. This list **must** contain one or both of the following parameters: A pipe-separated list that contains one or both of the following parameters: `domain`; `protocol` This parameter can also include only **one** of the following start time interval types: `year`; `year_month`; `year_month_day`; `year_month_day_hour`; `year_month_day_mour_minute` Note:  This parameter accepts a maximum of three values.; The function nests the return objects in the order that you declare the values in this parameter.
- `domains` · optional · string <domain> — A pipe-separated list of domains for which to provided data. Note:  If you do not include this parameter, the function will return data for all domains on the cPanel account.; The `UNKNOWN` "pseudo-domain" refers to data recorded without a specific domain. All traffic except HTTP traffic is recorded without a specific domain.
- `end` · optional · integer <unix_timestamp> · e.g. `1446664809` — The end date of the report window.
- `interval` · optional · string (`daily`, `hourly`, `5min`) · default `daily` · e.g. `daily` — Length of time between bandwidth data samples.; `daily`; `hourly`; `5min` Note: The interval's retention period determines availability of the interval's data. Use the `Bandwidth::get_retention_periods` API to determine an interval's retention period.
- `protocols` · optional · string — A pipe-separated list of the protocols for which to provide data.; `http`; `imap`; `smtp`; `pop3`; `ftp`
- `start` · optional · integer <unix_timestamp> · e.g. `1445664609` — The start date of the report window.
- `timezone` · optional · string <olson_timezone_name> · e.g. `America/Chicago` — The timezone in which to report the data.

**Returns** `data`: object — The function returns data in a hierarchy of objects that the order of values in the `grouping` parameter determines.

```bash
uapi --output=jsonpretty \
  --user=username \
  Bandwidth \
  query \
  grouping='domain|protocol|year'
```

