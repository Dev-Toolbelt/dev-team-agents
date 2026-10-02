<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — cPanel Plugin Framework

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Plugins**: [`Plugins::can_show_promotions`](#plugins-can-show-promotions), [`Plugins::create_user`](#plugins-create-user)

## Plugins

<a id="plugins-can-show-promotions"></a>
### `Plugins::can_show_promotions` — Enable plugin promotions

`GET /execute/Plugins/can_show_promotions` · RO/RW: unspecified · since 110 · requires plugin `Plugins`

This function determines if plugin promotions show in cPanel.

**Parameters**

- `plugin` · **required** · string · e.g. `koality` — The plugin whose promotions to target. Note: The only valid value is 'koality', which targets Site Quality Monitoring.

**Returns** `data`: object — An object that contains information about the plugin's promotions.

- `can_show_promotions` (integer (`0`, `1`)) — Whether the plugin can show promotions.; `1` — Can show promotions.; `0` — Can not show promotions.

```bash
uapi --output=jsonpretty \
  --user=username \
  Plugins \
  can_show_promotions
```

<a id="plugins-create-user"></a>
### `Plugins::create_user` — Create third-party user

`GET /execute/Plugins/create_user` · RO/RW: unspecified · since 118 · requires plugin `Plugins`

This function implements third-party user creation.

**Parameters**

- `Parameters` · optional · object · e.g. `{"plugin": "xovi"}` — The parameters required for the third-party account.

**Returns** `data`: object — The returned data from a third-party API call.

```bash
uapi --output=jsonpretty \
  --user=username \
  Plugins \
  create_user \
  plugin='xovi'
```

