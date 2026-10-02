<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Domain Management

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **AddonDomain**: [`AddonDomain::addaddondomain`](#addondomain-addaddondomain), [`AddonDomain::deladdondomain`](#addondomain-deladdondomain), [`AddonDomain::listaddondomains`](#addondomain-listaddondomains)
- **Domain Information**: [`DomainInfo::domains_data`](#domaininfo-domains-data), [`DomainInfo::list_domains`](#domaininfo-list-domains), [`DomainInfo::main_domain_builtin_subdomain_aliases`](#domaininfo-main-domain-builtin-subdomain-aliases), [`DomainInfo::primary_domain`](#domaininfo-primary-domain), [`DomainInfo::single_domain_data`](#domaininfo-single-domain-data)
- **DomainLookup**: [`DomainLookup::countbasedomains`](#domainlookup-countbasedomains), [`DomainLookup::getbasedomains`](#domainlookup-getbasedomains), [`DomainLookup::getdocroot`](#domainlookup-getdocroot), [`DomainLookup::getdocroots`](#domainlookup-getdocroots)
- **Direct Link Protection (Hotlink)**: [`Mime::add_hotlink`](#mime-add-hotlink), [`Mime::delete_hotlink`](#mime-delete-hotlink), [`Mime::list_hotlinks`](#mime-list-hotlinks)
- **Domain Redirection**: [`Mime::add_redirect`](#mime-add-redirect), [`Mime::delete_redirect`](#mime-delete-redirect), [`Mime::get_redirect`](#mime-get-redirect), [`Mime::list_redirects`](#mime-list-redirects)
- **Park**: [`Park::listparkeddomains`](#park-listparkeddomains), [`Park::park`](#park-park), [`Park::unpark`](#park-unpark)
- **SubDomain**: [`SubDomain::addsubdomain`](#subdomain-addsubdomain), [`SubDomain::delsubdomain`](#subdomain-delsubdomain), [`SubDomain::getreservedsubdomains`](#subdomain-getreservedsubdomains), [`SubDomain::listsubdomains`](#subdomain-listsubdomains), [`SubDomain::validregex`](#subdomain-validregex)
- **Virtual Host Information**: [`WebVhosts::list_domains`](#webvhosts-list-domains), [`WebVhosts::list_ssl_capable_domains`](#webvhosts-list-ssl-capable-domains)

## AddonDomain

<a id="addondomain-addaddondomain"></a>
### `AddonDomain::addaddondomain` — Create an addon domain

`GET /execute/AddonDomain/addaddondomain` · RW · rollback: none · since cPanel 138

This function creates an addon domain on the cPanel account. It creates a subdomain of the account's primary domain and then parks the new domain on that subdomain. Important:  The account's primary domain may **not** be a subdomain of the addon domain that you create.; You cannot create a wildcard addon domain.; If the subdomain already exists on the account, the system reuses it rather than failing.; If the park step fails, the system removes the subdomain it created, so that a failed call does not leave a partial addon domain behind.; The system also creates an [FTP](https://go.cpanel.net/ftpaccounts) account for the addon domain, which counts against the account's FTP account limit. When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `newdomain` · **required** · string <domain> · e.g. `addon.com` — The addon domain to create.
- `subdomain` · **required** · string · e.g. `addon` — The label of the subdomain to create on the account's primary domain and park the addon domain on. This value may **not** contain an asterisk (`*`).
- `dir` · optional · string <path> · e.g. `/public_html/addon` — The addon domain's document root, given as a directory path relative to the account's home directory. This value defaults to the subdomain label beneath the account's `public_html` directory.
- `disallowdot` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to remove the dot (`.`) characters from the `subdomain` value.; `1` - Remove dots from the subdomain label.; `0` - Do **not** remove dots from the subdomain label.
- `force` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Accepted for compatibility, but ignored for account-level callers. It can no longer cause the system to skip the domain name, [DNS](https://go.cpanel.net/dnsrecords), and registration checks, or to overwrite an existing DNS zone. The system still refuses to create a domain that another account owns.; `0` - Enforce the checks.; `1` - Accepted, but has no effect for account-level callers.

```bash
uapi --output=jsonpretty \
  --user=username \
  AddonDomain \
  addaddondomain \
  newdomain='addon.com' \
  subdomain='addon'
```

<a id="addondomain-deladdondomain"></a>
### `AddonDomain::deladdondomain` — Remove an addon domain

`GET /execute/AddonDomain/deladdondomain` · RW · rollback: none · since cPanel 138

This function removes an addon domain from the cPanel account. It unparks the addon domain and then removes the subdomain that the domain was parked on. Important:  The `domain` and `subdomain` values must match each other. If the subdomain does not correspond to the addon domain, the function fails.; If other domains are still parked on the subdomain, the system unparks the addon domain but leaves the subdomain in place, and says so in the `messages` field.; This function does **not** remove the addon domain's document root or the files in it. When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `addon.com` — The addon domain to remove.
- `subdomain` · **required** · string · e.g. `addon_example.com` — The subdomain that the addon domain is parked on, given in the underscore-separated `subdomain_rootdomain` form that the `AddonDomain::listaddondomains` function returns in its `domainkey` field.
- `disallowdot` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to remove the dot (`.`) characters from the subdomain label when the system removes the subdomain.; `1` - Remove dots from the subdomain label.; `0` - Do **not** remove dots from the subdomain label.

```bash
uapi --output=jsonpretty \
  --user=username \
  AddonDomain \
  deladdondomain \
  domain='addon.com' \
  subdomain='addon_example.com'
```

<a id="addondomain-listaddondomains"></a>
### `AddonDomain::listaddondomains` — List the addon domains

`GET /execute/AddonDomain/listaddondomains` · RO · since cPanel 138

This function lists the cPanel account's addon domains: the domains that are parked on a subdomain of the account's primary domain, rather than on the primary domain itself. Note: Use the `Park::listparkeddomains` function for the domains parked on the primary domain.

**Parameters**

- `regex` · optional · string · e.g. `addon[.]com$` — A Perl regular expression. The system returns only the addon domains whose name matches this pattern, case-insensitively.
- `return_https_redirect_status` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include the `can_https_redirect` and `is_https_redirecting` fields in each entry.; `1` - Include the HTTPS redirect status.; `0` - Omit the HTTPS redirect status.

```bash
uapi --output=jsonpretty \
  --user=username \
  AddonDomain \
  listaddondomains
```

## Domain Information

<a id="domaininfo-domains-data"></a>
### `DomainInfo::domains_data` — Return all domains' hosting configuration

`GET /execute/DomainInfo/domains_data` · RO · since cPanel 11.42

This function lists user data for the cPanel account's domains. Note: This function retrieves data from the `/var/cpanel/userdata/user/domain` file, where `user` represents the cPanel account username and `domain` represents the domain. For this reason, actual output may not contain all of the returns that this document lists.

**Parameters**

- `format` · optional · string (`hash`, `list`) · default `hash` · e.g. `hash` — The function's return format.; `hash` — Use a hash format. The function will return objects based on the domain type.; `list` — Use a list format. The function will return an array of objects, where each object is a domain.
- `hide_temporary_domains` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to hide temporary domains from the response arrays.; `1` — Hide temporary domains from `addon_domains`, `sub_domains`, and `parked_domains` arrays.; `0` — Return all domains, including the temporary domains.
- `return_https_redirects_status` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to return the secure redirect status of the addon domains.; `1` — Return the status.; `0` — Do **not** return the status.

**Returns** `data`: object — An object containing information about a cPanel account's domains.

- `addon_domains` (any) — An array of objects containing information about each addon domain.
  - *(array of objects)*
    - `all_aliases_valid` (integer (`1`, `0`)) — Whether a valid SSL certificate exists on the domain's aliases.; `1` — A valid SSL certificate exists.; `0` — A valid SSL certificate does **not** exist.
    - `can_https_redirect` (integer (`1`, `0`)) — Whether a valid SSL certificate exists or AutoSSL runs on the domain.; `1` — A valid SSL certificate exists or AutoSSL runs.; `0` — A valid SSL certificate does **not** exist and AutoSSL does **not** run.
    - `documentroot` (string <path>) — The absolute path to the domain's document root.
    - `domain` (string <domain>) — The domain's name.
    - `group` (string) — The domain's group.
    - `hascgi` (integer (`1`, `0`)) — Whether CGI is enabled for the domain.; `1` — Enabled.; `0` — Disabled.
    - `homedir` (string <path>) — The absolute path to the cPanel account's home directory.
    - `ip` (string <ipv4>) — The domain's IPv4 address.
    - `ipv6` (string <ipv6>) — The domain's IPv6 address.; null — The account does **not** use IPv6.
    - `is_https_redirecting` (integer (`1`, `0`)) — Whether the domain redirects to `https`.; `1` — The domain redirects to `https`.; `0` — The domain does **not** redirect to `https`.
    - `is_temporary` (integer (`1`, `0`)) — Whether the domain is a temporary domain.; `1` — The domain is temporary.; `0` — The domain is not temporary.
    - `no_cache_update` (integer (`1`, `0`)) — Whether the domain is subject to cache updates.; `1` — The domain updates caches.; `0` — The domain does **not** update caches.
    - `owner` (string) — The WHM account (`root` or a reseller) that owns the cPanel account.
    - `serveradmin` (string <email>) — The domain's administrator's contact email address.
    - `serveralias` (string <domain>) — A space-separated list of the domain's aliases.
    - `servername` (string <domain>) — The domain's identifier on the server.
    - `type` (string (`addon_domain`, `sub_domain`, `parked_domains`)) — The type of domain: `addon_domain` — The domain is an addon domain.; `sub_domain` — The domain is a subdomain.; `parked_domain` — The domain is a parked domain (domain alias).
    - `usecanonicalname` (string (`On`, `Off`)) — The domain's Canonical Name (CNAME) setting.; `On` — Use the domain's CNAME.; `Off` — Do **not** use the domain's CNAME.
    - `user` (string <username>) — The cPanel account's username.
    - `userdirprotect` (integer (`1`, `0`)) — The domain's [Apache `mod_userdir` Tweak](https://go.cpanel.net/whmdocsApachemod_userdirTweak) setting.; `1` — Enabled.; `0` — Disabled.
- `main_domain` (any) — An array of objects containing information about the main domain.
  - *(array of objects)*
    - `all_aliases_valid` (integer (`1`, `0`)) — Whether a valid SSL certificate exists on the domain's aliases.; `1` — A valid SSL certificate exists.; `0` — A valid SSL certificate does **not** exist.
    - `can_https_redirect` (integer (`1`, `0`)) — Whether a valid SSL certificate exists or AutoSSL runs on the domain.; `1` — A valid SSL certificate exists or AutoSSL runs.; `0` — A valid SSL certificate does **not** exist and AutoSSL does **not** run.
    - `customlog` (object) — The domain's [Apache log](http://httpd.apache.org/docs/2.2/mod/mod_log_config.html) information.
    - `documentroot` (string <path>) — The absolute path to the domain's document root.
    - `domain` (string <domain>) — The domain's name.
    - `group` (string) — The domain's group.
    - `hascgi` (integer (`1`, `0`)) — Whether CGI is enabled for the domain.; `1` — Enabled.; `0` — Disabled.
    - `homedir` (string <path>) — The absolute path to the cPanel account's home directory.
    - `ifmodulemodsuphpc` (object) — Information about PHP scripts and suPHP.
    - `ip` (string <ipv4>) — The domain's IPv4 address.
    - `ipv6` (string <ipv6>) — The domain's IPv6 address.; null — The account does **not** use IPv6.
    - `is_https_redirecting` (integer (`1`, `0`)) — Whether the domain redirects to `https`.; `1` — The domain redirects to `https`.; `0` — The domain does **not** redirect to `https`.
    - `no_cache_update` (integer (`1`, `0`)) — Whether the domain is subject to cache updates.; `1` — The domain updates caches.; `0` — The domain does **not** update caches.
    - `owner` (string) — The WHM account (`root` or a reseller) that owns the cPanel account.
    - `scriptalias` (object) — The domain's CGI information.
    - `serveradmin` (string <email>) — The domain's administrator's contact email address.
- … (truncated; see the online reference)

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainInfo \
  domains_data
```

<a id="domaininfo-list-domains"></a>
### `DomainInfo::list_domains` — Return cPanel account's domains

`GET /execute/DomainInfo/list_domains` · RO · since cPanel 11.42

This function lists the cPanel account's domains. Note: For this function to succeed, the `/var/cpanel/userdata/username/main` file (where `username` represents the authenticated user) **must** possess the correct permissions. If a permissions error occurs, this function returns blank values for **all** of its returns and does **not** return an error message.

**Parameters**

- `hide_temporary_domains` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to hide temporary domains from the response arrays.; `1` — Hide temporary domains from the `addon_domains`, `sub_domains`, and `parked_domains` arrays, and from the `main_domain` field.; `0` — Return all domains, including the temporary domains.

**Returns** `data`: object

- `addon_domains` (array of string <domain>) — An array of string values that lists the addon domains on the cPanel account.
- `main_domain` (string <domain>) — The cPanel account's main domain.
- `parked_domains` (array of string <domain>) — An array of string values that lists the parked domains on the cPanel account.
- `sub_domains` (array of string <domain>) — An array of string values that lists the subdomains on the cPanel account.
- `is_temporary` (object) — Whether the domain is a temporary domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainInfo \
  list_domains
```

<a id="domaininfo-main-domain-builtin-subdomain-aliases"></a>
### `DomainInfo::main_domain_builtin_subdomain_aliases` — Return built-in subdomain aliases

`GET /execute/DomainInfo/main_domain_builtin_subdomain_aliases` · RO · since cPanel 11.42

This function returns the built-in subdomain aliases for an account's main domain. Note: This function retrieves data from the `/var/cpanel/userdata/user/domain` file, where `user` represents the cPanel account username and `domain` represents the domain. For this reason, actual output may not contain all of the returns that this document lists.

**Parameters**

- `hide_temporary_domains` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to hide domain aliases if the main domain is a temporary domain.; `1` — Return empty array if the main domain is a temporary domain.; `0` — Show aliases regardless of domain type.

**Returns** `data`: array of string — A list of the built-in subdomain aliases for the account's main domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainInfo \
  main_domain_builtin_subdomain_aliases
```

<a id="domaininfo-primary-domain"></a>
### `DomainInfo::primary_domain` — Return the cPanel account's primary domain

`GET /execute/DomainInfo/primary_domain` · RO · since cPanel 11.42

This function returns the cPanel account's main domain.

**Parameters**

- `hide_temporary_domains` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to hide temporary domains from the response.; `1` — Return `null` if the main domain is a temporary domain.; `0` — Return the main domain if it's a temporary domain.

**Returns** `data`: object

- `primary_domain` (string) — The cPanel account's main domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainInfo \
  primary_domain
```

<a id="domaininfo-single-domain-data"></a>
### `DomainInfo::single_domain_data` — Return domain's hosting configuration

`GET /execute/DomainInfo/single_domain_data` · RO · since cPanel 11.42

This function lists user data for a domain. Important: This function retrieves data from the `/var/cpanel/userdata/user/domain` file, where `user` represents the cPanel account username and `domain` represents the domain.; Because aliases (parked domains) do **not** use a user data file, this function **cannot** query information for aliases. To retrieve information for an alias, specify the associated main or addon domain.; Due to differences in user data files, the function's actual output may not contain all of the returns that this document lists.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain on the cPanel account. Important: Do **not** specify an alias (parked domain).
- `hide_temporary_domains` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to hide temporary domains from the returned values.; `1` — Return an error if the requested domain is a temporary domain.; `0` — Return all domains, including the temporary domains. Note: If you set this parameter's value to `1` and the requested domain is temporary, the function will return an error similar to the following example: `Domain [example.com] is a temporary domain and `hide_temporary_domains` is enabled.`
- `return_https_redirect_status` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to return the secure redirect status of the addon domains.; `1` - Return status.; `0` - Do **not** return status.

**Returns** `data`: object

- `all_aliases_valid` (integer (`0`, `1`)) — Whether a valid SSL certificate exists on the domain's aliases.; `1` - A valid SSL certificate exists on the aliases.; `0` - A valid SSL certificate does **not** exist on the aliases.
- `can_https_redirect` (integer (`0`, `1`)) — Whether a valid SSL certificate exists or AutoSSL runs on the domain.; `1` - A valid SSL certificate exists or AutoSSL runs.; `0` - A valid SSL certificate does **not** exist, and AutoSSL does not run.
- `customlog` (object) — An object containing Apache log information.
  - `domain` (string) — The `target` log file's domain.
  - `target` (string <path>) — The absolute path to the domain's log file.
- `documentroot` (string <path>) — The absolute path to the domain's document root.
- `domain` (string <domain>) — The domain name on the cPanel account.
- `group` (string) — The domain's group name.
- `hascgi` (integer (`0`, `1`)) — Whether CGI is enabled for the domain.; `1` - Enabled.; `0` - Disabled.
- `homedir` (string <path>) — The absolute path to the account's home directory.
- `ifmodulemodsuphpc` (object) — An object containing information about PHP scripts and suPHP.
  - `group` (string) — If suPHP is enabled, the group that PHP scripts run as.
- `ip` (string <ipv4>) — The domain's IP address.
- `is_https_redirecting` (integer (`0`, `1`)) — Whether the domain redirects to https.; `1` - Redirects.; `0` - Does **not** redirect.
- `is_temporary` (integer (`0`, `1`)) — Whether the domain is a temporary domain.; `1` — The domain is temporary.; `0` — The domain is not temporary.
- `options` (string) — The Apache `Options` directive for the domain.
- `owner` (string <username>) — The WHM account (root or a reseller) that owns the cPanel account.
- `phpopenbasedirprotect` (integer (`0`, `1`)) — The domain's `open_basedir` setting.; `1` - Enabled.; `0` - Disabled.
- `port` (integer) — Apache's port to access the domain.
- `scriptalias` (object) — An object containing CGI information.
  - `path` (string <path>) — The absolute path to the domain's CGI directory.
  - `url` (string <url-path>) — The domain's CGI directory.
- `serveradmin` (string <email>) — The domain's administrator's contact email address.
- `serveralias` (string) — A space-separated list of the domain's aliases.
- `servername` (string <domain>) — The domain's identifier on the server.
- `type` (string (`addon_domain`, `sub_domain`, `main_domain`, `parked_domain`)) — The domain type.; `addon_domain` - The domain is an addon domain.; `sub_domain` - The domain is a subdomain.; `main_domain` - The domain is the account's main domain.; `parked_domain` - The domain is a parked domain (dom
- `usecanonicalname` (string (`On`, `Off`)) — The domain's Canonical Name (CNAME) setting.; `On` - Use the CNAME.; `Off` - Do **not** use the CNAME.
- `user` (string <username>) — The cPanel account's username.
- `userdirprotect` (integer (`0`, `1`)) — The domain's [Apache `mod_userdir` Tweak](https://go.cpanel.net/whmdocsApachemod_userdirTweak) setting.; `1` - Enabled.; `0` - Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainInfo \
  single_domain_data \
  domain='example.com'
```

## DomainLookup

<a id="domainlookup-countbasedomains"></a>
### `DomainLookup::countbasedomains` — Count the domains that have their own DNS zone

`GET /execute/DomainLookup/countbasedomains` · RO · since cPanel 138

This function counts the cPanel account's base domains: the primary domain, its addon domains and its parked domains. Note: The count excludes temporary domains, and matches the number of entries that the `DomainLookup::getbasedomains` function returns by default.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainLookup \
  countbasedomains
```

<a id="domainlookup-getbasedomains"></a>
### `DomainLookup::getbasedomains` — List the domains that have their own DNS zone

`GET /execute/DomainLookup/getbasedomains` · RO · since cPanel 138

This function lists the cPanel account's base domains: the primary domain, its addon domains and its parked domains. Note: Subdomains are **not** base domains and this function does not return them. Use the `SubDomain::listsubdomains` function for those.

**Parameters**

- `return_temporary_domain` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include the account's temporary domains in the result.; `1` - Include temporary domains.; `0` - Exclude temporary domains.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainLookup \
  getbasedomains
```

<a id="domainlookup-getdocroot"></a>
### `DomainLookup::getdocroot` — Return a domain's document root

`GET /execute/DomainLookup/getdocroot` · RO · since cPanel 138

This function retrieves the document root for a single domain on the cPanel account. Note: If the domain does not exist on the account, the system returns the account's `public_html` directory rather than an error.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — The domain to look up. The system converts this value to lowercase. Omit this parameter to retrieve the document root for the account's primary domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainLookup \
  getdocroot
```

<a id="domainlookup-getdocroots"></a>
### `DomainLookup::getdocroots` — Return every domain's document root

`GET /execute/DomainLookup/getdocroots` · RO · since cPanel 138

This function retrieves the document root for every domain on the cPanel account, including the primary domain, addon domains, parked domains and subdomains.

```bash
uapi --output=jsonpretty \
  --user=username \
  DomainLookup \
  getdocroots
```

## Direct Link Protection (Hotlink)

<a id="mime-add-hotlink"></a>
### `Mime::add_hotlink` — Enable hotlink protection

`GET /execute/Mime/add_hotlink` · RW · rollback: clean · since cPanel 11.42

This function adds hotlink protection for a site. Hotlink protection will redirect users to another URL if they navigate to a file with a specified extension, but an allowed URL did not refer them. Important: When you disable the [WebServer role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `extensions` · **required** · string — File types to hotlink protect. Note: To protect multiple file types, use a comma-separated list.
- `redirect_url` · **required** · string <url> · e.g. `http://redirect.example.com/` — The URL to which the system sends hotlinkers.
- `urls` · **required** · string — The site to hotlink protect. Note: To protect multiple URLs, separate each URL with a newline character.
- `allow_null` · optional · integer (`0`, `1`) · e.g. `1` — Whether the domain allows hotlinks.; `1` - Allows.; `0` - Does **not** allow.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  add_hotlink \
  urls='http://example.com/' \
  extensions='foo' \
  redirect_url='http://redirect.example.com/'
```

<a id="mime-delete-hotlink"></a>
### `Mime::delete_hotlink` — Disable hotlink protection

`GET /execute/Mime/delete_hotlink` · RW · rollback: clean · since cPanel 11.42

This function removes hotlink protection. Important: When you disable the [Web Server](https://go.cpanel.net/serverroles) role, the system **disables** this function.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  delete_hotlink
```

<a id="mime-list-hotlinks"></a>
### `Mime::list_hotlinks` — Return domains with hotlink protection

`GET /execute/Mime/list_hotlinks` · RO · since cPanel 11.42

This function lists domains with hotlink protection. Important: When you **disable** the [Web Server](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Returns** `data`: object

- `allow_null` (integer (`0`, `1`)) — Whether the domain allows hotlinks from an empty or null referral URL.; `1` - Allows hotlinks.; `0` - Does not allow hotlinks.
- `extensions` (string) — A comma-separated list of file types to hotlink protect.
- `redirect_url` (string <url>) — The URL to which to send hotlinkers.
- `state` (string (`enabled`, `disabled`)) — Whether hotlink protection is enabled.; `enabled`; `disabled`
- `urls` (array of string <url>) — An array of the domains with hotlink protection.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  list_hotlinks
```

## Domain Redirection

<a id="mime-add-redirect"></a>
### `Mime::add_redirect` — Add redirect to domain

`GET /execute/Mime/add_redirect` · RW · rollback: clean · since cPanel 11.42

This function adds a redirect to a domain. Important: When you disable the [*Web Server* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain from which to redirect.
- `redirect` · **required** · string <url> · e.g. `http://example.com/` — The URL to which to redirect.
- `redirect_wildcard` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to redirect all files within a directory to the same filename within the destination directory.; `1` - Redirect all files within the directory.; `0` - Do **not** redirect all files within the directory.
- `redirect_www` · optional · integer · default `0` · e.g. `0` — Whether to redirect domains with or without `www`.; `2` - Redirect with `www`.; `1` - Redirect without `www`.; `0` - Redirect with **and** without `www`.
- `src` · optional · string <url-path> · default `/` · e.g. `/specific-page` — A specific page from which to redirect.
- `type` · optional · string (`permanent`, `temp`) · default `permanent` · e.g. `permanent` — Whether the redirect is temporary.; `permanent`; `temp`

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  add_redirect \
  domain='example.com' \
  redirect='http://example.com/'
```

<a id="mime-delete-redirect"></a>
### `Mime::delete_redirect` — Remove redirect from domain

`GET /execute/Mime/delete_redirect` · RW · rollback: clean · since cPanel 11.42

This function removes a redirect from a domain. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain name.
- `args` · optional · string · default `` · e.g. `redirectme http://redirectme.com/` — An argument string that contains the arguments of a `Redirect` or `RedirectMatch` directives.
- `docroot` · optional · string <path> · e.g. `/home/example/public_html/` — The absolute file path to the document root containing the `.htaccess` file to change. If you don't pass this parameter, the system looks up the document root from the `domain` parameter's value.
- `src` · optional · string · default `` · e.g. `redirectpage.html` — The specific page that redirects visitors.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  delete_redirect \
  domain='example.com'
```

<a id="mime-get-redirect"></a>
### `Mime::get_redirect` — Return redirect URL for domain

`GET /execute/Mime/get_redirect` · RO · since cPanel 88

This function retrieves a redirection URL for a domain.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain's name.

**Returns** `data`: object

- `redirection_enabled` (integer (`0`, `1`)) — Whether the domain redirects to another URL.; `1` - Redirects.; `0` - Doesn't redirect.
- `url` (string <url>) — The URL to which to the domain redirects.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  get_redirect \
  domain='example.com'
```

<a id="mime-list-redirects"></a>
### `Mime::list_redirects` — Return .htaccess files' redirects

`GET /execute/Mime/list_redirects` · RO · since cPanel 11.42

This function lists the redirects in an account's .htaccess files. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `destination` · optional · string · e.g. `http://example.tld` — The string with which to filter results. ** Note: ** This will **only** return results that match the `destination` parameter **exactly**.
- `regex` · optional · string · e.g. `"^[a-z0-9_-]{6,18}$"` — A Perl regular expression that filters the results. The system matches the regular expression to the `sourceurl` return value.

**Returns** `data`: array of object

- *(array of objects)*
  - `destination` (string <url>) — The redirect's destination URL.
  - `displaydomain` (string (`ALL`)) — The domain to redirect.; `ALL` is the only possible value.
  - `displaysourceurl` (string <url-path>) — The path to the file within the domain to test, relative to the home directory.
  - `docroot` (string <path>) — The absolute file path to the source domain's document root.
  - `domain` (string <domain>) — The domain to redirect.
  - `kind` (string (`rewrite`, `redirect`, `redirectmatch`)) — The kind of redirect.; `rewrite` — The request sent a redirect to another path on the server.; `redirect` — The request sent a redirect for the URL.; `redirectmatch` — The request sent a redirect based on a regular expre
  - `matchwww` (integer (`1`, `0`)) — Whether the redirect matches `www.` subdomains.; `1` — Matches.; `0` — Does not match.
  - `matchwww_text` (string (`checked`)) — Whether the [*Redirect with or without www.* option](https://go.cpanel.net/Redirects) is active.; `checked` — The *Redirect with or without www.* option is active.
  - `opts` (string) — The options that the function passes to Apache as part of the [Rewrite rule](https://httpd.apache.org/docs/2.4/rewrite/flags.html#flag_l).
  - `source` (string <url-path>) — The path to the file within the domain to test, relative to the home directory.
  - `sourceurl` (string <url-path>) — The path to the file within the domain to test, relative to the home directory.
  - `statuscode` (string) — The [HTTP Status Code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes) of the request
  - `targeturl` (string <url>) — The redirect's destination URL.
  - `type` (string (`permanent`, `temporary`)) — Whether the redirect is permanent or temporary.; `permanent` — The redirect is permanent.; `temporary` — The redirect is temporary.
  - `urldomain` (string <domain>) — The domain to redirect.
  - `wildcard` (integer (`1`, `0`)) — Whether the wildcard subdomains match.; `1` — Matches.; `0` — Does **not** match.
  - `wildcard_text` (string (`checked`)) — Whether the [*Wild Card Redirect*](https://go.cpanel.net/Redirects) option is active.; `checked` — The *Wild Card Redirect* option is active.

```bash
uapi --output=jsonpretty \
  --user=username \
  Mime \
  list_redirects
```

## Park

<a id="park-listparkeddomains"></a>
### `Park::listparkeddomains` — List the parked (aliased) domains

`GET /execute/Park/listparkeddomains` · RO · since cPanel 138

This function lists the domains that are parked (aliased) on the cPanel account's primary domain. Note: This function lists only the domains parked on the primary domain. Use the `AddonDomain::listaddondomains` function for the domains parked on a subdomain.

**Parameters**

- `regex` · optional · string · e.g. `example[.]com$` — A Perl regular expression. The system returns only the parked domains whose name matches this pattern, case-insensitively.
- `return_https_redirect_status` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include the `can_https_redirect` and `is_https_redirecting` fields in each entry.; `1` - Include the HTTPS redirect status.; `0` - Omit the HTTPS redirect status.

```bash
uapi --output=jsonpretty \
  --user=username \
  Park \
  listparkeddomains
```

<a id="park-park"></a>
### `Park::park` — Park an alias domain on an existing domain

`GET /execute/Park/park` · RW · rollback: none · since cPanel 138

This function parks (aliases) a domain on the cPanel account, so that the domain serves the content of a domain that already exists on the account. Important:  Without the `topdomain` parameter, the system parks the domain on the account's primary domain.; With the `topdomain` parameter, the system parks the domain on a subdomain of the primary domain. That arrangement is how an addon domain is represented. To create an addon domain and its subdomain in one call, use the `AddonDomain::addaddondomain` function instead.; The account must have either the *Parked Domains* or the *Addon Domains* feature. Parking on the primary domain requires the *Parked Domains* feature specifically. When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `alias.example.com` — The domain to park. The system removes a leading `www.` from this value and converts it to lowercase before it validates the domain.
- `disallowdot` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to remove the dot (`.`) characters from the `topdomain` value, rather than only trimming a trailing dot. This parameter has no effect unless you also pass the `topdomain` parameter.; `1` - Remove dots from the subdomain label.; `0` - Do **not** remove dots from the subdomain label.
- `force` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Accepted for compatibility, but ignored for account-level callers. It can no longer cause the system to skip the domain name, [DNS](https://go.cpanel.net/dnsrecords), and registration checks, or to overwrite an existing DNS zone. The system still refuses to create a domain that another account owns.; `0` - Enforce the checks.; `1` - Accepted, but has no effect for account-level callers.
- `topdomain` · optional · string · e.g. `shop` — The subdomain label of the account's primary domain to park the `domain` value on. The system appends the primary domain to this value. Omit this parameter to park the domain on the primary domain itself.

```bash
uapi --output=jsonpretty \
  --user=username \
  Park \
  park \
  domain='alias.example.com'
```

<a id="park-unpark"></a>
### `Park::unpark` — Remove a parked (aliased) domain

`GET /execute/Park/unpark` · RW · rollback: none · since cPanel 138

This function unparks (removes the alias for) a domain on the cPanel account. Important:  This function removes the alias only. It does **not** remove the subdomain that an addon domain is parked on. To remove both, use the `AddonDomain::deladdondomain` function instead.; The account must have either the *Parked Domains* or the *Addon Domains* feature. When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `alias.example.com` — The parked domain to remove.
- `subdomain` · optional · string · e.g. `shop_example.com` — The subdomain that the domain is parked on, given in the underscore-separated form that the `AddonDomain::listaddondomains` function returns in its `domainkey` field. Omit this parameter to let the system determine the subdomain. Pass it only when the domain is parked on a subdomain rather than on the primary domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  Park \
  unpark \
  domain='alias.example.com'
```

## SubDomain

<a id="subdomain-addsubdomain"></a>
### `SubDomain::addsubdomain` — Create subdomain

`GET /execute/SubDomain/addsubdomain` · RW · rollback: none · since cPanel 70

This function creates a subdomain. Important: When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string · e.g. `subdomain` — The subdomain name to create.
- `rootdomain` · **required** · string <domain> · e.g. `example.com` — The domain on which to create the new subdomain.  The domain **must** already exist on the cPanel account.
- `canoff` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to use a canonical name (CNAME) in the [Apache® configuration for self-referential URLs](https://httpd.apache.org/docs/2.4/mod/core.html#usecanonicalname).; `1` - Use the CNAME.; `0` - Do **not** use the CNAME.
- `dir` · optional · string <path> · e.g. `/public_html/directory_name` — The subdomain's document `root` within the home directory, given as a valid directory path relative to the user's home directory. This value defaults to the user's home directory `/public_html/` path. Note: If the *Restrict document roots to public_html* value is set to *Off* in WHM's [*Tweak Settings*](https://go.cpanel.net/whmdocsTweakSettings#domains) interface (*WHM >> Home >> Server Configuration >> Tweak Settings*), this parameter defaults to the `/username/` path. For example, the `username` user's subdomain `example` would default to the `/home/username/example` path.
- `disallowdot` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to remove the dot (`.`) characters from the `domain` value.; `1` - Remove dots from the domain.; `0` - Do **not** remove dots from the domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SubDomain \
  addsubdomain \
  domain='subdomain' \
  rootdomain='example.com'
```

<a id="subdomain-delsubdomain"></a>
### `SubDomain::delsubdomain` — Remove a subdomain

`GET /execute/SubDomain/delsubdomain` · RW · rollback: none · since cPanel 138

This function removes a subdomain from the cPanel account. Important:  If any addon domain is parked on the subdomain, the system refuses to remove it and names the addon domains in the `errors` field. Remove those addon domains first with the `AddonDomain::deladdondomain` function.; This function does **not** remove the subdomain's document root or the files in it. When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string · e.g. `subdomain_example.com` — The subdomain to remove. Give this value either as the underscore-separated `subdomain_rootdomain` form that the `SubDomain::listsubdomains` function returns in its `domainkey` field, or as a fully qualified domain name.
- `disallowdot` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to remove the dot (`.`) characters from the subdomain label in the `domain` value.; `1` - Remove dots from the subdomain label.; `0` - Do **not** remove dots from the subdomain label.

```bash
uapi --output=jsonpretty \
  --user=username \
  SubDomain \
  delsubdomain \
  domain='subdomain_example.com'
```

<a id="subdomain-getreservedsubdomains"></a>
### `SubDomain::getreservedsubdomains` — List the reserved subdomain names

`GET /execute/SubDomain/getreservedsubdomains` · RO · since cPanel 138

This function lists the subdomain labels that the system reserves, and that an account therefore cannot use to create a subdomain. Note: The returned labels are **not** sorted.

```bash
uapi --output=jsonpretty \
  --user=username \
  SubDomain \
  getreservedsubdomains
```

<a id="subdomain-listsubdomains"></a>
### `SubDomain::listsubdomains` — List the subdomains

`GET /execute/SubDomain/listsubdomains` · RO · since cPanel 138

This function lists the subdomains on the cPanel account, including the subdomains that the account's addon domains are parked on.

**Parameters**

- `regex` · optional · string · e.g. `^shop` — A Perl regular expression. The system returns only the subdomains whose fully qualified name matches this pattern, case-insensitively. If this value is not a valid Perl regular expression, the function fails and reports the error in the `errors` field.
- `return_https_redirect_status` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether to include the `can_https_redirect` and `is_https_redirecting` fields in each entry.; `1` - Include the HTTPS redirect status.; `0` - Omit the HTTPS redirect status.

```bash
uapi --output=jsonpretty \
  --user=username \
  SubDomain \
  listsubdomains
```

<a id="subdomain-validregex"></a>
### `SubDomain::validregex` — Return the subdomain validation pattern

`GET /execute/SubDomain/validregex` · RO · since cPanel 138

This function retrieves the regular expression that the system uses to validate a subdomain label. Note: Use this value to validate a subdomain label in an interface before you call the `SubDomain::addsubdomain` function. It does **not** replace the server-side validation that `SubDomain::addsubdomain` performs.

```bash
uapi --output=jsonpretty \
  --user=username \
  SubDomain \
  validregex
```

## Virtual Host Information

<a id="webvhosts-list-domains"></a>
### `WebVhosts::list_domains` — Return virtual host names for domains

`GET /execute/WebVhosts/list_domains` · RO · since cPanel 56

This function lists virtual host names for each domain.

**Returns** `data`: array of object

- *(array of objects)*
  - `domain` (string <domain>) — The domain name.
  - `proxy_subdomains` (array of string) — An array of service subdomains (proxy subdomains) listed for the domain.
  - `vhost_is_ssl` (integer (`0`, `1`)) — Whether an SSL certificate secures the domain.; `1` - Secured.; `0` - **Not** secured.
  - `vhost_name` (string <domain>) — The name of the virtual host.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebVhosts \
  list_domains
```

<a id="webvhosts-list-ssl-capable-domains"></a>
### `WebVhosts::list_ssl_capable_domains` — Return domains that allow SSL certificate purchase

`GET /execute/WebVhosts/list_ssl_capable_domains` · RO · since cPanel 64

This function lists every domain for which you may purchase an SSL certificate. The possible domains for the Secure Sockets Layer (SSL) certificate include applicable [service subdomains.](https://go.cpanel.net/ServiceProxySubdomains)

**Parameters**

- `hide_temporary_domains` · optional · integer (`1`, `0`) · default `0` · e.g. `1` — Whether to hide temporary domains from the returned values.; `1` — Return an error if the requested domain is a temporary domain.; `0` — Return all domains, including the temporary domains. Note: If you set this parameter's value to `1` and the requested domain is temporary, the function will return an error similar to the following example: `Domain [example.com] is a temporary domain and `hide_temporary_domains` is enabled.`

**Returns** `data`: array of object — An array of objects containing data for a domain.

- *(array of objects)*
  - `domain` (string <domain>) — A valid domain name on the virtual host.
  - `is_proxy` (integer (`0`, `1`)) — Whether the system automatically created the service subdomain or a user manually created the domain.; `1` - The system automatically created the service subdomain.; `0` - A user manually created the domain.
  - `vhost_name` (string <domain>) — The name of the virtual host or website.

```bash
uapi --output=jsonpretty \
  --user=username \
  WebVhosts \
  list_ssl_capable_domains
```

