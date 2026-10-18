<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Domains

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Subdomains**: [`SubDomain::changedocroot`](#subdomain-changedocroot)

## Subdomains

<a id="subdomain-changedocroot"></a>
### `SubDomain::changedocroot` — Change a subdomain or addon domain document root

`GET /execute/SubDomain/changedocroot` · RW · rollback: none · since 11

This function changes the document root for a subdomain or addon domain that the calling cPanel user owns. Important:  This function does **not** apply to the account's primary domain. Use the WHM API `set_primary_domain_docroot` function to change the document root for a primary domain.; The target directory must already exist before you call this function. The function does not create it.; This function does **not** move any files. You must ensure that the files exist in the new path when you call this function.; Any parked domains (`ServerAlias` entries) on the affected domain will inherit the new document root.; AutoSSL HTTP-01 renewals will fail if the new document root is empty or missing at renewal time.; To revert a document root change, call this function again with the original path. When you disable the [Web Server role](https://go.cpanel.net/serverroles#roles), the system **disables** this function.

**Parameters**

- `docroot` · **required** · string <path> · e.g. `public_html/myapp/public` — The new document root as a path relative to the user's home directory. The target directory **must** already exist, and the path **must** begin with `public_html/` if the *Restrict document roots to public_html* value is set to *On* in WHM's [*Tweak Settings*](https://go.cpanel.net/TweakSettings-Domains) interface (*WHM >> Home >> Server Configuration >> Tweak Settings*).
- `domain` · **required** · string <domain> · e.g. `sub.example.com` — The full domain name of the subdomain or addon domain whose document root you want to change. The domain must belong to the calling cPanel user.

```bash
uapi --user=username --output=jsonpretty \
  SubDomain \
  changedocroot \
  domain='sub.example.com' \
  docroot='public_html/myapp/public'
```

