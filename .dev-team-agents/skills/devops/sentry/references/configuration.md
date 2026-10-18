# Sentry — Configuration Reference

## Environment Variables

| Variable | Required | Example |
|----------|----------|---------|
| `SENTRY_DSN` | Yes | `https://abc123@o0.ingest.sentry.io/0` |
| `SENTRY_RELEASE` | Yes (in CI) | `v1.4.2` or `$(git rev-parse --short HEAD)` |
| `SENTRY_ENVIRONMENT` | Yes | `production`, `staging`, `development` |
| `SENTRY_TRACES_SAMPLE_RATE` | Recommended | `0.2` |
| `SENTRY_AUTH_TOKEN` | CI only (for CLI) | scoped to `project:releases` |

**Never hardcode the DSN in source.** It is considered a credential — rotating it requires redeploying every service that embeds it.

Set `SENTRY_RELEASE` in CI from git:

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

### Dynamic sampler

```typescript
Sentry.init({
  tracesSampler: (samplingContext) => {
    const url = samplingContext.request?.url ?? "";
    if (url.includes("/health") || url.includes("/ping") || url.includes("/metrics")) {
      return 0;   // Never sample health checks
    }
    if (url.includes("/checkout") || url.includes("/payment")) {
      return 1.0; // Always sample critical flows
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

Source maps let Sentry show original TypeScript/JSX code in stack traces.

```bash
sentry-cli sourcemaps upload \
  --org "$SENTRY_ORG" \
  --project "$SENTRY_PROJECT" \
  --release "$SENTRY_RELEASE" \
  ./dist
```

**Do not serve source maps publicly.** Block at CDN/Nginx:

```nginx
location ~* \.map$ {
    return 403;
}
```

---

## Alerts Configuration

Configure at `sentry.io/settings/<org>/alerts/` or via the Sentry API.

### Minimum alert set

| Trigger | Type | Destination |
|---------|------|-------------|
| New issue in current release | Issue alert | Slack `#alerts-errors` |
| Error rate > 5% in any 5-minute window | Metric alert | PagerDuty / on-call |
| P95 transaction duration > 2× baseline | Metric alert | Slack `#alerts-performance` |
| First occurrence of previously resolved issue | Issue alert | Slack `#alerts-errors` |

Assign alert ownership to a team or individual — unowned alerts go unacknowledged.

---

## Performance Metrics

Key metrics to review weekly:

| Metric | Description |
|--------|-------------|
| **Apdex** | User satisfaction score (1.0 = all fast) |
| **Throughput** | Requests per minute by transaction |
| **P95 latency** | 95th percentile response time — main SLO target |
| **Error rate** | Percentage of transactions that raise an exception |

---

## Self-Hosted Sentry (Docker)

Use the official [getsentry/self-hosted](https://github.com/getsentry/self-hosted) — do not hand-assemble a compose file.

```bash
git clone https://github.com/getsentry/self-hosted.git
cd self-hosted
./install.sh   # prompts for initial admin credentials
docker compose up -d
```

### Required environment variables

| Variable | Description |
|----------|-------------|
| `SENTRY_SECRET_KEY` | 50+ char random string — `openssl rand -base64 50` |
| `SENTRY_POSTGRES_HOST` | Postgres hostname |
| `SENTRY_DB_USER` / `SENTRY_DB_PASSWORD` | Postgres credentials |
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

- [ ] Postgres volume — daily dump via `pg_dump`, stored off-host
- [ ] File attachments volume — sync to S3/GCS or equivalent
- [ ] Cleanup cron configured (`SENTRY_CLEANUP_DAYS`, default: 90)
- [ ] Test restore procedure before going to production
