# Sentry — SDK Setup by Language

Always initialize Sentry **as early as possible** in the application lifecycle — before any other imports when possible.

## JavaScript / TypeScript (Node.js)

```typescript
import * as Sentry from "@sentry/node";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.SENTRY_RELEASE,   // set from git SHA in CI
  tracesSampleRate: 0.2,
  sendDefaultPii: false,                  // GDPR — never send PII by default
});
```

## JavaScript / TypeScript (Browser)

```typescript
import * as Sentry from "@sentry/browser";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.VITE_APP_ENV,
  release: import.meta.env.VITE_SENTRY_RELEASE,
  tracesSampleRate: 0.1,
  sendDefaultPii: false,
  integrations: [Sentry.browserTracingIntegration()],
});
```

## Python

```python
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],
    environment=os.environ.get("APP_ENV", "development"),
    release=os.environ.get("SENTRY_RELEASE"),
    traces_sample_rate=0.2,
    send_default_pii=False,
)
```

## Go

```go
import "github.com/getsentry/sentry-go"

sentry.Init(sentry.ClientOptions{
    Dsn:              os.Getenv("SENTRY_DSN"),
    Environment:      os.Getenv("APP_ENV"),
    Release:          os.Getenv("SENTRY_RELEASE"),
    TracesSampleRate: 0.2,
    SendDefaultPii:   false,
})
defer sentry.Flush(2 * time.Second)
```

> **Go / CLI apps**: always call `sentry.Flush(2 * time.Second)` — short-lived processes exit before events are sent otherwise.

## PHP (Laravel)

In `config/sentry.php` — values pulled from `.env`:

```php
'dsn' => env('SENTRY_LARAVEL_DSN'),
'environment' => env('APP_ENV', 'production'),
'release' => env('SENTRY_RELEASE'),
'traces_sample_rate' => (float) env('SENTRY_TRACES_SAMPLE_RATE', 0.2),
'send_default_pii' => false,
```

---

## Custom Context

Add context before errors occur — not inside catch blocks.

```typescript
// Identify the user (after authentication)
Sentry.setUser({ id: user.id, username: user.email });

// Tag for filtering in the Sentry UI
Sentry.setTag("tenant", tenantSlug);

// Structured extra data (non-indexed)
Sentry.setExtra("requestBody", sanitizedPayload);

// Breadcrumb for manual audit trail
Sentry.addBreadcrumb({
  category: "auth",
  message: "User elevated to admin",
  level: "warning",
});
```

**PII rules**:
- `send_default_pii: false` keeps IP addresses and full request bodies out of events.
- Never put passwords, tokens, credit card numbers, or full email addresses in `setExtra` or breadcrumbs.
- If GDPR applies and you need to store email: hash it first or use only the user ID.

---

## Custom Spans for Performance Visibility

```typescript
// Node.js / TypeScript
const span = Sentry.startInactiveSpan({ name: "db.query.getUserById", op: "db.query" });
const user = await db.query("SELECT * FROM users WHERE id = $1", [userId]);
span.end();
```

```python
# Python
with sentry_sdk.start_span(op="db.query", name="getUserById"):
    user = db.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```
