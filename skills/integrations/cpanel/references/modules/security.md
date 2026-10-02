<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Security

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Known SSH Hosts Management**: [`KnownHosts::create`](#knownhosts-create), [`KnownHosts::delete`](#knownhosts-delete), [`KnownHosts::update`](#knownhosts-update), [`KnownHosts::verify`](#knownhosts-verify)
- **Login Information**: [`LastLogin::get_last_or_current_logged_in_ip`](#lastlogin-get-last-or-current-logged-in-ip), [`Variables::get_session_information`](#variables-get-session-information)

## Known SSH Hosts Management

<a id="knownhosts-create"></a>
### `KnownHosts::create` — Create host

`GET /execute/KnownHosts/create` · RW · rollback: clean · since cPanel 74

This function registers a host in the cPanel account's `/home/user/.ssh/known_hosts` file.

**Parameters**

- `host_name` · **required** · string <hostname> or string <ipv4> — The hostname or IP address to add.
- `port` · optional · integer · default `22` · e.g. `1234` — The SSH port to use, if the system uses a non-standard SSH port.

**Returns** `data`: object

- `host` (array of object) — An array of objects containing information for the host.
  - *(array of objects)*
    - `host` (string <hostname> or string <ipv4>) — The hostname or IP address.
    - `key` (string) — The host's key.
    - `line` (string) — The host's entry in the `/home/user/.ssh/known_hosts` file, where `user` is the cPanel account username.
    - `meta` (object) — An object containing metadata about the host's public key.

```bash
uapi --output=jsonpretty \
  --user=username \
  KnownHosts \
  create \
  host_name='hostname.example.com'
```

<a id="knownhosts-delete"></a>
### `KnownHosts::delete` — Delete host

`GET /execute/KnownHosts/delete` · RW · rollback: clean · since cPanel 74

This function removes a host from the cPanel account's `/home/user/.ssh/known_hosts` file.

**Parameters**

- `host_name` · **required** · string <hostname> or string <ipv4> · e.g. `host.example.com` — The hostname or IP address of the host to delete.
- `port` · optional · integer · default `22` · e.g. `1234` — The SSH port to use.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  KnownHosts \
  delete \
  host_name='host.example.com'
```

<a id="knownhosts-update"></a>
### `KnownHosts::update` — Update host in the known_hosts file

`GET /execute/KnownHosts/update` · RW · rollback: clean · since cPanel 74

This function updates a host's entry in the cPanel account's /home/user/.ssh/known_hosts file.

**Parameters**

- `host_name` · **required** · string <hostname> or string <ipv4> · e.g. `host.example.com` — The host to update.
- `port` · optional · integer · default `22` · e.g. `1234` — The SSH port to use.

**Returns** `data`: object

- `host` (array of object) — An array of objects containing the host's information.
  - *(array of objects)*
    - `host` (string <hostname> or string <ipv4>) — The updated host and its associated key value.
    - `key` (string) — The host's key.
    - `line` (string) — The host's entry in the `/home/user/.ssh/known_hosts` file, where user is the cPanel account username.
    - `meta` (object) — An object containing metadata about the host's public key.

```bash
uapi --output=jsonpretty \
  --user=username \
  KnownHosts \
  update \
  host_name='host.example.com'
```

<a id="knownhosts-verify"></a>
### `KnownHosts::verify` — Validate host

`GET /execute/KnownHosts/verify` · RO · since cPanel 74

This function checks whether a host's public key exists in the cPanel account's `/home/user/.ssh/known_hosts` file.

**Parameters**

- `host_name` · **required** · string <domain> or string <ipv4> · e.g. `host.example.com` — The host to query.
- `port` · optional · integer · default `22` · e.g. `1234` — The SSH port to use.

**Returns** `data`: object

- `errors` (array of string) — An array of errors that the system generated.
- `failure_type` (string (`new`, `changed`)) — The reason why the system will register the hostname.; `new` — The host does **not** already exist.; `changed` — The host's information has changed.
- `host` (array of object) — An array of objects that contain information about the host.
  - *(array of objects)*
    - `host` (string <domain> or string <ipv4>) — The hostname or IP address.
    - `key` (string) — The host's key.
    - `line` (string) — The host's entry in the `/home/user/.ssh/known_hosts` file, where `user` is the cPanel account username.
    - `meta` (object) — An object that contains information about the host's public key.
- `status` (integer (`0`, `1`)) — Whether the host already exists in the `/home/user/.ssh/known_hosts` file, where `user` is the cPanel account username.; `1` — Exists.; `0` — The host does **not** already exist, or the system must re-register the hostna

```bash
uapi --output=jsonpretty \
  --user=username \
  KnownHosts \
  verify \
  host_name='host.example.com'
```

## Login Information

<a id="lastlogin-get-last-or-current-logged-in-ip"></a>
### `LastLogin::get_last_or_current_logged_in_ip` — Return last authenticated login IP address

`GET /execute/LastLogin/get_last_or_current_logged_in_ip` · RO · since cPanel 11.48

This function returns the IP address of the user who most recently logged in.

**Returns** `data`: array of string <ipv4> — The IP address of the user who most recently logged in.

```bash
uapi --output=jsonpretty \
  --user=username \
  LastLogin \
  get_last_or_current_logged_in_ip
```

<a id="variables-get-session-information"></a>
### `Variables::get_session_information` — Return web server's hostname

`GET /execute/Variables/get_session_information` · RO · since cPanel 86

This function retrieves a web server's hostname.

**Parameters**

- `name` · optional · string (`host`) · default `host` · e.g. `host` — The web server environment variable to retrieve. You can **only** retrieve the web server's hostname.; `host` is the only possible value.

**Returns** `data`: object

- `host` (string) — The web server's hostname.

```bash
uapi --output=jsonpretty \
  --user=username \
  Variables \
  get_session_information
```

