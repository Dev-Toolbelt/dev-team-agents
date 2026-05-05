---
name: sentry
description: Sentry error tracking and performance monitoring — SDK setup, DSN configuration, environments, releases, performance/tracing, custom context, alerts, source maps, and self-hosted deployment. Load when a project uses Sentry or when setting up error tracking / APM.
---

# Sentry — Error Tracking & Performance Monitoring

## Detection Signals

| Signal | Location |
|--------|----------|
| `SENTRY_DSN` env var | `.env`, `.env.example`, CI secrets |
| `@sentry/` prefix | `package.json` dependencies |
| `sentry-sdk` | `requirements.txt`, `pyproject.toml` |
| `sentry/sentry-laravel` or `sentry/sentry-php` | `composer.json` |
| `sentry` service | `docker-compose.yml` |
| `.sentryclirc` or `sentry.properties` | repo root |

---

## Core Concepts

| Term | Meaning |
|------|---------|
| **DSN** | Data Source Name — the endpoint URL that SDKs send events to |
| **Organization** | Top-level billing unit in Sentry |
| **Project** | Maps to one application or service |
| **Environment** | `production`, `staging`, `development` — segments events |
| **Release** | Tagged version (`v1.2.3` or git SHA) — ties issues to deploys |
| **Issue** | Grouped set of similar events (same error + stacktrace fingerprint) |
| **Event** | A single captured error or transaction |
| **Breadcrumb** | Ordered log of actions leading up to an event |
| **Transaction** | A performance trace for one request or operation |
| **Span** | A timed segment inside a transaction (DB query, HTTP call) |

---

## SDK Setup

Always initialize Sentry **as early as possible** in the application lifecycle — before any other imports when possible.

### JavaScript / TypeScript (Node.js)

```typescript
import * as Sentry from "@sentry/node";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NODE_ENV,
  release: process.env.SENTRY_RELEASE,   // set from git SHA in CI
  tracesSampleRate: 0.2,                  // see Sampling Strategy below
  sendDefaultPii: false,                  // GDPR — never send PII by default
});
```

### JavaScript / TypeScript (Browser)

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

### Python

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

### Go

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

### PHP (Laravel)

In `config/sentry.php` — values pulled from `.env`:

```php
'dsn' => env('SENTRY_LARAVEL_DSN'),
'environment' => env('APP_ENV', 'production'),
'release' => env('SENTRY_RELEASE'),
'traces_sample_rate' => (float) env('SENTRY_TRACES_SAMPLE_RATE', 0.2),
'send_default_pii' => false,
```

---

## Environment Configuration

| Variable | Required | Example |
|----------|----------|---------|
| `SENTRY_DSN` | Yes | `https://abc123@o0.ingest.sentry.io/0` |
| `SENTRY_RELEASE` | Yes (in CI) | `v1.4.2` or `$(git rev-parse --short HEAD)` |
| `SENTRY_ENVIRONMENT` | Yes | `production`, `staging`, `development` |
| `SENTRY_TRACES_SAMPLE_RATE` | Recommended | `0.2` |
| `SENTRY_AUTH_TOKEN` | CI only (for CLI) | scoped to `project:releases` |

**Never hardcode the DSN in source.** It is considered a credential — rotating it requires redeploying every service that embeds it.

Set `SENTRY_RELEASE` in CI from the git commit:

```bash
export SENTRY_RELEASE=$(git rev-parse --short HEAD)
# or for tagged releases:
export SENTRY_RELEASE=$(git describe --tags --abbrev=0)
```

---

## Sampling Strategy

Error capture always uses `sampleRate: 1.0` — never drop errors. Adjust `tracesSampleRate` for performance data only.

| Traffic volume | `tracesSampleRate` |
|---------------|-------------------|
| < 1k req/day | `1.0` |
| 1k – 50k req/day | `0.2` |
| > 50k req/day | `0.05` + dynamic sampler |

### Dynamic sampler — exclude noise, protect critical paths

```typescript
Sentry.init({
  tracesSampler: (samplingContext) => {
    const url = samplingContext.request?.url ?? "";
    // Never sample health checks
    if (url.includes("/health") || url.includes("/ping") || url.includes("/metrics")) {
      return 0;
    }
    // Always sample checkout and payment flows
    if (url.includes("/checkout") || url.includes("/payment")) {
      return 1.0;
    }
    return 0.05;
  },
});
```

---

## Release & Deployment Tracking

Linking releases to commits enables Sentry to show which deploy introduced a regression.

### Create release and upload commits (CLI)

```bash
# Install once: npm install -g @sentry/cli
sentry-cli releases new "$SENTRY_RELEASE"
sentry-cli releases set-commits "$SENTRY_RELEASE" --auto
sentry-cli releases finalize "$SENTRY_RELEASE"
sentry-cli releases deploys "$SENTRY_RELEASE" new -e production
```

### GitHub Actions — wire into deploy job

```yaml
- name: Create Sentry release
  env:
    SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
    SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
    SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
    SENTRY_RELEASE: ${{ github.sha }}
  run: |
    npm install -g @sentry/cli
    sentry-cli releases new "$SENTRY_RELEASE"
    sentry-cli releases set-commits "$SENTRY_RELEASE" --auto
    sentry-cli releases finalize "$SENTRY_RELEASE"
    sentry-cli releases deploys "$SENTRY_RELEASE" new -e production
```

Place this step **after deploy succeeds**, not before.

---

## Source Maps

