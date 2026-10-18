# Cloudflare Workers — Deployment Reference

## Setup with Wrangler

```bash
npm install -g wrangler
wrangler login  # opens browser; stores token in ~/.wrangler/config.toml
```

## `wrangler.toml` — Full Config

```toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[vars]
APP_ENV = "production"

# Secrets: set via CLI, never in wrangler.toml
# wrangler secret put DB_PASSWORD

# Named environments
[env.staging]
name = "my-worker-staging"
vars = { APP_ENV = "staging" }
```

## Deploy Commands

```bash
wrangler deploy                    # deploy to production
wrangler deploy --env staging      # deploy to named environment
wrangler tail                      # stream live logs
wrangler secret put SECRET_NAME    # set secret interactively
wrangler dev                       # local dev server
```

---

## KV Store Bindings

Globally replicated key-value store. Best for configuration, feature flags, and session data. Not suited for data requiring strong consistency.

```toml
[[kv_namespaces]]
binding = "MY_KV"
id = "abc123"
preview_id = "def456"   # for local dev
```

```bash
# Create namespace
wrangler kv namespace create MY_KV

# Write / read
wrangler kv key put --namespace-id=<ID> "my-key" "my-value"
wrangler kv key get --namespace-id=<ID> "my-key"

# List keys
wrangler kv key list --namespace-id=<ID>
```

---

## R2 Object Storage Bindings

S3-compatible, no egress fees. Use as a drop-in for S3 when egress costs matter.

```toml
[[r2_buckets]]
binding = "MY_BUCKET"
bucket_name = "my-bucket"
```

```bash
# Create bucket
wrangler r2 bucket create my-bucket

# Upload file
wrangler r2 object put my-bucket/path/to/file.txt --file ./local-file.txt

# Download
wrangler r2 object get my-bucket/path/to/file.txt --file ./local-copy.txt
```

For S3-compatible SDK access, generate an R2 API Token with S3 Auth enabled:
- Endpoint: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
- Auth: AWS Signature v4

---

## Durable Objects Bindings

```toml
[[durable_objects.bindings]]
name = "MY_DO"
class_name = "MyDurableObject"

[[migrations]]
tag = "v1"
new_classes = ["MyDurableObject"]
```

---

## Service Bindings

```toml
[[services]]
binding = "AUTH_SERVICE"
service = "auth-worker"
```

---

## Zero Trust / Access (Protect Workers)

Protect internal Workers or staging environments behind SSO without a VPN.

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/access/apps" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "name": "Staging App",
    "domain": "staging.example.com",
    "type": "self_hosted",
    "session_duration": "24h"
  }'
```

Access Policies define who can reach the app (email allowlist, GitHub org, GSuite domain). Always pair with a Tunnel for self-hosted apps.
