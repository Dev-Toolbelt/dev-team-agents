---
name: observability-slo
description: Observability and SLO/SLI — defining service level objectives, error budgets, alerting, and the four golden signals.
---

## Four Golden Signals

| Signal | Definition | Example Threshold |
|--------|-----------|------------------|
| Latency | Time to serve a request; track p50, p95, p99 separately — errors must not lower the average | p99 < 500ms for checkout API |
| Traffic | Request rate; baseline for anomaly detection | Requests per second, events per minute |
| Errors | Rate of failed requests (5xx, timeouts, business logic failures) | < 0.1% error rate |
| Saturation | How "full" the service is — CPU, memory, queue depth, connection pool | CPU < 80%, queue depth < 1000 |

Define explicit thresholds for all four signals per service before writing alerts.

---

## SLI Definition

An SLI (Service Level Indicator) is a quantitative measure of service behavior:

- **Percentage-based** — expressed as a ratio of good events to total events
- **Directly tied to user experience** — not internal metrics like CPU
- **Measurable with existing instrumentation**

Examples:
- `% of /api/checkout requests completing in < 500ms`
- `% of API requests returning 2xx or 3xx`
- `% of background jobs completing without error within SLA window`

Avoid vanity SLIs (e.g., uptime of internal health-check endpoint that users never call).

---

## SLO Targets

| Principle | Rule |
|-----------|------|
| Realistic, not aspirational | Never set 100% — it is unachievable and creates perverse incentives |
| Agreed with stakeholders | Product, engineering, and support must align on the target |
| Documented in the service runbook | Include what the SLO is, how it is measured, and what triggers a response |

Common reference points:

| SLO | Monthly downtime budget |
|-----|------------------------|
| 99.0% | 7.3 hours |
| 99.5% | 3.6 hours |
| 99.9% | 43.8 minutes |
| 99.95% | 21.9 minutes |

---

## Error Budget

- **Error budget = 100% - SLO target**
- Represents how much unreliability is acceptable per rolling window (typically 30 days)
- When the error budget is **burned**, freeze new feature work and redirect the team to reliability improvements
- Track error budget burn rate as a primary team health metric

---

## Alerting Rules

Alert on **SLO burn rate**, not on raw metric spikes:

| Condition | Action |
|-----------|--------|
| Burn rate > 2x in the last 1 hour | Page on-call — budget will be exhausted in ~2 days at this rate |
| Burn rate > 5x in the last 5 minutes | Page on-call immediately — acute incident in progress |
| Budget < 10% remaining in the window | Notify team lead — feature freeze decision required |

Do not alert on:
- CPU > threshold (alert on saturation affecting SLI, not raw CPU)
- Single failed requests (alert on error rate over a window)
- Low traffic periods using absolute thresholds (use relative burn rate)

---

## Instrumentation

Three pillars — all three are required for effective observability:

| Pillar | Purpose | Tool |
|--------|---------|------|
| Structured logs | Searchable event records with context (user ID, trace ID, error code) | JSON logs → Loki, CloudWatch, Datadog |
| Distributed traces | Request flow across services; latency breakdown per span | OpenTelemetry → Jaeger, Tempo, X-Ray |
| Metrics | Aggregated counters and histograms over time | Prometheus, CloudWatch Metrics |

Use **OpenTelemetry** for instrumentation — vendor-neutral, avoids SDK lock-in. Export to any backend.

Minimum required instrumentation per service:
- Incoming request count, latency (histogram), error count
- Outgoing dependency calls (DB, external APIs) — same signals
- Business-level events (order placed, payment processed)

---

## Dashboards

One dashboard per service with:

1. **Golden signals panel** — latency (p50/p95/p99), traffic, error rate, saturation
2. **SLO burn rate** — current burn rate vs. the 2x and 5x thresholds
3. **Error budget remaining** — percentage and time left in the rolling window
4. **Recent deployments** — overlay deploy events on all time-series charts

Link the dashboard URL in the service runbook and on-call rotation doc.

---

## On-Call Rotation

- Auto-rotate weekly — no one person should carry on-call indefinitely
- Escalation path must be defined and tested before going on-call
- **Post-mortem required** for any SEV1 or SEV2 incident (see `skills/shared/incident-response/SKILL.md`)
- On-call engineer reviews error budget status at the start of each rotation
