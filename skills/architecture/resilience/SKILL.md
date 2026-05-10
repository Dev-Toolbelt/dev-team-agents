---
name: resilience
description: Resilience patterns — circuit breaker, retry with backoff, bulkhead, timeout, fallback, rate limiting, and health checks.
---

## Patterns Reference

| Pattern | Problem Solved | When to Use |
|---------|---------------|------------|
| Circuit Breaker | Prevents cascading failures to a degraded dependency | Any synchronous external call |
| Retry + Exponential Backoff | Recovers from transient failures automatically | Idempotent operations, network timeouts, 5xx errors |
| Bulkhead | Isolates resource pools so one slow dependency doesn't block others | Services with multiple downstream dependencies |
| Timeout | Prevents indefinite blocking on slow responses | Every network boundary |
| Fallback | Provides a degraded but functional response on failure | Non-critical dependencies (recommendations, ads, enrichment) |
| Rate Limiter | Protects services from traffic spikes and abuse | Inbound API endpoints, outbound third-party calls |

## Circuit Breaker

States and transitions:

```
CLOSED → (N consecutive failures) → OPEN → (probe timeout) → HALF-OPEN → (probe succeeds) → CLOSED
                                                                         → (probe fails)    → OPEN
```

- **CLOSED:** requests pass through; failure counter increments on error
- **OPEN:** requests fail immediately with a fallback; no calls to the downstream
- **HALF-OPEN:** one probe request is allowed through to test recovery

Rules:
- Open after N failures within a rolling time window (e.g., 5 failures in 30s)
- Never open on client errors (4xx) — those are the caller's fault, not the downstream's
- Set the probe timeout long enough for the downstream to recover (e.g., 30s – 60s)
- Emit metrics on state transitions; alert on circuit opening

## Retry Policy

- Max **3 retries** (4 total attempts) for most cases
- **Exponential backoff with jitter:**

```
attempt 1 delay: 100ms + rand(0–50ms)
attempt 2 delay: 200ms + rand(0–100ms)
attempt 3 delay: 400ms + rand(0–200ms)
```

- Retry only transient failures: 5xx responses, network timeouts, connection resets
- Do NOT retry: 4xx errors (except 429 with `Retry-After`), validation failures, business logic errors
- Ensure the operation is idempotent before retrying — use idempotency keys for non-idempotent operations
- Combine with circuit breaker: stop retrying when the circuit is open

## Timeout

- Set a timeout at **every** network boundary — database, HTTP call, message broker, internal RPC
- Client-side timeout must be **shorter** than server-side timeout:
  - If the client times out first and retries, the server may process the original request twice
  - Rule of thumb: client timeout = 80–90% of the server's configured processing timeout
- Use separate timeouts for connection establishment and total response time
- Log timeout events with the full call target and duration for observability

## Bulkhead

- Assign a **separate thread pool or connection pool** to each critical downstream dependency
- One pool exhaustion must not prevent calls to other dependencies
- Size pools independently based on expected concurrency and dependency SLA:

```
billing-service pool:    max 20 threads, queue 50
inventory-service pool:  max 10 threads, queue 20
notification-service pool: max 5 threads, queue 10
```

- Reject requests with a clear error (503 + explanation) when the pool is saturated — never silently queue indefinitely
- Monitor pool saturation as a leading indicator of downstream degradation

## Fallback

- Always provide an explicit fallback — never return a silent empty response on failure
- Fallback options in priority order:
  1. Return a cached (possibly stale) result
  2. Return a safe default value (empty list, zero, placeholder)
  3. Return a degraded response (feature disabled message)
  4. Return a clear error to the caller with enough context to retry later
- Never swallow exceptions silently — log the original error even when serving a fallback
- Mark fallback responses in the payload or headers so callers can distinguish real from degraded data

## Rate Limiting

| Algorithm | Behavior | Best For |
|-----------|----------|---------|
| Token Bucket | Smooth average rate; allows short bursts | APIs, outbound calls |
| Sliding Window | Precise request counting per window | Burst detection, abuse prevention |
| Fixed Window | Simple but allows boundary bursts | Internal rate limiting where precision is less critical |
| Leaky Bucket | Constant output rate regardless of input spikes | Traffic shaping |

- Return `429 Too Many Requests` with a `Retry-After` header specifying seconds until the next allowed request
- Apply rate limits per API key, user ID, or IP — never globally only
- Implement rate limits as close to the edge as possible (API gateway, CDN) to reduce backend load
- Log rate-limit hits with the client identifier for abuse analysis

## Health Checks

Three distinct probes — do not conflate them:

| Probe | Question | Failing means |
|-------|---------|--------------|
| Liveness | Is the process alive and not deadlocked? | Kill and restart the container |
| Readiness | Can this instance serve traffic right now? | Remove from load balancer pool |
| Startup | Has initialization completed? | Delay liveness/readiness checks |

- Expose all probes at `/health` with sub-paths: `/health/live`, `/health/ready`, `/health/startup`
- Readiness checks must verify critical dependencies (DB connection, cache availability)
- Liveness checks must be lightweight — never check external dependencies in liveness
- Return `200` on healthy, `503` on unhealthy; include a JSON body with individual component status
- Set appropriate Kubernetes probe parameters: `initialDelaySeconds`, `periodSeconds`, `failureThreshold`
