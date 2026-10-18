<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — cPanel Account

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Account Enhancements**: [`AccountEnhancements::has_enhancement`](#accountenhancements-has-enhancement), [`AccountEnhancements::list`](#accountenhancements-list)
- **DomainRecommendations**: [`DomainRecommendations::domain_availability`](#domainrecommendations-domain-availability), [`DomainRecommendations::domain_suggestions`](#domainrecommendations-domain-suggestions), [`DomainRecommendations::get_store_config`](#domainrecommendations-get-store-config), [`DomainRecommendations::is_enabled`](#domainrecommendations-is-enabled), [`DomainRecommendations::purchase_domain`](#domainrecommendations-purchase-domain), [`DomainRecommendations::supported_tlds`](#domainrecommendations-supported-tlds)
- **cPanel Features**: [`Features::get_feature_metadata`](#features-get-feature-metadata), [`Features::has_feature`](#features-has-feature), [`Features::has_features_like`](#features-has-features-like), [`Features::list_features`](#features-list-features), [`Features::list_features_like`](#features-list-features-like)
- **Personalization**: [`Personalization::get`](#personalization-get), [`Personalization::set`](#personalization-set)
- **Disk Quotas**: [`Quota::get_local_quota_info`](#quota-get-local-quota-info), [`Quota::get_quota_info`](#quota-get-quota-info)
- **Account Information**: [`Resellers::list_accounts`](#resellers-list-accounts), [`Variables::get_user_information`](#variables-get-user-information)
- **Resource Usage and Statistics**: [`ResourceUsage::get_usages`](#resourceusage-get-usages), [`StatsBar::get_stats`](#statsbar-get-stats)
- **Team Users**: [`Team::add_roles`](#team-add-roles), [`Team::add_team_user`](#team-add-team-user), [`Team::cancel_expire`](#team-cancel-expire), [`Team::edit_team_user`](#team-edit-team-user), [`Team::get_team_users_with_roles_count`](#team-get-team-users-with-roles-count), [`Team::list_team`](#team-list-team), [`Team::password_reset_request`](#team-password-reset-request), [`Team::reinstate_team_user`](#team-reinstate-team-user), [`Team::remove_roles`](#team-remove-roles), [`Team::remove_team_user`](#team-remove-team-user), [`Team::set_contact_email`](#team-set-contact-email), [`Team::set_expire`](#team-set-expire), [`Team::set_locale`](#team-set-locale), [`Team::set_notes`](#team-set-notes), [`Team::set_password`](#team-set-password), [`Team::set_roles`](#team-set-roles), [`Team::suspend_team_user`](#team-suspend-team-user)
- **Team Roles**: [`TeamRoles::list_feature_descriptions`](#teamroles-list-feature-descriptions)
- **Account Management**: [`UserManager::change_password`](#usermanager-change-password), [`Users::change_password`](#users-change-password)
- **Subaccount Management**: [`UserManager::check_account_conflicts`](#usermanager-check-account-conflicts), [`UserManager::create_user`](#usermanager-create-user), [`UserManager::delete_user`](#usermanager-delete-user), [`UserManager::dismiss_merge`](#usermanager-dismiss-merge), [`UserManager::edit_user`](#usermanager-edit-user), [`UserManager::list_users`](#usermanager-list-users), [`UserManager::lookup_service_account`](#usermanager-lookup-service-account), [`UserManager::lookup_user`](#usermanager-lookup-user), [`UserManager::merge_service_account`](#usermanager-merge-service-account), [`UserManager::unlink_service_account`](#usermanager-unlink-service-account)

## Account Enhancements

<a id="accountenhancements-has-enhancement"></a>
### `AccountEnhancements::has_enhancement` — Validate Account Enhancement assignment

`GET /execute/AccountEnhancements/has_enhancement` · RO · since cPanel 98

This function returns whether a cPanel account has a specific [Account Enhancement](https://go.cpanel.net/account-enhancements).

**Parameters**

- `id` · **required** · string · e.g. `sample-enhancement-id` — The identifier for a specific Account Enhancement. Note: To retrieve a list of all Account Enhancements IDs on the server, run the WHM API 1 `list_account_enhancements` function.

**Returns** `data`: integer (`1`, `0`) — * `1` - The Account Enhancement is assigned to the cPanel account.; `0` - The Account Enhancement is not assigned to the cPanel account.

```bash
uapi --output=jsonpretty \
  --user=username \
  AccountEnhancements \
  has_enhancement \
  id=account_enhancement
```

<a id="accountenhancements-list"></a>
### `AccountEnhancements::list` — Return all cPanel account's Account Enhancements

`GET /execute/AccountEnhancements/list` · RO · since cPanel 98

This function lists a cPanel account's [Account Enhancements](https://go.cpanel.net/account-enhancements).

**Returns** `data`: any — An object that contains the Account Enhancements that the cPanel account can access

- *(array of objects)*
  - `id` (string) — The Account Enhancement's id.
  - `name` (string) — The Account Enhancement's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  AccountEnhancements \
  list
```

## DomainRecommendations

<a id="domainrecommendations-domain-availability"></a>
### `DomainRecommendations::domain_availability` — Check whether a domain is available for registration

`GET /execute/DomainRecommendations/domain_availability` · RO · since cPanel 134

This function checks whether a specific domain name is available for registration through the configured domain store. The system caches the results for up to two minutes per domain. Use the `use_cache=0` option to bypass the cache and force a live request. Note: This function requires the `domain_recommendation` feature.

**Parameters**

- `domain` · **required** · string · e.g. `mybusiness.com` — The fully-qualified domain name (FQDN) to check for availability. Note: This value must include the TLD (for example, `mybusiness.com`).
- `use_cache` · optional · integer (`1`, `0`) · default `1` · e.g. `1` — Whether to use the local response cache.; `1` — Use the cache (default). The system caches the results for up to two minutes.; `0` — Bypass the cache and make a live request to the store.

**Returns** `data`: object — An object containing the domain availability result from the configured domain store.

- `domain_name` (string) — The fully-qualified domain name (FQDN) that the function checked.
- `group` (string) — The domain group, if applicable.
- `idn_domain_name` (string) — The internationalized domain name (IDN) of the checked domain.
- `idn_sld` (string) — The internationalized second-level domain (SLD) portion of the checked domain.
- `is_domain_available` (boolean) — Whether the domain is available for registration.; `true` — Available.; `false` — Not available.
- `is_premium` (boolean) — Whether the domain is a premium domain with special pricing.; `true` — The domain is a premium domain.; `false` — The domain is not a premium domain.
- `is_tld_available` (boolean) — Whether the TLD is available for registration through the configured store.; `true` — The TLD is available.; `false` — The TLD is not available.
- `premium_cost_pricing` (object) — The pricing structure for the premium domain, if applicable.
- `pricing` (array of object) — An array of pricing options for each registration period (in years).
  - *(array of objects)*
    - `period` (integer) — The registration period in years.
    - `register` (object) — The registration price for this period.
    - `renew` (object) — The renewal price for this period.
    - `transfer` (object) — The transfer price for this period.
- `shortest_period` (object) — Pricing for a single registration period.
  - `period` (integer) — The registration period in years.
  - `register` (object) — The registration price for this period.
  - `renew` (object) — The renewal price for this period.
  - `transfer` (object) — The transfer price for this period.
- `sld` (string) — The second-level domain (SLD) portion of the checked domain.
- `status` (string) — A string describing the availability status of the domain.
- `tld` (string) — The top-level domain (TLD) portion of the checked domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainRecommendations \
  domain_availability \
  domain=mybusiness.com
```

<a id="domainrecommendations-domain-suggestions"></a>
### `DomainRecommendations::domain_suggestions` — Search for available domain names and pricing

`GET /execute/DomainRecommendations/domain_suggestions` · RO · since cPanel 134

This function returns available domain name suggestions and their registration pricing for a given search term. The system retrieves the results from the configured domain store and caches them for up to two minutes per unique combination of `search_field`, `page`, `page_size`, and the requested `tld` list. Use the `use_cache=0` option to bypass the cache and force a live request. Note: This function requires the `domain_recommendation` feature.

**Parameters**

- `search_field` · **required** · string · e.g. `mybusiness` — The search term used to generate domain suggestions. This is a free-text query, not necessarily a fully-qualified domain name. Note: Use the base domain name without the TLD (for example, `mybusiness` instead of `mybusiness.com`).
- `page` · optional · integer · e.g. `1` — The page number to retrieve (1-indexed). If you do not set this value, the function uses the store's default page.
- `page_size` · optional · integer · e.g. `10` — The number of suggestions to return per page. If you do not set this value, the function uses the store's default page size.
- `use_cache` · optional · integer (`1`, `0`) · default `1` · e.g. `1` — Whether to use the local response cache.; `1` — Use the cache (default). The function caches the results for up to two minutes.; `0` — Bypass the cache and make a live request to the store.

**Returns** `data`: object — An object containing pagination metadata and domain suggestions.

- `meta` (object) — Pagination and result metadata that the store returns.
  - `page` (integer) — The current page number (1-indexed).
  - `page_size` (integer) — The number of results per page.
  - `total_items` (integer) — The total number of available matching domain suggestions.
  - `total_pages` (integer) — The total number of available pages.
- `suggestions` (object) — A mapping of available domain names to pricing periods.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainRecommendations \
  domain_suggestions \
  search_field=mybusiness
```

<a id="domainrecommendations-get-store-config"></a>
### `DomainRecommendations::get_store_config` — Retrieve the sanitized domain store configuration

`GET /execute/DomainRecommendations/get_store_config` · RO · since cPanel 134

This function returns the allowlisted store configuration for the Domain Recommendations feature. Important: This function returns only explicitly allowlisted fields. Any key not on the allowlist — including credentials, URLs, and future additions — is excluded by default. Note: This function requires the `domain_recommendation` feature.

**Returns** `data`: object — An object containing the allowlisted store configuration values.

- `store_type` (string) — The type of the configured domain store.; `WHMCS` — The store uses a WHMCS backend.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainRecommendations \
  get_store_config
```

<a id="domainrecommendations-is-enabled"></a>
### `DomainRecommendations::is_enabled` — Check whether Domain Recommendations is enabled

`GET /execute/DomainRecommendations/is_enabled` · RO · since cPanel 134

This function returns the enablement status of the Domain Recommendations feature on the server. Note: This function requires the `domain_recommendation` feature. If the cPanel account does not have this feature, the function returns an error.

**Returns** `data`: object — An object containing the enabled status of the Domain Recommendations feature.

- `is_enabled` (integer (`1`, `0`)) — Whether the server has the Domain Recommendations feature enabled.; `1` — Enabled.; `0` — Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainRecommendations \
  is_enabled
```

<a id="domainrecommendations-purchase-domain"></a>
### `DomainRecommendations::purchase_domain` — Get a URL to purchase a domain

`GET /execute/DomainRecommendations/purchase_domain` · RW · rollback: none · since cPanel 138

This function returns a URL for the configured domain store's checkout page. This URL allows the user to complete the purchase of a domain name. Note: This function requires the `domain_recommendation` feature.

**Parameters**

- `domain` · **required** · string · e.g. `mybusiness.com` — The fully-qualified domain name (FQDN) to purchase. Note: This value must include the TLD (for example, `mybusiness.com`).
- `period` · **required** · integer · e.g. `1` — The registration period in years.

**Returns** `data`: object — An object that contains the URL to complete the domain purchase.

- `purchase_url` (string) — The URL to redirect the user to in order to complete the domain purchase through the configured store.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainRecommendations \
  purchase_domain \
  domain=mybusiness.com \
  period=1
```

<a id="domainrecommendations-supported-tlds"></a>
### `DomainRecommendations::supported_tlds` — List the TLDs supported by the domain store

`GET /execute/DomainRecommendations/supported_tlds` · RO · since cPanel 138

This function returns the list of top-level domains (TLDs) that the configured domain store supports for registration. The system caches the results for up to two minutes. Use the `use_cache=0` option to bypass the cache and force a live request. Note: This function requires the `domain_recommendation` feature.

**Parameters**

- `use_cache` · optional · integer (`1`, `0`) · default `1` · e.g. `1` — Whether to use the local response cache.; `1` — Use the cache (default). The system caches the results for up to two minutes.; `0` — Bypass the cache and make a live request to the store.

**Returns** `data`: object — An object containing the list of supported TLDs.

- `tlds` (array of string) — An array of top-level domain (TLD) strings that the configured store supports for registration.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainRecommendations \
  supported_tlds
```

## cPanel Features

<a id="features-get-feature-metadata"></a>
### `Features::get_feature_metadata` — Return cPanel account's features' metadata

`GET /execute/Features/get_feature_metadata` · RO · since cPanel 80

This function lists the details of a cPanel account's available feature lists.

**Returns** `data`: array of object — An array of objects containing feature information.

- *(array of objects)*
  - `id` (string) — The feature's system ID.
  - `is_plugin` (integer (`1`, `0`)) — Whether the feature is a [plugin](https://go.cpanel.net/cpanelplugin).; `1` — Plugin.; `0` — **Not** a plugin.
  - `name` (string) — The feature's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  Features \
  get_feature_metadata
```

<a id="features-has-feature"></a>
### `Features::has_feature` — Validate cPanel account's feature access

`GET /execute/Features/has_feature` · RO · since cPanel 11.42

This function checks whether a cPanel account has access to a [feature](https://go.cpanel.net/whmdocsFeatureManager#selectable-features).

**Parameters**

- `name` · **required** · string · e.g. `autossl` — The feature's name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Features \
  has_feature \
  name='autossl'
```

<a id="features-has-features-like"></a>
### `Features::has_features_like` — Return whether queried features are enabled

`GET /execute/Features/has_features_like` · RO · since cPanel 11.130

This function allows you to search for cPanel account features and determine whether those features are enabled.

**Parameters**

- `pattern` · **required** · string · e.g. `mail` — The feature's name that you wish to search. Note: To use a regular expression, you must set the `is_regex` parameter's value to `true`.
- `is_regex` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether the `pattern` parameter's value is a regular expression.; `1` - The `pattern` parameter's value is a regular expression.; `0` - The `pattern` parameter's value is **not** a regular expression

**Returns** `data`: object — Object containing the result of the feature search.

- `has_matching_features` (integer (`0`, `1`)) — Whether any features match the search pattern and are enabled.; `1` - At least one matching feature is enabled.; `0` - No matching features are enabled (either no matches or all matches are disabled).

```bash
uapi --output=jsonpretty \
  --user=username \
  Features \
  has_features_like \
  pattern='mail'
```

<a id="features-list-features"></a>
### `Features::list_features` — Return cPanel account's features

`GET /execute/Features/list_features` · RO · since cPanel 11.42

This function lists a cPanel account's features.

**Returns** `data`: object — Features available to the account.

```bash
uapi --output=jsonpretty \
  --user=username \
  Features \
  list_features
```

<a id="features-list-features-like"></a>
### `Features::list_features_like` — Return queried cPanel account features

`GET /execute/Features/list_features_like` · RO · since cPanel 11.130

This function allows you to search for enabled cPanel account features and lists those features in the returned payload.

**Parameters**

- `pattern` · **required** · string · e.g. `mail` — The feature's name that you wish to search. Note: To use a regular expression, you must set the `is_regex` parameter's value to `true`.
- `is_regex` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether the `pattern` parameter's value is a regular expression.; `1` - The `pattern` parameter's value is a regular expression.; `0` - The `pattern` parameter's value is **not** a regular expression

**Returns** `data`: array of string — A list of enabled feature names that match the search pattern.

```bash
uapi --output=jsonpretty \
  --user=username \
  Features \
  list_features_like \
  pattern='mail'
```

## Personalization

<a id="personalization-get"></a>
### `Personalization::get` — Retrieve NVData data from file

`POST /execute/Personalization/get` · RO · since cPanel 74

This function retrieves the data from an NVData file on disk. cPanel NVData is a per-account configuration storage mechanism that you can use to maintain persistent cPanel & WHM settings across multiple sessions. This includes custom settings for your own themes and plugins. Note: NVData keys and values are limited to 128 and 2048 bytes, respectively.

**Request body** (`application/json`)

- `names` (array of string) — List of NVData keys to query the server about.

**Returns** `data`: object

- `personalization` (any) — The retrieved NVData information stored on the server.

```bash
echo '{"names":["coffee","milk"]}' | \
uapi --input=json --output=jsonpretty \
  --user=username \
  Personalization \
  get
```

<a id="personalization-set"></a>
### `Personalization::set` — Save NVData data to file

`POST /execute/Personalization/set` · RW · rollback: none · since cPanel 74

This function saves its data to an NVData file on disk. cPanel NVData is a per-account configuration storage mechanism that you can use to maintain persistent cPanel & WHM settings across multiple sessions. This includes custom settings for your own themes and plugins. Note: NVData keys and values are limited to 128 and 2048 bytes, respectively.

**Request body** (`application/json`)

- `personalization` (object) — The NVData keys and values to update.

**Returns** `data`: object

- `personalization` (any) — The saved NVData information stored on the server.

```bash
echo '{"personalization":{"coffee":"hot","milk":"cold"}}' | \
uapi --input=json --output=jsonpretty \
  --user=username \
  Personalization \
  set
```

## Disk Quotas

<a id="quota-get-local-quota-info"></a>
### `Quota::get_local_quota_info` — Return local disk quota information

`GET /execute/Quota/get_local_quota_info` · RO · since cPanel 88

This function retrieves the cPanel account's quota for the server where you run the function. For example, a [distributed cPanel account](https://go.cpanel.net/glossaryD) could approach its quota. The servers will balance that cPanel user's quota between the parent and the child node. Note: This function runs on **only** the local server. To retrieve the cPanel account's total quota, use the UAPI `Quota::get_quota` function instead.

**Returns** `data`: object

- `byte_limit` (integer) — The limit for disk space the cPanel account may use on this server, in bytes.; A positive integer.; `0` - Unlimited or disabled server quotas.
- `bytes_used` (integer) — The amount of disk space the cPanel account uses on this server, in bytes.; A positive integer.; `0` - No usage or disabled server quotas.
- `inode_limit` (integer) — The limit for inodes that the cPanel account may use on this server.; A positive integer.; `0` - Unlimited or disabled server quotas.
- `inodes_used` (integer) — The number of inodes that the cPanel account uses on this server.; A positive integer.; `0` - No usage or disabled server quotas.

```bash
uapi --output=jsonpretty \
  --user=username \
  Quota \
  get_local_quota_info
```

<a id="quota-get-quota-info"></a>
### `Quota::get_quota_info` — Return disk quota information

`GET /execute/Quota/get_quota_info` · RO · since cPanel 56

This function retrieves the cPanel account's quota.

**Returns** `data`: object — An object containing the cPanel account's quota.

- `inode_limit` (integer or integer (`0`)) — The account's inode quota limit.; `0` — Unlimited or disabled server quotas.
- `inodes_remain` (integer or integer (`0`)) — The account's available inode quota.; `0` — Unlimited or disabled server quotas.
- `inodes_used` (integer or integer (`0`)) — The account's number of used inodes.; `0` — No usage or disabled server quotas.
- `megabyte_limit` (number or number (`0`)) — The account's disk space limit, in megabytes (MB).; `0.00` — Unlimited or disabled server quotas.
- `megabytes_remain` (number or number (`0`)) — The account's available disk space in, megabytes (MB).; `0.00` — Unlimited or disabled server quotas.
- `megabytes_used` (number or number (`0`)) — The account's used disk space, in megabytes (MB).; `0.00` — No usage or disabled server quotas.
- `under_inode_limit` (integer (`1`, `0`)) — Whether the account is under its inode limit.; `1` — Under limit.; `0` — Over limit.
- `under_megabyte_limit` (integer (`1`, `0`)) — Whether the account is under its disk space limit, in megabytes (MB).; `1` — Under limit.; `0` — Over limit.
- `under_quota_overall` (integer (`1`, `0`)) — Whether the account is under both its inode and disk megabyte (MB) limit.; `1` — Under limit.; `0` — Over limit.

```bash
uapi --output=jsonpretty \
  --user=username \
  Quota \
  get_quota_info
```

## Account Information

<a id="resellers-list-accounts"></a>
### `Resellers::list_accounts` — Return reseller's cPanel accounts

`GET /execute/Resellers/list_accounts` · RO · since cPanel 11

This function lists all of a reseller's cPanel accounts.

**Returns** `data`: array of object — An array of objects containing the reseller's cPanel accounts.

- *(array of objects)*
  - `domain` (string <domain>) — The cPanel account's domain.
  - `select` (string (`1`, ``)) — Whether the cPanel account's user is currently logged in.; `1` — Logged in.; An empty string — **Not** logged in.
  - `user` (string <username>) — The cPanel account's username.

```bash
uapi --output=jsonpretty \
  --user=username \
  Resellers \
  list_accounts
```

<a id="variables-get-user-information"></a>
### `Variables::get_user_information` — Return cPanel account's configuration settings

`GET /execute/Variables/get_user_information` · RO · rollback: none · since cPanel 86

This function retrieves the user's account configuration settings.

**Parameters**

- `name` · optional · string · e.g. `domain` — The user configuration variables to retrieve. If you don't use this parameter, this function returns **all** of the user's configuration data. Note: To retrieve multiple account configuration settings for a user, increment the parameter name. For example: `name-0`, `name-1`, and `name-2`.

**Returns** `data`: object

- `backup_enabled` (integer (`0`, `1`)) — Whether the user has backups enabled.; `1` - Backups enabled.; `0` - Backups not enabled.
- `bandwidth_limit` (integer) — The account's bandwidth limit.; `0` - unlimited; A maximum amount of bandwidth, in bytes.
- `cgi_enabled` (integer (`0`, `1`)) — Whether CGI is enabled.; `1` - Enabled.; `0` - Not enabled.
- `contact_email` (string <email>) — The account's contact email address.
- `contact_email_2` (string <email>) — The account's alternate contact email address, if one exists.
- `cpanel_root_directory` (string <path>) — The `root` directory.
- `created` (integer <unix_timestamp>) — The account's creation date in [Unix time](http://en.wikipedia.org/wiki/Unix_time) format.
- `created_in_version` (string <cPanel version>) — The version of cPanel used during account creation.
- `database_owner` (string <username>) — The owner of the account's databases.; `root`; A reseller account's username.; The account's username.
- `dead_domains` (array of string <domain>) — The account's inactive domains.
- `demo_mode` (integer (`0`, `1`)) — Whether demo mode is enabled.; `1` - Enabled.; `0` - Not enabled.
- `disk_block_limit` (integer) — The number of disk blocks for the account.; `0` - unlimited; A maximum amount of disk blocks, in kilobytes.
- `dkim_enabled` (integer (`0`, `1`)) — Whether DomainKeys Identified Mail (DKIM) is enabled.; `1` - Enabled.; `0` - Not enabled.
- `domain` (string <domain>) — The account's main domain.
- `domains` (array of string <domain>) — list of the account's domains and subdomains.
- `feature` (object) — The available features on the account that exist in the `/var/cpanel/users/user` file`, where user represents the cPanel user.
  - `additionalProperties` (integer (`0`, `1`)) — Whether the feature is enabled.; `1` - Enabled.; `0` - Disabled.
- `feature_list` (string) — The account's [feature list](https://go.cpanel.net/whmdocs84FeatureManager) name.
- `gid` (integer) — The account's group ID.
- `home` (string <path>) — The user's home directory.
- `home_directory_links` (array of any) — Any symlinks to the cPanel account's home directory.
- `ip` (string <ipv4>) — The account's IPv4 address.
- `lang` (string) — The account's language.
- `last_modified` (integer <unix_timestamp>) — The most recent modification time of the `/var/cpanel/users/user` file in [Unix time format](https://en.wikipedia.org/wiki/Unix_time).
- `legacy_backup_enabled` (integer (`0`, `1`)) — Whether legacy backups are enabled.; `1` - Enabled.; `0` - Disabled.
- `locale` (string <ISO-3166-1 (alpha-2)>) — The account's default locale, a two-letter [ISO-3166 code](http://www.iso.org/iso/country_codes.htm).
- `mailbox_format` (string (`maildir`, `mbox`)) — The storage format that the account's mailboxes use.; `maildir`; `mbox`
- `maximum_addon_domains` (integer or string (`unlimited`)) — The account's maximum number of addon domains.; `unlimited`; An integer that represents a number of addon domains.
- `maximum_databases` (integer or string (`unlimited`)) — The account's maximum number of SQL databases.; `unlimited`; An integer that represents a number of SQL databases.
- `maximum_defer_fail_percentage` (integer or string (`unlimited`)) — The [percentage of failed or deferred email messages](https://go.cpanel.net/howtopreventspam) that the account can send per hour before outgoing mail is rate-limited.; `unlimited`; An integer value.
- `maximum_email_account_disk_quota` (integer or string (`unlimited`)) — The maximum size, that the account can define when it creates an email account.; `unlimited`; An integer value, in Megabytes (MB).
- `maximum_emails_per_hour` (integer or string (`unlimited`)) — The maximum number of emails that the account can send in one hour.; A positive integer.; `0` or `unlimited` - The account can send an unlimited number of emails.
- `maximum_ftp_accounts` (integer or string (`unlimited`)) — The account's maximum number of FTP accounts.; `unlimited`; An integer that represents a number of FTP accounts.
- `maximum_mail_accounts` (integer or string (`unlimited`)) — The maximum number of email accounts for the account.; `unlimited`; An integer that represents a number of email accounts.
- `maximum_mailing_lists` (integer or string (`unlimited`)) — The account's maximum number of mailing lists.; `unlimited`; An integer that represents a number of mailing lists.
- `maximum_parked_domains` (integer or string (`unlimited`)) — The account's maximum number of aliases.; `unlimited`; An integer that represents a number of aliases.
- `maximum_passenger_apps` (integer or string (`unlimited`)) — The account's maximum number of Ruby applications.; `unlimited`; An integer that represents a number of applications.
- `maximum_subdomains` (integer or string (`unlimited`)) — The account's maximum number of subdomains.; `unlimited`; An integer that represents a number of subdomains.
- `mxcheck` (object) — Domains and their mail exchanger (MX) type.
  - `additionalProperties` (string (`local`, `remote`, `secondary`)) — The domain's MX type.; `local` - Accept mail locally for the domain.; `remote` - Do not accept mail locally for the domain.; `secondary` - Accept mail until a higher priority mail server is available.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  Variables \
  get_user_information
```

## Resource Usage and Statistics

<a id="resourceusage-get-usages"></a>
### `ResourceUsage::get_usages` — Return resource usage and custom statistics

`GET /execute/ResourceUsage/get_usages` · RO · since cPanel 70

This function retrieves resource usage and custom statistics for a cPanel user account.

**Returns** `data`: array of object — An array of objects containing resource usage information from the account's query.

- *(array of objects)*
  - `description` (string) — The resource's UI display name.
  - `error` (string) — An error message, if applicable.
  - `formatter` (string or string (`format_bytes`, `format_bytes_per_second`, `percent`)) — The resource's defined output format.; `format_bytes`; `format_bytes_per_second`; `percent`; `null` — No defined output format.
  - `id` (string) — The resource's reference name.; `disk_usage`; `filesusage` - This function **only** returns this value if the *Display File Usage information in the cPanel stats bar* setting is enabled in the *Display* section of WHM's 
  - `maximum` (integer) — The resources's maximum usage value.
  - `url` (string <url-path>) — The resource's defined URL link to its corresponding interface, in applicable.
  - `usage` (integer) — The resource's current usage value.

```bash
uapi --output=jsonpretty \
  --user=username \
  ResourceUsage \
  get_usages
```

<a id="statsbar-get-stats"></a>
### `StatsBar::get_stats` — Return cPanel account statistics

`GET /execute/StatsBar/get_stats` · RO · since cPanel 11.42

This function retrieves a cPanel account's statistics.

**Parameters**

- `display` · **required** · string · e.g. `bandwidthusage|diskusage` — A pipe-delimited list of the account's statistics. <details> <summary>Click for a list of available display parameters.</summary>; `addondomains` — Information about the account's addon domains.; `apacheversion` — The server's Apache version.; `autoresponders` — Information about the account's auto-responders.; `bandwidthusage` — Information about the account's bandwidth usage.; `cachedlistdiskusage` — The amount of cached mailing list disk space the account currently uses.; `cachedmysqldiskusage` — The amount of cached disk space that the account's MySQL® databases currently use.; `cachedpostgresdiskusage` — The amount of cached disk space that the account's PostgreSQL databases use.; `cpanelversion` — The server's cPanel version.; `dedicatedip` — Account websites that use dedicated IP addresses.; `diskusage` — Information the account's disk space usage.; `emailaccounts` — Information about the account's email accounts.; `emailfilters` — Information the account's email filters.; `emailforwarders` — Information about the account's forwarders.; `fileusage` — Information about the account's file usage.; `ftpaccounts` — Information about the account's FTP accounts.; `hostingpackage` — The account's hosting package.; `hostname` — The server's hostname.; `kernelversion` — The operating system's kernel version.; `localip` — Account websites that use local IP addresses.; `machinetype` — The type of operating system that the server uses.; `mailinglists` — Information the account's mailing lists.; `mysqldatabases` — The number of MySQL databases the account possesses.; `mysqldiskusage` — The amount of disk space that the account's MySQL databases use.; `mysqlversion` — The server's MySQL version.; `operatingsystem` — The server's operating system.; `parkeddomains` — Information about the account's parked domains (aliases).; `perlpath` — The Perl binary's absolute path.; `perlversion` — The server's Perl version.; `phpversion` — The server's PHP version.; `postgresqldatabases` — The number of PostgreSQL databases the cPanel account possesses.; `postgresdiskusage` — The amount of disk space that the cPanel account's PostgreSQL databases use.; `sendmailpath` — The path to the system's sendmail binary.; `sharedip` — Any of the account's websites that use a shared IP address.; `shorthostname` — The short version of your server's hostname.; `sqldatabases` — Information about the all of the account's SQL databases.; `subdomains` — Information about the account's subdomains.; `theme` — The account's current theme. </details> Note:  This function may require URI-encode format (`%7C`) or quotes (`"`) in some contexts, such as the command line tool.; Some display parameters may be unavailable based on the server's configuration.
- `infinityimg` · optional · string · default `None` · e.g. `/home/example/infinity.png` — The absolute file path to an alternative infinity symbol image.
- `infinitylang` · optional · string · default `None` · e.g. `infinity` — A phrase to represent infinity that the locales system can use.
- `rowcounter` · optional · string · default `None` · e.g. `even` — The type of row.; `odd`; `even`
- `warninglevel` · optional · integer · default `None` · e.g. `87` — The minimum level at which to return warnings.
- `warnings` · optional · integer (`1`, `0`) · e.g. `0` — Whether to return all results with a warning.; `1` — Return only warnings that **exceed** the `warninglevel` parameter's value.; `0` — Return all results.
- `warnout` · optional · integer (`1`, `0`) · e.g. `0` — Whether to display results with a value of `100%`.; `1` — Display results with a value of `100%`.; `0` — Hide results with a value of `100%`.

**Returns** `data`: array of object — An array of objects containing results from the queried account.

- *(array of objects)*
  - `_count` (string) — The queried data's value.
  - `_max` (string) — The queried parameter's limit.
  - `_maxed` (integer (`1`, `0`)) — Whether the queried value reached its maximum value.; `1` — Reached maximum value.; `0` — Has **not** reached maximum value.
  - `condition` (integer (`1`, `0`)) — Whether the queried data's value possesses a conditional requirement.; `1` — Possesses a condition.; `0` — Does **not** possess a condition.
  - `count` (string) — The queried data's value.
  - `feature` (string) — The queried item's feature name.
  - `id` (string) — The queried item's reference name.
  - `is_maxed` (integer (`1`, `0`)) — Whether the queried value has reached its maximum value.; `1` — The queried value has reached its maximum value.; `0` — The queried value has **not** reached its maximum value.
  - `item` (string) — A human-readable version of the queried item.
  - `max` (string) — The queried value's maximum limit.
  - `maxed_phrase` (string) — The [`maketext`-formatted](https://go.cpanel.net/locale) message that the interface displays when the user reaches their maximum allowed value.
  - `module` (string) — The module that retrieved the information.
  - `name` (string) — The display key.
  - `near_limit_phrase` (string) — The [`maketext`-formatted](https://go.cpanel.net/locale) message that the interface displays when the user approaches their maximum allowed value.
  - `normalized` (integer (`1`, `0`)) — Whether the function normalized the output values.; `1` — Normalized.; `0` — Did **not** normalize.
  - `percent` (integer) — The percentage of value, if applicable.
  - `percent10` (integer) — The percentage of value that the system rounds to the nearest ten, if applicable.
  - `percent20` (integer) — The percentage of value that the system rounds to the nearest twenty, if applicable.
  - `percent5` (integer) — The percentage of value that the system rounds to the nearest five, if applicable.
  - `phrase` (string) — The human-readable name of the queried item.
  - `role` (string (`CalendarContact`, `DNS`, `FileStorage`, `FTP`, `MailLocal`, `MailReceive`, `MailSend`, `MySQL`, `Postgres`, `SpamFilter`, `Webmail`, `WebDisk`, …)) — The queried value's role.; `CalendarContact`; `DNS`; `FileStorage`; `FTP`; `MailLocal`; `MailReceive`; `MailSend`; `MySQL`; `Postgres`; `SpamFilter`; `Webmail`; `WebDisk`; `WebServer`
  - `rowtype` (string (`even`, `odd`)) — The queried value's row type.; `even`; `odd`
  - `units` (string) — The queried value's unit of measure.
  - `zeroisunlimited` (integer (`1`, `0`)) — Whether a value of `0` means unlimited or zero.; `1` — Unlimited.; `0` — Zero.

```bash
uapi --output=jsonpretty \
  --user=username \
  StatsBar \
  get_stats \
  display='bandwidthusage|diskusage'
```

## Team Users

<a id="team-add-roles"></a>
### `Team::add_roles` — Add roles to a team user

`GET /execute/Team/add_roles` · RW · rollback: none · since 108

This function adds roles to a team user. Note: This action may result in team users gaining access to team owner level privileges.

**Parameters**

- `role` · **required** · string · e.g. `database` — The role or roles to add to the team user. Current roles include admin, database, email, web.
- `user` · **required** · string · e.g. `teamuser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  add_roles \
  user='teamuser' \
  role='database'
```

<a id="team-add-team-user"></a>
### `Team::add_team_user` — Add a team user

`GET /execute/Team/add_team_user` · RW · rollback: none · since 104

This function creates and adds a new team user. Note: This action may result in team users gaining access to team owner level privileges.

**Parameters**

- `email1` · **required** · string · e.g. `teamuser@example.com` — The contact email for the new team user.
- `user` · **required** · string · e.g. `teamuser` — The username of the team user. Follows cPanel standards.
- `activation_email` · optional · integer · e.g. `1` — Send an email to the team user that allows them to set their own password.; `1` - Enabled. Note:  You must pass either the `password` or `activation_email` parameter.
- `email2` · optional · string · e.g. `teamuser-backup@example.com` — The secondary email for the new team user.
- `expire_date` · optional · integer or string — The epoch time on which the team user account expires, or the offset from the current time, in days. Integers are treated as Unix Epoch Time unless followed by 'days'.
- `expire_reason` · optional · string · e.g. `teamUser gave a two week notice.` — The reason for expiration.
- `notes` · optional · string · e.g. `This is a note about teamuser` — Notes about the new team user. This field should not contain private information. Maximum of 100 characters.
- `password` · optional · string · e.g. `securepassword` — The password to set for the new team user. Note:  You must pass either the `password` or `activation_email` parameter.
- `roles` · optional · string · e.g. `email,database` — A comma-separated list of roles assigned to the new team user. Current roles include admin, database, email, web. Note:  This parameter is named `roles`, not `role`. This function rejects the `role` parameter with an error.; A team user with no roles **cannot** use any features. To assign roles after you create the team user, use the `set_roles` or `add_roles` functions.
- `services.email.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to create an email subaccount for the team user. A subaccount is always created for a team user, but it does not have any associated service subaccounts by default.; `1` - Create an email subaccount.; `0` - **Do Not** create an email subaccount.
- `services.email.quota` · optional · string · e.g. `500` — The maximum amount of disk space, in megabytes (MB), allocated to the team user's email account.; `0` or `unlimited` - The subaccount has unlimited disk space. This value defaults to the defined system value. Note: This value **cannot** be larger than the system's maximum email quota.
- `services.ftp.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to create an FTP subaccount for the team user. A subaccount is always created for a team user, but it does not have any associated service subaccounts by default.; `1` - Create an FTP subaccount.; `0` - **Do Not** create an FTP subaccount.
- `services.ftp.homedir` · optional · string <path> · e.g. `/Teamusername` — The team user's FTP home directory, relative to the cPanel account's home directory. Note:  This parameter is **required** if you enabled the `services.ftp.homedir` parameter.; The directory **must** exist.
- `services.webdisk.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to create a Web Disk subaccount for the team user. A subaccount is always created for a team user, but it does not have any associated service subaccounts by default.; `1` - Create a Web Disk subaccount.; `0` - **Do Not** create a Web Disk subaccount.
- `services.webdisk.enabledigest` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable the Web Disk Digest Authentication.; `1` - Enabled.; `0` - Disabled. Note:  **Only** enable Digest Authentication for clients that require additional compatibility support on certain versions of Windows® operating systems. This compatibility support is **only** required on servers that use a self-signed certificate for the `cpsrvd` and `cpdavd` daemons.; We recommend that you do **not** use Digest Authentication.
- `services.webdisk.homedir` · optional · string <path> · e.g. `/Teamusername` — The team user's Web Disk home directory, relative to the cPanel account's home directory. Note: This parameter is **required** if you enable the `services.webdisk.enabled` parameter.
- `services.webdisk.perms` · optional · string · default `rw` · e.g. `rw` — The team user's file permissions for its Web Disk home directory.; `ro` - Read-only permissions.; `rw` - Read and write permissions. Note: The `services.webdisk.homedir` parameter determines the team user's Web Disk home directory.
- `services.webdisk.private` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to set the directory's permissions to public or private.; `1` - Private (`0700`).; `0` - Public (`0755`).

**Returns** `data`: integer <unix-timestamp> — The unix timestamp that represents when the team user expires.

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  add_team_user \
  user='teamuser' \
  email1='teamuser@example.com'
```

<a id="team-cancel-expire"></a>
### `Team::cancel_expire` — Stop a team user from expiring

`GET /execute/Team/cancel_expire` · RW · rollback: none · since 110

This function stops a team user from expiring.

**Parameters**

- `user` · **required** · string · e.g. `teamUser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  cancel_expire \
  user='teamUser'
```

<a id="team-edit-team-user"></a>
### `Team::edit_team_user` — Edit a team user

`GET /execute/Team/edit_team_user` · RW · rollback: none · since 110

This function modifies a team user.

**Parameters**

- `user` · **required** · string · e.g. `teamUser` — The username of the team user.
- `add_role` · optional · string · e.g. `database` — The role or roles to add to the team user.
- `email1` · optional · string · e.g. `teamuser@example.com` — The primary contact email address to set for the team user.
- `email2` · optional · string · e.g. `teamuser@example.com` — The secondary contact email address to set for the team user.
- `expire_reason` · optional · string · e.g. `teamUser gave a two week notice.` — The reason for expiration.
- `notes` · optional · string · e.g. `This is a note about teamUser` — Notes about the new team user. This field should not contain private information.
- `password` · optional · string · e.g. `securepassword` — The password to set for the team user.
- `remove_role` · optional · string · e.g. `database` — The role or roles to remove from the team user.
- `services.email.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to create or remove an email subaccount for the team user. A subaccount is always created for a team user, but it does not have any associated service subaccounts by default.; `1` - Create and associate an email subaccount.; `0` - Remove any associated email subaccounts.
- `services.email.quota` · optional · string · e.g. `500` — The maximum amount of disk space, in megabytes (MB), allocated to the team user's email account.; `0` or `unlimited` - The subaccount has unlimited disk space. This value defaults to the defined system value. Note: This value **cannot** be larger than the system's maximum email quota.
- `services.ftp.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to create or remove an FTP subaccount for the team user. A subaccount is always created for a team user, but it does not have any associated service subaccounts by default.; `1` - Create and associate an FTP subaccount.; `0` - Remove any associated FTP subaccounts.
- `services.ftp.homedir` · optional · string <path> · e.g. `/Teamusername` — The team user's FTP home directory, relative to the cPanel account's home directory. Note:  This parameter is **required** if you enabled the `services.ftp.homedir` parameter.; The directory **must** exist.
- `services.webdisk.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to create or remove a Web Disk subaccount for the team user. A subaccount is always created for a team user, but it does not have any associated service subaccounts by default.; `1` - Create and associate a Web Disk subaccount.; `0` - Remove any associated Web Disk subaccounts.
- `services.webdisk.enabledigest` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable the Web Disk Digest Authentication.; `1` - Enabled.; `0` - Disabled. Note:  **Only** enable Digest Authentication for clients that require additional compatibility support on certain versions of Windows® operating systems. This compatibility support is **only** required on servers that use a self-signed certificate for the `cpsrvd` and `cpdavd` daemons.; We recommend that you do **not** use Digest Authentication.
- `services.webdisk.homedir` · optional · string <path> · e.g. `/Teamusername` — The team user's Web Disk home directory, relative to the cPanel account's home directory. Note: This parameter is **required** if you enable the `services.webdisk.enabled` parameter.
- `services.webdisk.perms` · optional · string · default `rw` · e.g. `rw` — The team user's file permissions for its Web Disk home directory.; `ro` - Read-only permissions.; `rw` - Read and write permissions. Note: The `services.webdisk.homedir` parameter determines the team user's Web Disk home directory.
- `services.webdisk.private` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to set the directory's permissions to public or private.; `1` - Private (`0700`).; `0` - Public (`0755`).
- `set_expire` · optional · integer or string — The epoch time the team user account expires on or the offset in days.
- `set_role` · optional · string · e.g. `email` — The role or roles to set for the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  edit_team_user \
  user='teamUser'
```

<a id="team-get-team-users-with-roles-count"></a>
### `Team::get_team_users_with_roles_count` — Get number of team users with roles

`GET /execute/Team/get_team_users_with_roles_count` · RO · since 118

This function returns the current and maximum number of team users with roles.

**Returns** `data`: object

- `max` (integer) — Maximum number of team users with roles.
- `used` (integer) — The current number of team users with roles.

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  get_team_users_with_roles_count
```

<a id="team-list-team"></a>
### `Team::list_team` — List Team Users

`GET /execute/Team/list_team` · RO · rollback: none · since 104

This function lists the team users connected to a cPanel account. This list is given in an array by default, but can be given in a hash.

**Parameters**

- `format` · optional · string · e.g. `array` — The format in which the team data is listed.

**Returns** `data`: array of object or object

- *variant: array*
  - *(array of objects)*
    - `contact-email` (string <email>) — 
    - `created` (integer <unix_timestamp>) — 
    - `expire_date` (integer <unix_timestamp>) — 
    - `expire_reason` (string) — 
    - `lastlogin` (integer <unix_timestamp>) — 
    - `locale` (string) — 
    - `notes` (string) — 
    - `password` (string) — 
    - `roles` (array of string) — 
    - `secondary-contact-email` (string <email>) — 
    - `services` (object) — 
      - `email` (string) — 
      - `ftp` (integer) — 
      - `webdisk` (string) — 
    - `suspend_date` (integer <unix-timestamp>) — 
    - `suspend_reason` (string) — 
    - `username` (string) — 
- *variant: object*
  - `owner` (string) — 
  - `users` (object) — 
    - `username` (string) — 
    - `info` (object) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  list_team
```

<a id="team-password-reset-request"></a>
### `Team::password_reset_request` — Sends a password reset request link to team user.

`GET /execute/Team/password_reset_request` · RW · rollback: none · since 108

This function enables a team user to reset the password by sending a password reset request link.

**Parameters**

- `user` · **required** · string · e.g. `teamuser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  password_reset_request \
  user='teamuser'
```

<a id="team-reinstate-team-user"></a>
### `Team::reinstate_team_user` — Reinstate a team user

`GET /execute/Team/reinstate_team_user` · RW · rollback: none · since 108

This function reinstates a team user by removing any suspended or expired statuses. The reason field is also cleared.

**Parameters**

- `user` · **required** · string · e.g. `teamUser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  reinstate_team_user \
  user='teamUser'
```

<a id="team-remove-roles"></a>
### `Team::remove_roles` — Remove roles from a team user

`GET /execute/Team/remove_roles` · RW · rollback: none · since 108

This function removes roles from a team user.

**Parameters**

- `role` · **required** · string · e.g. `database` — The role or roles to remove from the team user.
- `user` · **required** · string · e.g. `teamuser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  remove_roles \
  user='teamuser' \
  role='database'
```

<a id="team-remove-team-user"></a>
### `Team::remove_team_user` — Remove a team user

`GET /execute/Team/remove_team_user` · RW · rollback: none · since 108

This function removes a team user.

**Parameters**

- `user` · **required** · string · e.g. `teamuser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  remove_team_user \
  user='teamuser'
```

<a id="team-set-contact-email"></a>
### `Team::set_contact_email` — Set a contact email address for a team user

`GET /execute/Team/set_contact_email` · RW · rollback: none · since 110

This function sets or changes primary and secondary email addresses.

**Parameters**

- `user` · **required** · string · e.g. `teamUser` — The username of the team user.
- `email1` · optional · string · e.g. `email1@example.com` — The primary contact email address to set for the team user.
- `email2` · optional · string · e.g. `email2@example.com` — The secondary contact email address to set for the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  set_contact_email \
  user='teamUser'
```

<a id="team-set-expire"></a>
### `Team::set_expire` — Set a team user to expire

`GET /execute/Team/set_expire` · RW · rollback: none · since 110

This function expires a team user after a specified amount of time. If the team user already has an expire date set, it's replaced with a new date and reason.

**Parameters**

- `date` · **required** · integer or string — The epoch time on which the team user account expires, or the offset from the current time, in days. Integers are treated as Unix Epoch Time unless followed by 'days'.
- `user` · **required** · string · e.g. `teamUser` — The username of the team user.
- `reason` · optional · string · e.g. `teamUser gave a two week notice.` — The reason for expiration.

**Returns** `data`: integer <unix-timestamp> — The unix timestamp that represents when the team user expires.

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  set_expire \
  user='teamUser' \
  date='120days'
```

<a id="team-set-locale"></a>
### `Team::set_locale` — Set locale for a team user

`GET /execute/Team/set_locale` · RW · rollback: none · since 108

This function sets locale for a team user.

**Parameters**

- `locale` · **required** · string · e.g. `es_es` — The new locale for the team user.
- `user` · **required** · string · e.g. `teamuser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  set_locale \
  user='teamuser' \
  locale='es_es'
```

<a id="team-set-notes"></a>
### `Team::set_notes` — Set notes for a team user

`GET /execute/Team/set_notes` · RW · rollback: none · since 110

This function replaces the current notes field with new text.

**Parameters**

- `notes` · **required** · string · e.g. `teamUser is a good employee` — The content of the notes field.
- `user` · **required** · string · e.g. `teamUser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  set_notes \
  user='teamUser' \
  notes='teamUser '
```

<a id="team-set-password"></a>
### `Team::set_password` — Set password for a team user

`GET /execute/Team/set_password` · RW · rollback: none · since 106

This function replaces the current password with a new one.

**Parameters**

- `password` · **required** · string · e.g. `securepassword` — The password to set for the team user.
- `user` · **required** · string · e.g. `teamuser` — The username of the team user.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  set_password \
  user='teamuser' \
  password='securepassword'
```

<a id="team-set-roles"></a>
### `Team::set_roles` — Set roles for a team user

`GET /execute/Team/set_roles` · RW · rollback: none · since 108

This function sets roles for a team user. Note: This action may result in team users gaining access to team owner level privileges.

**Parameters**

- `user` · **required** · string · e.g. `teamuser` — The username of the team user.
- `role` · optional · string · e.g. `database` — The role or roles to set for the team user. Current roles include admin, database, email, web. Note:  This function replaces the team user's current roles. If you omit this parameter, the team user loses every role and **cannot** use any features.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  set_roles \
  user='teamuser'
```

<a id="team-suspend-team-user"></a>
### `Team::suspend_team_user` — Suspend a team user

`GET /execute/Team/suspend_team_user` · RW · rollback: none · since 108

This function immediately suspends a team user.

**Parameters**

- `user` · **required** · string · e.g. `teamuser` — The username of the team user.
- `reason` · optional · string · e.g. `teamuser is on vacation` — The reason for suspension.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Team \
  suspend_team_user \
  user='teamuser'
```

## Team Roles

<a id="teamroles-list-feature-descriptions"></a>
### `TeamRoles::list_feature_descriptions` — List all role feature descriptions

`GET /execute/TeamRoles/list_feature_descriptions` · RO · since 108

This function gives a list of all team roles and their included features.

**Returns** `data`: object

- `features` (array of string) — The list of features in a role.
- `id` (string) — The role's ID.
- `title` (string) — The role's title.

```bash
uapi --output=jsonpretty \
  --user=username \
  TeamRoles \
  list_feature_descriptions
```

## Account Management

<a id="usermanager-change-password"></a>
### `UserManager::change_password` — Update cPanel account password (User Manager)

`GET /execute/UserManager/change_password` · RW · rollback: none · since cPanel 116

This function updates the password of the main cPanel account, from the User Manager interface. It applies to the account owner only.

**Parameters**

- `newpass` · **required** · string <password> · e.g. `MyNewPassw0rd!` — The new password.
- `oldpass` · **required** · string <password> · e.g. `ThisWasMyPassword!` — The current password.
- `enablemysql` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to update the cPanel account's MySQL password.; `1` - Update MySQL password.; `0` - Do not update MySQL passowrd.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  change_password \
  oldpass='MyPreviousPassword' \
  newpass='MyUpdatedPassword'
```

<a id="users-change-password"></a>
### `Users::change_password` — Update cPanel account password

`GET /execute/Users/change_password` · RW · rollback: none · since 116

This function updates the cPanel account's password.

**Parameters**

- `newpass` · **required** · string <password> · e.g. `MyNewPassw0rd!` — The new password.
- `oldpass` · **required** · string <password> · e.g. `ThisWasMyPassword!` — The current password.
- `enabledigest` · optional · integer (`0`, `1`) · e.g. `0` — Whether to use Digest Authentication.; `1` - Use Digest Auth.; `0` - Do not use Digest Auth. Note:  Windows® Vista, Windows® 7, Windows® 8, and Windows® 10 require that you use Digest Authentication in order to access your Web Disk over a clear text, unencrypted connection.
- `enablemysql` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to update the cPanel account's MySQL password.; `1` - Update MySQL password.; `0` - Do not update MySQL password.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Users \
  change_password \
  oldpass='MyPreviousPassword' \
  newpass='MyUpdatedPassword'
```

## Subaccount Management

<a id="usermanager-check-account-conflicts"></a>
### `UserManager::check_account_conflicts` — Return Subaccounts and service accounts conflicts

`GET /execute/UserManager/check_account_conflicts` · RO · since cPanel 56

This function lists the other Subaccounts or services accounts that conflict with the specified username. Note: If the function returns more than one account, it will return some values multiple times within the return arrays.

**Parameters**

- `full_username` · **required** · string <email> · e.g. `username@example.com` — The Subaccount's username and domain name.

**Returns** `data`: object

- `accounts` (object) — An object containing the service accounts that match the queried `full_username` parameter.
  - `alternate_email` (string <email>) — An alternate email address for the Subaccount's user.
  - `avatar_url` (string <url>) — The URL to the user's Subaccount profile image file.
  - `can_delete` (integer (`1`, `0`)) — Whether the cPanel account user can delete the Subaccount.; `1` — Can delete.; `0` — **Cannot** delete.
  - `can_set_password` (integer (`1`, `0`)) — Whether the cPanel account user can change the Subaccount's password.; `1` — Can change the password.; `0` — **Cannot** change the password.
  - `can_set_quota` (integer (`1`, `0`)) — Whether the cPanel account user can change the Subaccount's disk usage quota.; `1` — Can change the Subaccount's disk usage quota.; `0` — **Cannot** change the Subaccount's disk useage quota.
  - `dismissed` (integer (`1`, `0`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` — Dismissed.; `0` — Did **not** dismiss.
  - `dismissed_merge_candidates` (array of string) — A list of the service accounts that the user dismissed the merge prompt for.
  - `domain` (string <domain>) — The Subaccount user's associated domain.
  - `full_username` (string <email>) — The Subaccount's username.
  - `guid` (string) — The Subaccount's system-assigned unique identifier.
  - `has_expired_invite` (integer (`1`, `0`)) — Whether the Subaccount owns an expired invitation.; `1` — Owns an expired invitation.; `0` — Does **not** own an expired invitation.
  - `has_invite` (integer (`1`, `0`)) — Whether the Subaccount owns an active invitation.; `1` — Own an active invitation.; `0` — Does **not** own an active invitation.
  - `has_siblings` (integer (`1`, `0`)) — Whether the service account shares the queried `full_username` value with another service account.; `1` — Shares the service account.; `0` — Does **not** share the service account.
  - `invite_expiration` (integer <unix_timestamp>) — The time at which the new Subaccount invitation will expire.; `null` — The account does **not** own an active invitation.
  - `issues` (array of object) — An array of objects containing information about any issues or problems with the Subaccount.
  - `merge_candidates` (array of object) — An array of objects containing the service accounts that the system could merge for this Subaccount.
- `conflict` (integer (`1`, `0`)) — Whether the system detected an account conflict.; `1` — Conflict.; `0` — **No** conflict.

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  check_account_conflicts \
  full_username='username@example.com'
```

<a id="usermanager-create-user"></a>
### `UserManager::create_user` — Create Subaccount

`GET /execute/UserManager/create_user` · RW · rollback: none · since cPanel 54

This function creates a Subaccount.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The Subaccount user's associated domain that the cPanel account owns.
- `password` · **required** · string <password> · e.g. `123456luggage` — The Subaccount's password. Note: Email, FTP, and Web Disk services use this password.
- `username` · **required** · string <username> · e.g. `example` — The username for the Subaccount. The username can only contain alphanumeric characters, dots (`.`), hyphens (`-`), and underscores (`_`). Note: This value does **not** include the domain name.
- `alternate_email` · optional · string <email> · e.g. `user@example.com` — An alternate email address for the Subaccount's user. Note: You **must** use this parameter if you set the `send_invite` value to `1`.
- `avatar_url` · optional · string <url> · e.g. `https://img.example.com/avatars/example.jpg` — The URL path to the user's Subaccount profile photo. Note: You **must** use the HTTPS protocol to prevent mixed content warnings when users view the image from another HTTPS URL. Warning: We reserved this parameter for future use. Do **not** use this parameter.
- `phone_number` · optional · string · e.g. `+15551234567` — A phone number for the Subaccount user that conforms to [ITU-T](https://en.wikipedia.org/wiki/ITU-T)'s [E.164](https://en.wikipedia.org/wiki/E.164) standards. Warning: We reserved this parameter for future use. Do **not** use this parameter.
- `real_name` · optional · string · e.g. `John Doe` — The Subaccount user's first and/or last name.
- `send_invite` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to send a reset password email to the Subaccount's alternate email address.; `1` - Send.; `0` - Do not send.
- `services.email.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to grant the Subaccount email access.; `1` - Can access.; `0` - **Cannot** access.
- `services.email.quota` · optional · string · e.g. `500` — The maximum amount of disk space, in megabytes (MB), allocated to Subaccount's email account.; `0` or `unlimited` - The subaccount has unlimited disk space. This value defaults to the defined system value. Note: This value **cannot** be larger than the system's maximum email quota.
- `services.email.send_welcome_email` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to send client configuration instructions to the account.; `1` - Send the instructions.; `0` - Do **not** send the instructions.
- `services.ftp.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to grant the Subaccount FTP access.; `1` - Can access.; `0` - **Cannot** access.
- `services.ftp.homedir` · optional · string <path> · e.g. `/Subaccount` — The Subaccount's FTP home directory, relative to the cPanel account's home directory. Note:  This parameter is **required** if you enabled the `services.ftp.homedir` parameter.; The directory **must** exist.
- `services.webdisk.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to grant the Subaccount Web Disk access.; `1` _ Can access.; `0` - **Cannot** access.
- `services.webdisk.enabledigest` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable the Web Disk Digest Authentication.; `1` - Enabled.; `0` - Disabled. Note:  **Only** enable Digest Authentication for clients that require additional compatibility support on certain versions of Windows® operating systems. This compatibility support is **only** required on servers that use a self-signed certificate for the `cpsrvd` and `cpdavd` daemons.; We recommend that you do **not** use Digest Authentication.
- `services.webdisk.homedir` · optional · string <path> · e.g. `/Subaccount` — The Subaccount's Web Disk home directory, relative to the cPanel account's home directory. Note: This parameter is **required** if you enable the `services.webdisk.enabled` parameter.
- `services.webdisk.perms` · optional · string · default `rw` · e.g. `rw` — The Subaccount's file permissions for its Web Disk home directory.; `ro` - Read-only permissions.; `rw` - Read and write permissions. Note: The `services.webdisk.homedir` parameter determines the Subaccount's Web Disk home directory.
- `services.webdisk.private` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to set the directory's permissions to public or private.; `1` - Private (`0700`).; `0` - Public (`0755`).
- `type` · optional · string (`sub`) · default `sub` · e.g. `sub` — The type of account.; `sub` - A Subaccount.

**Returns** `data`: object

- `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
- `avatar_url` (string <url>) — The HTTPS URL to the user's subaccount profile photo image file.
- `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
- `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
- `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
- `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` - Dismissed.; `0` - Did **not** dismiss.
- `domain` (string <domain>) — The subaccount user's associated domain.
- `full_username` (string <email>) — The subaccount's username and domain name.
- `guid` (string) — The subaccount unique identifier.
- `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does **not** share.
- `issues` (array of object) — Information about any issues or problems with the subaccount.
  - *(array of objects)*
    - `area` (string) — The affected section of cPanel & WHM.
    - `limit` (integer) — The set quota megabyte (MB) limit for the affected subaccount.
    - `message` (string) — The description of the issue.
    - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.; `email`; `ftp`; `webdisk`
    - `type` (string (`error`, `warning`, `info`)) — The type of issue.; `error`; `warning`; `info`
    - `used` (integer) — The number of megabytes (MB) that the account currently uses.
- `parent_type` (string) — The type of account that could own the service account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** yet exist, but the user could create as part of a merge.; `null` - **Not** a me
- `phone_number` (string) — The subaccount user's phone number.
- `real_name` (string) — The name of the subaccount's user, if provided.
- `services` (object) — Information about the subaccount's access to email, FTP, and Web Disk.
  - `email` (object) — Information about the subaccount's email status.
  - `ftp` (object) — Information about the subaccount's FTP status.
  - `webdisk` (object) — Information about the subaccount's Web Disk status.
- `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user **cannot** remove.; `1` - A special account.; `0` - **Not** a special account.
- `sub_account_exists` (integer (`0`, `1`)) — Whether a subaccount exists with the same username.; `1` - Exists.; `0` - Does not exist.
- `synced_password` (integer (`0`, `1`)) — Whether the user has synchronized the passwords for each of the subaccount's service accounts.; `1` - Synchronized.; `0` - **Not** synchronized.
- `type` (string (`sub`, `hypothetical`, `service`, `cpanel`)) — The type of account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does not exist, but that the user could create as part of a merge.; `service` - A service account.; `cpanel` - The cPanel accou
- `username` (string) — The subaccount's username.
- `dismissed_merge_candidates` (array of object) — An array of objects containing service candidates that the system dismissed from merges.
  - *(array of objects)*
    - `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
    - `avatar_url` (string <url>) — The HTTPS URL to the user's subaccount profile photo image file.
    - `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
    - `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
    - `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
    - `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` - Dismissed.; `0` - Did **not** dismiss.
    - `domain` (string <domain>) — The subaccount user's associated domain.
    - `full_username` (string <email>) — The subaccount's username and domain name.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  create_user \
  domain='example.com' \
  password='123456luggage' \
  username='example'
```

<a id="usermanager-delete-user"></a>
### `UserManager::delete_user` — Delete Subaccount

`GET /execute/UserManager/delete_user` · RW · rollback: none · since cPanel 54

This function deletes a Subaccount. This function returns only metadata if no other service accounts exist with the same username and domain.; If one service account uses the same username and domain, the function returns the service account's information.; If two or more service accounts use the same username and domain, the function returns a hypothetical Subaccount. Note:  A hypothetical Subaccount consists of two or more service accounts that use the same username and domain.; This function returns only metadata if the specified username and domain do **not** match any service accounts or hypothetical Subaccounts.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The Subaccount's associated domain.  The domain **must** be one that the cPanel account owns.
- `username` · **required** · string · e.g. `example` — The Subaccount's username.; Characters — `a-z`, `A-Z`, `0-9`, dot (`.`), hyphen (`-`), underscore (`_`) Note: This value does **not** include the domain name.

**Returns** `data`: object

- `alternate_email` (string <email>) — An alternate email address for the account's user.
- `avatar_url` (string <url>) — The user's account profile photo.
- `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the account.; `1` - Can delete.; `0` - **Cannot** delete.
- `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the account's password.; `1` - Can change password.; `0` - **Cannot** change password.
- `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the account's disk usage quota.; `1` - Can change quota.; `0` - **Cannot** change quota.
- `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` - Dismissed prompt.; `0` - Did **not** dismiss prompt.
- `dismissed_merge_candidates` (array of object) — An array of objects that represent the service accounts that the user dismissed the merge prompt for.
- `domain` (string <domain>) — The account user's associated domain.
- `full_username` (string) — The account's username and domain name, separated by the `@` character.
- `guid` (string) — The account unique identifier.
- `has_expired_invite` (integer (`0`, `1`)) — Whether the Subaccount owns an expired invitation.; `1` - Owns an expired invitation.; `0` - Does **not** own an expired invitation.
- `has_invite` (integer (`0`, `1`)) — Whether the Subaccount owns an active invitation.; `1` - Owns an invitation.; `0` - Does **not** own an invitation.
- `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does not share.
- `invite_expiration` (integer <unix_timestamp>) — The time at which the new Subaccount invitation will expire, given as a valid Unix epoch time or null.
- `issues` (array of object) — Information about any issues or problems with the account.
  - *(array of objects)*
    - `area` (string) — The affected section of cPanel & WHM.
    - `limit` (integer) — The set quota megabyte (MB) limit for the affected account.
    - `message` (string) — The description of the issue.
    - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.; `email`; `ftp`; `webdisk`
    - `type` (string (`error`, `warning`, `info`)) — The type of issue.; `error`; `warning`; `info`
    - `used` (integer) — The number of megabytes (MB) that the account currently uses.
- `merge_candidates` (array of object) — The service accounts that the system could merge for this account.
  - *(array of objects)*
    - `alternate_email` (string) — 
    - `avatar_url` (string) — 
    - `can_delete` (integer) — 
    - `can_set_password` (integer) — 
    - `can_set_quota` (integer) — 
    - `dismissed` (integer) — 
    - `dismissed_merge_candidates` (array of string) — 
    - `domain` (string <domain>) — 
    - `full_username` (string) — 
    - `guid` (string) — 
    - `has_expired_invite` (integer) — 
    - `has_invite` (integer) — 
    - `has_siblings` (integer) — 
    - `invite_expiration` (integer) — 
    - `issues` (array of string) — 
    - `merge_candidates` (array of string) — 
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  delete_user \
  username='example' \
  domain='example.com'
```

<a id="usermanager-dismiss-merge"></a>
### `UserManager::dismiss_merge` — Remove service account link request

`GET /execute/UserManager/dismiss_merge` · RW · rollback: none · since cPanel 54

This function removes a service account as a link candidate to create a subaccount or link to a subaccount. When you use this function, the system removes the *Link* option in cPanel's [*User Manager*](https://go.cpanel.net/cpaneldocsUserManager) interface (_cPanel >> Home >> Preferences >> User Manager_). Note: You **must** use at least one of the following parameters: `services.email.dismiss`; `services.ftp.dismiss`; `services.webdisk.dismiss`

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The service account's associated domain.
- `username` · **required** · string <username> · e.g. `example1` — The username for the service account. Note: This parameter does **not** include the domain name.
- `services.email.dismiss` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to dismiss the merge of the email service account.; `1` - Dismiss.; `0` - Do **not** dismiss.
- `services.ftp.dismiss` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to dismiss the merge of the FTP service account.; `1` - Dismiss.; `0` - Do **not** dismiss.
- `services.webdisk.dismiss` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to dismiss the merge of the Web Disk service account.; `1` - Dismiss.; `0` - Do **not** dismiss.

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  dismiss_merge \
  username='example1' \
  domain='example.com'
```

<a id="usermanager-edit-user"></a>
### `UserManager::edit_user` — Update Subaccount settings

`GET /execute/UserManager/edit_user` · RW · rollback: none · since cPanel 54

This function edits a Subaccount.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The Subaccount user's associated domain. A domain that the cPanel account owns.
- `username` · **required** · string · e.g. `example` — The Subaccount's username.; Length - 64 characters.; Characters - `a-z`, `A-Z`, `0-9`, dot (`.`), hyphen (`-`), underscore (`_`). Note: This value does **not** include the domain name.
- `alternate_email` · optional · string <email> · default `None` · e.g. `user@example.com` — An alternate email address for the Subaccount's user. Note: The cPanel account user could use this email address to contact the Subaccount user if their primary email address's domain is unavailable.
- `avatar_url` · optional · string <url> · default `None` · e.g. `https://img.example.com/avatars/example.jpg` — Warning: We reserved this parameter for future use. Do **not** use this parameter. The user's Subaccount profile photo. Note: You **must** use the HTTPS protocol to prevent mixed content warnings when users view the photo from another HTTPS URL.
- `password` · optional · string · e.g. `12345luggage` — The Subaccount's new password. Note: The Subaccount uses this password for email, FTP, and Web Disk services.
- `phone_number` · optional · string · default `None` · e.g. `+15551234567` — The Subaccount user's phone number. Warning: We reserved this parameter for future use. Do **not** use this parameter. The number conforms to the [ITU-T](https://en.wikipedia.org/wiki/ITU-T)'s [E.164](https://en.wikipedia.org/wiki/E.164)-recommended standard for the representation of telephone numbers.
- `real_name` · optional · string · default `None` · e.g. `John Doe` — The Subaccount user's name.; A first name.; A last name.; A first name and last name.; An empty string.
- `services.email.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to grant the Subaccount email access.; `1` - Can access.; `0` - **Cannot** access.
- `services.email.quota` · optional · integer · e.g. `500` — The maximum amount of disk space, in megabytes (MB), that the subaccount's email account may use. If you do not declare a value, the system defaults to the defined system value. Note: This value **cannot** be greater than the maximum email quota.; `0` or `unlimited` - The subaccount possesses unlimited disk space.
- `services.ftp.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to grant the Subaccount FTP access.; `1` - Can access.; `0` - **Cannot** access.
- `services.ftp.homedir` · optional · string <path> · e.g. `/Subaccount` — The Subaccount's FTP home directory. Note: This parameter is **required** if you enable FTP access. A relative path from the cPanel account's home directory. Note: The specified directory **must** exist.
- `services.webdisk.enabled` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to grant the Subaccount Web Disk access.; `1` - Can access.; `0` - **Cannot** access.
- `services.webdisk.enabledigest` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to enable Web Disk digest authentication. Notes:  **Only** enable Digest Authentication for clients that require additional compatibility support on certain versions of Windows® operating systems. This compatibility support is **only** required on servers that use a self-signed certificate for the `cpsrvd` and `cpdavd` daemons.; We recommend that you do **not** use Digest Authentication.; `1` - Enabled; `0` - Disabled.
- `services.webdisk.homedir` · optional · string <path> · e.g. `/Subaccount` — The Subaccount's Web Disk home directory. Note: This parameter is **required** if you enable Web Disk access. A relative path from the cPanel account's home directory.
- `services.webdisk.perms` · optional · string (`ro`, `rw`) · default `rw` · e.g. `rw` — Whether to grant write permissions to the Subaccount. Note: The `services.webdisk.homedir` parameter determines the Subaccount's Web Disk home directory.; `ro` - Read-only permissions.; `rw` - Read and write permissions.
- `services.webdisk.private` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to set the Web Disk directory's permissions to public or private.; `1` - Private (`0700`).; `0` - Public (`0755`).
- `type` · optional · string (`sub`) · default `sub` · e.g. `sub` — The type of account.; `sub` - A Subaccount.

**Returns** `data`: object

- `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
- `avatar_url` (string <url>) — The user's subaccount profile photo.
- `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
- `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
- `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
- `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.
- `domain` (string <domain>) — The Subaccount user's associated domain.
- `full_username` (string) — The subaccount's username and domain name.
- `guid` (string) — The subaccount unique identifier.
- `has_expired_invite` (integer (`0`, `1`)) — Whether an expired account login invitation exists.; `1` - Expired account invitation exists.; `0` - Expired account invitation does **not** exist.
- `has_invite` (integer (`0`, `1`)) — Whether an account login invitation exists.; `1` - Account invitation exists.; `0` - Account invitation does **not** exist.
- `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does **not** share.
- `invite_expiration` (integer <unix_timestamp>) — When the invitation expires.
- `issues` (array of object) — Information about any issues or problems with the subaccount.
  - *(array of objects)*
    - `area` (string) — The affected section of cPanel & WHM.
    - `limit` (integer) — The set quota megabyte (MB) limit for the affected subaccount.
    - `message` (string) — The description of the issue.
    - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.; `email`; `ftp`; `webdisk`
    - `type` (string (`error`, `warning`, `info`)) — The type of issue.; `error`; `warning`; `info`
    - `used` (integer) — The number of megabytes (MB) that the account currently uses.
- `parent_type` (string) — The type of account that could own the service account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** yet exist, but the user could create as part of a merge.; `null`- **Not** a mer
- `phone_number` (string) — The subaccount user's phone number.
- `real_name` (string) — The name of the subaccount's user.; A first name, a last name, or a first name and last name.; An empty string.
- `services` (object) — This object contains information about the subaccount's access to email, FTP, and Web Disk.
  - `email` (object) — This object contains the information that indicates the subaccount's email status.
  - `ftp` (object) — This object contains the information that indicates the subaccount's FTP status.
  - `webdisk` (object) — This object contains information that indicates the subaccount's Web Disk status.
- `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user **cannot** remove.; `1` - A special account.; `0` - **Not** a special account.
- `sub_account_exists` (integer (`0`, `1`)) — Whether a subaccount exists with the same username.; `1` - Exists.; `0` - Does **not** exist.
- `synced_password` (integer (`0`, `1`)) — Whether the user has synchronized the passwords for each of the subaccount's service accounts.; `1` - Synchronized.; `0` - **Not** synchronized.
- `type` (string) — The type of account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** exist, but that the user could create as part of a merge.; `service` - A service account.; `cpanel` - The cPanel a
- `username` (string) — The username for the subaccount.; Length - 64 characters.; Characters - `a-z`, `A-Z`, `0-9`, dot (`.`), hyphen (`-`), underscore (`_`).
- `merge_candidates` (array of object) — An array of objects that represents the service accounts that the system could merge for this subaccount.
  - *(array of objects)*
    - `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
    - `avatar_url` (string <url>) — The user's subaccount profile photo.
    - `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
    - `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
    - `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  edit_user \
  domain='example.com' \
  password='12345luggage' \
  username='example'
```

<a id="usermanager-list-users"></a>
### `UserManager::list_users` — Return cPanel account's Subaccounts

`GET /execute/UserManager/list_users` · RO · since cPanel 54

This function lists the cPanel account's Subaccounts.

**Parameters**

- `flat` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to return Subaccounts with the same name under the merge_candidates array.; `1` - Do **not** return.; `0` - Return.

**Returns** `data`: array of object

- *(array of objects)*
  - `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
  - `avatar_url` (string <url>) — The user's subaccount profile photo.
  - `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
  - `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
  - `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
  - `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` - Dismissed.; `0` - Did **not** dismiss.
  - `dismissed_merge_candidates` (array of string) — An array of objects containing information about service candidates that the system dismissed from merges.
  - `domain` (string <domain>) — The subaccount user's associated domain.
  - `full_username` (string) — The subaccount's username and domain name.
  - `guid` (string) — The subaccount unique identifier.
  - `has_expired_invite` (integer (`0`, `1`)) — Whether an expired account login invitation exists.; `1` - Expired account invitation exists.; `0` - Expired account invitation does **not** exist.
  - `has_invite` (integer (`0`, `1`)) — Whether an account login invitation exists.; `1` - Account invitation exists.; `0` - Account invitation does **not** exist.
  - `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a full_username value with another service account.; `1` - Shares.; `0` - Does **not** share.
  - `invite_expiration` (integer <unix_timestamp>) — When the invitation expires.
  - `issues` (array of object) — Information about any issues or problems with the subaccount.
    - *(array of objects)*
      - `area` (string) — The affected section of cPanel & WHM.
      - `limit` (integer <megabytes>) — The set quota megabyte (MB) limit for the affected subaccount.
      - `message` (string) — The description of the issue.
      - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.
      - `type` (string (`error`, `warning`, `info`)) — The type of issue.
      - `used` (integer <megabytes>) — The number of megabytes (MB) that the account currently uses.
  - `merge_candidates` (array of string) — An array of objects that represents the service accounts that the system could merge for this subaccount.
  - `parent_type` (string (`sub`, `hypothetical`)) — The type of account that could own the service account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** yet exist, but the user could create as part of a merge.; `null` - **Not** a me
  - `phone_number` (string) — The subaccount user's phone number.
  - `real_name` (string) — The name of the subaccount's user.
  - `services` (object) — An object containing information about the subaccount's access to email, FTP, and Web Disk.
    - `email` (object) — An object containing the information that indicates the subaccount's email status.
    - `ftp` (object) — An object containing the information that indicates the subaccount's FTP status.
    - `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user cannot remove.; `1` - A special account.; `0` - **Not** a special account.
    - `webdisk` (object) — An object containing information that indicates the subaccount's Web Disk status.
  - `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user **cannot** remove.; `1` — A special account.; `0` — **Not** a special account.
  - `sub_account_exists` (integer (`0`, `1`)) — Whether a subaccount exists with the same username.; `1` - Exists.; `0` - Does **not** exist.
  - `synced_password` (integer (`0`, `1`)) — Whether the user has synchronized the passwords for each of the subaccount's service accounts.; `1` - Synchronized.; `0` - Not synchronized.
  - `type` (string (`sub`, `hypothetical`, `service`, `cpanel`)) — The type of account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does not exist, but that the user could create as part of a merge.; `service` - A service account.; `cpanel` - The cPanel accou
  - `username` (string) — The username for the subaccount.

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  list_users
```

<a id="usermanager-lookup-service-account"></a>
### `UserManager::lookup_service_account` — Return service account's information

`GET /execute/UserManager/lookup_service_account` · RO · since cPanel 54

This function lists a service account's information.

**Parameters**

- `full_username` · **required** · string · e.g. `username@example.com` — The full username for the system account.
- `type` · **required** · string (`email`, `ftp`, `webdisk`) · e.g. `email` — The type of system account.; `email`; `ftp`; `webdisk`

**Returns** `data`: object

- `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
- `avatar_url` (string <url>) — The user's subaccount profile photo.
- `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
- `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
- `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
- `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.
- `domain` (string <domain>) — The Subaccount user's associated domain.
- `full_username` (string) — The subaccount's username and domain name.
- `guid` (string) — The subaccount unique identifier.
- `has_expired_invite` (integer (`0`, `1`)) — Whether an expired account login invitation exists.; `1` - Expired account invitation exists.; `0` - Expired account invitation does **not** exist.
- `has_invite` (integer (`0`, `1`)) — Whether an account login invitation exists.; `1` - Account invitation exists.; `0` - Account invitation does **not** exist.
- `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does **not** share.
- `invite_expiration` (integer <unix_timestamp>) — When the invitation expires.
- `issues` (array of object) — Information about any issues or problems with the subaccount.
  - *(array of objects)*
    - `area` (string) — The affected section of cPanel & WHM.
    - `limit` (integer) — The set quota megabyte (MB) limit for the affected subaccount.
    - `message` (string) — The description of the issue.
    - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.; `email`; `ftp`; `webdisk`
    - `type` (string (`error`, `warning`, `info`)) — The type of issue.; `error`; `warning`; `info`
    - `used` (integer) — The number of megabytes (MB) that the account currently uses.
- `parent_type` (string) — The type of account that could own the service account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** yet exist, but the user could create as part of a merge.; `null`- **Not** a mer
- `phone_number` (string) — The subaccount user's phone number.
- `real_name` (string) — The name of the subaccount's user.; A first name, a last name, or a first name and last name.; An empty string.
- `services` (object) — This object contains information about the subaccount's access to email, FTP, and Web Disk.
  - `email` (object) — This object contains the information that indicates the subaccount's email status.
  - `ftp` (object) — This object contains the information that indicates the subaccount's FTP status.
  - `webdisk` (object) — This object contains information that indicates the subaccount's Web Disk status.
- `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user **cannot** remove.; `1` - A special account.; `0` - **Not** a special account.
- `sub_account_exists` (integer (`0`, `1`)) — Whether a subaccount exists with the same username.; `1` - Exists.; `0` - Does **not** exist.
- `synced_password` (integer (`0`, `1`)) — Whether the user has synchronized the passwords for each of the subaccount's service accounts.; `1` - Synchronized.; `0` - **Not** synchronized.
- `type` (string) — The type of account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** exist, but that the user could create as part of a merge.; `service` - A service account.; `cpanel` - The cPanel a
- `username` (string) — The username for the subaccount.; Length - 64 characters.; Characters - `a-z`, `A-Z`, `0-9`, dot (`.`), hyphen (`-`), underscore (`_`).
- `merge_candidates` (array of object) — An array of objects that represents the service accounts that the system could merge for this subaccount.
  - *(array of objects)*
    - `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
    - `avatar_url` (string <url>) — The user's subaccount profile photo.
    - `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
    - `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
    - `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  lookup_service_account \
  type='email' \
  full_username='username@example.com'
```

<a id="usermanager-lookup-user"></a>
### `UserManager::lookup_user` — Return Subaccount's information

`GET /execute/UserManager/lookup_user` · RO · since cPanel 54

This function lists a single Subaccount's information.

**Parameters**

- `guid` · **required** · string — The Subaccount's unique identifier.

**Returns** `data`: object

- `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
- `avatar_url` (string <url>) — The user's subaccount profile photo.
- `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - Cannot delete.
- `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - Cannot change.
- `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - Cannot change.
- `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` - Dismissed.; `0` - Did not dismiss.
- `domain` (string <domain>) — The subaccount user's associated domain.
- `full_username` (string) — The subaccount's username and domain name.
- `guid` (string) — The subaccount unique identifier.
- `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does not share.
- `issues` (array of object) — Information about any issues or problems with the subaccount.
  - *(array of objects)*
    - `area` (string) — The affected section of cPanel & WHM.
    - `limit` (integer) — The set quota megabyte (MB) limit for the affected subaccount.
    - `message` (string) — The description of the issue.
    - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.
    - `type` (string (`error`, `info`, `warning`)) — The type of issue.
    - `used` (integer) — The number of megabytes (MB) that the account currently uses.
- `merge_candidates` (array of object) — An array of service account objects that the system could merge for this subaccount.
  - *(array of objects)*
    - `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
    - `avatar_url` (string <url>) — The user's subaccount profile photo.
    - `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - Cannot delete.
    - `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - Cannot change.
    - `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - Cannot change.
    - `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.; `1` - Dismissed.; `0` - Did not dismiss.
    - `domain` (string <domain>) — The subaccount user's associated domain.
    - `full_username` (string) — The subaccount's username and domain name.
    - `guid` (string) — The subaccount unique identifier.
    - `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does not share.
    - `issues` (array of object) — Information about any issues or problems with the subaccount.
    - `merge_candidates` (array of object) — An array of service account objects that the system could merge for this subaccount.
    - `parent_type` (string (`sub`, `hypothetical`)) — The type of account that could own the service account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does not yet exist, but the user could create as part of a merge.; `null` - Not a merge cand
    - `phone_number` (string) — The subaccount user's phone number.
    - `real_name` (string) — The name of the subaccount's user.; A first name, a last name, or a first name and last name.; An empty or null string.
    - `services` (object) — Information about the subaccount's access to email, FTP, and Web Disk.
    - `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user **cannot** remove.; `1` - A special account.; `0` - Not a special account.
    - `sub_account_exists` (integer (`0`, `1`)) — Whether a subaccount exists with the same username.; `1` - Exists.; `0` - Does not exist.
    - `synced_password` (integer (`0`, `1`)) — Whether the user has synchronized the passwords for each of the subaccount's service accounts.; `1` - Synchronized.; `0` - Not synchronized.
    - `type` (string (`cpanel`, `hypothetical`, `service`, `sub`)) — The type of account.; `cpanel` - The cPanel account.; `hypothetical` - A hypothetical subaccount that does not exist, but that the user could create as part of a merge.; `service` - A service account.; `sub` - A subaccou
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  lookup_user \
  guid='EXAMPLE1:EXAMPLE.COM:564CD663%3AFE50072F2620B50988EA4E5F46022546FBE6BDDE3C36C2F2534F4967C661EC37'
```

<a id="usermanager-merge-service-account"></a>
### `UserManager::merge_service_account` — Register service account to Subaccount

`GET /execute/UserManager/merge_service_account` · RW · rollback: none · since cPanel 54

This function links service accounts to subaccounts and creates a subaccount if one does not exist. Note: You can only link email, FTP, or Web Disk accounts. **Important** You must use at least **one** of the following parameters: services.email.merge; services.ftp.merge; services.webdisk.merge To link multiple service accounts, the service accounts **must** share the same username and domain.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The service account's associated domain.
- `username` · **required** · string <username> · e.g. `example` — The username for the service account that meets the account name limitations.; Length - 64 characters; Characters — `a-z`, `A-Z`, `0-9`, dot (`.`), hyphen (`-`), underscore (`_`). Note: This value does **not** include the domain name.
- `services.email.merge` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to link the email account to the subaccount.; `1` - Merge.; `0` - Do **not** merge.
- `services.ftp.merge` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to link the FTP account to the subaccount.; `1` - Merge.; `0` - Do **not** merge.
- `services.webdisk.merge` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to link the Web Disk account to the subaccount.; `1` - Merge.; `0` - Do **not** merge.

**Returns** `data`: object

- `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
- `avatar_url` (string <url>) — The user's subaccount profile photo.
- `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
- `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
- `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
- `dismissed` (integer (`0`, `1`)) — Whether the cPanel account user dismissed the merge prompt for the service account.
- `dismissed_merge_candidates` (array of object) — An array of objects of service candidates that the system dismissed from merges.
  - *(array of objects)*
    - `alternate_email` (string <email>) — An alternate email address for the subaccount's user.
    - `avatar_url` (string <url>) — The user's subaccount profile photo.
    - `can_delete` (integer (`0`, `1`)) — Whether the cPanel account user can delete the subaccount.; `1` - Can delete.; `0` - **Cannot** delete.
    - `can_set_password` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's password.; `1` - Can change.; `0` - **Cannot** change.
    - `can_set_quota` (integer (`0`, `1`)) — Whether the cPanel account user can change the subaccount's disk usage quota.; `1` - Can change.; `0` - **Cannot** change.
    - `domain` (string <domain>) — The subaccount user's associated domain that the cPanel account owns.
    - `full_username` (string <email>) — The subaccount's username and domain name.
    - `guid` (string) — The subaccount unique identifier.
    - `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does **not** share.
    - `issues` (array of object) — Information about any issues or problems with the subaccount.
    - `parent_type` (string (`sub`, `hypothetical`)) — The type of account that could own the service account.; `sub`          - A subaccount.; `hypothetical` - A hypothetical subaccount that does not yet exist, but the user could create as part of a merge.; `null`         -
    - `phone_number` (string) — The subaccount user's phone number.
    - `real_name` (string) — The name of the subaccount's user.; A first name.; Last name.; First name and last name.; An empty string.
    - `services` (object) — This object contains information about the subaccount's access to email, FTP, and Web Disk.
    - `special` (integer (`0`, `1`)) — Whether the account is a system-created special account that the user **cannot** remove.; `1` - A special account.; `0` - **Not** a special account.
    - `sub_account_exists` (integer (`0`, `1`)) — Whether a subaccount exists with the same username.; `1` - Exists.; `0` - Does **not** exist.
    - `synced_password` (integer (`0`, `1`)) — Whether the user has synchronized the passwords for each of the subaccount's service accounts.; `1` - Synchronized.; `0` - **Not** synchronized.
    - `type` (string (`sub`, `hypothetical`, `service`, `cpanel`)) — The type of account.; `sub` - A subaccount.; `hypothetical` - A hypothetical subaccount that does **not** exist, but that the user could create as part of a merge.; `service` - A service account.; `cpanel` - The cPanel a
    - `username` (string <username>) — The username for the subaccount.
- `domain` (string <domain>) — The subaccount user's associated domain.
- `full_username` (string <email>) — The subaccount's username and domain name.
- `guid` (string) — The subaccount unique identifier.
- `has_expired_invite` (integer (`0`, `1`)) — Whether an expired account login invitation exists.; `1` - Expired account invitation exists.; `0` - Expired account invitation does **not** exist.
- `has_invite` (integer (`0`, `1`)) — Whether an account login invitation exists.; `1` - Account invitation exists.; `0` - Account invitation does **not** exist.
- `has_siblings` (integer (`0`, `1`)) — Whether the service account shares a `full_username` value with another service account.; `1` - Shares.; `0` - Does **not** share.
- `invite_expiration` (integer <unix_timestamp>) — When the invitation expires.
- `issues` (array of object) — Information about any issues or problems with the subaccount.
  - *(array of objects)*
    - `area` (string) — The affected section of cPanel & WHM.
    - `limit` (integer) — The set quota megabyte (MB) limit for the affected subaccount.
    - `message` (string) — The description of the issue.
    - `service` (string (`email`, `ftp`, `webdisk`)) — The affected service.; `email`; `ftp`; `webdisk`
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  merge_service_account \
  username='example' \
  domain='example.com'
```

<a id="usermanager-unlink-service-account"></a>
### `UserManager::unlink_service_account` — Unregister service account from Subaccount

`GET /execute/UserManager/unlink_service_account` · RW · rollback: none · since cPanel 56

This function unlinks a service account from a subaccount.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The subaccount's associated domain.
- `service` · **required** · string (`email`, `ftp`, `webdisk`) · e.g. `ftp` — The service to unlink.; `email`; `ftp`; `webdisk`
- `username` · **required** · string <username> · e.g. `example` — The subaccount's username. Note: This value does **not** include the domain name.
- `dismiss` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether to dismiss the service account as a merge candidate.; `1` - Dismiss as merge candidate.; `0` - Display as merge candidate. Note: If any email, FTP, or Web Disk accounts use the same username, cPanel's [*User Manager*](https://go.cpanel.net/cpaneldocsUserManager) interface (*cPanel >> Home >> Preferences >> User Manager*) allows you to merge those accounts into a subaccount.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  UserManager \
  unlink_service_account \
  username='example' \
  domain='example.com' \
  service='ftp'
```

