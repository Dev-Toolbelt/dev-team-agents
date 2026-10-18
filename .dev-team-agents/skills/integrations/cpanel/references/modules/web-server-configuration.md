<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Web Server Configuration

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **PHP**: [`EA4::get_php_recommendations`](#ea4-get-php-recommendations)
- **EA4**: [`EA4::get_recommendations`](#ea4-get-recommendations)

## PHP

<a id="ea4-get-php-recommendations"></a>
### `EA4::get_php_recommendations` — Get custom PHP recommendations.

`GET /execute/EA4/get_php_recommendations` · RO · since 82

This function returns a list of recommended PHP versions.

**Returns** `data`: array of string — An array of recommended PHP versions.

```bash
uapi --output=jsonpretty \
  --user=username \
  EA4 \
  get_php_recommendations
```

## EA4

<a id="ea4-get-recommendations"></a>
### `EA4::get_recommendations` — Get EA4 configuration recommendations

`GET /execute/EA4/get_recommendations` · RO · since cPanel 84

This function retrieves a list of EasyApache 4 (EA4) configuration recommendations.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  EA4 \
  get_recommendations
```

