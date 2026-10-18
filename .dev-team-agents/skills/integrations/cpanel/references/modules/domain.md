<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Domain

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Temporary Domains**: [`Domain::convert_temporary_to_registered`](#domain-convert-temporary-to-registered), [`Domain::is_temporary_domain`](#domain-is-temporary-domain), [`Domain::temporary_domain_is_disabled`](#domain-temporary-domain-is-disabled)
- **Domain**: [`Domain::rename_domain`](#domain-rename-domain)

## Temporary Domains

<a id="domain-convert-temporary-to-registered"></a>
### `Domain::convert_temporary_to_registered` — Convert a temporary domain to a registered domain

`POST /execute/Domain/convert_temporary_to_registered` · RW · rollback: none · since 130

This function converts a temporary domain into a registered domain and moves its document root files to the new document root location. Note:  For more information about temporary domains, read our [Temporary Domains](https://go.cpanel.net/cp-temporary-domain) documentation.; You cannot use this function to convert a cPanel account's main domain.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `wonderful-fushsia-owl.10-20-30-40.cpanel.site` — A valid temporary domain on the account.
- `registered` · **required** · string <domain> · e.g. `example.com` — A valid domain name.
- `docroot` · optional · string · e.g. `example.com` — The path to the domain's document root directory. If you do not specify a value, this parameter defaults to the domain's name. Note: The function will create a symlink in place of the previous temporary domain's document root directory. The symlink will point to the registered domain's document root.

**Returns** `data`: object

- `message` (string) — A message describing the result of the conversion.

```bash
uapi --output=jsonpretty \
  --user=username \
  Domain \
  convert_temporary_to_registered \
  domain=wonderful-fushsia-owl.10-20-30-40.cpanel.site \
  registered=example.com
```

<a id="domain-is-temporary-domain"></a>
### `Domain::is_temporary_domain` — Return whether a domain is temporary

`GET /execute/Domain/is_temporary_domain` · RO · since 130

This function determines whether a domain is temporary. Note: For more information about temporary domains, read our [Temporary Domains](https://go.cpanel.net/cp-temporary-domain) documentation.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `example.com` — A domain on the cPanel account.

**Returns** `data`: integer (`0`, `1`) — Whether the domain is a temporary domain.; `1` - The domain is a temporary domain.; `0` -  The domains is **not** a temporary domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  Domain \
  is_temporary_domain \
  domain=example.com
```

<a id="domain-temporary-domain-is-disabled"></a>
### `Domain::temporary_domain_is_disabled` — Return whether temporary domains are disabled

`GET /execute/Domain/temporary_domain_is_disabled` · RO · since 138

This function returns whether the temporary domains feature is disabled by server configuration. Note: For more information about temporary domains, read our [Temporary Domains](https://go.cpanel.net/cp-temporary-domain) documentation.

**Returns** `data`: object — An object containing the disabled state of the temporary domains feature.

- `is_disabled` (integer (`0`, `1`)) — Whether temporary domains are disabled by server configuration.; `1` - Temporary domains are disabled.; `0` - Temporary domains are enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  Domain \
  temporary_domain_is_disabled
```

## Domain

<a id="domain-rename-domain"></a>
### `Domain::rename_domain` — Rename a primary, addon, or alias domain

`POST /execute/Domain/rename_domain` · RW · rollback: none · since 138

This function renames a primary domain, addon domain, or alias domain on a cPanel account. The system updates all relevant configuration files, document root paths, and DNS entries automatically. Note:  You cannot rename a domain while another rename operation is in progress.; You cannot rename the server hostname.; The new domain must not already be configured on the account.

**Parameters**

- `domain` · **required** · string <domain> · e.g. `old.example.com` — The current domain name to rename.
- `new_domain` · **required** · string <domain> · e.g. `new.example.com` — The new domain name.
- `docroot` · optional · string · e.g. `new.example.com` — The path to the domain's document root directory. If you do not specify a value, this parameter defaults to the new domain name.

**Returns** `data`: object

- `message` (string) — A message describing the result of the rename.

```bash
uapi --output=jsonpretty \
  --user=username \
  Domain \
  rename_domain \
  domain=old.example.com \
  new_domain=new.example.com
```

