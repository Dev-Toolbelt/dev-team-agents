---
name: rate-limiting
description: Rate-limiting algorithms, granularity tiers, storage backends, headers, and failure modes.
---

# Rate Limiting

## When to Load

Load when implementing API rate limiting, protecting endpoints from abuse, or designing fair-use policies.

## Algorithms

| Algorithm | Behaviour | Best for |
|-----------|-----------|----------|
| **Fixed Window** | Counter resets at clock boundary | Simple; bursts at window edge |
| **Sliding Window Log** | Track timestamp of each request | Accurate; high memory per user |
| **Sliding Window Counter** | Weighted blend of current + previous window | Good accuracy with low storage |
| **Token Bucket** | Tokens refill at rate R; burst up to capacity C | Bursty traffic; smooth average |
| **Leaky Bucket** | Queue drains at fixed rate | Strict output rate; latency on burst |

**Recommended default**: sliding window counter for API rate limiting; token bucket for bursty workloads.

## Granularity

Apply limits at the right level (can stack multiple):

| Level | Key | Example |
|-------|-----|---------|
| Per-IP | `ip` | Unauthenticated endpoints |
| Per-user | `user_id` | Authenticated API |
| Per-API-key | `api_key` | B2B integrations |
| Per-tenant | `tenant_id` | Multi-tenant SaaS |
| Per-endpoint | `route` | Expensive operations |
| Global | — | Service-wide DoS protection |

## Where to Apply

| Layer | Tool | Scope |
|-------|------|-------|
| Edge / CDN | Cloudflare Rate Limiting, AWS WAF | Global; no app code needed |
| API Gateway | Kong, Tyk, AWS API Gateway | Per-service |
| Application middleware | Express rate-limit, Django throttling, Nginx limit_req | Per-route |
| Database | Connection pool limits | Prevent DB overload |

## Storage Backends

| Backend | Use when |
|---------|----------|
| In-memory (local) | Single instance; no distributed coordination needed |
| Redis | Multiple instances; atomic `INCR` + `EXPIRE`; recommended default |
| DynamoDB | Serverless; conditional writes for atomic counters |

**Redis pattern (sliding window)**:
```
MULTI
ZREMRANGEBYSCORE key 0 (now - window_ms)
ZADD key now now
ZCARD key
EXPIRE key window_s
EXEC
```

## Response Headers

Always include these on rate-limited responses:

| Header | Value |
|--------|-------|
| `X-RateLimit-Limit` | Maximum requests allowed |
| `X-RateLimit-Remaining` | Requests remaining in window |
| `X-RateLimit-Reset` | Unix timestamp when window resets |
| `Retry-After` | Seconds until retry (on 429) |

Return `429 Too Many Requests` (not 503) when rate exceeded.

## Failure Modes

| Failure | Degraded behaviour |
|---------|-------------------|
| Redis unavailable | Fail open (allow requests) or fail closed (deny all) — choose per risk level |
| Clock skew between instances | Use Redis server time, not local clock |
| Rate limit store full | Evict oldest keys; alert on capacity |

## Decision Checklist

- [ ] Which layer owns the rate limit? (edge vs gateway vs app)
- [ ] What is the key? (IP, user, tenant, API key)
- [ ] What algorithm fits the traffic pattern? (bursty → token bucket; steady → sliding window)
- [ ] Is Redis available for distributed counting?
- [ ] What is the failure mode if the rate store is unavailable?
- [ ] Are `X-RateLimit-*` headers included in all responses?
