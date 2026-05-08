---
name: gotrue
description: GoTrue auth — user management, JWT, refresh tokens, custom claims, and admin API.
---

# GoTrue

GoTrue is a stateless authentication microservice. It issues JWTs, manages user sessions, and handles OAuth flows. Supabase embeds it as the `auth` service; it can also run standalone.

---

## Detection Signals

| Signal | Meaning |
|---|---|
| `GOTRUE_*` env vars | Standalone GoTrue |
| `supabase.auth.*` calls in code | GoTrue via Supabase client |
| `auth.users` table in Postgres | GoTrue-managed user table |
| `auth` schema in database | GoTrue schema |

---

## Auth Methods

| Method | API call (supabase-js) |
|---|---|
| Email + password | `supabase.auth.signInWithPassword({ email, password })` |
| Magic link | `supabase.auth.signInWithOtp({ email })` |
| Phone OTP | `supabase.auth.signInWithOtp({ phone })` |
| OAuth (Google, GitHub, etc.) | `supabase.auth.signInWithOAuth({ provider: 'google' })` |
| Anonymous | `supabase.auth.signInAnonymously()` |
| SSO / SAML | `supabase.auth.signInWithSSO({ domain })` |

Registration:
```typescript
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'securepassword',
  options: { data: { display_name: 'Jane' } }  // stored in raw_user_meta_data
})
```

---

## JWT Structure

GoTrue issues JWTs with these standard claims:

```json
{
  "iss": "https://your-project.supabase.co/auth/v1",
  "sub": "uuid-of-user",
  "aud": "authenticated",
  "role": "authenticated",
  "exp": 1700000000,
  "iat": 1699996400,
  "email": "user@example.com",
  "phone": "",
  "app_metadata": {
    "provider": "email",
    "providers": ["email"]
  },
  "user_metadata": {
    "display_name": "Jane"
  }
}
```

Key claims:
- `sub` — user UUID; equals `auth.uid()` in RLS policies
- `role` — `anon` (unauthenticated) or `authenticated`; used by PostgREST to select Postgres role
- `app_metadata` — server-controlled; safe for custom claims (roles, permissions)
- `user_metadata` — user-controlled; do not use for authorization decisions

**JWT expiry**: 1 hour by default. Configure via `JWT_EXPIRY` env var (seconds).

---

## Session & Token Management

GoTrue uses a two-token system:
- **Access token** (JWT) — short-lived, stateless, used for API calls
- **Refresh token** — long-lived, stored in the database, used to obtain a new access token

```typescript
// Get current session
const { data: { session } } = await supabase.auth.getSession()

// Listen for auth changes (handles refresh automatically)
supabase.auth.onAuthStateChange((event, session) => {
  if (event === 'SIGNED_IN') { /* store session */ }
  if (event === 'SIGNED_OUT') { /* clear session */ }
  if (event === 'TOKEN_REFRESHED') { /* update stored token */ }
})

// Manually sign out
await supabase.auth.signOut()
```

The supabase-js client handles token refresh automatically when using `getSession()` or `onAuthStateChange`. In server-side contexts, refresh manually:

```typescript
const { data, error } = await supabase.auth.refreshSession({ refresh_token })
```

---

## Custom Claims

Add custom data to the JWT via **app_metadata** — writable only with service-role key or via hooks:

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

---

## Admin API

The Admin API requires the service-role key. Available endpoints (via supabase-js):

```typescript
// List users
const { data } = await adminSupabase.auth.admin.listUsers()

// Get user by ID
const { data } = await adminSupabase.auth.admin.getUserById(userId)

// Create user (no email confirmation)
const { data } = await adminSupabase.auth.admin.createUser({
  email: 'user@example.com',
  password: 'pass',
  email_confirm: true
})

// Delete user
await adminSupabase.auth.admin.deleteUser(userId)

// Generate a magic link (for passwordless invites)
const { data } = await adminSupabase.auth.admin.generateLink({
  type: 'magiclink',
  email: 'user@example.com'
})
```

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

---

## Server-Side JWT Verification

Always verify the JWT on the server before trusting it:

```typescript
import { createClient } from '@supabase/supabase-js'

// Pass the user's JWT — GoTrue validates it
const supabase = createClient(url, anonKey, {
  global: { headers: { Authorization: `Bearer ${userJwt}` } }
})
const { data: { user }, error } = await supabase.auth.getUser()
if (error) throw new Error('Invalid token')
```

Or verify manually using the `SUPABASE_JWT_SECRET`:
```typescript
import jwt from 'jsonwebtoken'
const payload = jwt.verify(token, process.env.SUPABASE_JWT_SECRET!)
```

---

## Common Pitfalls

- Reading `user_metadata` for authorization — users control it, never trust it for permissions
- Not calling `onAuthStateChange` on the client — sessions expire silently
- Using `getSession()` on the server without re-verification — the session in the cookie may be stale; always call `getUser()` to verify server-side
- Exposing the service-role key in client code — gives full auth admin access
- Not enabling email confirmations in production — GoTrue defaults may differ between environments
