# GoTrue — Client and Admin API Reference

Code-level reference for sign-in, session handling, the Admin API, and server-side verification. Decision-level rules live in `../SKILL.md`.

All examples use `supabase-js`; standalone GoTrue exposes the same operations over its REST endpoints.

---

## Registration

```typescript
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'securepassword',
  options: { data: { display_name: 'Jane' } }  // stored in raw_user_meta_data
})
```

Anything passed in `options.data` lands in **user_metadata** — user-controlled. Never put roles or permissions there.

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

| Claim | Meaning |
|---|---|
| `sub` | User UUID; equals `auth.uid()` in RLS policies |
| `role` | `anon` (unauthenticated) or `authenticated`; used by PostgREST to select the Postgres role |
| `app_metadata` | Server-controlled; safe for custom claims (roles, permissions) |
| `user_metadata` | User-controlled; never use for authorization decisions |

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

## Admin API

The Admin API requires the service-role key and must run **server-side only**.

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

`getSession()` reads whatever is in the cookie or storage and does **not** re-verify it. On the server, always follow with `getUser()`.
