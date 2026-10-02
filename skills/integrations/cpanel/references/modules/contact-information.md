<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Contact Information

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **notifications**: [`ContactInformation::get_notification_preferences`](#contactinformation-get-notification-preferences), [`ContactInformation::set_notification_preferences`](#contactinformation-set-notification-preferences)
- **Contact Information**: [`ContactInformation::get_pushbullet_access_token`](#contactinformation-get-pushbullet-access-token), [`ContactInformation::set_email_addresses`](#contactinformation-set-email-addresses), [`ContactInformation::set_pushbullet_access_token`](#contactinformation-set-pushbullet-access-token), [`ContactInformation::unset_email_addresses`](#contactinformation-unset-email-addresses), [`Contactus::is_enabled`](#contactus-is-enabled)

## notifications

<a id="contactinformation-get-notification-preferences"></a>
### `ContactInformation::get_notification_preferences` — Return the account's notification preferences.

`GET /execute/ContactInformation/get_notification_preferences` · RO

Use this function to get a cPanel or Webmail account's notification preferences.

**Returns** `data`: array of object — An array of objects describing the cPanel or Webmail account's notification preferences.

- *(array of objects)*
  - `additionalProperties` (string) — 
  - `descp` (string) — A description of the notification setting.
  - `enabled` (integer (`0`, `1`)) — - 1 - Notification is enabled; 0 - Notification is disabled
  - `name` (string) — The notification preference key name.

```bash
uapi --output=jsonpretty \
  --user=username \
  ContactInformation \
  get_notification_preferences
```

<a id="contactinformation-set-notification-preferences"></a>
### `ContactInformation::set_notification_preferences` — Set the account's notification preferences.

`POST /execute/ContactInformation/set_notification_preferences` · RW · rollback: none

Use this function to set the logged in cPanel or Webmail account's notification preferences. Note: To set a cPanel account's notification email address, call `set_email_addresses`. To return the list of account notification preferences you can set with `set_notification_preferences`, call `get_notification_preferences`.

**Request body** (`application/json`)

- `preferences` (object) — 

**Returns** `data`: array of object — An array of cPanel and Webmail account notification preferences, including the newly-set preferences.

- *(array of objects)*
  - `additionalProperties` (string) — 
  - `descp` (string) — A description of the notification setting.
  - `enabled` (integer (`0`, `1`)) — - 1 - Notification is enabled; 0 - Notification is disabled
  - `name` (string) — The notification preference key name.

```bash
echo '{"preferences": { "notify_account_authn_link": 1 }}' | \
  uapi --output=jsonpretty \
  --user=muser \
  --input=json \
  ContactInformation \
  set_notification_preferences
```

## Contact Information

<a id="contactinformation-get-pushbullet-access-token"></a>
### `ContactInformation::get_pushbullet_access_token` — Return Pushbullet access token

`GET /execute/ContactInformation/get_pushbullet_access_token` · RW · rollback: none · since 130

This function retrieves the cPanel account's Pushbullet™ access token.

**Returns** `data`: string — The cPanel account's Pushbullet access token.

```bash
uapi --output=jsonpretty \
  --user=username \
  ContactInformation \
  get_pushbullet_access_token
```

<a id="contactinformation-set-email-addresses"></a>
### `ContactInformation::set_email_addresses` — Set contact email address(es)

`GET /execute/ContactInformation/set_email_addresses` · RW · rollback: none · since 102

Use this function to set an account's contact email address(es). To unset all contact email addresses, call `unset_email_addresses`.

**Parameters**

- `address` · **required** · array of string <email> — The account’s new contact email addresses.
- `old_address` · **required** · array of string <email> — The account’s existing contact email addresses. If this list does not match the account’s current current email address(es), then the request will fail. This control is here to prevent race conditions.
- `password` · **required** · string · e.g. `q1df%D9<z0ShqdxRP%^` — The account’s password.

```bash
uapi --output=jsonpretty \
  --user=username \
  ContactInformation \
  set_email_addresses \
  address='foo@example.com' address='bar@example.com' \
  old_address='old1@example.com' \
  password='q1df%D9<z0ShqdxRP%^'
```

<a id="contactinformation-set-pushbullet-access-token"></a>
### `ContactInformation::set_pushbullet_access_token` — Update Pushbullet access token

`GET /execute/ContactInformation/set_pushbullet_access_token` · RW · rollback: none · since 130

This function updates the cPanel account's Pushbullet™ access token.

**Parameters**

- `pushbullet_access_token` · **required** · string · e.g. `a1b2c3d4e5f6g7h8i9j0` — The account’s new Pushbullet access token.

```bash
uapi --output=jsonpretty \
  --user=username \
  ContactInformation \
  set_pushbullet_access_token \
  pushbullet_access_token='a1b2c3d4e5f6g7h8i9j0'
```

<a id="contactinformation-unset-email-addresses"></a>
### `ContactInformation::unset_email_addresses` — Unset contact email addresses

`GET /execute/ContactInformation/unset_email_addresses` · RW · rollback: none · since 102

Use this function to unset all contact email address for an account. To set contact email address(es), call `set_email_addresses`.

**Parameters**

- `old_address` · **required** · array of string <email> — The account’s existing contact email addresses. If this list does not match the account’s current current email address(es), then the request will fail. This control is here to prevent race conditions.
- `password` · **required** · string · e.g. `q1df%D9<z0ShqdxRP%^` — The account’s password.

```bash
uapi --output=jsonpretty \
  --user=username \
  ContactInformation \
  unset_email_addresses \
  old_address='old1@example.com' \
  password='q1df%D9<z0ShqdxRP%^'
```

<a id="contactus-is-enabled"></a>
### `Contactus::is_enabled` — Return whether contact option is enabled

`GET /execute/Contactus/is_enabled` · RO · since cPanel 11.42

This function checks whether the cPanel account can contact their hosting provider from the cPanel interface.

**Returns** `data`: object

- `enabled` (integer (`0`, `1`)) — Whether the cPanel account can contact their hosting provider from the cPanel interface.; `1` — The cPanel account can contact their hosting provider from the cPanel interface.; `0` — The cPanel account **cannot** contac

```bash
uapi --output=jsonpretty \
  --user=username \
  Contactus \
  is_enabled
```

