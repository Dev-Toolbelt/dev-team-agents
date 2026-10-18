<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — SSL Certificates

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Verify Domain Ownership**: [`DCV::check_domains_via_dns`](#dcv-check-domains-via-dns), [`DCV::check_domains_via_http`](#dcv-check-domains-via-http), [`DCV::ensure_domains_can_pass_dcv`](#dcv-ensure-domains-can-pass-dcv)
- **Auto-generated SSL Certificates**: [`SSL::add_autossl_excluded_domains`](#ssl-add-autossl-excluded-domains), [`SSL::get_autossl_excluded_domains`](#ssl-get-autossl-excluded-domains), [`SSL::get_autossl_problems`](#ssl-get-autossl-problems), [`SSL::get_autossl_renewal_status`](#ssl-get-autossl-renewal-status), [`SSL::is_autossl_check_in_progress`](#ssl-is-autossl-check-in-progress), [`SSL::remove_autossl_excluded_domains`](#ssl-remove-autossl-excluded-domains), [`SSL::set_autossl_excluded_domains`](#ssl-set-autossl-excluded-domains), [`SSL::start_autossl_check`](#ssl-start-autossl-check)
- **cPanel Account SSL Management**: [`SSL::can_ssl_redirect`](#ssl-can-ssl-redirect), [`SSL::check_shared_cert`](#ssl-check-shared-cert), [`SSL::delete_ssl`](#ssl-delete-ssl), [`SSL::fetch_best_for_domain`](#ssl-fetch-best-for-domain), [`SSL::fetch_cert_info`](#ssl-fetch-cert-info), [`SSL::fetch_certificates_for_fqdns`](#ssl-fetch-certificates-for-fqdns), [`SSL::fetch_key_and_cabundle_for_certificate`](#ssl-fetch-key-and-cabundle-for-certificate), [`SSL::find_certificates_for_key`](#ssl-find-certificates-for-key), [`SSL::find_csrs_for_key`](#ssl-find-csrs-for-key), [`SSL::get_cabundle`](#ssl-get-cabundle), [`SSL::get_cn_name`](#ssl-get-cn-name), [`SSL::installed_host`](#ssl-installed-host), [`SSL::installed_hosts`](#ssl-installed-hosts), [`SSL::list_certs`](#ssl-list-certs), [`SSL::list_csrs`](#ssl-list-csrs), [`SSL::list_keys`](#ssl-list-keys), [`SSL::list_ssl_items`](#ssl-list-ssl-items), [`SSL::rebuildssldb`](#ssl-rebuildssldb), [`SSL::set_default_key_type`](#ssl-set-default-key-type), [`SSL::toggle_ssl_redirect_for_domains`](#ssl-toggle-ssl-redirect-for-domains)
- **SSL Certificate Management**: [`SSL::delete_cert`](#ssl-delete-cert), [`SSL::delete_csr`](#ssl-delete-csr), [`SSL::delete_key`](#ssl-delete-key), [`SSL::generate_cert`](#ssl-generate-cert), [`SSL::generate_csr`](#ssl-generate-csr), [`SSL::generate_key`](#ssl-generate-key), [`SSL::install_ssl`](#ssl-install-ssl), [`SSL::set_cert_friendly_name`](#ssl-set-cert-friendly-name), [`SSL::set_csr_friendly_name`](#ssl-set-csr-friendly-name), [`SSL::set_key_friendly_name`](#ssl-set-key-friendly-name), [`SSL::set_primary_ssl`](#ssl-set-primary-ssl), [`SSL::show_cert`](#ssl-show-cert), [`SSL::show_csr`](#ssl-show-csr), [`SSL::show_key`](#ssl-show-key), [`SSL::upload_cert`](#ssl-upload-cert), [`SSL::upload_key`](#ssl-upload-key)
- **SNI Email Settings**: [`SSL::disable_mail_sni`](#ssl-disable-mail-sni), [`SSL::enable_mail_sni`](#ssl-enable-mail-sni), [`SSL::is_mail_sni_supported`](#ssl-is-mail-sni-supported), [`SSL::is_sni_supported`](#ssl-is-sni-supported), [`SSL::mail_sni_status`](#ssl-mail-sni-status), [`SSL::rebuild_mail_sni_config`](#ssl-rebuild-mail-sni-config)

## Verify Domain Ownership

<a id="dcv-check-domains-via-dns"></a>
### `DCV::check_domains_via_dns` — Verify domain ownership via DNS

`POST /execute/DCV/check_domains_via_dns` · RW · rollback: none · since cPanel 74

This function checks whether the account's domains can pass Domain Control Validation (DCV) via a DNS request.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain or domains to check. Note: To check multiple domains, increment the parameter name. For example, `domain-0`, `domain-1`, and `domain-2`.

**Returns** `data`: array of object — An array of objects containing the results from each `domain` parameter’s DCV check.

- *(array of objects)*
  - `dcv_string` (string) — The expected value of the queried DNS record.
  - `domain` (string <domain>) — The domain that the system verified.
  - `failure_reason` (string) — A message that contains the reason why the DCV check failed.
  - `query_results` (array of string) — The strings that the DNS query returned.
  - `succeeded` (integer (`1`, `0`)) — Whether the DCV check succeeded.; `1` - At least one of the `query_results` values equals the `dcv_string` value.; `0` - None of the `query_results` values equal the `dcv_string` value.
  - `zone` (string <domain>) — The altered and queried DNS zone name.

```bash
uapi --output=jsonpretty \
  --user=username \
  DCV \
  check_domains_via_dns \
  domain='example.com'
```

<a id="dcv-check-domains-via-http"></a>
### `DCV::check_domains_via_http` — Verify domain ownership via HTTP

`GET /execute/DCV/check_domains_via_http` · RW · rollback: none · since cPanel 60

This function checks whether the account's domains can pass Domain Control Validation (DCV) via an HTTP request.

**Parameters**

- `domain` · **required** · string <domain> — The domains to check. Note: To check more than one domain, repeat or increment the parameter name. For example, `domain-1`, `domain-2`, and `domain-3`.
- `dcv_file_allowed_characters` · optional · array of string · default `['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',` — An array of characters that the certificate provider allows in the DCV check file's filename.
- `dcv_file_extension` · optional · string · default `` · e.g. `txt` — The DCV check file extension that the certificate provider requires.
- `dcv_file_random_character_count` · optional · integer · default `100` · e.g. `32` — The number of characters that the certificate provider allows in the DCV check file's filename.
- `dcv_file_relative_path` · optional · string · default `.well-known/pki-validation` · e.g. `.well-known/pki-validation` — The DCV check file's file path, relative to the domain's document `root` directory.
- `dcv_max_redirects` · optional · integer · default `None` · e.g. `2` — The number of domain redirects the system permits the DCV check to follow. The function checks the provider's supported number of redirects. It will then return the `redirect` array of objects for the passed value, plus one. This ensures the function will display any redirects causing DCV failures, if any exist. Note:  If you pass a `0` value, this function does **not** limit the number of redirect returns.; Use the `Market::get_provider_specific_dcv_constraints` UAPI function to list a provider's supported number of redirects.
- `dcv_user_agent_string` · optional · string · e.g. `SECTIGO+DCV` — The [user agent string](https://wikipedia.org/wiki/User_agent) that the system uses for the imitated local DCV check. Important: The default value can change at any time.

**Returns** `data`: array of object — An array of objects that contains results from each domain's DCV check.

- *(array of objects)*
  - `failure_reason` (string) — The reason that the DCV check failed.; `null` — The domain passed the DCV check.
  - `redirects` (array of object) — An array of objects that contains DCV check redirect information.
    - *(array of objects)*
      - `content` (string) — A message that explains why the function failed.
      - `headers` (object) — An object that contains the [HTTP::Tiny](http://search.cpan.org/~dagolden/HTTP-Tiny-0.070/lib/HTTP/Tiny.pm) CPAN module returns.
      - `protocol` (string) — The URL's HTTP protocol.
      - `reason` (string) — The HTTP response status message.
      - `redirects` (array of object) — An array of objects containing the redirects, if the value exists.
      - `status` (integer) — The [HTTP response status code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes).
      - `success` (integer (`0`, `1`) or string (``)) — Whether the server returns a [2XX HTTP status code](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#2xx_Success).; `1` — The server returns a 2XX status code.; `0` or an empty string — The server does **not** ret
      - `url` (string <url>) — The URL that the function searches for the DCV file.
  - `redirects_count` (integer) — The number of HTTP redirects that the DCV check follows.

```bash
uapi --output=jsonpretty \
  --user=username \
  DCV \
  check_domains_via_http \
  domain='example.com'
```

<a id="dcv-ensure-domains-can-pass-dcv"></a>
### `DCV::ensure_domains_can_pass_dcv` — Verify domain ownership

`GET /execute/DCV/ensure_domains_can_pass_dcv` · RW · rollback: none · since cPanel 56 · **DEPRECATED**

This function indicates whether the account's domains can pass a Domain Control Validation (DCV) check. Warning: We deprecated this function. Use UAPI's `DCV::check_domains_via_http` function.

**Parameters**

- `domain` · **required** · string — The domains to check. Note: To check multiple domains, duplicate or increment the parameter name. For example, `domain-1`, `domain-2`, and `domain-3`.

**Returns** `data`: array of string — A list of results from each domain parameter's DCV check.; `null` — The domain passes the DCV check.

```bash
uapi --output=jsonpretty \
  --user=username \
  DCV \
  ensure_domains_can_pass_dcv \
  domain='example.com'
```

## Auto-generated SSL Certificates

<a id="ssl-add-autossl-excluded-domains"></a>
### `SSL::add_autossl_excluded_domains` — Disable AutoSSL for domains

`GET /execute/SSL/add_autossl_excluded_domains` · RW · rollback: none · since cPanel 66

This function disables AutoSSL for the domains that you specify. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domains` · **required** · string <domain> · e.g. `example.com,example2.com` — A comma-separated list of domains for which to disable AutoSSL. Note: For browser-based calls, use a URI encoded comma (`%2C`).

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  add_autossl_excluded_domains \
  domains='example.com,example2.com'
```

<a id="ssl-get-autossl-excluded-domains"></a>
### `SSL::get_autossl_excluded_domains` — Return AutoSSL disabled domains

`GET /execute/SSL/get_autossl_excluded_domains` · RO · since cPanel 66

This function lists the domains with AutoSSL disabled.

**Returns** `data`: array of object — An array of objects that include domain's AutoSSL information.

- *(array of objects)*
  - `excluded_domain` (string) — A domain that has AutoSSL disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  get_autossl_excluded_domains
```

<a id="ssl-get-autossl-problems"></a>
### `SSL::get_autossl_problems` — Return domains with AutoSSL problems

`GET /execute/SSL/get_autossl_problems` · RO · since cPanel 68

This function retrieves a list of domains that possess AutoSSL problems. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `domain` (string <domain>) — The certificate's hostname.
  - `problem` (string) — text description of the problem.
  - `time` (string <ISO-8601 Date Time>) — When the problem occurred.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  get_autossl_problems
```

<a id="ssl-get-autossl-renewal-status"></a>
### `SSL::get_autossl_renewal_status` — Return AutoSSL renewal status for a domain

`GET /execute/SSL/get_autossl_renewal_status` · RO · since cPanel 134

This function returns the AutoSSL renewal status for a domain. It indicates whether AutoSSL is active, the domain is excluded, the domain has DCV problems, and whether the certificate will auto-renew.

**Parameters**

- `domain` · **required** · string · e.g. `example.com` — The fully qualified domain name to check.

**Returns** `data`: object — An object that contains the AutoSSL renewal status for the domain.

- `has_problems` (integer (`0`, `1`)) — Whether AutoSSL has DCV failures recorded for this domain.
- `is_active` (integer (`0`, `1`)) — Whether an AutoSSL provider is configured on the server.
- `is_excluded` (integer (`0`, `1`)) — Whether the domain is on the user's AutoSSL exclusion list.
- `will_renew` (integer (`0`, `1`)) — Whether AutoSSL will auto-renew the certificate for this domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  get_autossl_renewal_status \
  domain=example.com
```

<a id="ssl-is-autossl-check-in-progress"></a>
### `SSL::is_autossl_check_in_progress` — Return whether AutoSSL check in progress

`GET /execute/SSL/is_autossl_check_in_progress` · RO · since cPanel 68

This function verifies whether the `autossl_check` task is in progress for the current user. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: integer (`0`, `1`) — Whether the `autossl_check` task is in progress for the current user.; `1` - In progress.; `0` - **Not** currently in progress.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  is_autossl_check_in_progress
```

<a id="ssl-remove-autossl-excluded-domains"></a>
### `SSL::remove_autossl_excluded_domains` — Enable AutoSSL for specifed domains

`GET /execute/SSL/remove_autossl_excluded_domains` · RW · rollback: none · since cPanel 66

This function enables AutoSSL for the domains that you specify. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domains` · **required** · string — Enable AutoSSL for this domain.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  remove_autossl_excluded_domains \
  domains='example.com'
```

<a id="ssl-set-autossl-excluded-domains"></a>
### `SSL::set_autossl_excluded_domains` — Disable AutoSSL for specifed domains

`GET /execute/SSL/set_autossl_excluded_domains` · RW · rollback: none · since cPanel 66

This function disables AutoSSL for every domain that you specify. Warning: This function **replaces** the list of any domains that you previously excluded. To add domains to the list of excluded domains, use the UAPI function `SSL::add_autossl_excluded_domains`. Important: When you disable the the [Calendar and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domains` · optional · string · e.g. `example.com,example.net` — A comma-separated list of domains for which to disable AutoSSL. Note: If you do not include this parameter, the function will **enable** AutoSSL for every domain on the account.

**Returns** `data`: object (`None`)

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  set_autossl_excluded_domains
```

<a id="ssl-start-autossl-check"></a>
### `SSL::start_autossl_check` — Start AutoSSL for current user

`GET /execute/SSL/start_autossl_check` · RW · rollback: none · since cPanel 68

This function initiates an [AutoSSL](https://go.cpanel.net/whmdocsManageAutoSSL) check for the user. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and  Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  start_autossl_check
```

## cPanel Account SSL Management

<a id="ssl-can-ssl-redirect"></a>
### `SSL::can_ssl_redirect` — Return whether domains can redirect to secure URL

`GET /execute/SSL/can_ssl_redirect` · RO · since cPanel 80

This function determines whether the system can automatically redirect domains on a cPanel account to use SSL.

**Returns** `data`: integer (`0`, `1`) — Whether the system can automatically redirect the domains to use SSL.; `1` - Can redirect.; `0` - **Cannot** redirect.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  can_ssl_redirect
```

<a id="ssl-check-shared-cert"></a>
### `SSL::check_shared_cert` — Return whether shared SSL certificate exists

`GET /execute/SSL/check_shared_cert` · RO · since cPanel 11.42 · **DEPRECATED**

This function checks whether a shared SSL certificate is associated with the account.

**Returns** `data`: integer (`0`, `1`) — Whether a shared SSL certificate is associated with the account.; `1` - Associated.; `0` - Not associated.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  check_shared_cert
```

<a id="ssl-delete-ssl"></a>
### `SSL::delete_ssl` — Remove SSL for domain

`GET /execute/SSL/delete_ssl` · RW · rollback: none · since cPanel 11.42

This function removes SSL from a domain. Note: This function removes domains from the current certificate to end SSL coverage for those domains. To delete certificates from SSL storage, use the UAPI function `SSL::delete_cert` instead. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, **and** Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  delete_ssl \
  domain='example.com'
```

<a id="ssl-fetch-best-for-domain"></a>
### `SSL::fetch_best_for_domain` — Request best SSL certificate

`GET /execute/SSL/fetch_best_for_domain` · RW · rollback: none · since cPanel 11.42

This function retrieves the best-available certificate for the domain. The function also retrieves the certificate's associated private key and CA bundle, if available. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The domain name.

**Returns** `data`: object

- `cab` (string <pem-certificate>) — The CA bundle's contents (if applicable).
- `crt` (string <pem-certificate>) — The certificate's contents.
- `crt_origin` (string <username>) — The username that generated the certificate.
- `domain` (string <domain>) — The domain that generated the private key.
- `ip` (string <ipv4>) — The IP address.
- `key` (string <pem-private-key>) — The private key.
- `key_origin` (string <username>) — The username that generated the private key.
- `searched_users` (array of string <username>) — The cPanel accounts that the system searched for domain information.
- `status` (integer (`0`, `1`)) — Whether the certificate is active.; `1` - Active.; `0` - Inactive.
- `statusmsg` (string) — The certificate's status.
- `user` (string <username>) — The username that stores the private key.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  fetch_best_for_domain \
  domain='example.com'
```

<a id="ssl-fetch-cert-info"></a>
### `SSL::fetch_cert_info` — Return SSL certificate information

`GET /execute/SSL/fetch_cert_info` · RW · rollback: none · since cPanel 11.42

This function retrieves all of a certificate's available information. Important:  You **must** call either the `friendly_name` or `id` parameter.; When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `friendly_name` · **required** · string · e.g. `TestCert` — The certificate's human readable name.
- `id` · **required** · string — The certificate's ID.

**Returns** `data`: object

- `cabundle` (string <pem-certificate>) — The CA bundle's contents (if applicable).
- `certificate` (string <pem-certificate>) — The certificate's contents.
- `is_self_signed` (integer (`0`, `1`)) — Whether the certificate is self-signed.; `1` - Self-signed.; `0` - **Not** self-signed.
- `key` (string <pem-private-key>) — The private key.
- `subject.commonName_ip` (string <ipv4>) — The IP address.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  fetch_cert_info \
  id='example_com_cb497_a394d_1397249671_d1272da8f13a1fd837493a5ad1f0a0f3' \
  friendly_name='TestCert'
```

<a id="ssl-fetch-certificates-for-fqdns"></a>
### `SSL::fetch_certificates_for_fqdns` — Return SSL certificate information for all FQDN

`GET /execute/SSL/fetch_certificates_for_fqdns` · RW · rollback: none · since cPanel 66

This function retrieves the certificate information for all fully qualified domain names (FQDNs) that the account owns.

**Parameters**

- `domains` · **required** · string — A domain or comma-delimited list of domains for which to retrieve information.

**Returns** `data`: array of object

- *(array of objects)*
  - `cab` (string <pem-certificate>) — The CA bundle's contents.
  - `created` (integer <unix_timestamp>) — When the certificate was created.
  - `crt` (string <pem-certificate>) — The certificate's contents in Base64 PEM format.
  - `domain_is_configured` (integer (`0`, `1`)) — Whether the certificate is installed on the account.; `1` — Installed.; `0` — Not installed.
  - `domains` (array of string) — The domains that the CSR covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `friendly_name` (string) — The certificate's friendly name.
  - `id` (string) — The certificate's identification.
  - `is_self_signed` (integer (`0`, `1`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer.commonName` (string) — The name that issued the certificate.
  - `issuer.organizationName` (string) — The certificate's organization.
  - `issuer_text` (string) — The certificate's issuer information.
  - `key` (string <pem-private-key>) — The private key in Base64 PEM format.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — When the certificate expired.
  - `not_before` (integer <unix_timestamp>) — When the certificate started.
  - `serial` (string) — The certificate's serial number.
  - `signature_algorithm` (string) — The OID of the hash algorithm used to sign the certificate request.
  - `subject.commonName` (string <domain>) — The certificate's common name.
  - `subject_text` (string) — The certificate's subject text information.
  - `validation_type` (string) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validated.; `dv` — Domain Validated.; `null` —  The system could not parse and determine the certificate's validation type.
  - `verify_error` (string) — A message that explains the reason for a verification error.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  fetch_certificates_for_fqdns \
  domains='example.com'
```

<a id="ssl-fetch-key-and-cabundle-for-certificate"></a>
### `SSL::fetch_key_and_cabundle_for_certificate` — Return private key and CA bundle

`POST /execute/SSL/fetch_key_and_cabundle_for_certificate` · RW · rollback: none · since cPanel 11.42

This function extracts the private key and CA bundle information from a certificate. Note: Due to the limited field length of `HTTP GET` method calls, you **must** use the `HTTP POST` method. For this reason, you **cannot** use a cPanel or Webmail session URL to call this function.

**Parameters**

- `certificate` · **required** · string <pem-certificate> — An SSL certificate.

**Request body** (`multipart/form-data`)

- `certificate` (string <pem-certificate>) — The certificate file.

**Returns** `data`: object

- `cab` (string <pem-certificate>) — The CA bundle's contents (if applicable).
- `crt` (string <pem-certificate>) — The certificate's contents.
- `crt_origin` (string <username>) — The username that generated the certificate.
- `domain` (string <domain>) — The domain that generated the private key.
- `ip` (string <ipv4>) — The IP address.
- `key` (string <pem-private-key>) — The private key.
- `key_origin` (string <username>) — The username that generated the private key.
- `searched_users` (array of string <username>) — The users that the system searched for certificate information.
- `status` (integer (`0`, `1`)) — Whether the certificate is active.; `1` - Active.; `0` - Inactive.
- `statusmsg` (string) — The certificate's status.
- `user` (string <username>) — The username that stores the private key.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  SSL \
  fetch_key_and_cabundle_for_certificate
```

<a id="ssl-find-certificates-for-key"></a>
### `SSL::find_certificates_for_key` — Return SSL certificate for private key

`GET /execute/SSL/find_certificates_for_key` · RW · rollback: none · since cPanel 11.42

This function retrieves SSL certificates for a private key. Note: When you call this function, you **must** include either the `id` **or** the `friendly_name` parameter.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestKey` — The key's friendly name.
- `id` · optional · string — The key's ID.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The date the certificate was created.
  - `domains` (array of string <domain>) — A list of the domains that the certificate covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `friendly_name` (string) — The certificate's friendly name.
  - `id` (string) — The certificate's ID.
  - `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer.commonName` (string) — The name that issued the certificate.
  - `issuer.organizationName` (string) — The certificate's organization name.
  - `issuer_text` (string) — The certificate's issuer information.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — The date the certificate expired.
  - `not_before` (integer <unix_timestamp>) — The date the certificate started.
  - `signature_algorithm` (string) — The certificate's signature OID hash algorithm.
  - `subject.commonName` (string) — The certificate's Common Name.
  - `subject_text` (string) — The certificate's subject text information.
  - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validation.; `dv` — Domain Validation.; `null` — The system could not parse and determine the certificate's validation type.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  find_certificates_for_key
```

<a id="ssl-find-csrs-for-key"></a>
### `SSL::find_csrs_for_key` — Return private key's certificate signing requests

`GET /execute/SSL/find_csrs_for_key` · RW · rollback: none · since cPanel 11.42

This function retrieves certificate signing requests (CSR) for a private key. Note: When you call this function, you **must** include either the `id` or the `friendly_name` parameter.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestKey` — The key's friendly name.
- `id` · optional · string — The key's ID.

**Returns** `data`: array of object

- *(array of objects)*
  - `commonName` (string <domain>) — The CSR's common name.
  - `created` (integer <unix_timestamp>) — The date the CSR was created.
  - `domains` (array of string <domain>) — A list of the domains that the CSR covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the CSR's key uses.; `prime256v1`; `secp384r1`; `null` — The CSR's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The CSR's key's ECDSA compressed public point, in hexadecimal format.; `null` — The CSR's key is **not** an ECDSA key.
  - `friendly_name` (string) — The CSR's friendly name.
  - `id` (string) — The CSR's ID.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The CSR's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The CSR's key's modulus, in hexadecimal format.; `null` — The CSR's key is **not** an RSA key.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  find_csrs_for_key
```

<a id="ssl-get-cabundle"></a>
### `SSL::get_cabundle` — Return certificate's CA bundle and hostname

`GET /execute/SSL/get_cabundle` · RO · since cPanel 11.42

This function retrieves a certificate's Certificate Authority (CA) bundle and hostname. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `cert` · **required** · string <pem-certificate> — The certificate's text.

**Returns** `data`: object

- `bundle` (string) — The CA bundle's tag.
- `cab` (string <pem-certificate>) — The CA bundle's contents.
- `domain` (string <domain>) — The certificate's hostname.

```bash
uapi --output=jsonpretty --user=username SSL get_cabundle cert='-----BEGIN CERTIFICATE-----\r\nMIIDcTCCAlmgAwIBAgIFAU+BNVgwDQYJKoZIhvcNAQEFBQAwUTESMBAGA1UEAwwJ\r\nc2lza28udGxkMQswCQYDVQQGEwJVUzEPMA0GA1UECgwGY1BhbmVsMQswCQYDVQQI\r\nDAJUWDEQMA4GA1UEBwwHSG91c3RvbjAeFw0xNDEwMDYyMjI2MTlaFw0xNTEwMDYy\r\nMjI2MTlaMFExEjAQBgNVBAMMCXNpc2tvLnRsZDELMAkGA1UEBhMCVVMxDzANBgNV\r\nBAoMBmNQYW5lbDELMAkGA1UECAwCVFgxEDAOBgNVBAcMB0hvdXN0b24wggEiMA0G\r\nCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC9zx6zGiHdmWA0dKtoXmJiWXpZ9E3P\r\nXx3YHsjFEWW7e5pH0vZ+jVMzDmm5nsJ7RXrAkZO1IvpIpVLvoQfiJOWVvkD+o9fW\r\nvoK1tWJS72FSgPju+58mA2ieBuc87A790Pzuv1P3NR3zFLAjUR99zkHR1fpri/da\r\nM3PBWO8ET48FWkyU1kOeZaUlF67/+wrEiNgg+t1qhKOCAB61PdNVkLaSGHimksuC\r\n+Czk8Kq9nuS0E0TCnDtjjEyJ455FUcaCfczlTb8xkB/F9ORe74yTzD+vlk0tFMG6\r\nPLj/ajIwWqwO0qmQ8wX3NRxkWgGz5kVO1wrVJarKQ5EYQ3/mgvit0v6dAgMBAAGj\r\nUDBOMB0GA1UdDgQWBBRw+wKBo34+bgexjAa3EMDsgSCd7zAfBgNVHSMEGDAWgBRw\r\n+wKBo34+bgexjAa3EMDsgSCd7zAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBBQUA\r\nA4IBAQCHRXIs53opzKM2rM8Qe8lcw524WK6hqy2EWrZHp78N7rU7/6DQ/I3hv3Wh\r\ncDDIO04I2/Xhe88MLBaLoM367Ya+vy7CaLr14aLi/SfQszMA0ALBvMao+Fis0iVw\r\nFYq/NLgSXw+fgnpFskt8v8iQZ+4Kaal8U8e9sVgu8m0RgO7rzym1eRiIKpsKd1rh\r\n/SD7LbSN7M7TRL3QqF7ltw9sQhAAsQcRaBBF21pdWrqhiGZ+Eioo3hhgwNavH2ag\r\nqz78ddHwrFpHFwrEeUk1OfpPb76MYIce7xIy/4oQNdg6fOq4l/FrajBv+WkzDVPa\r\nKm6r7YmwfLN/YMZBHXSR58oOGP9W\r\n-----END CERTIFICATE-----'
```

<a id="ssl-get-cn-name"></a>
### `SSL::get_cn_name` — Request best SSL domain for service

`GET /execute/SSL/get_cn_name` · RO · since cPanel 11.42

This function retrieves the most secure domain for a service.

**Parameters**

- `domain` · **required** · string <domain> or string <email> or string <username> — A domain name, cPanel username, or email address.
- `service` · **required** · string (`cpanel`, `imap`, `pop3`, `smtp`) · e.g. `cpanel` — The service's name.; `cpanel`; `imap`; `pop3`; `smtp`
- `add_mail_subdomain` · optional · integer (`1`, `0`) · default `0` · e.g. `0` — Whether to append `mail` to the `domain` value to find the best match. For example, if you specify the domain `example.com` and call this parameter, the function only searches the `mail.example.com` service domains.; `1` — Append `mail` to the `domain` value during the search.; `0` — Match on the specified `domain` value **only**.

**Returns** `data`: object

- `cert_match_method` (string (`none`, `exact`, `exact-wildcard`, `mail-wildcard`, `www-wildcard`, `hostname-wildcard`, `hostname`, `localdomain_on_cert-mail-wildcard`, `localdomain_on_cert-www-wildcard`, `localdomain_on_cert`)) — The method that the system used to match the certificate with the mail service.; `none` — No domain matches the certificate.; `exact` — The domain exactly matches the certificate.; `exact-wildcard` — The domain exactly m
- `cert_valid_not_after` (integer <unix_timestamp>) — The certificate's expiration date.
- `is_currently_valid` (integer (`1`, `0`)) — Whether the certificate is currently valid.; `1` — Valid.; `0` — Invalid.
- `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
- `is_wild_card` (integer (`1`, `0`)) — Whether the certificate is a wildcard certificate.; `1` — Wildcard.; `0` — Not a wildcard.
- `ssldomain` (string <domain>) — The best domain to use to access the service.
- `ssldomain_matches_cert` (integer (`1`, `0`)) — Whether an SSL-protected domain matches the certificate.; `1` — Matches.; `0` — Does **not** match.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  get_cn_name \
  domain='example.com' \
  service='cpanel'
```

<a id="ssl-installed-host"></a>
### `SSL::installed_host` — Return SSL certificate's info for dedicated IP

`GET /execute/SSL/installed_host` · RO · since cPanel 11.42

This function retrieves information about a certificate that is installed on a domain's dedicated IP address. Important:  If you do **not** possess a dedicated IP address, this function will **fail**. For non-dedicated IP addresses, use the `SSL::installed_hosts` function.; When you disable the _Calendars and Contacts_, _Receive Mail_, _Web Disk_ , _Webmail_ , **and**  _Web Server_ [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `domain` · optional · string <domain> · e.g. `example.com` — The domain name. Note: The parameter defaults to the account's main domain.
- `verify_certificate` · optional · integer (`0`, `1`) · default `0` · e.g. `1` — Verify the certificate.; `1` — Verify the certificate.; `0` — Do **not** verify the certificate.

**Returns** `data`: object

- `certificate` (object) — An object containing the certificate information.
  - `domains` (array of string <domain>) — The domains that the certificate covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `id` (string) — The certificate's ID.
  - `is_self_signed` (integer (`0`, `1`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer.commonName` (string) — The issuer's Common Name, typically a domain name.
  - `issuer.organizationName` (string) — The certificate's organization.
  - `issuer_text` (string) — The X.509 information about the issuer that contains CSR information.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — The certificate's expiration time.
  - `not_before` (integer <unix_timestamp>) — The certificate's start time.
  - `signature_algorithm` (string) — The signature algorithm of the certificate.
  - `subject.commonName` (string) — The certificate's Common Name.
  - `subject_text` (string) — The X.509 information about the certificate's subject that contains CSR information.
  - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validation.; `dv` — Domain Validation.; `null` — The system could not parse and determine the certificate's validation type.
  - `verify_error` (string) — Any errors that exist during the certificate verification process.
- `host` (string <domain>) — The issuer's hostname.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  installed_host
```

<a id="ssl-installed-hosts"></a>
### `SSL::installed_hosts` — Return domains with SSL certificate information

`GET /execute/SSL/installed_hosts` · RO · since cPanel 11.42

This function retrieves a list of the account's websites, their domains, and certificate information. Important: For a dedicated IP address, use the UAPI `SSL::installed_host` function. Important: When you disable the *CalendarContact* , *MailReceive* , *WebDisk* , *Webmail* , and  *WebServer* [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `certificate` (object) — An object that contains information about each certificate.
    - `auto_ssl_provider` (string) — The AutoSSL provider's name.
    - `auto_ssl_provider_display_name` (string) — The AutoSSL provider's display name.
    - `domains` (array of string <domain>) — The domains that the certificate covers.
    - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
    - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
    - `id` (string) — The certificate's ID.
    - `is_autossl` (integer (`0`, `1`)) — Whether the AutoSSL service provided the certificate.; `1` - Provided by the AutoSSL service.; `0` - Not provided by the AutoSSL service.
    - `is_self_signed` (integer (`0`, `1`)) — Whether the certificate is self-signed.; `1` - Self-signed.; `0` - Not self-signed.
    - `issuer.commonName` (string <domain>) — The name that issued the certificate.
    - `issuer.organizationName` (string) — The certificate's organization name.
    - `issuer_text` (string) — The issuer's X.509 information.
    - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
    - `modulus` (string <hex>) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
    - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
    - `not_after` (integer <unix_timestamp>) — When the certificate expired.
    - `not_before` (integer <unix_timestamp>) — When the certificate started.
    - `signature_algorithm` (string <sha256>) — The signature algorithm of the certificate.
    - `subject.commonName` (string <domain>) — The certificate's common name.
    - `subject_text` (string) — The subject's X.509 information.
    - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.
  - `certificate_text` (string <pem-certificate>) — The certificate's text.
  - `docroot` (string <path>) — The document root of the domain that the certificate covers.
  - `domains` (array of string <domain>) — The domains that the certificate covers.
  - `fqdns` (array of string <domain>) — An array of every valid fully qualified domain name (FQDN) on the virtual host, which includes service subdomains (proxy subdomains).
  - `ip` (string <ipv4> or string <ipv6>) — The host's IP address.
  - `is_primary_on_ip` (integer (`0`, `1`)) — Whether the website is primary on the IP address.; `1` - Primary.; `0` - Not primary.
  - `mail_sni_status` (integer (`0`, `1`)) — Whether SNI is active on the domain.; `1` - Active.; `0` - Inactive.
  - `needs_sni` (integer (`0`, `1`)) — Whether the website requires SNI to function.; `1` - Requires SNI.; `0` - Does not require SNI.
  - `servername` (string <domain>) — The server's hostname.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  installed_hosts
```

<a id="ssl-list-certs"></a>
### `SSL::list_certs` — Return all SSL certificates

`GET /execute/SSL/list_certs` · RO · rollback: none · since cPanel 11.42

This function lists an account's certificates. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The date the certificate was created.
  - `domain_is_configured` (integer (`1`, `0`)) — Whether the certificate is installed on the account.; `1` — Installed.; `0` — Not installed.
  - `domains` (array of string) — A list of domains that the certificate covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `friendly_name` (string) — The certificate's friendly name.
  - `id` (string) — The certificate's ID.
  - `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer.commonName` (string) — The issuer's name.
  - `issuer.organizationName` (string) — The certificate's organization.
  - `issuer_text` (string) — The certificate's issuer information.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — The certificate's expiration date.
  - `not_before` (integer <unix_timestamp>) — The certificate's start date.
  - `serial` (string) — The certificate's serial number.
  - `signature_algorithm` (string) — The OID hash algorithm signature of the certificate.
  - `subject.commonName` (string) — The certificate's Common Name (CN).
  - `subject_text` (string) — The certificate's subject text information.
  - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validation.; `dv` — Domain Validation.; `null` — The system could not parse and determine the certificate's validation type.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  list_certs
```

<a id="ssl-list-csrs"></a>
### `SSL::list_csrs` — Return all certificate signing requests

`GET /execute/SSL/list_csrs` · RO · rollback: none · since cPanel 11.42

This function lists an account's certificate signing requests (CSR). Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `commonName` (string) — The CSR's Common Name or Distinguished Name.
  - `created` (integer <unix_timestamp>) — The CSR's creation date.
  - `domains` (array of string <domain>) — A list of the domains that the CSR covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the CSR's key uses.; `prime256v1`; `secp384r1`; `null` — The CSR's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The CSR's key's ECDSA compressed public point, in hexadecimal format.; `null` — The CSR's key is **not** an ECDSA key.
  - `friendly_name` (string) — The CSR's friendly name.
  - `id` (string) — The CSR's ID.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The CSR's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The CSR's key's modulus, in hexadecimal format.; `null` — The CSR's key is **not** an RSA key.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  list_csrs
```

<a id="ssl-list-keys"></a>
### `SSL::list_keys` — Return all private keys

`GET /execute/SSL/list_keys` · RO · rollback: none · since cPanel 11.42

This function lists an account's private keys. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The key's creation date.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the key uses.; `prime256v1`; `secp384r1`; `null` — The key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The key's ECDSA compressed public point, in hexadecimal format.; `null` — The key is **not** an ECDSA key.
  - `friendly_name` (string) — The key's friendly name.
  - `id` (string) — The key ID.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The key's modulus, in hexadecimal format.; `null` — The key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the key's modulus.; `null` — The key is **not** an RSA key.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  list_keys
```

<a id="ssl-list-ssl-items"></a>
### `SSL::list_ssl_items` — Return SSL-related items

`GET /execute/SSL/list_ssl_items` · RO · rollback: none · since cPanel 11.42

This function lists SSL-related items on a domain. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.com/serverroles), the system **disables** this function.

**Parameters**

- `domains` · optional · string — The domain name or names.
- `item` · optional · string · default `key` — The SSL item type or types.; `key`; `csr`; `crt`

**Returns** `data`: array of object

- *(array of objects)*
  - `host` (string <domain>) — The hostname.
  - `id` (string) — The certificate's ID.
  - `type` (string (`key`, `csr`, `crt`)) — The type of SSL item.; `key`; `csr`; `crt`

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  list_ssl_items
```

<a id="ssl-rebuildssldb"></a>
### `SSL::rebuildssldb` — Start SSL database rebuild

`GET /execute/SSL/rebuildssldb` · RW · rollback: none · since cPanel 11.42

This function rebuilds the account's SSL database.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  rebuildssldb
```

<a id="ssl-set-default-key-type"></a>
### `SSL::set_default_key_type` — Update SSL TLS key type

`GET /execute/SSL/set_default_key_type` · RW · rollback: none · since cPanel 92

This function sets a user’s preferred SSL/TLS key type.

**Parameters**

- `type` · **required** · string (`system`, `rsa-2048`, `rsa-4096`, `ecdsa-prime256v1`, `ecdsa-secp384r1`) — The key type to set.; `system` — Use the system’s `ssl_default_key_type` value.; `rsa-2048` — 2,048-bit RSA.; `rsa-4096` — 4,096-bit RSA.; `ecdsa-prime256v1` — ECDSA prime256v1 (“P-256”).; `ecdsa-secp384r1` — ECDSA secp384r1 (“P-384”).

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  set_default_key_type \
  type='ecdsa-prime256v1'
```

<a id="ssl-toggle-ssl-redirect-for-domains"></a>
### `SSL::toggle_ssl_redirect_for_domains` — Enable or disable secure redirects

`GET /execute/SSL/toggle_ssl_redirect_for_domains` · RW · rollback: none · since cPanel 80

This function enables or disables secure redirects (HTTPS) for the cPanel account's domains that you specify. Important: To call this function, one of the following conditions **must** exist: AutoSSL **must** exist on the domains for which you enable secure redirects.; A valid SSL certificate **must** exist for each domain for which you wish to enable secure redirects.; You **must** own the domains for which you wish to enable secure redirects.

**Parameters**

- `domains` · **required** · string · e.g. `main.example,addon.example,addon.main.example` — A comma-separated list of the cPanel account's domains for which to enable or disable secure redirects. Important: To enable or disable redirects for addon domains, you **must** pass the addon domain **and** its subdomain.
- `state` · **required** · integer (`0`, `1`) · e.g. `1` — Whether to enable or disable redirects for the specified domains.; `1` — Enable.; `0` — Disable.

**Returns** `data`: array of string — The domains for which the function enabled or disabled secure redirects.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  toggle_ssl_redirect_for_domains \
  domains='main.example,addon.example,addon.main.example' \
  state='1'
```

## SSL Certificate Management

<a id="ssl-delete-cert"></a>
### `SSL::delete_cert` — Delete SSL certificate

`GET /execute/SSL/delete_cert` · RW · rollback: none · since cPanel 11.42

This function deletes an SSL certificate. Note:  When you call this function, you **must** include the `id` or the `friendly_name` parameter.; This function **only** deletes certificates from SSL storage. To end SSL coverage for a domain, use the UAPI `SSL::delete_ssl` function instead. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestCert` — The certificate's friendly name.
- `id` · optional · string — The certificate's ID.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The date the certificate was created.
  - `domains` (array of string <domain>) — A list of the domains that the certificate covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `friendly_name` (string) — The certificate's friendly name.
  - `id` (string) — The certificate's ID.
  - `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer.commonName` (string) — The certificate's Common Name.
  - `issuer.organizationName` (string) — The certificate's Organization Name.
  - `issuer_text` (string) — The certificate's issuer information.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — The date the certificate expired.
  - `not_before` (integer <unix_timestamp>) — The date the certificate started.
  - `serial` (string) — The certificate's serial number.
  - `signature_algorithm` (string) — The certificate's OID signature hash algorithm.
  - `subject.commonName` (string) — The certificate's Common Name.
  - `subject_text` (string) — The certificate's subject text information.
  - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validation.; `dv` — Domain Validation.; `null` — The system could not parse and determine the certificate's validation type.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  delete_cert
```

<a id="ssl-delete-csr"></a>
### `SSL::delete_csr` — Delete certificate signing request

`GET /execute/SSL/delete_csr` · RW · rollback: none · since cPanel 11.42

This function deletes a certificate signing request (CSR). Note:  When you call this function, you **must** include the `id` or the `friendly_name` parameter.; To delete a private key, use the UAPI `SSL::delete_key` function instead. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestCSR` — The CSR's friendly name.
- `id` · optional · string · e.g. `example_com_e095f_0ab2f_ebcbe4a571276f48562241411556647f` — The CSR's ID.

**Returns** `data`: array of object

- *(array of objects)*
  - `commonName` (string <domain>) — The CSR's Common Name.
  - `created` (integer <unix_timestamp>) — The CSR's creation date.
  - `domains` (array of string) — A list of the domains that the CSR covers.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the CSR's key uses.; `prime256v1`; `secp384r1`; `null` — The CSR's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The CSR's key's ECDSA compressed public point, in hexadecimal format.; `null` — The CSR's key is **not** an ECDSA key.
  - `friendly_name` (string) — The CSR's friendly name.
  - `id` (string) — The CSR's ID.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The CSR's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The CSR's key's modulus, in hexadecimal format.; `null` — The CSR's key is **not** an RSA key.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  delete_csr
```

<a id="ssl-delete-key"></a>
### `SSL::delete_key` — Delete private key

`GET /execute/SSL/delete_key` · RW · rollback: none · since cPanel 11.42

This function deletes a private key. Note:  When you call this function, you **must** include the `id` or the `friendly_name` parameter.; To delete a certificate signing request (CSR), use the UAPI `SSL::delete_csr` function instead. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestKey` — The private key's friendly name.
- `id` · optional · string · e.g. `example_com_e095f_0ab2f_ebcbe4a571276f48562241411556647f` — The private key's ID.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The private key's creation date.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the key uses.; `prime256v1`; `secp384r1`; `null` — The key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The key's ECDSA compressed public point, in hexadecimal format.; `null` — The key is **not** an ECDSA key.
  - `friendly_name` (string) — The private key's friendly name.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The key's modulus, in hexadecimal format.; `null` — The key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the key's modulus.; `null` — The key is **not** an RSA key.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  delete_key
```

<a id="ssl-generate-cert"></a>
### `SSL::generate_cert` — Create self-signed SSL certificate

`GET /execute/SSL/generate_cert` · RW · rollback: none · since cPanel 11.42

This function generates a self-signed SSL certificate. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `countryName` · **required** · string <ISO-3166-1 (alpha-2)> · e.g. `US` — The two-letter country code.
- `domains` · **required** · string <domain> — A comma-separated list of domains for which to generate the certificate.
- `key_id` · **required** · string — The key's ID.
- `localityName` · **required** · string · e.g. `Houston` — The certificate's city or locality name.
- `organizationName` · **required** · string · e.g. `Organization` — The certificate's Organization Name.
- `stateOrProvinceName` · **required** · string · e.g. `TX` — The two-letter state or locality abbreviation.
- `emailAddress` · optional · string <email> · e.g. `username@example.com` — An email address to associate with the certificate.
- `friendly_name` · optional · string · e.g. `TestCert` — A friendly name for the new certificate. This parameter defaults to the domain's name for which you generated the certificate.
- `organizationalUnitName` · optional · string · default `` · e.g. `Department` — The certificate's organizational unit or department name.

**Returns** `data`: object

- `created` (integer <unix_timestamp>) — The certificate's creation date.
- `domains` (array of string <domain>) — A list of domains that the certificate covers.
- `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
- `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; null — The certificate's key is **not** an ECDSA key.
- `friendly_name` (string) — The certificate's friendly name.
- `id` (string) — The certificate's ID.
- `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
- `issuer.commonName` (string) — The certificate's Common Name.
- `issuer.organizationName` (string) — The certificate's Organization Name.
- `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
- `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
- `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
- `not_after` (integer <unix_timestamp>) — The date that the certificate expires.
- `not_before` (integer <unix_timestamp>) — The certificate's start date.
- `serial` (string) — The certificate's serial number.
- `signature_algorithm` (string) — The certificate's OID hash algorithm signature.
- `subject.commonName` (string <domain>) — The domain that issued the certificate.
- `text` (string <pem-certificate>) — The certificate's text.
- `validation_type` (string) — The certificate's validation type, if one exists.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  generate_cert \
  domains='example.com' \
  countryName='US' \
  stateOrProvinceName='TX' \
  localityName='Houston' \
  organizationName='Organization' \
  key_id='example_com_cb497_a394d_1397249671_d1272da8f13a1fd837493a5ad1f0a0f3'
```

<a id="ssl-generate-csr"></a>
### `SSL::generate_csr` — Create certificate signing request

`GET /execute/SSL/generate_csr` · RW · rollback: none · since cPanel 11.42

This function generates a certificate signing request (CSR). Note: This function **requires** a valid key in the account's `ssl` directory. You can generate a key with UAPI's `SSL::generate_key` function. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and WebServer [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `countryName` · **required** · string <ISO-3166-1 (alpha-2)> · e.g. `US` — The two-letter country code.
- `domains` · **required** · string — A comma-separated list of the domains for which to generate the certificate.
- `key_id` · **required** · string — The key's ID.
- `localityName` · **required** · string · e.g. `Houston` — The certificate's city or locality name.
- `organizationName` · **required** · string · e.g. `Organization` — The certificate's organization.
- `stateOrProvinceName` · **required** · string · e.g. `Texas` — The certificate's state or locality name.
- `emailAddress` · optional · string <email> · e.g. `username@example.com` — An email address to associate with the certificate.
- `friendly_name` · optional · string · e.g. `TestCert` — A friendly name for the new certificate. This parameter defaults to the domain name for which you generated the certificate.
- `organizationalUnitName` · optional · string · default `` · e.g. `Department` — The certificate's organizational unit or department name.

**Returns** `data`: object

- `commonName` (string) — The name that issued the CSR.
- `created` (integer <unix_timestamp>) — The date the CSR was created.
- `domains` (array of string <domain>) — The domains that the CSR covers.
- `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the CSR's key uses.; `prime256v1`; `secp384r1`; `null` — The CSR's key is **not** an ECDSA key.
- `ecdsa_public` (string) — The CSR's key's ECDSA compressed public point, in hexadecimal format.; `null` — The CSR's key is **not** an ECDSA key.
- `friendly_name` (string) — The CSR's friendly name.
- `id` (string) — The CSR's ID.
- `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The CSR's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
- `modulus` (string) — The CSR's key's modulus, in hexadecimal format.; `null` — The CSR's key is **not** an RSA key.
- `text` (string <pem-certificate-request>) — The CSR's text.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  generate_csr \
  domains='example.com' \
  countryName='US' \
  stateOrProvinceName='Texas' \
  localityName='Houston' \
  organizationName='Organization' \
  key_id='example_com_cb497_a394d_1397249671_d1272da8f13a1fd837493a5ad1f0a0f3'
```

<a id="ssl-generate-key"></a>
### `SSL::generate_key` — Create private key

`GET /execute/SSL/generate_key` · RW · rollback: none · since cPanel 11.42

This function generates a private key. Important:  You **cannot** call both the `keytype` and `keysize` parameters in a single call.; When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, **and** Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestKey` — A friendly name for the new key. This parameter defaults to the key's type, creation date, and creation time.
- `keysize` · optional · integer · default `2048` · e.g. `2048` — The key's modulus size. Note: Use the `keytype` parameter.
- `keytype` · optional · string (`system`, `rsa-2048`, `rsa-4096`, `ecdsa-prime256v1`, `ecdsa-secp384r1`) · e.g. `rsa-2048` — The key's type.; `system` — The system's default value.; `rsa-2048` — 2,408-bit RSA.; `rsa-4096` — 4,096-bit RSA.; `ecdsa-prime256v1` — ECDSA prime256v1 ("P-256").; `ecdsa-secp384r1` — ECDSA secp384r1 ("P-384"). This parameter defaults to the user's [default SSL/TLS key type](https://go.cpanel.net/cpaneldocsSSLTLS#default-ssl-tls-key-type). Note: If you do **not** use this parameter, the system defaults to the `keysize` parameter's default value.

**Returns** `data`: object

- `created` (integer <unix_timestamp>) — The key's creation date.
- `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the key uses.; `prime256v1`; `secp384r1`; `null` — The key is **not** an ECDSA key.
- `ecdsa_public` (string) — The key's ECDSA compressed public point, in hexadecimal format.; `null` — The key is **not** an ECDSA key.
- `friendly_name` (string) — The key's friendly name.
- `id` (string) — The key's ID.
- `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
- `modulus` (string) — The key's modulus, in hexadecimal format.; `null` — The key is **not** an RSA key.
- `modulus_length` (integer) — The length, in bits, of the key's modulus.; `null` — The key is **not** an RSA key.
- `text` (string <pem-private-key>) — The key's contents.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  generate_key
```

<a id="ssl-install-ssl"></a>
### `SSL::install_ssl` — Install SSL certificate

`GET /execute/SSL/install_ssl` · RW · rollback: none · since cPanel 11.42

This function installs an SSL certificate. Note: Due to their inherent complexities, SSL-related functions often present problems for third-party developers. For the additional steps required to successfully call this function, read our [Call UAPI's SSL::install_ssl Function in Custom Code](https://go.cpanel.net/tutorial-call-uapis-ssl-install-ssl-function-in-custom-code) documentation. Important: When you disable the *Calendars and Contacts*, *Receive Mail*, *Web Disk*, *Webmail*, and *Web Server* [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `cert` · **required** · string <pem-certificate> — The certificate to install. Note:  You **must** URI-encode this value.; You can use a Perl command to URI-encode your SSL certificate for this parameter. For example, you can use the following string, where `CERT.FILE` is the SSL certificate file: ```$(perl -MURI::Escape -ne 'print uri_escape($_);' CERT.FILE)```
- `domain` · **required** · string <domain> · e.g. `example.com` — The domain name.
- `cabundle` · optional · string <pem-certificate> — The Certificate Authority (CA) bundle data, if the certificate requires it. Note:  You **must** URI-encode this value.; You can use a Perl command to URI-encode your SSL certificate for this parameter. For example, you can use the following string, where `CABUNDLE.FILE` is the SSL certificate file: ```$(perl -MURI::Escape -ne 'print uri_escape($_);' CABUNDLE.FILE)```
- `domain_dcv_method` · optional · object · e.g. `{"example.com": "http"}` — A map of each domain to its domain control validation (DCV) method.
- `key` · optional · string <pem-private-key> — The certificate's key. If you omit it, the system uses the matching key already saved to your account. Note:  You **must** URI-encode this value.; You can use a Perl command to URI-encode your SSL certificate for this parameter. For example, you can use the following string, where `KEY.FILE` is the SSL certificate file: ```$(perl -MURI::Escape -ne 'print uri_escape($_);' KEY.FILE)```
- `order_item_id` · optional · string · e.g. `67890` — The cPanel Store order item ID associated with the certificate.
- `originating_certificate_id` · optional · string · e.g. `12345` — The cPanel Store certificate ID that this certificate descends from. The short-lived certificate re-issue workflow sets this so the system can supersede the prior certificate after installation; end users do not normally set it.
- `parent_cert_expiry` · optional · integer · e.g. `1735689600` — The expiration of the parent subscription certificate, as a Unix timestamp.
- `vhost_names` · optional · array of string <domain> — The virtual host names onto which to install the certificate. To set multiple names, duplicate or increment the parameter name. For example, `vhost_names-1` and `vhost_names-2`.

**Returns** `data`: object

- `action` (string) — The action that the function used to install the certificate.
- `cert_id` (string) — The certificate ID.
- `domain` (string <domain>) — The domain that the certificate covers.
- `extra_certificate_domains` (array of string <domain>) — The domains that require extra certificates for mail and other services.
- `html` (string) — The results, in HTML format.
- `ip` (string <ipv4> or string <ipv6>) — The domain's IP address.
- `key_id` (string) — The key ID.
- `message` (string) — The results, in text format.
- `statusmsg` (string) — The results.
- `user` (string <username>) — The domain's owner.
- `warning_domains` (array of string <domain>) — The domains that the certificate does not cover.
- `working_domains` (array of string <domain>) — The domains that the certificate covers.

```bash
uapi --output=jsonpretty --user=username SSL install_ssl domain='example.com' cert='-----BEGIN%20CERTIFICATE-----%0AMIIEEzCCAvugAwIBAgIJALF%2FjFpw6p1bMA0GCSqGSIb3DQEBBQUAMIGfMRYwFAYD%0AVQQDEw10ZXN0c2ltb24uY29tMRYwFAYDVQQLEw1Eb2N1bWVudGF0aW9uMQswCQYD%0AVQQGEwJVUzEoMCYGCSqGSIb3DQEJARYZbGF1cmVuY2Uuc2ltb25AY3BhbmVsLm5l%0AdDEUMBIGA1UEChMLY1BhbmVsIEluYy4xDjAMBgNVBAgTBVRleGFzMRAwDgYDVQQH%0AEwdIb3VzdG9uMB4XDTEzMDUxNzE2MTMwN1oXDTE0MDUxNzE2MTMwN1owgZ8xFjAU%0ABgNVBAMTDXRlc3RzaW1vbi5jb20xFjAUBgNVBAsTDURvY3VtZW50YXRpb24xCzAJ%0ABgNVBAYTAlVTMSgwJgYJKoZIhvcNAQkBFhlsYXVyZW5jZS5zaW1vbkBjcGFuZWwu%0AbmV0MRQwEgYDVQQKEwtjUGFuZWwgSW5jLjEOMAwGA1UECBMFVGV4YXMxEDAOBgNV%0ABAcTB0hvdXN0b24wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDRO0AP%0AN5XtjDqkEyJ6ctfYqUtt9yUXyRuCETFjW6opNLSmZSHeF6L2aZka646lhj02CFyl%0AkzsNSxysN66tY%2BWZcTmvgPisJdQFpFvjroJZgDjYRV0QqokKdRy%2F5BU0%2BtHXoYpj%0A9JOQlbvEWxiGR3R80sL1ma4AfSE6Gv8M%2FPULTadan51eHaikXqjOXdPJQKuWP3g9%0AFnIuf38WRYwzGrre88qsZrpsMrADX5dotHWgqAf7Tap6xfA4CUAgQo9tldariuVi%0ABz%2BsRJ%2FSjgxnhw1HYWGttBuBZFhMpdHpPnTJ7DIFMd%2FFN5gG%2Ftah30SapWpo35Ux%0A3BpJcdUjtazy82K5AgMBAAGjUDBOMB0GA1UdDgQWBBQAlv7%2FtALOYb7zAXbYG2%2B9%0AAMI3xjAfBgNVHSMEGDAWgBQAlv7%2FtALOYb7zAXbYG2%2B9AMI3xjAMBgNVHRMEBTAD%0AAQH%2FMA0GCSqGSIb3DQEBBQUAA4IBAQCxzpe71Hc7Es0dqIN7bhIFYIIgcr6wxM6a%0Aa9d%2BQG%2BQPH0x0KAqV8EgUbZysvyxEF0bPxW3ZAr1Is1wk80PMuU3bToFFVbFFIIr%0AHRNfKLGvxiMXnZA1c6L4N0lowvXHgZxTTUXtDFLXyrcwrLsvUErEV7rbizuxqfPw%0AcaRtXn4uc%2Bt6HYuW7yWesBauCWnJNiKbjN%2FF%2BuCTurN3QMAeWf3ZJtsfkAgk8dyq%0AR%2F83a3kDtSPrpt%2BjX%2BqdjKEpRtQ5Qpm6XT2gCOQPgnfiUtOCH419pp922P%2FAAGc%2B%0AZUhYoWcRWKw%2Fy6gI7Ru%2B%2B9%2B8%2BwkadL9EbKMZxhVwD5qVm4ZlWK2a%5Cr%5Cn%0A-----END%20CERTIFICATE-----' key='-----BEGIN%20RSA%20PRIVATE%20KEY-----%0AMIIEpAIBAAKCAQEA4AVM6J4Qg3DIFWr%2FeJ5GRmIATYsJIepKbrDy70sq%2BudcO8R8%0Axxak0oMZ%2F9mUdpjSNK%2FfLVTuCO0kxTfQ9VUWJllX7ThD6Zh9ZvlC%2Fnf%2FOEZLm3Zb%0ABgu8rbC8E9wuDOkKbJLnINgdhtowIydLK2MJ%2B%2Bq62bFV89jkHWTMcKyyqHENo3h%0Ac%2Blkpd9vnp8rZTinaVb7nX26uQqAFZYRo%2BWU0G%2FNPsq40QVSMoqPxyEz4qXo0hvu%0AIlCXmzFZq%2F6fCVPEKPLhQgMmpdBkMz4dVOazREfqXdjMD2%2BQXSNiA1AwWr8l0r4r%0AtzlxEYDJIR41yXp0xMl3KoolxMyvLBqZy32niQIDAQABAoIBAQCmbGmhWmPsMeoC%0At1WJFxQgD4goE0U6k%2BKt7vjbOt14Pk6v%2FB2yjaju1wSGpO59WLS4%2FXrwI2se6IXr%0Amba7u3VUEgWXLriNHoLy7%2FSMNTs%2BZEKhAMG36eNe3tVdT7busTag31r6sEMGGwCs%0AIwpU%2Bazosk0oylWLEX%2Fm%2FuHWEs1eaIEWWWtgHB%2BKZrrP7Rr9RYfVQ144DxmOxS3C%0Aa9%2BmST62WqAVPR6POWGEfZqnZl%2FePWZPcQYbFrhwnnefNoYBl%2FbnLZBo8rbNWxAq%0AOEOuKfkrBzglKG%2F39WKPw8rj4JIVzY0yOuFCW6xCDWRkOrhU8Ol%2F3FvwDa3uJpkp%0AmgPr4TgxAoGBAPGPLmxSuOYR97mDAXxrs037F2GCbqWvI6m7%2FezWe9yn%2BbMpjSIW%0Afsgtq4FsyqzPueEkDdQWi3xh6nu2WI%2F1Tl875opGAqEIJMqss%2Fu11tnva5wzu1cC%0AL6H85A5%2BHMOBvP3sm6CObKcVw92h7kxynVIUJJWhjfeZMN8gBFFpKIVFAoGBAO1p%0AtXBmXLC%2FYKKvtHI3M16%2FZopvM8ZqU2HcAHaw214Refw9JJ%2Fe3%2FxTNfSerVTyCAQO%0A1AdWTzJKBN8jmSYv1Mk1D3RpQPNR7wVzi46KR081AU41uMpqIGVOwHtyVnW%2FZfLr%0Ac1DLIK8Cx8aHfoxffwzoMO5SEQSooeZfOLhsfDN1AoGBAKQTUEINsj%2B75psgbAr6%0AELGgItJ9yPBLVRr%2BcUzEpx9LDWVvjMihpP4NX1gq8EOPWT%2BewLHVmmsjCyV6xw8J%0AXXF8e2xif3in0m3D%2FwCzE7u2T06rKM3B017hKnrZmGoHnrqPU2osM4sOUpshWX6d%0Av1Q4EF1%2BfbK3YCW%2BVpCBsB9NAoGAQo%2BuhNLODee56iKkzpjXWCsFTq6ar3hD5F3P%0A63buKdNwhd2GlSPhXFbf%2B7M5GWW6BZk6rMvv7EOAVice2uvyFm8%2F4%2F1WbmF8R%2BT7%0ALX1rPLO5p%2Fm701QpvP11TabiwqRkqtSEQhSRF0AKTojSW%2FyyHCZFAawUhV%2FZ9EKi%0AHmKb97kCgYAyzmFc2it0HqnsOnRybop603nqMtWGTQO4cxa93HUDpYajuK2K3Dfr%0AxUj6lG3z%2FoKJGGE2JqgZ6LBAhNJtJWJu2ox3pKGE63QjLJnVwb8y1NFYpe%2FcrbLe%0APuBwIR0L7drXxfv7O5btY7h6QI2d1%2FUIAQPAWbxLoTM%2BndQ%2FuPEdfA%3D%3D%0A-----END%20RSA%20PRIVATE%20KEY-----'
```

<a id="ssl-set-cert-friendly-name"></a>
### `SSL::set_cert_friendly_name` — Update SSL certificate's friendly name

`GET /execute/SSL/set_cert_friendly_name` · RW · rollback: none · since cPanel 11.42

This function changes a certificate's friendly name. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `friendly_name` · **required** · string · e.g. `TestCert` — The certificate's friendly name.
- `new_friendly_name` · **required** · string · e.g. `TestCert2` — The certificate's new friendly name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  set_cert_friendly_name \
  friendly_name='TestCert' \
  new_friendly_name='TestCert2'
```

<a id="ssl-set-csr-friendly-name"></a>
### `SSL::set_csr_friendly_name` — Update certificate signing request's friendly name

`GET /execute/SSL/set_csr_friendly_name` · RW · rollback: none · since cPanel 11.42

This function changes a certificate signing request's (CSR) friendly name. Important:  You **must** call either the `friendly_name` or `id` parameter.; When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `friendly_name` · **required** · string · e.g. `TestCSR` — The CSR's friendly name.
- `id` · **required** · string · e.g. `example_com_eda9d_543fb_a3009b4b01a592390866ab3a47c0df18` — The CSR's ID. Note: To retrieve a CSR's ID, use the UAPI `list_csrs` function.
- `new_friendly_name` · **required** · string · e.g. `TestCSR2` — The CSR's new friendly name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  set_csr_friendly_name \
  friendly_name='TestCSR' \
  id='example_com_eda9d_543fb_a3009b4b01a592390866ab3a47c0df18' \
  new_friendly_name='TestCSR2'
```

<a id="ssl-set-key-friendly-name"></a>
### `SSL::set_key_friendly_name` — Update private key's friendly name

`GET /execute/SSL/set_key_friendly_name` · RW · rollback: none · since cPanel 11.42

This function changes a key's friendly name. Important:  You **must** call either the `friendly_name` or `id` parameter.; When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `friendly_name` · **required** · string · e.g. `TestKey` — The key's friendly name.
- `id` · **required** · string · e.g. `a9b72_63971_2cb6d8897b362cfb1548e047d8428b8d` — The key's ID.
- `new_friendly_name` · **required** · string · e.g. `TestKey2` — The key's new friendly name.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  set_key_friendly_name \
  friendly_name='TestKey' \
  id='a9b72_63971_2cb6d8897b362cfb1548e047d8428b8d' \
  new_friendly_name='TestKey2'
```

<a id="ssl-set-primary-ssl"></a>
### `SSL::set_primary_ssl` — Update SSL website for dedicated IP address

`GET /execute/SSL/set_primary_ssl` · RW · rollback: none · since cPanel 11.42

This function sets a new primary SSL website for a dedicated IP address. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `servername` · **required** · string <domain> · e.g. `hostname.example.com` — The primary SSL website's servername.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  set_primary_ssl \
  servername='hostname.example.com'
```

<a id="ssl-show-cert"></a>
### `SSL::show_cert` — Export SSL certificate

`GET /execute/SSL/show_cert` · RW · rollback: none · since cPanel 11.42

This function retrieves a certificate. Note: When you call this parameter, you **must** include either the `id` or the `friendly_name` parameter. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, **and** Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestCert` — The certificate's friendly name.
- `id` · optional · string — The certificate's ID.

**Returns** `data`: object

- `cert` (string <pem-certificate>) — The contents of the certificate.
- `details` (object) — An object containing the certificate's details.
  - `domains` (array of string <domain>) — A list of the certificate's domains.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `friendly_name` (string) — The certificate's friendly name.
  - `id` (string) — The certificate's ID.
  - `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer` (object) — A object that contains the issuer's details.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — The certificate's expiration date.
  - `not_before` (integer <unix_timestamp>) — The certificate's start time.
  - `signature_algorithm` (string) — The certificate's OID hash algorithm signature.
  - `subject` (object) — An object containing the certificate's ownership details.
  - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validation.; `dv` — Domain Validation.; `null` — The system could not parse and determine the certificate's validation type.
- `text` (string) — The parsed information from the OpenSSL command-line tool.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  show_cert
```

<a id="ssl-show-csr"></a>
### `SSL::show_csr` — Export certificate signing request

`GET /execute/SSL/show_csr` · RW · rollback: none · since cPanel 11.42

This function retrieves a certificate signing request (CSR). Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function. Note: When you call this function, you **must** include either the `id` or the `friendly_name` parameter.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestCSR` — The CSR's friendly name.
- `id` · optional · string · e.g. `example_com_e095f_0ab2f_ebcbe4a571276f48562241411556647f` — The CSR's ID.

**Returns** `data`: object

- `csr` (string) — The CSR's text.
- `details` (object) — An object contaning the CSR's contents.
  - `commonName` (string) — The CSR's Common Name or Distinguished Name.
  - `countryName` (string) — The CSR's [ISO-3166](https://en.wikipedia.org/wiki/ISO_3166) country code.
  - `created` (integer <unix_timestamp>) — The CSR's creation date.
  - `domains` (array of string) — A list of the domains that the CSR covers.
  - `emailAddress` (string <email>) — The CSR's email address.
  - `friendly_name` (string) — The CSR's friendly name.
  - `id` (string) — The CSR's ID.
  - `key_algorithm` (string) — The key algorithm that encrypts the CSR.
  - `localityName` (string) — The certificate's locality or city.
  - `modulus` (string) — The CSR's modulus.
  - `organizationName` (string) — The CSR's organization name.
  - `organizationalUnitName` (string) — The CSR's organizational unit name.
  - `stateOrProvinceName` (string) — The CSR's state or province name.
- `text` (string) — The parsed information from the OpenSSL command-line tool.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  show_csr
```

<a id="ssl-show-key"></a>
### `SSL::show_key` — Export private key

`GET /execute/SSL/show_key` · RW · rollback: none · since cPanel 11.42

This function retrieves a private key. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, **and** Web Server [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `friendly_name` · optional · string · e.g. `TestKey` — The key's friendly name. Note: You **must** use either the `id` or the `friendly_name` parameter.
- `id` · optional · string — The key's ID. Note: You **must** use either the `id` or the `friendly_name` parameter.

**Returns** `data`: object

- `details` (object) — An object of the key's details.
  - `created` (integer <unix_timestamp>) — The key's creation date.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the key uses.; `prime256v1`; `secp384r1`; `null` — The key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The key's ECDSA compressed public point, in hexadecimal format.; `null` — The key is **not** an ECDSA key.
  - `friendly_name` (string) — The key's friendly name.
  - `id` (string) — The key's ID.
  - `key` (string <pem-private-key>) — The key's contents.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The key's modulus, in hexadecimal format.; `null` — The key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the key's modulus.; `null` — The key is **not** an RSA key.
- `text` (string) — The raw information from the [OpenSSL](https://www.openssl.org/) command-line tool.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  show_key
```

<a id="ssl-upload-cert"></a>
### `SSL::upload_cert` — Import SSL certificate

`POST /execute/SSL/upload_cert` · RW · rollback: none · since cPanel 11.42

This function uploads a certificate. Important:  Due to the limited field length of HTTP GET method calls, you **must** use the HTTP POST method. For this reason, you **cannot** use a cPanel or Webmail session URL to call this function.; When you disable the Calendar and Contacts, Receive Mail, Web Disk, Webmail, and Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `crt` · **required** · string <pem-certificate> — The certificate's contents.
- `friendly_name` · optional · string · e.g. `TestCert` — The certificate's friendly name.

**Request body** (`multipart/form-data`)

- `crt` (string <pem-certificate>) — The certificate file.
- `friendly_name` (string) — The certificate's friendly name.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The certificate's creation date.
  - `domains` (array of string <domain>) — A list of the certificate's domains.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the certificate's key uses.; `prime256v1`; `secp384r1`; `null` — The certificate's key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The certificate's key's ECDSA compressed public point, in hexadecimal format.; `null` — The certificate's key is **not** an ECDSA key.
  - `friendly_name` (string) — The certificate's friendly name.
  - `id` (string) — The certificate's ID.
  - `is_self_signed` (integer (`1`, `0`)) — Whether the certificate is self-signed.; `1` — Self-signed.; `0` — Not self-signed.
  - `issuer.commonName` (string) — The issuer's Common Name or Distinguished Name.
  - `issuer.organizationName` (string) — The issuer's Organization Name.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The certificate's key's algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The certificate's key's modulus, in hexadecimal format.; `null` — The certificate's key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the certificate's key's modulus.; `null` — The certificate's key is **not** an RSA key.
  - `not_after` (integer <unix_timestamp>) — The certificate's expiration date.
  - `not_before` (integer <unix_timestamp>) — The certificate's start date.
  - `signature_algorithm` (string) — The certificiate's OID hash algorithm signature.
  - `subject.commonName` (string) — The issuer's Common Name or Distinguished Name.
  - `validation_type` (string (`ev`, `ov`, `dv`)) — The certificate's validation type.; `ev` — Extended Validation.; `ov` — Organization Validation.; `dv` — Domain Validation.; `null` — The system could not parse and determine the certificate's validation type.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  SSL \
  upload_cert
```

<a id="ssl-upload-key"></a>
### `SSL::upload_key` — Import private key

`POST /execute/SSL/upload_key` · RW · rollback: none · since cPanel 11.42

This function uploads a private key. Note: Due to the limited field length of HTTP GET method calls, you **must** use the HTTP POST method. For this reason, you **cannot** use a cPanel or Webmail session URL to call this function. Important: When you disable the Calendars and Contacts, Receive Mail, Web Disk, Webmail, **and** Web Server [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `key` · **required** · string <pem-private-key> — The key's contents.
- `friendly_name` · optional · string · e.g. `TestKey` — The key's friendly name.

**Request body** (`multipart/form-data`)

- `crt` (string <pem-private-key>) — The key's contents.
- `friendly_name` (string) — The key's friendly name.

**Returns** `data`: array of object

- *(array of objects)*
  - `created` (integer <unix_timestamp>) — The key's creation date.
  - `ecdsa_curve_name` (string (`prime256v1`, `secp384r1`)) — The ECDSA curve that the key uses.; `prime256v1`; `secp384r1`; `null` — The key is **not** an ECDSA key.
  - `ecdsa_public` (string) — The key’s ECDSA compressed public point, in hexadecimal format.; `null` — The key is **not** an ECDSA key.
  - `friendly_name` (string) — The key's friendly name.
  - `id` (string) — The key's ID.
  - `key_algorithm` (string (`rsaEncryption`, `id-ecPublicKey`)) — The key’s algorithm.; `rsaEncryption` — RSA.; `id-ecPublicKey` — ECDSA.
  - `modulus` (string) — The key's modulus, in hexadecimal format.; `null` — The key is **not** an RSA key.
  - `modulus_length` (integer) — The length, in bits, of the key's modulus.; `null` — The key is **not** an RSA key.

```bash
uapi --input=json --output=jsonpretty \
  --user=username \
  SSL \
  upload_key
```

## SNI Email Settings

<a id="ssl-disable-mail-sni"></a>
### `SSL::disable_mail_sni` — Disable SNI mail services for domain

`GET /execute/SSL/disable_mail_sni` · RW · rollback: none · since cPanel 11.48

This function disables SNI mail services on the specified domains. Note: Mail SNI is **always** enabled.; After you change the SNI status, you **must** run UAPI's `rebuild_mail_sni_config` function.; Functions that enable Mail SNI succeed with a warning that Mail SNI is always enabled.; Functions that disable Mail SNI fail and make no changes.

**Parameters**

- `domains` · **required** · string · e.g. `example.com|example1.com|example2.com` — A pipe-delimited list of the account's domains.

**Returns** `data`: object

- `failed_domains` (object) — An object containing the domains that failed to disable mail SNI.
- `updated_domains` (object) — AN object containing the domains with disabled mail SNI.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  disable_mail_sni \
  domains='example.com|example1.com|example2.com'
```

<a id="ssl-enable-mail-sni"></a>
### `SSL::enable_mail_sni` — Enable SNI mail services for domain

`GET /execute/SSL/enable_mail_sni` · RW · rollback: none · since cPanel 11.48

This function enables SNI mail services on the specified domains. Warning: Mail SNI is **always** enabled.; Mail SNI is **not** compatible with Webmail and will **not** function for any Webmail connection. Webmail connections use the cPanel service SSL certificate.; Functions that enable Mail SNI succeed with a warning that Mail SNI is always enabled.; Functions that disable Mail SNI fail and make no changes. Important: When you disable the *Calendars and Contacts*, *Mail Receive*, *Web Disk*, *Webmail*, **and** *Web Server* [roles](https://go.cpanel.net/howtouseserverprofiles#roles), the system **disables** this function.

**Parameters**

- `domains` · **required** · string · e.g. `example.com|example1.com|example2.com` — A pipe-delimited list of the account's domains.

**Returns** `data`: object

- `failed_domains` (object) — An object that contains the domains that did not enable mail SNI.
- `updated_domains` (object) — An object that contains the domains with disabled mail SNI.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  enable_mail_sni \
  domains='example.com|example1.com|example2.com'
```

<a id="ssl-is-mail-sni-supported"></a>
### `SSL::is_mail_sni_supported` — Return whether mail SNI is enabled

`GET /execute/SSL/is_mail_sni_supported` · RO · since cPanel 11.48

This function checks whether the sslinstall feature is enabled. Warning: Mail SNI is always enabled.; Mail SNI is **not** compatible with Webmail and will **not** function for any Webmail connection. Webmail connections use the cPanel service SSL certificate.; Functions that enable Mail SNI succeed with a warning that Mail SNI is always enabled.; Functions that disable Mail SNI will fail and make no changes. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: integer (`0`, `1`) — Whether the sslinstall feature is enabled.; `1` - Enabled.; `0` - Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  is_mail_sni_supported
```

<a id="ssl-is-sni-supported"></a>
### `SSL::is_sni_supported` — Return whether Apache web server supports mail SNI

`GET /execute/SSL/is_sni_supported` · RO · since cPanel 11.42

This function checks whether the Apache web server supports SNI. Important: When you disable the [Calendars and Contacts, Receive Mail, Web Disk, Webmail, and Web Server roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Returns** `data`: integer (`0`, `1`) — Whether the Apache web server supports SNI.; `1` - Supported.; `0` - **Not** supported.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  is_sni_supported
```

<a id="ssl-mail-sni-status"></a>
### `SSL::mail_sni_status` — Return status of domain's SNI mail services

`GET /execute/SSL/mail_sni_status` · RO · since cPanel 11.48

This function retrieves the status of the domain's SNI mail services. Warning: Mail SNI is **not** compatible with Webmail and will not function for any Webmail connection. Webmail connections use the cPanel service SSL certificate. Note: Mail SNI is always enabled.; Functions that enable Mail SNI succeed with a warning that Mail SNI is always enabled.; Functions that disable Mail SNI fail and make no changes.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — The account's domain.

**Returns** `data`: object

- `enabled` (integer (`0`, `1`)) — Whether SNI for mail is enabled.; `1` - SNI is enabled.; `0` - SNI is **not** enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  mail_sni_status \
  domain='example.com'
```

<a id="ssl-rebuild-mail-sni-config"></a>
### `SSL::rebuild_mail_sni_config` — Start SNI configuration files rebuild

`GET /execute/SSL/rebuild_mail_sni_config` · RW · rollback: none · since cPanel 11.48

This function rebuilds the SNI configuration files. Note:  You **must** run this function after you change the SNI status through the UAPI's `enable_mail_sni` or `disable_mail_sni` functions.; Mail SNI is **always** enabled.; Functions that enable Mail SNI succeed with a warning that Mail SNI is always enabled. Functions that disable Mail SNI fail and make no changes.; Functions that disable Mail SNI will fail and make no changes. Important: When you disable the _Calendars and Contacts_, _Receive Mail_, _Web Disk_, _Webmail_, **and**  _Web Server_ [roles](https://go.cpanel.net/serverroles), the system **disables** this function.

**Parameters**

- `reload_dovecot` · optional · integer (`0`, `1`) · default `1` · e.g. `1` — Whether to reload the Dovecot service after the system rebuilds the configuration files.; `1` - Reload Dovecot.; `0` - Do **not** reload Dovecot.

**Returns** `data`: object

- `success` (integer (`0`, `1`)) — Whether the system rebuilt the configuration files.; `1` - Configuration files rebuilt.; `0` - Configuration files **not** rebuilt.

```bash
uapi --output=jsonpretty \
  --user=username \
  SSL \
  rebuild_mail_sni_config
```

