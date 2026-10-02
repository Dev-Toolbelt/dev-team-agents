# Ban a user (ADR-0029 SR-35)

A ban has three steps, all required. Run them in the SQL editor of the target project (`dev` or `prod`)
as the `postgres` role. Replace `<user-id>` with the account's `auth.users.id`.

```sql
begin;

-- 1. License: the entitlement function issues a `banned` token from the next call.
update public.licenses
set status = 'banned', banned_at = now(), ban_reason = 'reason in a few words'
where user_id = '<user-id>';

-- 2. Auth: refresh fails from now on.
update auth.users set banned_until = 'infinity' where id = '<user-id>';

-- 3. Sessions: revoke every session and its refresh tokens.
delete from auth.sessions where user_id = '<user-id>';

commit;
```

What each step buys:

- Access tokens already issued stay valid until `jwt_expiry` (1 hour), and a cached entitlement stays valid
  offline until its `exp` (at most `max_offline_days`). Both are accepted limits of ADR-0029 section 4.
- The email HMAC is not written here, because the pepper is never stored in the database. It is written
  automatically if the banned account deletes itself (`account-delete`), so deletion does not lift the ban.
  To block a not-yet-deleted address pre-emptively, set it from a shell that holds the pepper:

```bash
printf '%s' "$(printf '%s' "$EMAIL" | tr '[:upper:]' '[:lower:]')" \
  | openssl dgst -sha256 -hmac "$BAN_HMAC_KEY" -binary | xxd -p -c 64
```

  then `insert into public.banned_identities (email_hmac, reason) values ('\x<hex>', 'reason');`.
  The shell command trims nothing and does not NFC-normalize, so use it only for plain ASCII addresses.

To lift a ban: set `licenses.status = 'active', banned_at = null, ban_reason = null`, clear
`auth.users.banned_until`, and delete the `banned_identities` row if one exists.
