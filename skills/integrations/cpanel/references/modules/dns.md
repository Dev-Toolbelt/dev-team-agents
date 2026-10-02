<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — DNS

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **DNS Information**: [`DNS::ensure_domains_reside_only_locally`](#dns-ensure-domains-reside-only-locally), [`DNS::ensure_domains_use_recognized_nameservers`](#dns-ensure-domains-use-recognized-nameservers), [`DNS::fetch_cpanel_generated_domains`](#dns-fetch-cpanel-generated-domains), [`DNS::has_local_authority`](#dns-has-local-authority), [`DNS::is_alias_available`](#dns-is-alias-available), [`DNS::is_https_available`](#dns-is-https-available), [`DNS::is_svcb_available`](#dns-is-svcb-available), [`DNS::lookup`](#dns-lookup), [`DNS::mass_edit_zone`](#dns-mass-edit-zone), [`DNS::parse_zone`](#dns-parse-zone)
- **DNS**: [`DNS::swap_ip_in_zones`](#dns-swap-ip-in-zones)
- **DNS Security**: [`DNSSEC::activate_zone_key`](#dnssec-activate-zone-key), [`DNSSEC::add_zone_key`](#dnssec-add-zone-key), [`DNSSEC::deactivate_zone_key`](#dnssec-deactivate-zone-key), [`DNSSEC::disable_dnssec`](#dnssec-disable-dnssec), [`DNSSEC::enable_dnssec`](#dnssec-enable-dnssec), [`DNSSEC::export_zone_dnskey`](#dnssec-export-zone-dnskey), [`DNSSEC::export_zone_key`](#dnssec-export-zone-key), [`DNSSEC::fetch_ds_records`](#dnssec-fetch-ds-records), [`DNSSEC::import_zone_key`](#dnssec-import-zone-key), [`DNSSEC::remove_zone_key`](#dnssec-remove-zone-key), [`DNSSEC::set_nsec3`](#dnssec-set-nsec3), [`DNSSEC::unset_nsec3`](#dnssec-unset-nsec3)
- **Dynamic DNS**: [`DynamicDNS::create`](#dynamicdns-create), [`DynamicDNS::delete`](#dynamicdns-delete), [`DynamicDNS::list`](#dynamicdns-list), [`DynamicDNS::recreate`](#dynamicdns-recreate), [`DynamicDNS::set_description`](#dynamicdns-set-description)
- **Email DNS Settings**: [`Email::add_mx`](#email-add-mx), [`Email::change_mx`](#email-change-mx), [`Email::delete_mx`](#email-delete-mx), [`Email::list_mxs`](#email-list-mxs), [`EmailAuth::apply_dmarc`](#emailauth-apply-dmarc), [`EmailAuth::disable_dkim`](#emailauth-disable-dkim), [`EmailAuth::enable_dkim`](#emailauth-enable-dkim), [`EmailAuth::ensure_dkim_keys_exist`](#emailauth-ensure-dkim-keys-exist), [`EmailAuth::fetch_dkim_private_keys`](#emailauth-fetch-dkim-private-keys), [`EmailAuth::install_dkim_private_keys`](#emailauth-install-dkim-private-keys), [`EmailAuth::install_spf_records`](#emailauth-install-spf-records), [`EmailAuth::remove_dmarc`](#emailauth-remove-dmarc), [`EmailAuth::validate_current_dkims`](#emailauth-validate-current-dkims), [`EmailAuth::validate_current_dmarcs`](#emailauth-validate-current-dmarcs), [`EmailAuth::validate_current_ptrs`](#emailauth-validate-current-ptrs), [`EmailAuth::validate_current_spfs`](#emailauth-validate-current-spfs)
- **ZoneEdit**: [`ZoneEdit::resetzone`](#zoneedit-resetzone)

## DNS Information

<a id="dns-ensure-domains-reside-only-locally"></a>
### `DNS::ensure_domains_reside_only_locally` — Return whether domains only resolve locally

`GET /execute/DNS/ensure_domains_reside_only_locally` · RO · since cPanel 56

This function indicates whether the account's domains resolve exclusively to this server.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example1.com` — The domain to check. Note: To check multiple domains, duplicate or increment the parameter name. For example, to exclude three domains, you could: Use the `domain` parameter multiple times.; Use the `domain`, `domain-1`, and `domain-2` parameters.

**Returns** `data`: array of string — The results from each domain parameter's DNS query.; `null` - The domain **only** resolves locally to the server.; A valid string that explains to where the domain resolves.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNS \
  ensure_domains_reside_only_locally \
  domain='example.com'
```

<a id="dns-ensure-domains-use-recognized-nameservers"></a>
### `DNS::ensure_domains_use_recognized_nameservers` — Return whether domains use recognized nameservers

`GET /execute/DNS/ensure_domains_use_recognized_nameservers` · RO · since cPanel 138

This function indicates whether the account's domains' nameservers resolve to an IP address that this server recognizes as its own. It predicts the outcome of the create-time nameserver validation that runs when a domain is added to the account, without performing any privileged action.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example1.com` — The domain to check. Note: To check multiple domains, duplicate or increment the parameter name. For example, to check three domains, you could: Use the `domain` parameter multiple times.; Use the `domain`, `domain-1`, and `domain-2` parameters.

**Returns** `data`: array of object — The results from each domain parameter's nameserver check.; `null` - The domain would pass the create-time nameserver validation.; An object describing why it would not, with a `type` field set to one of: `domain_not_reg

- *(array of objects)*
  - `message` (string) — The validator's own localized message.
  - `type` (string (`domain_not_registered`, `unrecognized_nameservers`)) — A short machine-readable reason code.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNS \
  ensure_domains_use_recognized_nameservers \
  domain='example.com'
```

<a id="dns-fetch-cpanel-generated-domains"></a>
### `DNS::fetch_cpanel_generated_domains` — Retrieve cPanel-generated subdomains for a domain

`GET /execute/DNS/fetch_cpanel_generated_domains` · RO · since cPanel 120

This function retrieves the list of subdomains that cPanel automatically generates for a given domain. These include proxy subdomains such as `webmail`, `mail`, and `cpanel`, as well as other system-generated domain names.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain for which to retrieve cPanel-generated subdomains.

**Returns** `data`: array of object — An array of objects containing the cPanel-generated domain names for the specified domain.

- *(array of objects)*
  - `domain` (string <domain>) — A cPanel-generated domain name, returned as a fully-qualified domain name (FQDN) with a trailing dot.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNS \
  fetch_cpanel_generated_domains \
  domain='example.com'
```

<a id="dns-has-local-authority"></a>
### `DNS::has_local_authority` — Return whether local DNS server is authoritative

`GET /execute/DNS/has_local_authority` · RO · since cPanel 78

This function checks whether the local server is authoritative for the domain's DNS records.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain to check whether the local server is authoritative for the domain's DNS records. Note: To check multiple domains, increment or duplicate the parameter name. For example, `domain-0`, `domain-1`, and `domain-2`.

**Returns** `data`: array of object — An array of objects containing information about the authoritative status of a domain's local DNS zone files.

- *(array of objects)*
  - `domain` (string <domain>) — The queried domain.
  - `error` (string) — An error message that details the reason why the local server's authoritative check failed.
  - `local_authority` (integer (`1`, `0`)) — Whether the local server is authoritative for the domain's DNS records.; `1` — The local server is authoritative for the domain's DNS records.; `0` — The local server is **not** authoritative for the domain's DNS records
  - `nameservers` (array of string <domain>) — The domain's nameservers, if any exist.
  - `zone` (string <domain>) — The domain's DNS zone, if one exists.; `null` — No valid DNS zone.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNS \
  has_local_authority \
  domain='example.com'
```

<a id="dns-is-alias-available"></a>
### `DNS::is_alias_available` — Return `ALIAS` DNS record availability & resolver

`GET /execute/DNS/is_alias_available` · RO · since cPanel 122

This function returns whether `ALIAS` and `ANAME` records are available and the value of the running PowerDNS (PDNS) `resolver` setting, if any exists. For more information, read our [`ALIAS` documentation](https://go.cpanel.net/dns-alias-record).

**Returns** `data`: object

- `alias` (integer (`1`, `0`)) — Whether `ALIAS` records are available.; `1` - Available.; `0` - Not available.
- `aname` (integer (`1`, `0`)) — Whether `ANAME` records are available.; `1` - Available.; `0` - Not available.
- `resolver` (string) — The value (if any) of the running PDNS’s `resolver` setting.

```bash
uapi --output=jsonpretty --user=username DNS is_alias_available
```

<a id="dns-is-https-available"></a>
### `DNS::is_https_available` — Return DNS HTTPS record support information

`GET /execute/DNS/is_https_available` · RO · since cPanel 122

This function fetches information regarding HTTPS records support. HTTPS records are defined in RFC 9460 and provide service parameters for HTTPS endpoints. For more information, read our [Zone Editor documentation](https://go.cpanel.net/cpaneldocsZoneEditor).

**Returns** `data`: object

- `https` (integer (`1`, `0`)) — Whether HTTPS records are supported.; `1` - Supported.; `0` - Not supported.
- `dns_server` (string) — The DNS server type currently in use (bind, pdns, etc.).

```bash
uapi --output=jsonpretty --user=username DNS is_https_available
```

<a id="dns-is-svcb-available"></a>
### `DNS::is_svcb_available` — Return DNS SVCB record support information

`GET /execute/DNS/is_svcb_available` · RO · since cPanel 122

This function fetches information regarding SVCB records support. SVCB records are defined in RFC 9460 and provide service binding and aliasing for arbitrary services. For more information, read our [Zone Editor documentation](https://go.cpanel.net/cpaneldocsZoneEditor).

**Returns** `data`: object

- `svcb` (integer (`1`, `0`)) — Whether SVCB records are supported.; `1` - Supported.; `0` - Not supported.
- `dns_server` (string) — The DNS server type currently in use (bind, pdns, etc.).

```bash
uapi --output=jsonpretty --user=username DNS is_svcb_available
```

<a id="dns-lookup"></a>
### `DNS::lookup` — Return domain's DNS information

`GET /execute/DNS/lookup` · RO · since 90

This function returns DNS zone information about a domain.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — A fully qualified domain name.

**Returns** `data`: array of string — Contains each response item.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNS \
  lookup \
  domain='example.com'
```

<a id="dns-mass-edit-zone"></a>
### `DNS::mass_edit_zone` — Update a DNS zone

`GET /execute/DNS/mass_edit_zone` · RW · rollback: none · since 96

This function updates a DNS zone by allowing multiple records to be added, modified, or removed in a single call. It also ensures modified records occupy the same number of lines as before the edit. **NOTE:** You cannot use this function to edit temporary domains.

**Parameters**

- `serial` · **required** · integer · e.g. `202001010100` — The current serial number in the DNS zone’s SOA (Start of Authority) record. If this value does not match the zone’s current state, the request fails.
- `zone` · **required** · string · e.g. `example.com` — The name of one of the user’s DNS zones.
- `add` · optional · array of string <json> — The records to add to the zone. Each item must be a serialized JSON object that contains: `dname` — The record’s name.; `ttl` — The record’s TTL (Time-To-Live) value.; `record_type` — The record’s type. For example, `A` or `TXT`.; `data` — An array of strings. The format and number of the strings depend on the `record_type` value.
- `edit` · optional · array of string <json> — The records to edit in the zone. Each item must be a serialized JSON object that contains: `line_index` — The line number in the DNS zone where the record starts. This is a 0-based index, so to edit the first line in the file use the `0` value. To edit the second line, give `1`, and so forth.; `dname` — The record’s name.; `ttl` — The record’s TTL (Time-To-Live) value.; `record_type` — The record’s new type. For example, `A` or `TXT`.; `data` — An array of strings. The format and number of the strings depend on the `record_type` value.
- `remove` · optional · array of integer — The line indexes of records to remove from the zone.

**Returns** `data`: object

- `new_serial` (integer) — The DNS zone’s SOA record’s new serial number.

```bash
uapi --output=jsonpretty --user=username DNS mass_edit_zone zone='example.com' serial='202001010100' remove=23 add='{"dname":"example","ttl":14400,"record_type":"A","data":["127.0.0.1"]}'
```

<a id="dns-parse-zone"></a>
### `DNS::parse_zone` — Return a parsed DNS zone

`GET /execute/DNS/parse_zone` · RO · since 96

This function parses a given DNS zone. Important: Most DNS zones contain only 7-bit ASCII. However, it is possible for DNS zones to contain any binary sequence. An application that decodes this function's base64 output **must** be able to handle cases where the decoded octets do not match any specific character encoding.

**Parameters**

- `zone` · **required** · string · e.g. `example.com` — The name of one of the user’s DNS zones.

**Returns** `data`: array of object — The zone’s content.

- *(array of objects)*
  - *variant: object*
    - `line_index` (integer) — The line’s index in the zone file.
    - `type` (string (`record`, `control`, `comment`)) — The type of object in the zone file: `record` - A resource record.; `control` - A control statement.; `comment` - A line comment.
    - `data_b64` (array of string <base64>) — The resource record’s content, encoded to base64.
    - `dname_b64` (string <base64>) — The resource record’s owner, encoded to base64.
    - `record_type` (string) — The resource record’s type.
    - `ttl` (integer) — The resource record’s TTL (Time-to-Live).
  - *variant: object*
    - `line_index` (integer) — The line’s index in the zone file.
    - `type` (string (`record`, `control`, `comment`)) — The type of object in the zone file: `record` - A resource record.; `control` - A control statement.; `comment` - A line comment.
    - `text_b64` (string <base64>) — The line’s text, encoded to base64.
  - *variant: object*
    - `line_index` (integer) — The line’s index in the zone file.
    - `type` (string (`record`, `control`, `comment`)) — The type of object in the zone file: `record` - A resource record.; `control` - A control statement.; `comment` - A line comment.
    - `text_b64` (string <base64>) — The line’s text, encoded to base64.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNS \
  parse_zone \
  zone='example.com'
```

## DNS

<a id="dns-swap-ip-in-zones"></a>
### `DNS::swap_ip_in_zones` — Update IP addresses in zone files

`GET /execute/DNS/swap_ip_in_zones` · RW · rollback: none · since cPanel 96

This function replaces a domain's IPv4 address in the DNS zone file with the specified destination IPv4 address.

**Parameters**

- `dest_ip` · **required** · string <ipv4> · e.g. `192.0.2.1` — The IPv4 address to use as the replacement in the zone files.
- `domain` · **required** · string <domain> · e.g. `example.com` — The domain to perform the zone file updates on. Note: To update multiple domains, increment or duplicate the parameter name. For example, `domain-0`, `domain-1`, and `domain-2`.
- `ftp_ip` · optional · string <ipv4> · e.g. `192.0.2.1` — The IPv4 address to use as the replacement for FTP records in the zone files. If this parameter is **not** provided, then the system will use the `dest_ip` value.
- `source_ip` · optional · string <ipv4> · e.g. `192.0.2.0` — The IPv4 address to replace in the zone files. The detected source IPv4 address is one of: If there is an A record for the root of the zone **and** the IP address is **not** a loopback address, then the system will use its address.; If there are any A records in the zone whose addresses are **not** loopback addresses, then the system will use the address of the first such A record in the zone file.; If no A records exist in the zone **or** all A records have loopback addresses, then the system will **not** update the zone file. If you do **not** call this parameter, the system will automatically detect the IP addresses in the zone files.

**Returns** `data`: any — An array of objects containing the updated DNS records, including their previous values.

- *(array of objects)*
  - `zone_name` (string <domain>) — The DNS zone in which the system updated the domain's record.
  - `record_name` (string <domain>) — The name of the domain's updated DNS record.
  - `record_type` (string) — The type of the DNS record which was updated.
  - `old_value` (string) — The value of the DNS record before it was updated.
  - `new_value` (string) — The value of the DNS record after it was updated.

```bash
uapi --user=username DNS swap_ip_in_zones domain='example.com' source_ip='192.0.2.0' dest_ip='192.0.2.1'
```

## DNS Security

<a id="dnssec-activate-zone-key"></a>
### `DNSSEC::activate_zone_key` — Enable DNSSEC security key

`GET /execute/DNSSEC/activate_zone_key` · RW · rollback: none · since cPanel 84

This function activates a DNSSEC security key. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The security key's domain.
- `key_id` · **required** · integer · e.g. `1` — The security key's ID.

**Returns** `data`: object

- `domain` (string <domain>) — The domain for which the system activated a security key.
- `error` (string) — An error message that describes why the system could not activate the security key.
- `key_id` (string) — The security key's ID.
- `success` (integer (`1`, `0`)) — Whether the system activated the security key.; `1` - Activated.; `0` - The system failed to activate the security key.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  activate_zone_key \
  domain='example.com' \
  key_id='1'
```

<a id="dnssec-add-zone-key"></a>
### `DNSSEC::add_zone_key` — Create DNSSEC security key

`GET /execute/DNSSEC/add_zone_key` · RW · rollback: none · since cPanel 84

This function generates a DNSSEC zone key for a domain. Note:  After you enable DNSSEC on the domain, you **must** add the DS records to your registrar.; You **cannot** modify the DNSSEC security key. To make any changes, you **must** disable (and delete) and re-create the DNSSEC security key. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `algo_num` · **required** · integer (`5`, `6`, `7`, `8`, `10`, `13`, `14`) · e.g. `8` — The algorithm that the system uses to generate the security key.; `5` — RSA/SHA-1; `6` — DSA-NSEC3-SHA1; `7` — RSASHA1-NSEC3-SHA1; `8` — RSA/SHA-256; `10` — RSA/SHA-512; `13` — ECDSA Curve P-256 with SHA-256; `14` — ECDSA Curve P-384 with SHA-384 Note: We recommend that you use 'ECDSA Curve P-256 with SHA-256' if your registrar supports it.
- `domain` · **required** · string <domain> · e.g. `example.com` — The domain on which to enable DNSSEC.
- `key_type` · **required** · string (`ksk`, `zsk`) · e.g. `ksk` — The type of key to add.; `ksk`; `zsk`
- `active` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to activate the newly-created key.; `1` — Activate the key.; `0` — Do **not** activate the key.
- `key_size` · optional · integer · e.g. `2048` — The key's size, in bits. Note: For the following `algo_num` and `key_type` parameters, the `key_size` defaults to the following values: `5` — ksk `2048` zsk `1024`; `6` — ksk `2048` zsk `1024`; `7` — ksk `2048` zsk `1024`; `8` — ksk `2048` zsk `1024`; `10` — ksk `2048` zsk `1024`; `13` — ksk `256` zsk `256`; `14` — ksk `384` zsk `384`

**Returns** `data`: object

- `domain` (string <domain>) — The domain for which the system added a security key.
- `error` (string) — An error message that describes why the system could not add the security key.
- `new_key_id` (string) — The security key's ID.
- `success` (integer (`1`, `0`)) — Whether the system added the security key.; `1` — The system added the security key.; `0` — The system failed to add the security key.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  add_zone_key \
  domain='example.com' \
  algo_num='8' \
  key_type='ksk'
```

<a id="dnssec-deactivate-zone-key"></a>
### `DNSSEC::deactivate_zone_key` — Disable DNSSEC security key

`GET /execute/DNSSEC/deactivate_zone_key` · RW · rollback: none · since cPanel 84

This function deactivates a DNSSEC security key. Important: When you disable the [*DNS* role](https://go.cpanel.net/serverroles/), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The security key's domain.
- `key_id` · **required** · integer · e.g. `1` — The security key's ID.

**Returns** `data`: object

- `domain` (string <domain>) — The domain for which the system deactivated a security key.
- `error` (string) — An error message that describes why the system could not deactivate the security key.
- `key_id` (string) — The security key's ID.
- `success` (integer (`1`, `0`)) — Whether the system deactivated the security key.; `1` - Deactivated.; `0` - The system failed to deactivate the security key.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  deactivate_zone_key \
  domain='example.com' \
  key_id='1'
```

<a id="dnssec-disable-dnssec"></a>
### `DNSSEC::disable_dnssec` — Disable DNSSEC

`GET /execute/DNSSEC/disable_dnssec` · RW · rollback: none · since cPanel 60

This function disables DNSSEC on the domain. Warning:  This action is **irreversible**. If you disable DNSSEC on the domain, you will lose the associated keys. You can only retrieve the previous state with a full backup.; If you disable DNSSEC, you **must** remove the DNS records at the registrar. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> — The domain on which to disable DNSSEC. Note: To enable DNSSEC on multiple domains, increment the parameter name. For example: `domain-0`, `domain-1`, `domain-2`.

**Returns** `data`: object

- `disabled` (object) — An array of objects that contain the domains for which the system disabled DNSSEC.
  - `additionalProperties` (integer (`0`, `1`)) — Information about the domains for which the system disabled DNSSEC.; `1` — Disabled.; `0` — The system failed to disable DNSSEC.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  disable_dnssec \
  domain='example.com'
```

<a id="dnssec-enable-dnssec"></a>
### `DNSSEC::enable_dnssec` — Enable DNSSEC

`GET /execute/DNSSEC/enable_dnssec` · RW · rollback: none · since cPanel 60

This function enables DNSSEC on the domain. Note:  After you enable DNSSEC on the domain, you **must** add the DNS records to your registrar.; You **cannot** modify the DNSSEC security key. To make any changes, you **must** disable (and delete) and re-create the DNSSEC security key. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> — The domain on which to enable DNSSEC. Note: To enable DNSSEC on multiple domains, increment the parameter name. For example: `domain-0`, `domain-1`, `domain-2`.
- `active` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to activate the newly-created key.; `1` — Activate the key.; `0` — Do **not** activate the key.
- `algo_num` · optional · integer · default `8` · e.g. `8` — The algorithm that the system uses to generate the security key.; `5` — RSA/SHA-1; `6` — DSA-NSEC3-SHA1; `7` — RSASHA1-NSEC3-SHA1; `8` — RSA/SHA-256; `10` — RSA/SHA-512; `13` — ECDSA Curve P-256 with SHA-256; `14` — ECDSA Curve P-384 with SHA-384 Note: We recommend that you use `ECDSA Curve P-256 with SHA-256` if your registrar supports it.
- `key_setup` · optional · string (`simple`, `classic`) · default `classic` · e.g. `classic` — The manner in which the system creates the security key.; `simple` — Use a single key for both KSK and ZSK. Use this value when the `algo_nom` parameter is greater than `8`.; `classic` — Use separate keys for KSK and ZSK. Use this value when the `algo_nom` parameter is equal to or less than `8`.
- `nsec3_iterations` · optional · integer · default `0` · e.g. `7` — The number of times that the system rehashes the first resource record hash operation. A positive integer less than `501`. Note: In cPanel & WHM version 132 and earlier, the default value is `7`.
- `nsec3_narrow` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether NSEC3 will operate in Narrow or Inclusive mode. In Narrow mode, PowerDNS sends out white lies about the next secure record. Rather than query the resource record in the database, PowerDNS sends the hash plus `1` as the next secure record.; `1` — Narrow mode.; `0` — Inclusive mode.
- `nsec3_opt_out` · optional · integer (`0`, `1`) · default `0` · e.g. `0` — Whether the system will create records for all delegations.; `1` — Create records for all delegations.; `0` — Create records only for secure delegations. Note: **Only** select `1` if you **must** create records for all delegations.
- `nsec3_salt` · optional · string <hex> · default `-` · e.g. `1A2B3C4D5E6F` — A hexadecimal string that the system appends to the domain name before it applies the hash function to the name. For more information about the salt value, read the [RFC 5155](https://tools.ietf.org/html/rfc5155#section-3.1.5) documentation. **NOTE:**; In cPanel & WHM version 132 and later, this parameter also accepts the literal value `-` to indicate that no salt should be used. If you do not declare a value, the system defaults to no salt.; In cPanel & WHM version 130 and earlier, if you did not declare a value, the system defaulted to a random 64-bit value.
- `use_nsec3` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether the domain will use [Next Secure Record](https://tools.ietf.org/html/rfc4470) (NSEC) or NSEC3 semantics.; `1` — Use NSEC3 semantics.; `0` — Use NSEC semantics. Note: If you use NSEC semantics (`0`), the system ignores the other NSEC3 options.

**Returns** `data`: object

- `enabled` (object) — An object containing information about the domains for which the system enabled DNSSEC.
  - `additionalProperties` (object) — Information about the domain for which the system enabled DNSSEC.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  enable_dnssec \
  domain='example.com'
```

<a id="dnssec-export-zone-dnskey"></a>
### `DNSSEC::export_zone_dnskey` — Export DNSKEY record value

`GET /execute/DNSSEC/export_zone_dnskey` · RO · since cPanel 88

This function exports a domain's DNSKEY record value. Important: When you disable the [_DNS_ role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain from which to fetch the DNSKEY record value.
- `key_id` · **required** · integer · e.g. `12345` — The DNSSEC record's ID.

**Returns** `data`: object

- `dnskey` (string) — The DNSKEY record value.
- `key_id` (integer) — The DNSSEC record's ID.
- `success` (integer (`0`, `1`)) — Whether the DNSKEY record exported successfully.; `1` - The system exported the record successfully.; `0` - The system failed to export the record.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  export_zone_dnskey \
  domain='example.com' \
  key_id='12345'
```

<a id="dnssec-export-zone-key"></a>
### `DNSSEC::export_zone_key` — Export DNSSEC security key

`GET /execute/DNSSEC/export_zone_key` · RW · rollback: none · since cPanel 84

This function exports a DNSSEC security key. Important: When you disable the [DNS](https://go.cpanel.net/serverroles) role, the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The security key's domain.
- `key_id` · **required** · integer · e.g. `12345` — The security key's ID.

**Returns** `data`: object

- `domain` (string <domain>) — The security key's domain.
- `key_content` (string) — The content of the key, which includes the algorithm.
- `key_id` (integer) — The security key's ID.
- `key_tag` (integer) — The security key's internal identifier.
- `key_type` (string (`CSK`, `KSK`, `ZSK`)) — The security key's signing type.; `CSK` - Combined Signing Key.; `KSK` - Key Signing Key.; `ZSK` - Zone Signing Key.
- `success` (integer (`0`, `1`)) — Whether the function succeeded.; `1` - The function succeeded.; `0` - The function failed.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  export_zone_key \
  domain='example.com' \
  key_id='12345'
```

<a id="dnssec-fetch-ds-records"></a>
### `DNSSEC::fetch_ds_records` — Return domain's DS records

`GET /execute/DNSSEC/fetch_ds_records` · RO · rollback: none · since cPanel 82

This function fetches a domain's Delegation of Signing (DS) records. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> — The domain from which to fetch DS records. Note: To enable DNSSEC on multiple domains, increment the parameter name. For example: `domain-0`, `domain-1`, `domain-2`.

**Returns** `data`: object

- `additionalProperties` (object) — An object containing the domain's DS record information.
  - `keys` (object) — The DS keys on the requested domain.
  - `nsec_details` (object) — An object containing the [Next Secure Record](https://tools.ietf.org/html/rfc4470) (NSEC) information for the selected domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  fetch_ds_records \
  domain='example.com'
```

<a id="dnssec-import-zone-key"></a>
### `DNSSEC::import_zone_key` — Add DNSSEC security key

`GET /execute/DNSSEC/import_zone_key` · RW · rollback: none · since cPanel 84

This function imports a DNSSEC security key. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The security key's domain.
- `key_data` · **required** · string — The security key data that the [`pdnsutil`](https://doc.powerdns.com/authoritative/manpages/pdnsutil.1.html) utility's `export-zone-key` call returns.
- `key_type` · **required** · string (`ksk`, `zsk`) · e.g. `ksk` — The security key's type.; `ksk`; `zsk`

**Returns** `data`: object

- `domain` (string <domain>) — The domain for which the system imported the zone key.
- `error` (string) — An error message that describes why the system could not import the security key.
- `new_key_id` (string) — The security key's ID.
- `success` (integer (`0`, `1`)) — Whether the system imported the security key.; `1` - The system imported the security key.; `0` - The system **failed** to import the security key.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  import_zone_key \
  domain='example.com' \
  key_type='ksk' \
  key_data=$'Private-key-format:%20v1.2%0AAlgorithm:%2013%20\\(ECDSAP256SHA256\\)%0APrivateKey:%20xCM281KtWE9oCsUX8fP1hDZ02/X7JCjp4QZA/DZjfX0=%0A%0A'
```

<a id="dnssec-remove-zone-key"></a>
### `DNSSEC::remove_zone_key` — Remove DNSSEC security key

`GET /execute/DNSSEC/remove_zone_key` · RW · rollback: none · since cPanel 84

This function removes a DNSSEC security key. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The security key's domain.
- `key_id` · **required** · integer · e.g. `1` — The security key's ID.

**Returns** `data`: object

- `domain` (string <domain>) — The domain for which the system removed a security key.
- `error` (string) — An error message that describes why the system could not remove the security key.
- `key_id` (string) — The security key's ID.
- `success` (integer (`1`, `0`)) — Whether the system removed the security key.; `1` — The system removed the security key.; `0` — The system failed to remove the security key.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  remove_zone_key \
  domain='example.com' \
  key_id='1'
```

<a id="dnssec-set-nsec3"></a>
### `DNSSEC::set_nsec3` — Update domain to use NSEC3

`GET /execute/DNSSEC/set_nsec3` · RW · rollback: none · since cPanel 60

This function configures the domain to use [Next Secure Record 3](https://tools.ietf.org/html/rfc4470) (NSEC3) semantics. Important: When you disable the [DNS role](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain on which to enable NSEC3 semantics.
- `nsec3_iterations` · **required** · integer · e.g. `7` — The number of times that the system re-executes the first resource record hash operation.
- `nsec3_narrow` · **required** · integer (`0`, `1`) · e.g. `1` — Whether NSEC3 will operate in Narrow mode or Inclusive mode. In Narrow mode, PowerDNS sends out white lies about the next secure record. Rather than query the resource record in the database, PowerDNS sends the hash plus 1 as the next secure record.; `1` - Narrow mode. * `0` - Inclusive mode.
- `nsec3_opt_out` · **required** · integer (`0`, `1`) · e.g. `0` — Whether the system will create records for all delegations.; `1` - Create records for all delegations.; `0` - Create records **only** for secure delegations. Note: **Only** select `1` if you **must** create records for all delegations.
- `nsec3_salt` · **required** · string <hex> · e.g. `1A2B3C4D5E6F` — The salt value that PowerDNS uses in the hashes. For more information about the salt value, read the [RFC 5155 documentation](https://tools.ietf.org/html/rfc5155). Note: In cPanel & WHM version 132 and later, this parameter also accepts the literal value `-` to indicate no salt value.

**Returns** `data`: object

- `enabled` (object) — Contains the domains for which the system enabled NSEC3.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  set_nsec3 \
  domain='example.com' \
  nsec3_opt_out='0' \
  nsec3_iterations='0' \
  nsec3_narrow='1' \
  nsec3_salt='-'
```

<a id="dnssec-unset-nsec3"></a>
### `DNSSEC::unset_nsec3` — Update domain to use NSEC

`GET /execute/DNSSEC/unset_nsec3` · RW · rollback: none · since cPanel 60

This function configures the domain to use [Next Secure Record](https://tools.ietf.org/html/rfc4470) (NSEC) semantics instead of Next Secure Record 3 (NSEC3) semantics. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The domain on which to disable NSEC3 semantics and use NSEC semantics.

**Returns** `data`: object

- `disabled` (object) — A list of the domains for which the system disabled NSEC3.
  - `additionalProperties` (integer (`1`, `0`)) — Whether the system disabled NSEC3 on the domain.; `1` — Disabled.; `0` — The system failed to disable NSEC3.

```bash
uapi --output=jsonpretty \
  --user=username \
  DNSSEC \
  unset_nsec3 \
  domain='example.com'
```

## Dynamic DNS

<a id="dynamicdns-create"></a>
### `DynamicDNS::create` — Create Dynamic DNS domain

`GET /execute/DynamicDNS/create` · RW · rollback: none · since 82

This function creates a Dynamic DNS (DDNS) domain. Important: When you disable the [_DNS_ role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `home.example.com` — The fully-qualified domain name to create as a DDNS domain.
- `description` · optional · string · e.g. `Home network` — A human-readable string that describes the domain.

**Returns** `data`: object — Information about the newly-created DDNS domain.

- `created_time` (integer <unix_timestamp>) — The creation time of the Dynamic DNS domain.
- `id` (string) — The DDNS domain’s ID.

```bash
uapi --output=jsonpretty \
  --user=username \
  DynamicDNS \
  create \
  domain='home.example.com'
```

<a id="dynamicdns-delete"></a>
### `DynamicDNS::delete` — Delete Dynamic DNS domain

`GET /execute/DynamicDNS/delete` · RW · rollback: none · since 82

This function deletes an existing Dynamic DNS (DDNS) domain. Important: When you disable the [_DNS_ role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `id` · **required** · string · e.g. `ggiugyxxjwnkmqtwysgmvrurplmafxpq` — The DDNS domain’s ID.

**Returns** `data`: object — Information about the deletion.

- `deleted` (number (`0`, `1`)) — Whether a DDNS domain with the given ID existed for deletion.; `0` - No DDNS domain with the given ID existed.; `1` - A DDNS domain with the given ID existed but is now deleted.

```bash
uapi --output=jsonpretty \
  --user=username \
  DynamicDNS \
  delete \
  id='ggiugyxxjwnkmqtwysgmvrurplmafxpq'
```

<a id="dynamicdns-list"></a>
### `DynamicDNS::list` — Return Dynamic DNS domains

`GET /execute/DynamicDNS/list` · RO · since 82

This function lists the user’s Dynamic DNS (DDNS) domains. Important: When you disable the [_DNS_ role](https://go.cpanel.net/serverroles), the system disables this function.

**Returns** `data`: array of object — The user’s DDNS domains.

- *(array of objects)*
  - `created_time` (integer <unix_timestamp>) — The DDNS domain’s creation time.
  - `description` (string) — A user-editable string that describes the DDNS domain.
  - `domain` (string <domain>) — The domain.
  - `id` (string) — The domain’s DDNS ID.
  - `last_run_times` (array of integer <unix_timestamp>) — The most recent times when the web call ran.
  - `last_update_time` (integer <unix_timestamp>) — The most recent update time for the DDNS domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  DynamicDNS \
  list
```

<a id="dynamicdns-recreate"></a>
### `DynamicDNS::recreate` — Update Dynamic DNS domain ID

`GET /execute/DynamicDNS/recreate` · RW · rollback: none · since 82

This function gives a new, randomly-generated ID to an existing Dynamic DNS (DDNS) domain. Important: When you disable the [_DNS_ role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `id` · **required** · string · e.g. `ggiugyxxjwnkmqtwysgmvrurplmafxpq` — The DDNS domain’s ID.

**Returns** `data`: object — Information about the DDNS domain.

- `id` (string) — The DDNS domain’s new ID.

```bash
uapi --output=jsonpretty \
  --user=username \
  DynamicDNS \
  recreate \
  id='ggiugyxxjwnkmqtwysgmvrurplmafxpq'
```

<a id="dynamicdns-set-description"></a>
### `DynamicDNS::set_description` — Update Dynamic DNS domain description

`GET /execute/DynamicDNS/set_description` · RW · rollback: none · since 82

This function sets the description on a user’s Dynamic DNS (DDNS) domain. Important: When you disable the [_DNS_ role](https://go.cpanel.net/serverroles), the system disables this function.

**Parameters**

- `description` · **required** · string · e.g. `Home network` — A human-readable string that describes the domain.
- `id` · **required** · string · e.g. `ggiugyxxjwnkmqtwysgmvrurplmafxpq` — The DDNS domain’s ID.

```bash
uapi --output=jsonpretty \
  --user=username \
  DynamicDNS \
  set_description \
  id='ggiugyxxjwnkmqtwysgmvrurplmafxpq' \
  description='Home network'
```

## Email DNS Settings

<a id="email-add-mx"></a>
### `Email::add_mx` — Create mail exchanger record

`GET /execute/Email/add_mx` · RW · rollback: none · since cPanel 11.42

This function creates a Mail Exchanger (MX) record. For more information about MX record settings, read our [Email Routing Configuration](https://go.cpanel.net/whmdocsEmailRoutingConfiguration) documentation. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The new mail exchanger's domain.
- `exchanger` · **required** · string <domain> · e.g. `mail.example.com` — The new mail exchanger's name.
- `priority` · **required** · integer · e.g. `5` — The new mail exchanger's [priority value](https://go.cpanel.net/whmdocsEditMXEntry). Note: It is common practice to set a priority value that is divisible by five.
- `alwaysaccept` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether the mail exchanger accepts all mail for the domain.; `1` — The mail exchanger always accepts mail.; `0` — The mail exchanger does **not** always accept mail.

**Returns** `data`: object

- `checkmx` (object) — An object of the mail exchanger's data.
  - `changed` (integer (`0`, `1`)) — Whether a change occurred during the function.; `1` - Change occurred.; `0` - **No** change.
  - `detected` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto`; `local`; `secondary`; `remote`
  - `isprimary` (integer (`0`, `1`)) — Whether the mail exchanger is the primary mail exchanger.; `1` - Primary.; `0` - **Not** primary.
  - `issecondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` - Secondary.; `0` - **Not** secondary.
  - `local` (integer (`0`, `1`)) — Whether the mail exchanger is a local exchanger.; `1` - Local.; `0` - **Not** local.
  - `mxcheck` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto`; `local`; `secondary`; `remote`
  - `remote` (integer (`0`, `1`)) — Whether the mail exchanger is a remote exchanger.; `1` - Remote.; `0` - **Not** remote.
  - `secondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` - Secondary.; `0` - **Not** secondary.
  - `warnings` (array of string) — Warning messages, if any exist.
- `results` (string) — A message of success, or an error message.; A message of success that begins with `Added entry:`.; An error message.
- `status` (integer (`0`, `1`)) — Whether the function succeeded.; `1` - Success.; `0` - Failure.
- `statusmsg` (string) — A message of success, or an error message.; A message of success that begins with `Added entry:`.; An error message.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  add_mx \
  domain='example.com' \
  exchanger='mail.example.com' \
  priority='5'
```

<a id="email-change-mx"></a>
### `Email::change_mx` — Update mail exchanger record

`GET /execute/Email/change_mx` · RW · rollback: none · since cPanel 11.42

This function creates a Mail Exchanger (MX) record. For more information about MX record settings, read our [Email Routing Configuration](https://go.cpanel.net/whmdocsEmailRoutingConfiguration) documentation. Important: When you disable the [*Receive Mail* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The mail exchanger's domain.
- `exchanger` · **required** · string <domain> · e.g. `mail.example.com` — The mail exchanger's name.
- `oldexchanger` · **required** · string <domain> · e.g. `mail.example.com` — The mail exchanger's current name.
- `priority` · **required** · integer · e.g. `15` — The mail exchanger's new [priority value](https://go.cpanel.net/whmdocsEditMXEntry). Note: Common practice sets a priority value divisible by five.
- `alwaysaccept` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Whether the mail exchanger accepts all mail for the domain.; `1` — The mail exchanger always accepts mail.; `0` — The mail exchanger does **not** always accept mail.
- `oldpriority` · optional · integer · e.g. `5` — The mail exchanger's current priority value. If multiple MX entries match the `oldexchanger` value, the system uses this parameter to find the correct entry.

**Returns** `data`: object

- `checkmx` (object) — An object of the mail exchanger's data.
  - `changed` (integer (`0`, `1`)) — Whether a change occurred during the function.; `1` - Change occurred.; `0` - **No** change.
  - `detected` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto`; `local`; `secondary`; `remote`
  - `isprimary` (integer (`0`, `1`)) — Whether the mail exchanger is the primary mail exchanger.; `1` - Primary.; `0` - **Not** primary.
  - `issecondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` - Secondary.; `0` - **Not** secondary.
  - `local` (integer (`0`, `1`)) — Whether the mail exchanger is a local exchanger.; `1` - Local.; `0` - **Not** local.
  - `mxcheck` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto`; `local`; `secondary`; `remote`
  - `remote` (integer (`0`, `1`)) — Whether the mail exchanger is a remote exchanger.; `1` - Remote.; `0` - **Not** remote.
  - `secondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` - Secondary.; `0` - **Not** secondary.
  - `warnings` (array of string) — Warning messages, if any exist.
- `results` (string) — A message of success, or an error message.; A message of success that begins with `Added entry:`.; An error message.
- `status` (integer (`0`, `1`)) — Whether the function succeeded.; `1` - Success.; `0` - Failure.
- `statusmsg` (string) — A message of success, or an error message.; A message of success that begins with `Added entry:`.; An error message.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  change_mx \
  domain='example.com' \
  exchanger='mail.example.com' \
  oldexchanger='mail.example.com' \
  priority='15'
```

<a id="email-delete-mx"></a>
### `Email::delete_mx` — Delete mail exchanger record

`GET /execute/Email/delete_mx` · RW · rollback: none · since cPanel 11.42

This function deletes a Mail Exchanger (MX) record. For more information about MX record settings, read our [Email Routing Configuration](https://go.cpanel.net/whmdocsEmailRoutingConfiguration) documentation. Important: When you disable the [DNS role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The mail exchanger's domain.
- `exchanger` · **required** · string · e.g. `mail.example.com` — The mail exchanger's name.
- `priority` · **required** · integer · e.g. `15` — The mail exchanger's [priority value](https://go.cpanel.net/whmdocsEditMXEntry). If multiple MX entries match the exchanger value, the system uses this parameter to find the correct entry.

**Returns** `data`: object

- `checkmx` (object) — An object containing the mail exchanger's data.
  - `changed` (integer (`0`, `1`)) — Whether a change occurred during the function.; `1` - Change occurred.; `0` - **No** change.
  - `detected` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto`; `local`; `secondary`; `remote`
  - `isprimary` (integer (`0`, `1`)) — Whether the mail exchanger is the primary mail exchanger.; `1` - Primary.; `0` - **Not** primary.
  - `issecondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` - Secondary.; `0` - **Not** secondary.
  - `local` (integer (`0`, `1`)) — Whether the mail exchanger is a local exchanger.; `1` - Local.; `0` - **Not** local.
  - `mxcheck` (string (`auto`, `local`, `secondary`, `remote`)) — The mail exchanger type.; `auto`; `local`; `secondary`; `remote`
  - `remote` (integer (`0`, `1`)) — Whether the mail exchanger is a remote exchanger.; `1` - Remote.; `0` - **Not** remote.
  - `secondary` (integer (`0`, `1`)) — Whether the mail exchanger is a secondary exchanger.; `1` - Secondary.; `0` - **Not** secondary.
  - `warnings` (string) — Warning messages, if any exist.
- `results` (string) — A message of success, or an error message.; A message of success that begins with `Removed entry:`.; An error message.
- `status` (integer (`0`, `1`)) — Whether the function succeeded.; `1` - Success.; `0` - Failure.
- `statusmsg` (string) — A message of success, or an error message.; A message of success that begins with Added entry.; An error message.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  delete_mx \
  domain='example.com' \
  exchanger='mail.example.com' \
  priority='15'
```

<a id="email-list-mxs"></a>
### `Email::list_mxs` — Return mail exchanger records

`GET /execute/Email/list_mxs` · RO · since cPanel 11.42

This function lists Mail Exchanger (MX) records. Important: When you disable the [*DNS* role](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — The domain to query. If you do **not** use this parameter, the function returns MX records for all of the cPanel account's domains.

**Returns** `data`: array of object

- *(array of objects)*
  - `alwaysaccept` (integer (`0`, `1`)) — Whether the domain's highest-priority mail exchanger accepts local mail.; `1` - Accept local mail.; `0` - Does **not** accept local mail.
  - `detected` (string (`auto`, `local`, `remote`, `secondary`)) — The domain's highest-priority mail exchanger's type.; `auto`; `local`; `remote`; `secondary`
  - `domain` (string <domain>) — The domain name.
  - `entries` (array of object) — An array of objects that contains information about mail exchangers.
    - *(array of objects)*
      - `domain` (string <domain>) — The mail exchanger's domain.
      - `entrycount` (integer) — The mail exchanger's order in the list of priorities.
      - `mx` (string <domain>) — The mail exchanger's name.
      - `priority` (integer) — The mail exchanger's [priority value](https://go.cpanel.net/whmdocsEditMXEntry).
      - `row` (string (`even`, `odd`)) — Whether the mail exchanger is an odd or an even entry.; `even`; `odd`
  - `local` (integer (`0`, `1`)) — Whether the domain's highest priority mail exchanger is a local mail exchanger.; `1` - Local.; `0` - **Not** local.
  - `mx` (string <domain>) — The domain's highest-priority mail exchanger's name.
  - `mxcheck` (string (`auto`, `local`, `remote`, `secondary`)) — The domain's highest-priority mail exchanger's type.; `auto`; `local`; `remote`; `secondary`
  - `remote` (integer (`0`, `1`)) — Whether the domain's highest-priority mail exchanger is remote.; `1` - Remote.; `0` - **Not** remote.
  - `secondary` (integer (`0`, `1`)) — Whether the domain's highest-priority mail exchanger is secondary.; `1` - Secondary.; `0` - **Not** secondary.
  - `status` (integer (`0`, `1`)) — Whether the function succeeded.; `1` - Success.; `0` - Failure.
  - `statusmsg` (string) — A success or error message message.; A success message.; An error message.

```bash
uapi --output=jsonpretty \
  --user=username \
  Email \
  list_mxs
```

<a id="emailauth-apply-dmarc"></a>
### `EmailAuth::apply_dmarc` — Apply DMARC records to domains.

`GET /execute/EmailAuth/apply_dmarc` · RW · rollback: none · since 124

This function applies a DMARC record to the specified domain(s)

**Parameters**

- `policy` · **required** · string — The DMARC record to apply to the requested domains. Note: Visit the following link for more information about the DMARC record specification: https://dmarc.org/resources/specification/
- `domain` · optional · string <domain> — The domain for which to apply the DMARC record. Note: To enable multiple domain DMARC records, duplicate or increment the parameter. For example, to enable DMARC records for three domains, perform either of the following actions: Use the `domain` parameter three times.; Use the `domain`, `domain-1`, and `domain-2` parameters. If you do not include this argument, the system applies the DMARC record to all the user's domains. You cannot use this function to edit temporary domains' DMARC records.

**Returns** `data`: array of object — An array that contains information about the DMARC records applied to domains.

- *(array of objects)*
  - `domain` (string <domain>) — The domain for which the DMARC record was applied.
  - `msg` (string) — The domain's DMARC record status message.
  - `status` (integer (`0`, `1`)) — Whether the system applied a DMARC record to the domain.; `1` - Applied.; `0` - The system did **not** apply a DMARC record.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  apply_dmarc \
  domain='example.com' \
  policy='v=DMARC1; p=reject;'
```

<a id="emailauth-disable-dkim"></a>
### `EmailAuth::disable_dkim` — Remove domains' DKIM records

`GET /execute/EmailAuth/disable_dkim` · RW · rollback: none · since cPanel 78

This function removes the DomainKeys Identified Mail (DKIM) records on the DNS server for one or more domains.

**Parameters**

- `domain` · **required** · string — The domain for which to remove DKIM records on the DNS server. Note: To remove multiple domain DKIM records, duplicate the parameter name. For example, use the `domain=example.com`, `domain=example2.com`, and `domain=example3.com` parameters.

**Returns** `data`: array of object — An array of objects that contain information about the removal of a domain's DKIM record on the DNS server.

- *(array of objects)*
  - `domain` (string <domain>) — The domain for which the system removed the DKIM record.
  - `msg` (string) — Information about the removed DKIM record.
  - `status` (integer (`0`, `1`)) — Whether the system removed the domain's DKIM record on the DNS server.; `1` - The system removed the domain's DKIM record.; `0` - The system did **not** remove the domain's DKIM record.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  disable_dkim \
  domain='example.com'
```

<a id="emailauth-enable-dkim"></a>
### `EmailAuth::enable_dkim` — Enable domains' DKIM records

`GET /execute/EmailAuth/enable_dkim` · RW · rollback: none · since cPanel 78

This function enables DomainKeys Identified Mail (DKIM) records on the DNS server for one or more domains. Note: If a DKIM record does **not** exist on the server, this function will install a new DKIM record.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to enable DKIM records on the DNS server. Note: To enable multiple domain DKIM records, duplicate or increment the parameter. For example, to perform this for three domains, you could: Use the `domain` parameter multiple times.; Use the `domain`, `domain-1`, and `domain-2` parameters.

**Returns** `data`: array of object — An array that contains information about the enabled state of a domain's DKIM records on the DNS server.

- *(array of objects)*
  - `domain` (string <domain>) — The domain for which the system enabled the DKIM record.
  - `msg` (string) — The domain's DKIM record status message.
  - `status` (integer (`0`, `1`)) — Whether the system enabled the domain's DKIM record on the DNS server.; `1` - Enabled.; `0` - The system did **not** enable the domain's DKIM record.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  enable_dkim \
  domain='example.com'
```

<a id="emailauth-ensure-dkim-keys-exist"></a>
### `EmailAuth::ensure_dkim_keys_exist` — Validate domains' DKIM private keys

`GET /execute/EmailAuth/ensure_dkim_keys_exist` · RW · rollback: none · since cPanel 78

This function confirms the validity of a DomainKeys Identified Mail (DKIM) key for one or more domains. Notes:  If an existing DKIM key does **not** meet the server's security requirements, the system replaces the existing DKIM key.; If no DKIM key exists, the system creates a new key for the domain.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to confirm a valid DKIM key exists. Note: To check the DKIM key validity for multiple domains, duplicate the parameter name. For example, use the `domain=example.com`, `domain=example2.com`, and `domain=example3.com` parameters.

**Returns** `data`: array of object — An array of objects that contains information about the domain's DKIM key validity.

- *(array of objects)*
  - `domain` (string <domain>) — The domain for which the system confirmed that a valid DKIM key exists.
  - `msg` (string) — The domain's DKIM key status message.
  - `status` (integer (`0`, `1`)) — Whether the system verified that the domain's DKIM key exists.; `1` - The system verified the existence of the domain's DKIM key.; `0` - The system did **not** verify the existence of the domain's DKIM key.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  ensure_dkim_keys_exist \
  domain='example.com'
```

<a id="emailauth-fetch-dkim-private-keys"></a>
### `EmailAuth::fetch_dkim_private_keys` — Return domains' DKIM private keys

`GET /execute/EmailAuth/fetch_dkim_private_keys` · RW · rollback: none · since cPanel 78

This function returns a domain's installed DKIM private key in [Privacy-Enhanced Mail (PEM)](https://en.wikipedia.org/wiki/Privacy-Enhanced_Mail) format. Warning: We **strongly** recommend that you protect your private key. If others obtain your private DKIM key, they could sign emails and impersonate you as a sender.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to retrieve the installed DKIM private key. Note: To retrieve multiple domain DKIM keys, duplicate the parameter name. For example, use the `domain=example.com`, `domain=example2.com`, and `domain=example3.com` parameters.

**Returns** `data`: array of object — An array of objects that contains information about the domain's DKIM private key.

- *(array of objects)*
  - `domain` (string <domain>) — The queried domain.
  - `pem` (string <pem-private-key>) — The domain's DKIM private key, in PEM format.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  fetch_dkim_private_keys \
  domain='example.com'
```

<a id="emailauth-install-dkim-private-keys"></a>
### `EmailAuth::install_dkim_private_keys` — Add domains' DKIM record keys

`GET /execute/EmailAuth/install_dkim_private_keys` · RW · rollback: none · since cPanel 78

This function installs existing keys for use in a DomainKeys Identified Mail (DKIM) record. This is useful if you do not want the system to generate keys for DKIM records. Note:  This function does **not** update the local DNS server's records.; If the local DNS server is authoritative for the domain's DNS records, use the UAPI `EmailAuth::enable_dkim` function to update the local DNS server's DNS records.; We recommend that you use the UAPI `EmailAuth::install_dkim_private_keys` and `EmailAuth::enable_dkim functions` in a batch UAPI call.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to install a DKIM private key on the local server. Note: To install multiple RSA private keys for multiple domains, duplicate the parameter name. For example, use the `domain=example.com`, `domain=example2.com`, and `domain=example3.com` parameters.
- `key` · **required** · string <pem-private-key> — An RSA key in [Privacy-Enhanced Mail (PEM)](https://en.wikipedia.org/wiki/Privacy-Enhanced_Mail) format. Note: You **must** provide this parameter for each `domain` parameter.

**Returns** `data`: array of object — An array of objects that contains information about the DKIM private key installation to the local server.

- *(array of objects)*
  - `domain` (string <domain>) — The DKIM private key's associated domain.
  - `msg` (string) — The DKIM private key's installation status message.
  - `status` (integer (`0`, `1`)) — Whether the system installed the DKIM private key to the local server.; `1` - The system installed the DKIM private key.; `0` - The system **cannot** install the DKIM private key.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  install_dkim_private_keys \
  domain='example' \
  key='-----BEGIN%20RSA%20PRIVATE%20KEY-----%0aAAAAB3NzaC1yc2EAAAABIwAAAQEA5kSivOqhs0U9ZMN20nxFe27QZ3t0lT2zbH7OSXylKd%0a1rjAjYXGnSXC9j2uaZlemHlptBKVziMJC86ha7Hcj6dVOVrDQ6vF4q34bOCjtKLphQ0IjB%0azVIvqILH9eLJdRaOrS34CmgmPaisrCk5wKVlakygvUfcj3HzaTKS6THyZDGx5shdTpa9lb%0ay8tpOD3JceV7ay4w8r0DipoKPC0OLpvS4EABEeMo9sx8zQEaKv03XygjNCCYtFvxlQQIRG%0alVoL7mPaHSaL3anI05RpNbm/PS+9BhZg+BqNjU4ofHBbfkXk5MiN6M7ieR4Sk5BquccboG%0aF13U5slNgmCEekdt0amw%0a-----END%20RSA%20PRIVATE%20KEY-----%0a'
```

<a id="emailauth-install-spf-records"></a>
### `EmailAuth::install_spf_records` — Add domains' SPF records

`GET /execute/EmailAuth/install_spf_records` · RW · rollback: none · since cPanel 78

This function installs a Sender Policy Framework (SPF) record for a domain on the DNS server.

**Parameters**

- `domain` · **required** · string — The domain for which to install an SPF record on the DNS server. Note: To install multiple SPF records, duplicate the parameter name. For example, use the `domain=example.com`, `domain=example2.com`, and `domain=example3.com` parameters.
- `record` · **required** · string — An SPF record. Note: You **must** provide this parameter for each `domain` parameter.

**Returns** `data`: array of object — An array of objects that contains information about the domain's SPF record installation to the DNS server.

- *(array of objects)*
  - `domain` (string <domain>) — The SPF record's associated domain on the DNS server.
  - `msg` (string) — The SPF record's installation status to the DNS server.
  - `status` (integer (`0`, `1`)) — Whether the system installed the SPF record to the DNS server.; `1` - The system installed the SPF record on the DNS server.; `0` - The system **cannot** install the SPF record on the DNS server.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  install_spf_records \
  domain='example.com' \
  record='"v=spf1 ip4:10.0.0.1 %2Ba %2Bmx %2Bip4:10.0.0.2 %2Bip4:10.0.0.3 -all"'
```

<a id="emailauth-remove-dmarc"></a>
### `EmailAuth::remove_dmarc` — Remove DMARC record from domain(s)

`GET /execute/EmailAuth/remove_dmarc` · RW · rollback: none · since 124

This function removes the DMARC record for domains.

**Parameters**

- `domain` · optional · string — The domain from which to remove the DMARC record. Note: If you do not include this argument, the system will remove **all** DMARC records from **all** domains owned by the user. To remove multiple domain DMARC records, duplicate the parameter name. For example, use the `domain=example.com`, `domain=example2.com`, and `domain=example3.com` parameters. You **cannot** remove DMARC records on temporary domains.

**Returns** `data`: array of object — An array of objects that contain information about the removed DMARC records.

- *(array of objects)*
  - `domain` (string <domain>) — The domain for which the DMARC record was removed.
  - `msg` (string) — Information about the removed DMARC record.
  - `status` (integer (`0`, `1`)) — Whether the system removed the domain's DMARC record.; `1` - The system removed the domain's DMARC record.; `0` - The system did **not** remove the domain's DMARC record.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  remove_dmarc \
  domain='example.com'
```

<a id="emailauth-validate-current-dkims"></a>
### `EmailAuth::validate_current_dkims` — Validate domains' DKIM records

`GET /execute/EmailAuth/validate_current_dkims` · RO · since cPanel 78

This function retrieves and checks the DomainKeys Identified Mail (DKIM) records for one or more domains.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to check the DKIM records.

**Returns** `data`: array of object — An array that contains information about the domain's DKIM records.

- *(array of objects)*
  - `domain` (string <domain>) — The domain that the function used to check the DKIM record.
  - `error` (string) — A message that details the reason why the DNS lookup failed.
  - `expected` (string) — The DKIM record's contents.
  - `records` (array of object) — The domain's DNS DKIM TXT records.
    - *(array of objects)*
      - `current` (string) — The domain's DKIM TXT record data contents.
      - `reason` (string) — The reason why the DKIM TXT record is not correct, if one exists.
      - `state` (string (`VALID`, `MISMATCH`, `PERMFAIL`)) — The DKIM TXT record's status: `VALID` - The DKIM TXT record matches the local server's public key.; `MISMATCH` - The DKIM TXT record does not match the local server's public key.; `PERMFAIL` - Multiple DKIM TXT records f
  - `state` (string (`VALID`, `MALFORMED`, `MISMATCH`, `MISSING`, `MULTIPLE`, `NOPUB`, `ERROR`)) — The domain's DKIM record status.
  - `validity_cache_update` (string (`set`, `unset`, `valid`, `invalid`, `none`, `error`)) — The result of the DKIM record's validity cache update operation: `set` The domain is invalid but passed its validity check.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  validate_current_dkims \
  domain='example.com'
```

<a id="emailauth-validate-current-dmarcs"></a>
### `EmailAuth::validate_current_dmarcs` — Validate domains' DMARC records

`GET /execute/EmailAuth/validate_current_dmarcs` · RO · since cPanel 124

This function checks the validity of the current DMARC record for one or more domains.

**Parameters**

- `domain` · optional · string <domain> — The domain for which to check the DMARC record. Note: If you do not include this argument, the system will validate DMARC records for all domains owned by the user.

**Returns** `data`: array of object — An array that contains information about the domain's DMARC records.

- *(array of objects)*
  - `domain` (string <domain>) — The target domain of the DMARC policy.
  - `error` (string) — A message that details either why the DNS lookup failed, or if there is a SPF/DKIM failure.
  - `record` (string) — The domain's DMARC TXT record.
  - `state` (string (`VALID`, `MALFORMED`, `DKIM_SPF_ERROR`, `DKIM_ERROR`, `SPF_ERROR`, `MISSING`, `DNS_ERROR`)) — The domain's DMARC record status.
  - `subdomain` (string <domain>) — The domain that the function used to check the DMARC record.
  - `suggested` (string) — The recommended DMARC policy.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  validate_current_dmarcs \
  domain='example.com'
```

<a id="emailauth-validate-current-ptrs"></a>
### `EmailAuth::validate_current_ptrs` — Validate domains' PTR records

`GET /execute/EmailAuth/validate_current_ptrs` · RO · since cPanel 78

This function validates the pointer records (PTR) for IPv4 and IPv6 addresses that the account's domains send mail from. It retrieves the PTR records for each IP address and determines which of the domain's IP addresses send mail. It then validates the PTR records for each IP address and validates the A or AAAA records pointing to each domain. This function also ensures that at least one of that domain's A or AAAA records points back to the IP address.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to validate the PTR records.

**Returns** `data`: array of object — An array that contains information about the account's PTR records.

- *(array of objects)*
  - `arpa_domain` (string) — The IP address used to perform a reverse DNS (rDNS) lookup.
  - `domain` (string <domain>) — The queried domain.
  - `error` (string) — A mmessage that details the reason why the domain's IP address validation failed.
  - `helo` (string <domain>) — The hostname that the domain uses to identify itself to remote SMTP servers.
  - `ip_address` (string) — The IP address.
  - `ip_version` (integer (`4`, `6`)) — The IP version number.; 4; 6 Note: The function does **not** return this value for a domain with an invalid IP address.
  - `nameservers` (array of string <domain>) — The authoritative nameservers for the domain's PTR record.
  - `ptr_records` (array of object) — The domain's PTR records.
    - *(array of objects)*
      - `domain` (string <domain>) — The fully-qualified domain name (FQDN) that a PTR record points to.
      - `forward_records` (array of string) — A list of IP addresses that the domain resolves to for A (IPv4) and AAAA (IPv6) records.
      - `state` (string (`VALID`, `MISSING_FWD`, `FWD_MISMATCH`)) — The state of the domain's PTR record.; `VALID` - The PTR record is valid.; `MISSING_FWD` - The PTR points to a domain without an A or AAAA record.; `FWD_MISMATCH` - The PTR record points to a domain without an A or AAAA 
  - `state` (string (`ERROR`, `IP_IS_PRIVATE`, `VALID`, `MISSING_PTR`, `PTR_MISMATCH`)) — Whether the PTR records are valid for the domain.; `ERROR` - The domain's IP address is invalid.

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  validate_current_ptrs \
  domain='example.com'
```

<a id="emailauth-validate-current-spfs"></a>
### `EmailAuth::validate_current_spfs` — Validate domains' SPF records

`GET /execute/EmailAuth/validate_current_spfs` · RO · since cPanel 78

This function retrieves the the Sender Policy Framework (SPF) records for one or more domains.

**Parameters**

- `domain` · **required** · string <domain> — The domain for which to check the `SPF` records.

**Returns** `data`: array of object — A list of information about a domain's SPF records.

- *(array of objects)*
  - `domain` (string <domain>) — The queried domain.
  - `error` (string) — A message that details the reason why the DNS lookup failed.
  - `expected` (string) — The SPF record for the domain in the DNS.
  - `ip_address` (string) — The domain's IP address.
  - `ip_version` (integer (`4`, `6`)) — The IP address version.; `4`; `6`
  - `records` (array of object) — The SPF records of the domain's DNS.
    - *(array of objects)*
      - `current` (string) — The SPF record's contents.
      - `reason` (string) — The reason why the SPF record is **not** correct, if one exists.
      - `state` (string (`PASS`, `NEUTRAL`, `FAIL`, `SOFTFAIL`, `TEMPERROR`, `PERMERROR`)) — The SPF record's status: `PASS` - The `SPF` record confirms that the `ip_address` value is a valid sender.; `NEUTRAL` - The current `SPF` record configuration does not determine the `ip_address` value's validity.; `FAIL`
  - `state` (string (`VALID`, `MISMATCHED`, `MULTIPLE`, `MISSING`, `ERROR`)) — The SPF record's status: `VALID` - A single `SPF TXT` record exists in the domain's DNS with the correct `ip_address` value or redirect mechanism.; `MISMATCHED` - An `SPF TXT` record exists for the domain that does **not

```bash
uapi --output=jsonpretty \
  --user=username \
  EmailAuth \
  validate_current_spfs \
  domain='example.com'
```

## ZoneEdit

<a id="zoneedit-resetzone"></a>
### `ZoneEdit::resetzone` — Reset a DNS zone to the server defaults

`GET /execute/ZoneEdit/resetzone` · RW · rollback: none · since cPanel 138

This function resets a domain's [DNS](https://go.cpanel.net/dnsrecords) zone to the server's default zone template. Important:  This action **destroys** every custom record in the zone. Records that the zone template does not recreate, for example `MX`, `TXT` and `CNAME` records added by hand, are lost.; The reset outcome is reported in the `data` field rather than in the `status` field. A call can succeed at the API level while the zone rebuild itself fails, so check the `result.status` field in the returned data. When you disable the [DNS role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain whose DNS zone to reset.

```bash
uapi --output=jsonpretty \
  --user=username \
  ZoneEdit \
  resetzone \
  domain='example.com'
```

