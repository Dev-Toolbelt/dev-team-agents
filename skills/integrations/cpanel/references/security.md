# UAPI Security Rules

These rules apply to every integration and every agent that operates a cPanel account. They complement `skills/security/secret-management/SKILL.md` and `skills/shared/credentials/SKILL.md`.

## Credentials

| Rule | Why |
|---|---|
| Use **API tokens**, never the account password or Basic auth | A token can be scoped (`readonly=1`), given an expiry and revoked without touching the login |
| One token per integration, named after it (`ci-deploy`, `monitoring`) | Revocation does not break unrelated systems; `Tokens::list` stays auditable |
| Set `expires_at` and rotate before expiry | Expired tokens are **not** deleted automatically; revoke them with `Tokens::revoke` |
| `readonly=1` for reporting and monitoring | Write calls are rejected server-side |
| Store tokens in a secret manager or CI secret; load them from env vars (`CPANEL_HOST`, `CPANEL_USER`, `CPANEL_TOKEN`) | Never in code, `.env` committed to git, logs, tickets or chat |
| Never paste a token, password or private key into a prompt or command shown to the user | Transcripts and terminals are logged |

## Transport

- HTTPS only: port **2083** (cPanel) / **2096** (Webmail). Never `2082`/`2095` in production.
- Keep TLS verification **on**. If the server uses a self-signed or hostname-mismatched certificate, fix the certificate (AutoSSL) or pin it. Do not pass `-k` / `verify=False`.
- Send secrets (`password`, `pass`, `key`, `cert`, `content`) in a **POST body**, never in the query string. Query strings end up in web server logs, proxies and shell history. The vendor examples put passwords in URLs for brevity; do not copy that.

## Least Privilege

- An API token inherits **all** of the account's features. For narrower access, create a Subaccount (`UserManager::create_user`) with only the services it needs (email, FTP, Web Disk) instead of sharing the main account.
- Database users: grant only the privileges the app needs (`SELECT,INSERT,UPDATE,DELETE`), not `ALL PRIVILEGES`, unless the app runs migrations.
- Remote MySQL hosts (`Mysql::add_host`): the narrowest IP or CIDR possible, never `%`.

## Destructive Operations — Confirm First

Ask for explicit confirmation before any call that deletes data or cannot be undone, and state exactly what will be lost:

`Email::delete_pop` · `Mysql::delete_database` · `Mysql::delete_user` · `Postgresql::delete_*` · `SubDomain::delsubdomain` · `AddonDomain::deladdondomain` · `Park::unpark` · `ZoneEdit::resetzone` · `DNS::mass_edit_zone` (with `remove`) · `SSL::delete_ssl` · `Fileman::*` writes with overwrite · `Trash::remove` · `Restore::*` (overwrites current files) · `WebsiteBackup::restore_backup` · `WebsiteBackup::delete_backup` · `Tokens::revoke` · `BlockIP::add_ip` (can lock out the user's own IP)

Before a destructive call, read the current state (`list_*`, `parse_zone`, `get_file_content`) so it can be restored by hand if needed.

## Input Handling

- URI-encode every value; never build URLs by string concatenation with unescaped user input.
- Validate domain, email and path inputs before sending them. `Fileman::*` paths resolve against the account home; reject `..` segments coming from untrusted input.
- When piping mail to a script (`Email::add_forwarder fwdopt=pipe`), the script runs as the account user. Treat it as an execution surface.

## Auditing

- `ActiveSessions::list_active_sessions` and `LastLogin::get_last_or_current_logged_in_ip` show who is logged in.
- `Tokens::list` shows which tokens exist and when they expire. Review it at every rotation.
- Log every write call the integration makes: module, function, non-secret parameters and the `status`/`errors` returned. Never log secrets.
