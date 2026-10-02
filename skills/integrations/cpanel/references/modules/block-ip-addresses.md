<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Block Ip Addresses

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Block IP**: [`BlockIP::add_ip`](#blockip-add-ip), [`BlockIP::remove_ip`](#blockip-remove-ip)

## Block IP

<a id="blockip-add-ip"></a>
### `BlockIP::add_ip` — Add IP address to cPanel account's block list

`GET /execute/BlockIP/add_ip` · RW · rollback: none · since 82

This function blocks IP addresses from accessing the domains on a cPanel account. **Important** When you disable the Web Server role, the system disables this function.

**Parameters**

- `ip` · **required** · string — The IP address or IP address range that you wish to block.

**Returns** `data`: array of string — IP addresses that were added, as translated by the system.

```bash
uapi --output=jsonpretty \
  --user=username \
  BlockIP \
  add_ip \
  ip='192.168.0.1/16'
```

<a id="blockip-remove-ip"></a>
### `BlockIP::remove_ip` — Remove IP address from cPanel account's block list

`GET /execute/BlockIP/remove_ip` · RW · rollback: none · since 82

This function unblocks IP addresses from accessing domains on a cPanel account. **Important** When you disable the Web Server role, the system disables this function.

**Parameters**

- `ip` · **required** · string — The IP address or IP address range that you wish to unblock.

**Returns** `data`: array of string — The IP addresses that the function removed, and the system translated.

```bash
uapi --output=jsonpretty \
  --user=username \
  BlockIP \
  remove_ip \
  ip='192.168.0.1/16'
```

