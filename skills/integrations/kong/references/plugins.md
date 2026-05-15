# Kong Plugins Reference

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

## Supabase-Specific Auth

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
