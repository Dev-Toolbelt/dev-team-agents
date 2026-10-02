<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Account Security

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **ActiveSessions**: [`ActiveSessions::list_active_sessions`](#activesessions-list-active-sessions)

## ActiveSessions

<a id="activesessions-list-active-sessions"></a>
### `ActiveSessions::list_active_sessions` — Return active cPanel sessions

`GET /execute/ActiveSessions/list_active_sessions` · RO/RW: unspecified · since 138 · requires plugin `ActiveSessions`

This function returns the active cPanel sessions for the current user, so the account owner can review where their account is currently signed in and spot a session they do not recognize. Note:  This function returns an array, so UAPI's generic `api.filter_*`, `api.sort_*` and `api.paginate_*` parameters apply, and a caller-supplied sort replaces the default ordering of the `data` return value.; Session addresses are private, so this function is unavailable to demo (shared) accounts.

**Returns** `data`: array of object — The current user's active sessions, current session first, then the rest by most recently active.

- *(array of objects)*
  - `ip_address` (string) — Remote address the session connects from.
  - `is_current` (integer (`1`, `0`)) — Whether this is the session that made this request.; `1` - This is the current session.; `0` - It is another session.
  - `is_possessed` (integer (`1`, `0`)) — Whether an operator, such as the account's reseller or root, is acting as the user through this session.; `1` - The session is being operated on the user's behalf.; `0` - The user signed in directly.
  - `last_active` (integer <unix_timestamp>) — Unix timestamp of the session's last activity, taken from the session file's modification time.
  - `login_theme` (string) — The interface the session logged in to, for example `cpanel` or `webmail`.
  - `tfa_verified` (integer (`1`, `0`)) — Whether two-factor authentication was completed for this session.; `1` - Two-factor authentication was completed.; `0` - It was not.

```bash
uapi --output=jsonpretty \
  --user=username \
  ActiveSessions \
  list_active_sessions
```