Source maps let Sentry show original TypeScript/JSX code in stack traces instead of minified output.

```bash
# After build, before or alongside deploy:
sentry-cli sourcemaps upload \
  --org "$SENTRY_ORG" \
  --project "$SENTRY_PROJECT" \
  --release "$SENTRY_RELEASE" \
  ./dist
```

**Do not serve source maps publicly.** Upload them to Sentry only — exclude `*.map` files from CDN or set a `SourceMap` header that points nowhere public.

```nginx
# Block public access to source maps
location ~* \.map$ {
    return 403;
}
```

---

## Custom Context

Add context before errors occur — not inside catch blocks.

```typescript
// Identify the user (after authentication)
Sentry.setUser({ id: user.id, username: user.email });

// Tag for filtering in the Sentry UI
Sentry.setTag("tenant", tenantSlug);
Sentry.setTag("plan", user.plan);

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
- `send_default_pii: false` is the safe default — keeps IP addresses and full request bodies out of events.
- Never put passwords, tokens, credit card numbers, or full email addresses in `setExtra` or breadcrumbs.
- If GDPR applies and you need to store email: hash it first or use only the user ID.

---

## Alerts & Notifications

Configure alerts at `sentry.io/settings/<org>/alerts/` or via the Sentry API.

### Minimum alert set

| Trigger | Type | Destination |
|---------|------|-------------|
| New issue introduced in current release | Issue alert | Slack `#alerts-errors` |
| Error rate > 5% in any 5-minute window | Metric alert | PagerDuty / on-call channel |
| P95 transaction duration > 2× baseline | Metric alert | Slack `#alerts-performance` |
| First occurrence of a previously resolved issue | Issue alert | Slack `#alerts-errors` |

**Assign alert ownership** to a team or individual — unowned alerts go unacknowledged. Use `CODEOWNERS`-style ownership rules in Sentry project settings.

---

## Performance Monitoring

Key metrics to review weekly:

| Metric | Description |
|--------|-------------|
| **Apdex** | User satisfaction score (1.0 = all fast, 0 = all unacceptable) |
| **Throughput** | Requests per minute by transaction |
| **P95 latency** | 95th percentile response time — main SLO target |
| **Error rate** | Percentage of transactions that raise an exception |

### Custom spans for visibility into slow paths

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

---

## Self-Hosted Sentry (Docker)

Use the official [getsentry/self-hosted](https://github.com/getsentry/self-hosted) repository — do not hand-assemble a compose file.

```bash
git clone https://github.com/getsentry/self-hosted.git
cd self-hosted
./install.sh   # prompts for initial admin credentials
docker compose up -d
```

### Required environment variables (`.env`)

| Variable | Description |
|----------|-------------|
| `SENTRY_SECRET_KEY` | 50+ char random string — `openssl rand -base64 50` |
| `SENTRY_POSTGRES_HOST` | Postgres hostname |
| `SENTRY_DB_USER` | Postgres user |
| `SENTRY_DB_PASSWORD` | Postgres password |
| `SENTRY_REDIS_HOST` | Redis hostname |
| `SENTRY_SERVER_EMAIL` | From address for email notifications |
| `SENTRY_EMAIL_HOST` | SMTP host |

### Resource requirements

| Component | Minimum |
|-----------|---------|
| vCPU | 4 |
| RAM | 8 GB |
| Disk | 20 GB + event retention size |

### Backup checklist

- [ ] Postgres volume (`sentry-postgres`) — daily dump via `pg_dump`, stored off-host
- [ ] File attachments volume (`sentry-data`) — sync to S3/GCS or equivalent
- [ ] Cleanup cron for old events — configure `SENTRY_CLEANUP_DAYS` (default: 90)
- [ ] Test restore procedure before going to production

---

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| DSN committed to source | Always use `SENTRY_DSN` env var; rotate any exposed DSN immediately |
| `tracesSampleRate: 1.0` in high-traffic prod | Implement dynamic sampler; high rate causes quota exhaustion |
| Missing `release` tag | Wire `sentry-cli` into CI deploy step — regressions become unattributable |
| Health-check spam in Issues | Filter `/health`, `/ping`, `/metrics` in `beforeSend` or dynamic sampler |
| Source maps publicly accessible | Upload via CLI only; block `.map` files at CDN/Nginx |
| PII in breadcrumbs / extra | `send_default_pii: false`; scrub before `setExtra` |
| Alert fatigue | Assign owners; tune thresholds; group noisy issues |
| Sentry SDK initialized after imports | Init must run before any other module that could throw |
| Missing `sentry.Flush()` in Go/CLI apps | Short-lived processes exit before events are sent |

---

## Before Declaring Done

- [ ] `SENTRY_DSN` injected via env var — not hardcoded anywhere in source
- [ ] `environment` set correctly per deployment target (`production`, `staging`, `development`)
- [ ] `release` tied to git SHA or semver tag and created via `sentry-cli` in CI
- [ ] Sampling rate appropriate for traffic volume (not blindly `1.0` in prod)
- [ ] Source maps uploaded in CI build step; `.map` files not publicly accessible
- [ ] At minimum: new-issue alert + error-rate > 5% alert wired to a notification channel
- [ ] Health/ping/metrics routes excluded from error and performance capture
- [ ] `send_default_pii: false` unless GDPR exemption is documented and approved
- [ ] Alert ownership assigned — no unowned alert rules
- [ ] **If self-hosted**: backup procedure tested; cleanup cron configured
