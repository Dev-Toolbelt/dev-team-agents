<!-- GENERATED from https://api.docs.cpanel.net/_spec/specifications/cpanel.openapi.json (cPanel UAPI 11.138.0.10). Do not hand-edit; regenerate instead. -->
# UAPI — Site Quality Monitoring

Base: `https://<host>:2083/execute/<Module>/<function>` · auth: `Authorization: cpanel <user>:<token>` · CLI: `uapi --output=jsonpretty --user=<user> <Module> <function> key=value`. Conventions: [calling-conventions.md](../calling-conventions.md).

Legend: **RO** = read-only (`x-readonly`), **RW** = changes data; *rollback* = what happens on failure (`clean` = rolled back, `none` = no rollback, `lossy` = partial).

## Contents

- **SiteQuality**: [`SiteQuality::create_project`](#sitequality-create-project), [`SiteQuality::create_site_quality_user`](#sitequality-create-site-quality-user), [`SiteQuality::delete_site_quality_user`](#sitequality-delete-site-quality-user), [`SiteQuality::get_all_scores`](#sitequality-get-all-scores), [`SiteQuality::get_app_token`](#sitequality-get-app-token), [`SiteQuality::get_monitored_domains`](#sitequality-get-monitored-domains), [`SiteQuality::get_monitored_system_scores`](#sitequality-get-monitored-system-scores), [`SiteQuality::has_site_quality_user`](#sitequality-has-site-quality-user), [`SiteQuality::is_site_quality_user_enabled`](#sitequality-is-site-quality-user-enabled), [`SiteQuality::reset_config`](#sitequality-reset-config), [`SiteQuality::send_activation_email`](#sitequality-send-activation-email), [`SiteQuality::update_domain`](#sitequality-update-domain), [`SiteQuality::verify_code`](#sitequality-verify-code)

## SiteQuality

<a id="sitequality-create-project"></a>
### `SiteQuality::create_project` — Add domain to monitoring

`POST /execute/SiteQuality/create_project` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function creates a Site Quality Monitoring project. A project bundles together one or more URLs with a shared domain for monitoring.

**Parameters**

- `name` · **required** · string · e.g. `MyProject` — The name of the project to create.
- `url` · **required** · string · e.g. `https://example.com` — The URL to monitor.
- `standard_alerting` · optional · integer (`0`, `1`, `None`) · default `None` · e.g. `0` — Whether to enable standard email alerts.; `1` - Enable standard alerting.; `0` - Do not enable standard alerting.; `null` - Do not enable standard alerting.
- `system_type` · optional · string · default `Website` · e.g. `Website` — The monitoring template to use for the project.

**Returns** `data`: object — An object that contains project attributes.

- `id` (integer) — The project ID number.
- `identifier` (string) — The project identifier.
- `location` (string) — The region where monitoring checks originate.
- `name` (string) — The project's name.
- `role` (object) — Information about the user that owns the project.
  - `id` (integer) — The user's role ID number.
  - `name` (string) — The user's role title.
- `systems` (array of object) — Information about the system that the project monitors.
  - *(array of objects)*
    - `name` (string) — The name of the system.
    - `description` (string) — A description of the system.
    - `domain` (string) — The system's base domain.
    - `id` (integer) — The system's ID number.
    - `interval` (string) — The time interval for monitoring checks.
    - `limits` (object) — Restrictions placed on the monitoring checks.
    - `system_type` (object) — The monitoring template used for the system.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  create_project \
  name=MyProject \
  url='https://example.com'
```

<a id="sitequality-create-site-quality-user"></a>
### `SiteQuality::create_site_quality_user` — Register cPanel user for monitoring

`POST /execute/SiteQuality/create_site_quality_user` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function creates a Site Quality Monitoring user account associated with a cPanel user account.

**Parameters**

- `email` · **required** · string · e.g. `username@example.com` — The cPanel account's email address.
- `password` · optional · string · e.g. `An3xample!?` — The account's password. Note: If no password is given, one is auto-generated. The system does not save this value.

**Returns** `data`: object — An object that contains user attributes.

- `app_token` (string) — The long-lived token for this account.
- `username` (string) — The account's username.
- `enabled` (boolean) — Whether the account is enabled to process user data.; `false` - The account is disabled.; `true` - The account is enabled.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  create_site_quality_user \
  email=username@example.com
```

<a id="sitequality-delete-site-quality-user"></a>
### `SiteQuality::delete_site_quality_user` — Delete Site Quality Monitoring account

`GET /execute/SiteQuality/delete_site_quality_user` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function initiates the deletion of the Site Quality Monitoring user account associated with a cPanel user account.

**Returns** `data`: object — An object that contains whether the user has been deleted.

- `deleted` (integer (`0`, `1`)) — Whether or not the account has been successfully deleted.; `1` - Success; `0` - Failed

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  delete_site_quality_user
```

<a id="sitequality-get-all-scores"></a>
### `SiteQuality::get_all_scores` — Return all projects' monitoring results

`POST /execute/SiteQuality/get_all_scores` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function returns information about the cPanel user's Site Quality Monitoring projects' most recent monitoring check results.

**Parameters**

- `verbose` · **required** · integer (`0`, `1`, `None`) · default `None` · e.g. `1` — Whether to enable verbose output. ** Note: ** This includes information about the user's Site Quality Monitoring project's most recent results in each monitoring check subcategory.

**Returns** `data`: object — An object that contains score details.

- `scores` (array of object) — An array of objects containing score data and the associated system information.
  - *(array of objects)*
    - `system` (object) — 
    - `scores` (object) — 

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  get_all_scores \
  verbose=1
```

<a id="sitequality-get-app-token"></a>
### `SiteQuality::get_app_token` — Return koality authentication token

`GET /execute/SiteQuality/get_app_token` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function returns the long-lived application token used to authenticate with <a href="https://go.cpanel.net/5k" target="_blank">koality's</a> authentication servers.

**Returns** `data`: object — An object that contains user authentication attributes.

- `app_token` (string) — The long-lived token for this account.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  get_app_token
```

<a id="sitequality-get-monitored-domains"></a>
### `SiteQuality::get_monitored_domains` — Return the user's monitored domains.

`GET /execute/SiteQuality/get_monitored_domains` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function returns a list of the user's Site Quality Monitoring-enabled domains. It also returns the domains' associated project and system IDs.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  get_monitored_domains
```

<a id="sitequality-get-monitored-system-scores"></a>
### `SiteQuality::get_monitored_system_scores` — Return status for a user's monitored domains.

`GET /execute/SiteQuality/get_monitored_system_scores` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function returns a monitoring score and system ID for each domain the user monitors with Site Quality Monitoring.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  get_monitored_system_scores
```

<a id="sitequality-has-site-quality-user"></a>
### `SiteQuality::has_site_quality_user` — Validate monitoring account existence

`GET /execute/SiteQuality/has_site_quality_user` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function returns whether the cPanel user has an associated Site Quality Monitoring account.

**Returns** `data`: object — An object that contains Site Quality Monitoring user attributes.

- `has_site_quality_user` (integer (`0`, `1`)) — Whether the cPanel user has an associated Site Quality Monitoring account.; `1` - The user does have an associated account.; `0` - The user does not have an associated account.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  has_site_quality_user
```

<a id="sitequality-is-site-quality-user-enabled"></a>
### `SiteQuality::is_site_quality_user_enabled` — Validate monitoring account enablement

`GET /execute/SiteQuality/is_site_quality_user_enabled` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function verifies that <a href="https://go.cpanel.net/5k" target="_blank">koality</a> has enabled the cPanel user's Site Quality Monitoring account.

**Returns** `data`: object — An object that contains user attributes.

- `enabled` (integer (`0`, `1`)) — Whether or not the account has been enabled.; `1` - Enabled; `0` - Disabled

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  is_site_quality_user_enabled
```

<a id="sitequality-reset-config"></a>
### `SiteQuality::reset_config` — Remove monitoring user from cPanel configuration

`GET /execute/SiteQuality/reset_config` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function will remove Site Quality Monitoring account data from the cPanel user's configuration. Note:  This function will prevent cPanel & WHM from automatically logging the user into their Site Quality Monitoring account.; This function does not delete the Site Quality Monitoring account from the <a href="https://go.cpanel.net/5k" target="_blank">koality</a> servers.

**Returns** `data`: object — An object that contains the status of the account data removal from the cPanel user's configuration.

- `reset` (integer (`0`, `1`)) — Whether the account data was removed.; `1` - The account data was removed.; `0` - The account data was not removed.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  reset_config
```

<a id="sitequality-send-activation-email"></a>
### `SiteQuality::send_activation_email` — Request activation email

`GET /execute/SiteQuality/send_activation_email` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function sends a Site Quality Monitoring activation email to the currently-authenticated Site Quality Monitoring user. Note: This email contains the Site Quality Monitoring activation code.

**Returns** `data`: object — An object that contains the activation email request status.

- `send_activation_email` (integer (`0`, `1`)) — Whether the request to send an activation email was successful.; `1` - The request was successful.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  reset_config
```

<a id="sitequality-update-domain"></a>
### `SiteQuality::update_domain` — Update domain name in Site Quality Monitoring project

`POST /execute/SiteQuality/update_domain` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function updates the domain name for a Site Quality Monitoring project. It searches through all projects owned by the user to find systems that match the specified old domain and updates them to use the new domain. This is typically used when a website's domain name changes and the monitoring configuration needs to be updated accordingly.

**Parameters**

- `new_domain` · **required** · string · e.g. `newdomain.com` — The new domain name to replace the old domain in the Site Quality Monitoring project.
- `old_domain` · **required** · string · e.g. `olddomain.com` — The current domain name that needs to be updated in the Site Quality Monitoring project.

**Returns** `data`: object — An object that contains the updated system information from the Site Quality Monitoring API.

- `system` (object) — Information about the updated monitoring system.
  - `id` (integer) — The system's ID number.
  - `name` (string) — The updated system name (typically the new domain).
  - `system_size` (object) — Information about the system's subscription plan.
  - `url` (string) — The updated system URL with the new domain.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  update_domain \
  old_domain=olddomain.com \
  new_domain=newdomain.com
```

<a id="sitequality-verify-code"></a>
### `SiteQuality::verify_code` — Validate activation code

`GET /execute/SiteQuality/verify_code` · RO/RW: unspecified · since 110 · requires plugin `SiteQuality`

This function validates the activation code in a cPanel user's Site Quality Monitoring registration email.

**Parameters**

- `code` · **required** · string · e.g. `123456` — The user's Site Quality Monitoring activation code. Note: A user will receive an email with their activation code when they create a Site Quality Monitoring user account.

**Returns** `data`: object — An object that contains information about the user's activation code validation.

- `status` (integer (`0`, `1`)) — Whether the user's activation code is valid.; `1` - Valid.; `0` - Invalid.

```bash
uapi --output=jsonpretty \
  --user=username \
  SiteQuality \
  verify_code
```

