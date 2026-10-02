<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — ServiceProxy

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **ServiceProxy**: [`ServiceProxy::get_service_proxy_backends`](#serviceproxy-get-service-proxy-backends), [`ServiceProxy::set_service_proxy_backends`](#serviceproxy-set-service-proxy-backends), [`ServiceProxy::unset_all_service_proxy_backends`](#serviceproxy-unset-all-service-proxy-backends)

## ServiceProxy

<a id="serviceproxy-get-service-proxy-backends"></a>
### `ServiceProxy::get_service_proxy_backends` — Return a cPanel account’s service proxying setup

`GET /execute/ServiceProxy/get_service_proxy_backends` · RO · since cPanel 96

This function reports a cPanel account's [service proxying](https://go.cpanel.net/ServiceProxying) configuration.

**Returns** `data`: array of object — The account’s service proxying backends.

- *(array of objects)*
  - `backend` (string <domain>) — The name of the server to which the system will proxy requests for this service group.
  - `service_group` (string) — The name of the proxying service group, if applicable.; null — The account’s general service proxying backend.

```bash
uapi --output=jsonpretty \
  --user=username \
  ServiceProxy \
  get_service_proxy_backends
```

<a id="serviceproxy-set-service-proxy-backends"></a>
### `ServiceProxy::set_service_proxy_backends` — Add cPanel account service proxying

`GET /execute/ServiceProxy/set_service_proxy_backends` · RW · rollback: none · since cPanel 96

This function lets you configure a cPanel account's [service proxying](https://go.cpanel.net/ServiceProxying). Note:  If the [Web Server](https://go.cpanel.net/howtouseserverprofiles#roles) role is active on the server, this function rebuilds the user's web virtual hosts (vhosts) and restarts the web server.; If the system cannot rebuild the user's vhosts, the API call will still succeed. However, the function returns a failure warning in the metadata.; To remove an account's service proxying, use the UAPI `unset_all_service_proxy_backends` function.

**Parameters**

- `general` · optional · string <hostname> or string <ipv4> — The hostname or IP address to assign as the server that handles the account's service proxy requests. The proxy backend must be routable. The server rejects non-routable IP literals (loopback, RFC 1918, CGNAT, and cloud-metadata addresses) and obfuscated encodings of those addresses; use a routable hostname or IP address instead. This parameter defaults to the existing service proxy configuration, if one exists.
- `service_group` · optional · string (`Mail`) — The name of a service group for which to assign a proxy backend. The corresponding `service_group_backend` value will be the service group's new proxy backend.; `Mail` — The [Mail service group](https://go.cpanel.net/ServiceProxying#Mail). This parameter defaults to the existing setting, if one exists. Note:  When you call this parameter, you **must** include a corresponding `service_group_backend` value.; To add multiple `service_group` values, increment the parameter name. For example, `service_group`, `service_group-1`, and `service_group-2`.
- `service_group_backend` · optional · string <hostname> or string <ipv4> — The hostname or IP address of the server to assign as the corresponding `service_group` value's proxy backend server. This parameter defaults to the existing setting, if one exists. Note:  When you call this parameter, you **must** include a corresponding `service_group` value.; To add multiple `service_group_backend` values, increment the parameter name. For example, `service_group_backend`, `service_group_backend-1`, and `service_group_backend-2`.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  ServiceProxy \
  set_service_proxy_backends
```

<a id="serviceproxy-unset-all-service-proxy-backends"></a>
### `ServiceProxy::unset_all_service_proxy_backends` — Remove cPanel account service proxying

`GET /execute/ServiceProxy/unset_all_service_proxy_backends` · RW · rollback: none · since cPanel 96

This function removes a cPanel account's [service proxying](https://go.cpanel.net/ServiceProxying). Note:  If the [Web Server](https://go.cpanel.net/howtouseserverprofiles#roles) role is active on the server, this function rebuilds the cPanel user's web virtual hosts (vhosts) and restarts the web server.; If the system **cannot** rebuild the cPanel user's vhosts, the API call will still succeed. However, the function returns a failure warning in the metadata.; To set a service proxying for a cPanel account, use the UAPI `set_service_proxy_backends` function.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  ServiceProxy \
  unset_all_service_proxy_backends
```

