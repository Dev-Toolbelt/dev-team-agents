# Ban a user (ADR-0029 SR-34, SR-35, SR-38)

A ban is **one call** to the service-role-only `ban-user` Edge Function. It does every step, so none
can be skipped: the license (`banned`), the auth ban (`banned_until`, a far-future date — never
`infinity`, which GoTrue cannot scan), the revocation of every session and refresh token, and the
email HMAC in `banned_identities`, which survives a later deletion of the account. The function is
the only holder of the HMAC pepper, so the HMAC is never computed in a shell.

Read the service-role key without echo so it never lands in shell history or `ps`:

```bash
read -rs SERVICE_KEY && export SERVICE_KEY
curl -sS -X POST "https://<project-ref>.supabase.co/functions/v1/ban-user" \
  -H "Authorization: Bearer $SERVICE_KEY" -H "Content-Type: application/json" \
  --data '{"user_id": "<auth.users.id>", "reason": "reason in a few words"}'
unset SERVICE_KEY
```

A `200 {"ok": true, "identity_recorded": true}` means every step ran. `identity_recorded: false`
means the account has no email (an OAuth identity without one), so only the account itself is banned.

What remains after a ban, by design (ADR-0029 section 4): access tokens already issued stay valid until
`jwt_expiry` (1 hour), and a cached entitlement stays valid offline until its `exp` (at most
`max_offline_days`).

To lift a ban, as the `postgres` role in the SQL editor:

```sql
begin;
update public.licenses set status = 'active', banned_at = null, ban_reason = null where user_id = '<user-id>';
update auth.users set banned_until = null where id = '<user-id>';
commit;
```

Then delete the account's `banned_identities` row if the address must be allowed to register again
(match it by `created_at` and `reason`; the table holds no email).
