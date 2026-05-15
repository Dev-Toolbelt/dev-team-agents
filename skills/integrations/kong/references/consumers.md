# Kong Rate Limiting and Consumers Reference

## Rate Limiting Strategies

| Policy | Description | Use when |
|--------|-------------|---------|
| `local` | Per-node counters | Single Kong instance |
| `redis` | Shared counters via Redis | Multiple Kong instances (distributed) |
| `cluster` | Shared via Kong DB | Kong with a database backend |

**Important**: with `policy: local` on multiple Kong instances, counters are per-node. Use `redis` policy for distributed setups.

```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 100
      hour: 1000
      policy: redis
      limit_by: consumer   # or ip, header, path
      redis_host: redis
      redis_port: 6379
```

## Consumers

A Consumer represents a user or application that calls your API. Consumers are used by auth plugins (JWT, key-auth, basic-auth) to identify and authorize callers.

```bash
# Create a consumer
curl -X POST http://localhost:8001/consumers \
  --data username=my-app \
  --data custom_id=app-001

# Add a JWT credential to the consumer
curl -X POST http://localhost:8001/consumers/my-app/jwt \
  --data key=my-app-key \
  --data secret=my-app-secret

# Add an API key credential
curl -X POST http://localhost:8001/consumers/my-app/key-auth \
  --data key=my-api-key-value
```

## Common Pitfalls

- Rate limiting with `policy: local` on multiple Kong instances — counters are per-node; use `redis` policy for distributed setups
- Editing Kong config via Admin API in Supabase self-hosted — it's overwritten on restart; always use `kong.yml`
- Exposing the Admin API (port 8001) publicly — gives full control over all routes and plugins
- Missing `strip_path: true` — the prefix path is forwarded to the upstream, causing 404s if the upstream doesn't handle it
- Overlapping route paths — Kong matches longest path first; document route priority explicitly
- CORS plugin not including `apikey` in `headers` — Supabase JS client sends `apikey` as a header; missing it causes preflight failures
