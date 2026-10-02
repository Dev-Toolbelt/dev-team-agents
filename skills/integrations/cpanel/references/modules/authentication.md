<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Authentication

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **External Authentication**: [`ExternalAuthentication::configured_modules`](#externalauthentication-configured-modules), [`ExternalAuthentication::get_authn_links`](#externalauthentication-get-authn-links), [`ExternalAuthentication::has_external_auth_modules_configured`](#externalauthentication-has-external-auth-modules-configured), [`ExternalAuthentication::remove_authn_link`](#externalauthentication-remove-authn-link)
- **Two-Factor Settings**: [`TwoFactorAuth::generate_user_configuration`](#twofactorauth-generate-user-configuration), [`TwoFactorAuth::get_team_user_configuration`](#twofactorauth-get-team-user-configuration), [`TwoFactorAuth::get_user_configuration`](#twofactorauth-get-user-configuration), [`TwoFactorAuth::remove_user_configuration`](#twofactorauth-remove-user-configuration), [`TwoFactorAuth::set_user_configuration`](#twofactorauth-set-user-configuration)

## External Authentication

<a id="externalauthentication-configured-modules"></a>
### `ExternalAuthentication::configured_modules` — Return server's external authentication providers

`GET /execute/ExternalAuthentication/configured_modules` · RO · since cPanel 54

This function lists the display information for your server's available and configured external authentication identity provider modules.

**Returns** `data`: array of object

- *(array of objects)*
  - `color` (string <RGB>) — The background color of the button on the cPanel interface.
  - `display_name` (string) — The identity provider's friendly name.
  - `documentation_url` (string <url>) — The public URL of the identity provider's implementation documentation.
  - `icon` (string <base64 image>) — The icon file to display on the button in the cPanel login interface.
  - `icon_type` (string <MIME>) — The icon file's MIME type.
  - `label` (string) — The text label of the login icon in the cPanel login interface.
  - `link` (string <url>) — link to the identity provider's configuration for the appropriate service on the system.
  - `provider_name` (string) — The identity provider's system name.
  - `textcolor` (string <RGB>) — The color of the text label in the cPanel login interface.

```bash
uapi --output=jsonpretty \
  --user=username \
  ExternalAuthentication \
  configured_modules
```

<a id="externalauthentication-get-authn-links"></a>
### `ExternalAuthentication::get_authn_links` — Return external authentication links

`GET /execute/ExternalAuthentication/get_authn_links` · RO · since cPanel 54

This function lists the external authentication links to the current cPanel account.

**Returns** `data`: array of object

- *(array of objects)*
  - `link_time` (integer <unix_timestamp>) — When the user linked their account to the identity provider.
  - `preferred_username` (string) — The preferred username of the account on the identity provider.
  - `provider_id` (string) — The system's unique key for the identity provider.
  - `provider_protocol` (string) — The identity provider's protocol.
  - `subject_unique_identifier` (integer) — The unique identifier for the user at the identity provider.

```bash
uapi --output=jsonpretty \
  --user=username \
  ExternalAuthentication \
  get_authn_links
```

<a id="externalauthentication-has-external-auth-modules-configured"></a>
### `ExternalAuthentication::has_external_auth_modules_configured` — Return external authentication user status

`GET /execute/ExternalAuthentication/has_external_auth_modules_configured` · RO · since cPanel 66

This function determines whether the user enabled external authentication modules.

**Returns** `data`: integer (`0`, `1`) — Whether the cPanel user enabled any external modules.; `1` - Enabled.; `0` - **Not** enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  ExternalAuthentication \
  has_external_auth_modules_configured
```

<a id="externalauthentication-remove-authn-link"></a>
### `ExternalAuthentication::remove_authn_link` — Remove external authentication link

`GET /execute/ExternalAuthentication/remove_authn_link` · RW · rollback: none · since cPanel 54

This function removes a link to an account at an external authentication identity provider.

**Parameters**

- `provider` · **required** · string · e.g. `cpanelid` — The name of the identity provider.
- `subject_unique_identifier` · **required** · string · e.g. `123456789012345678901` — The unique identifier for the user at the identity provider.

**Returns** `data`: object

```bash
uapi --output=jsonpretty \
  --user=username \
  ExternalAuthentication \
  remove_authn_link \
  provider='cpanelid' \
  subject_unique_identifier='123456789012345678901'
```

## Two-Factor Settings

<a id="twofactorauth-generate-user-configuration"></a>
### `TwoFactorAuth::generate_user_configuration` — Create 2FA authentication code

`GET /execute/TwoFactorAuth/generate_user_configuration` · RW · rollback: none · since cPanel 54

This function generates an authentication code to enable configuration of two-factor authentication.

**Returns** `data`: object

- `otpauth_str` (string) — A one-time authentication URL to encode as the QR code.
- `secret` (string) — A generated code for use with two-factor authentication.

```bash
uapi --output=jsonpretty \
  --user=username \
  TwoFactorAuth \
  generate_user_configuration
```

<a id="twofactorauth-get-team-user-configuration"></a>
### `TwoFactorAuth::get_team_user_configuration` — Return team user 2FA config

`GET /execute/TwoFactorAuth/get_team_user_configuration` · RW · rollback: none · since cPanel 54

This function retrieves a [team user's](https://go.cpanel.net/manage-team) configuration settings for two-factor authentication.

**Parameters**

- `team_user` · **required** · string · e.g. `user@example.com` — The team user's username. Note: The username will always precede the cPanel account's primary domain.

**Returns** `data`: object

- `is_enabled` (integer (`0`, `1`)) — Whether two-factor authentication is enabled for the team user.; `1` - Enabled.; `0` - Disabled.
- `issuer` (string) — The authentication code issuer's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  TwoFactorAuth \
  get_team_user_configuration \
  team_user=teamuser
```

<a id="twofactorauth-get-user-configuration"></a>
### `TwoFactorAuth::get_user_configuration` — Return cPanel account 2FA config

`GET /execute/TwoFactorAuth/get_user_configuration` · RO · since cPanel 54

This function retrieves the cPanel account user's configuration settings for two-factor authentication.

**Returns** `data`: object

- `is_enabled` (integer (`0`, `1`)) — Whether two-factor authentication is enabled for the account.; `1` - Enabled.; `0` - Disabled.
- `issuer` (string) — The authentication code issuer's name.

```bash
uapi --output=jsonpretty \
  --user=username \
  TwoFactorAuth \
  get_user_configuration
```

<a id="twofactorauth-remove-user-configuration"></a>
### `TwoFactorAuth::remove_user_configuration` — Remove 2FA config

`GET /execute/TwoFactorAuth/remove_user_configuration` · RW · rollback: none · since cPanel 54

This function removes the user from the two-factor authentication `userdata` file.

**Returns** `data`: object

- `tfa_removed` (integer (`1`)) — Whether the system removed the user from the two-factor authentication `userdata` file.; `1` - Removed.

```bash
uapi --output=jsonpretty \
  --user=username \
  TwoFactorAuth \
  remove_user_configuration
```

<a id="twofactorauth-set-user-configuration"></a>
### `TwoFactorAuth::set_user_configuration` — Save 2FA config

`GET /execute/TwoFactorAuth/set_user_configuration` · RW · rollback: none · since cPanel 54

This function configures the two-factor authentication settings for an account.

**Parameters**

- `secret` · **required** · string · e.g. `JBSWY3DPEHPK3PXP` — The 16-character string that UAPI's `TwoFactorAuth::generate_user_configuration` function generates.
- `tfa_token` · **required** · integer · e.g. `528112` — The six-digit security code that the time-based one-time password (TOTP) authentication app generates.

**Returns** `data`: object

- `tfa_configured` (integer (`0`, `1`)) — Whether two-factor authentication is enabled.; `1` - Enabled.; `1` - Disabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  TwoFactorAuth \
  set_user_configuration \
  secret='JBSWY3DPEHPK3PXP' \
  tfa_token='528112'
```

