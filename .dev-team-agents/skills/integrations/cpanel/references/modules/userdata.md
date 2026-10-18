<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — UserData

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **UserData**: [`UserData::get_scoped_userdata`](#userdata-get-scoped-userdata), [`UserData::set_scoped_userdata`](#userdata-set-scoped-userdata)

## UserData

<a id="userdata-get-scoped-userdata"></a>
### `UserData::get_scoped_userdata` — Return scoped userdata mapping

`GET /execute/UserData/get_scoped_userdata` · RW · rollback: none · since 11.32

This function returns all userdata key/value pairs for a given scope.

**Parameters**

- `scope` · **required** · string · e.g. `example_scope` — The scope name whose userdata you wish to retrieve.

**Returns** `data`: object — The requested scoped userdata mapping.

```bash
uapi --output=jsonpretty \
--user=username \
UserData \
get_scoped_userdata \
scope=ui_prefs
```

<a id="userdata-set-scoped-userdata"></a>
### `UserData::set_scoped_userdata` — Set scoped userdata key/value

`GET /execute/UserData/set_scoped_userdata` · RW · rollback: none · since 11.32

This function sets (creates or updates) a userdata key/value pair within a specified scope and returns the full updated mapping for that scope.

**Parameters**

- `scope` · **required** · string · e.g. `example_scope` — The scope name to modify.
- `json` · optional · string · e.g. `{"theme":"dark"}` — A json string to save to the specified scope. Note: The "json" argument cannot be used with the "key" or "value" arguments.
- `key` · optional · string · e.g. `theme` — The userdata key to set. Note: The "json" argument cannot be used with the "key" or "value" arguments.
- `value` · optional · string · e.g. `dark` — The value to assign to the key. Note: The "json" argument cannot be used with the "key" or "value" arguments.

**Returns** `data`: object — The updated scoped userdata mapping after the key/value was set.

```bash
uapi --output=jsonpretty \
--user=username \
UserData \
set_scoped_userdata \
scope=ui_prefs \
key=theme \
value=dark
```

