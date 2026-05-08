---
name: kong
description: Kong API Gateway — routes, services, plugins, Admin API. Standalone and Supabase-embedded.
---

# Kong API Gateway

Kong is an open-source API gateway and platform built on Nginx/OpenResty. In Supabase, Kong routes all traffic to internal services (PostgREST, GoTrue, Realtime, Storage, Edge Functions).

---

## Detection Signals

| Signal | Meaning |
|---|---|
| `kong` service in `docker-compose.yml` | Self-hosted Kong |
| `volumes/api/kong.yml` in Supabase project | Supabase-embedded Kong config |
| `KONG_*` env vars | Kong configuration |
| `8000` / `8443` ports exposed | Kong proxy ports |
| `8001` / `8444` ports exposed | Kong Admin API ports |

---

## Core Concepts

| Concept | Description |
|---|---|
| **Service** | An upstream backend (e.g., PostgREST at `http://rest:3000`) |
| **Route** | A matching rule (host, path, method) that forwards to a Service |
| **Plugin** | Middleware attached to a Route, Service, or globally |
| **Upstream** | Load balancer target with health checks and multiple targets |
| **Consumer** | A user or application that calls your API (used for auth plugins) |

---

## Supabase Kong Configuration

Supabase uses a declarative Kong config at `volumes/api/kong.yml`. All Supabase internal services are pre-wired as Kong services:

```yaml
_format_version: "2.1"

services:
  - name: auth-v1
    url: http://auth:9999/
    routes:
      - name: auth-v1-all
        strip_path: true
        paths:
          - /auth/v1/

  - name: rest-v1
    url: http://rest:3000/
    routes:
      - name: rest-v1-all
        strip_path: true
        paths:
          - /rest/v1/

  - name: realtime-v1
    url: http://realtime-dev.supabase-realtime:4000/socket/
    routes:
      - name: realtime-v1-all
        strip_path: true
        paths:
          - /realtime/v1/

  - name: storage-v1
    url: http://storage:5000/
    routes:
      - name: storage-v1-all
        strip_path: true
        paths:
          - /storage/v1/

  - name: edge-functions-v1
    url: http://edge-runtime:9000/
    routes:
      - name: edge-functions-v1-all
        strip_path: true
        paths:
          - /functions/v1/
```

To add a custom service (e.g., your own backend), append to `kong.yml`:
```yaml
  - name: my-api
    url: http://my-api:3001/
    routes:
      - name: my-api-all
        strip_path: true
        paths:
          - /api/v1/
    plugins:
      - name: key-auth
```

Restart Kong after changes: `docker compose restart kong`

---

## Essential Plugins

### Rate Limiting

```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 100
      hour: 1000
      policy: local       # or redis for distributed
      limit_by: ip        # or consumer, header, path
```

### JWT Validation

```yaml
plugins:
  - name: jwt
    config:
      key_claim_name: kid       # claim that identifies the key
      claims_to_verify:
        - exp
        - nbf
      secret_is_base64: false
```

### CORS

```yaml
plugins:
  - name: cors
    config:
      origins:
        - "https://app.example.com"
        - "http://localhost:3000"
      methods:
        - GET
        - POST
        - PUT
        - PATCH
        - DELETE
        - OPTIONS
      headers:
        - Authorization
        - Content-Type
        - apikey
      exposed_headers:
        - X-RateLimit-Remaining
      credentials: true
      max_age: 3600
```

### Request Transformation

```yaml
plugins:
  - name: request-transformer
    config:
      add:
        headers:
          - "X-Internal-Service:my-api"
      remove:
        headers:
          - Authorization   # strip before forwarding if handled by Kong
```

### Response Caching

```yaml
plugins:
  - name: proxy-cache
    config:
      response_code:
        - 200
        - 301
      request_method:
        - GET
        - HEAD
      storage_ttl: 300
      strategy: memory
```

---

## Admin API

Kong exposes a REST Admin API (default port 8001). Use it for programmatic configuration.

```bash
# List all services
curl http://localhost:8001/services

# Create a service
curl -X POST http://localhost:8001/services \
  --data name=my-api \
  --data url=http://my-api:3001

# Create a route for the service
curl -X POST http://localhost:8001/services/my-api/routes \
  --data "paths[]=/api/v1" \
  --data strip_path=true

# Add a plugin to a route
curl -X POST http://localhost:8001/routes/<route-id>/plugins \
  --data name=rate-limiting \
  --data config.minute=60

# Enable a global plugin
curl -X POST http://localhost:8001/plugins \
  --data name=cors \
  --data config.origins[]=https://app.example.com
```

**In production**, disable the Admin API from public access — bind it to `127.0.0.1` or an internal network only.

---

## Upstreams & Load Balancing

```yaml
upstreams:
  - name: my-api-upstream
    algorithm: round-robin   # round-robin | least-connections | consistent-hashing
    healthchecks:
      active:
        http_path: /health
        healthy:
          interval: 10
          successes: 2
        unhealthy:
          interval: 5
          http_failures: 3
    targets:
      - target: my-api-1:3001
        weight: 100
      - target: my-api-2:3001
        weight: 100

services:
  - name: my-api
    host: my-api-upstream   # references the upstream name
```

---

## Supabase-Specific Notes

**`apikey` header**: Supabase uses a custom `apikey` header (the anon or service-role key) in addition to or instead of `Authorization`. The Supabase Kong config validates this via the JWT plugin — the `apikey` is a valid JWT signed with your `JWT_SECRET`.

**Adding auth to a custom route**:
```yaml
  - name: my-api
    url: http://my-api:3001/
    routes:
      - name: my-api-route
        paths: [/api/v1/]
        strip_path: true
    plugins:
      - name: jwt
        config:
          key_claim_name: role
```

**Supabase does not use the Kong Admin API** — all config is declarative in `kong.yml`. In self-hosted setups, always edit `kong.yml` rather than calling the Admin API, or changes will be lost on restart.

---

## Common Pitfalls

- Editing Kong config via Admin API in Supabase self-hosted — it's overwritten on restart; always use `kong.yml`
- Exposing the Admin API (port 8001) publicly — gives full control over all routes and plugins
- Missing `strip_path: true` — the prefix path is forwarded to the upstream, causing 404s if the upstream doesn't handle it
- Overlapping route paths — Kong matches longest path first; document route priority explicitly
- CORS plugin not including `apikey` in `headers` — Supabase JS client sends `apikey` as a header; missing it causes preflight failures
- Rate limiting with `policy: local` on multiple Kong instances — counters are per-node; use `redis` policy for distributed setups
