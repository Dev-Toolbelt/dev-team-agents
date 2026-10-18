# GoTrue — Custom Claims and Hooks Reference

Reference for injecting authorization data into the JWT and intercepting auth events. Decision-level rules live in `../SKILL.md`.

---

## Custom Claims

Add custom data to the JWT via **app_metadata** — writable only with the service-role key or via hooks:

```typescript
// Server-side only (service role)
await adminSupabase.auth.admin.updateUserById(userId, {
  app_metadata: { role: 'admin', tenant_id: 'acme' }
})
```

In RLS policies, read custom claims:

```sql
-- Check a custom role claim
create policy "Admin only"
on sensitive_table for select
to authenticated
using ((auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');
```

**Never** trust `user_metadata` for authorization — users can write it themselves.

Claims are baked into the JWT at issue time. A role changed via `updateUserById` does **not** take effect until the user's token is refreshed — force a refresh or accept the delay explicitly, and never rely on a stale token being revoked instantly.

---

## Hooks (GoTrue Hooks)

GoTrue supports hooks that fire at auth events, allowing custom logic:

| Hook | Trigger |
|---|---|
| `custom_access_token` | Before JWT is issued — add custom claims |
| `send_email` | Override email sending |
| `send_sms` | Override SMS sending |
| `mfa_verification_attempt` | Before MFA is checked |

Hooks are configured in `supabase/config.toml` (Supabase CLI) or via GoTrue env vars.

```toml
[auth.hook.custom_access_token]
enabled = true
uri = "pg-functions://postgres/public/custom_access_token_hook"
```

PostgreSQL function hook example:

```sql
create or replace function public.custom_access_token_hook(event jsonb)
returns jsonb language plpgsql as $$
declare claims jsonb;
begin
  claims := event -> 'claims';
  claims := jsonb_set(claims, '{app_metadata, role}', '"editor"');
  return jsonb_set(event, '{claims}', claims);
end;
$$;
```

A failing `custom_access_token` hook blocks token issuance — every sign-in fails. Keep the function total: handle a missing claims key, and never let it raise.
