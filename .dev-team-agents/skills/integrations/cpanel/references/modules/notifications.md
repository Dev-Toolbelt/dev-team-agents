<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Notifications

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **Pushbullet**: [`Pushbullet::send_test_message`](#pushbullet-send-test-message)

## Pushbullet

<a id="pushbullet-send-test-message"></a>
### `Pushbullet::send_test_message` — Validate Pushbullet token

`GET /execute/Pushbullet/send_test_message` · RW · rollback: none · since cPanel 11.52

This function sends a Pushbullet™ test message to determine that the token is valid and that the account holder can receive the message.

**Parameters**

- `access_token` · **required** · string · e.g. `a1b2c3d4e5f6g7h8i9j0` — The Pushbullet access token. Note:  Your Pushbullet token is available on [Pushbullet's My Account](https://www.pushbullet.com/account) page under the *Access Token* heading.; This is confidential information that your server sends via a secure channel.

**Returns** `data`: object

- `message_id` (string) — The test message's ID.
- `payload` (object) — The payload from the Pushbullet server.

```bash
uapi --output=jsonpretty \
  --user=username \
  Pushbullet \
  send_test_message \
  access_token='a1b2c3d4e5f6g7h8i9j0'
```

