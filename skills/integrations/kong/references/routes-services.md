# Kong Routes and Services Reference

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
