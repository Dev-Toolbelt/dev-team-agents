# UAPI Authentication

Source: cPanel *API Tokens in cPanel* and *Introduction to UAPI* guides (api.docs.cpanel.net/cpanel/tokens, /cpanel/introduction).

## Methods at a Glance

| Method | Where it runs | Credential | Use for |
|---|---|---|---|
| **API token** (header) | Any HTTP client, remote | `Authorization: cpanel <user>:<TOKEN>` | Integrations, CI/CD, scripts — **default choice** |
| **Basic auth** | Any HTTP client, remote | `Authorization: Basic base64(user:password)` | Legacy only; exposes the account password |
| **Session (cookie + `cpsess` token)** | Browser / cPanel UI session | Session cookie + `/cpsess##########/` URL segment | Code running inside a logged-in cPanel/Webmail session |
| **CLI `uapi`** | Shell on the cPanel server | OS user (`--user=` when root) | Server-side automation, cron, deploy hooks |
| **LiveAPI (PHP / Perl)** | Inside cPanel (plugins, theme pages) | Implicit — the logged-in account | cPanel plugins |
| **WHM API 1 `uapi_cpanel`** | WHM port `2087` | WHM token (root/reseller) | Running UAPI **on behalf of** many accounts |

> UAPI cannot be called on WHM ports (`2086`/`2087`) directly — only through WHM API 1's `uapi_cpanel` proxy.

## API Tokens

### Create

- **UI:** cPanel » Security » *Manage API Tokens*.
- **API:** `Tokens::create_full_access` — params `name` (required; `[A-Za-z0-9_-]`), `expires_at` (Unix timestamp; omitted = never expires), `readonly` (`1` = only non-mutating calls are accepted, rejected server-side otherwise).
- The token value is returned **once** in `data.token`. Store it in a secret manager immediately.

```bash
uapi --output=jsonpretty --user=username Tokens create_full_access name='ci-deploy' expires_at=1767225600
```

### Manage

| Function | Purpose |
|---|---|
| `Tokens::list` | List tokens (names, creation/expiry — never the secret) |
| `Tokens::rename` | Rename a token |
| `Tokens::revoke` | Delete a token (`name`) |

- Expired tokens are **not** deleted automatically — revoke them.
- A token only reaches the features the account has. If *File Manager* is disabled for the account, the token cannot call `Fileman::*`.
- Prefer `readonly=1` for monitoring/reporting integrations.

### Use

```bash
curl -sS -H "Authorization: cpanel $CPANEL_USER:$CPANEL_TOKEN" \
  "https://$CPANEL_HOST:2083/execute/Quota/get_quota_info"
```

| Item | Example |
|---|---|
| Host | `example.com` or the server hostname/IP |
| Port | `2083` (HTTPS, cPanel) — `2082` plain HTTP, avoid |
| Path | `/execute/<Module>/<function>` |
| Header | `Authorization: cpanel <cpanel-username>:<token>` |

## Session-Based Calls (browser)

Inside a cPanel or Webmail session, URLs carry the session security token:

```
https://example.com:2083/cpsess##########/execute/Email/list_pops
```

| Port | Context |
|---|---|
| `2083` | cPanel, HTTPS |
| `2082` | cPanel, HTTP |
| `2096` | Webmail, HTTPS |
| `2095` | Webmail, HTTP |

Cookie-based calls **require** the `cpsess` security token. Webmail sessions can only call the functions available to a Webmail user.

## Command Line (on the server)

```bash
uapi --user=username --output=jsonpretty Module function key=value
```

- Root must pass `--user`; a cPanel user calling as themselves may omit it.
- On CloudLinux use the full path `/usr/local/cpanel/bin/uapi`.
- No network, no token, no password: preferred for anything running **on** the server (cron, Git deploy tasks in `.cpanel.yml`).

## Choosing a Method

```
Running on the cPanel server itself?  → CLI `uapi`
Inside a cPanel plugin/theme page?    → LiveAPI PHP/Perl
Managing many accounts as host admin? → WHM API 1 `uapi_cpanel` with a WHM token
Anything else (remote integration)    → API token over HTTPS :2083
```
