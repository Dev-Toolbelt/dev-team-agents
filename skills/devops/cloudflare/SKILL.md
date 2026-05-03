---
name: cloudflare
description: Cloudflare configuration and operations skill. Covers DNS, Workers, Pages, Tunnels, Zero Trust/Access, WAF, Rate Limiting, R2, KV, and Cache Rules. Always collects credentials securely before acting.
---

# Cloudflare

## Credentials Protocol — Collect Before Acting

**Before any Cloudflare task**, instruct the user to provide the required credentials securely. Never ask for credentials in plain text in the chat.

### Step 1 — Identify what is needed

| Task | Required credentials |
|------|----------------------|
| DNS changes | API Token with `Zone:DNS:Edit` scope |
| Workers deploy | API Token with `Account:Workers Scripts:Edit` scope |
| Pages deploy | API Token with `Account:Cloudflare Pages:Edit` scope |
| Tunnel setup | API Token with `Account:Cloudflare Tunnel:Edit` scope |
| Zero Trust / Access | API Token with `Account:Access:Edit` scope |
| WAF / Rate Limiting | API Token with `Zone:Firewall Services:Edit` scope |
| R2 operations | API Token with `Account:Workers R2 Storage:Edit` scope |
| KV operations | API Token with `Account:Workers KV Storage:Edit` scope |
| General read/debug | API Token with read-only scopes for the relevant resource |

Always request **scoped API Tokens**, never the Global API Key.

### Step 2 — Instruct the user to create the token

Direct the user to: **Cloudflare Dashboard → My Profile → API Tokens → Create Token**

Use the "Custom Token" option to select only the scopes needed. Set TTL and IP restrictions where practical.

### Step 3 — Collect securely

Request the user to:
- Store the token in the appropriate secret store (GitHub Secrets, `.env` file outside git, CI/CD secret variable)
- Reference it as an environment variable: `$CLOUDFLARE_API_TOKEN`
- Also provide `$CLOUDFLARE_ACCOUNT_ID` and `$CLOUDFLARE_ZONE_ID` when zone-level operations are needed (found in the Dashboard overview sidebar)

**Never** commit tokens to source control. Verify `.gitignore` excludes `.env` files.

---

## Account & Zone IDs

Always confirm these before operating:

```bash
# List zones (requires Zone:Read token)
curl -s -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '.result[] | {name, id}'

# Account ID appears in the Dashboard URL and zone overview sidebar
```

---

## DNS

### Common record operations

```bash
# List DNS records
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '.result[]'

# Create A record
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"type":"A","name":"api","content":"1.2.3.4","ttl":1,"proxied":true}'

# Update record
curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/$RECORD_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"content":"1.2.3.5"}'
```

**Proxied vs DNS-only**
- `"proxied": true` — traffic goes through Cloudflare (CDN, WAF, DDoS protection active)
- `"proxied": false` — pure DNS resolution, Cloudflare features inactive for this record

---

## Workers

### Setup with Wrangler

```bash
npm install -g wrangler
wrangler login  # opens browser; stores token in ~/.wrangler/config.toml
```

### `wrangler.toml` — minimal config

```toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[vars]
APP_ENV = "production"

# Secrets: set via CLI, never in wrangler.toml
# wrangler secret put DB_PASSWORD
```

### Deploy

```bash
wrangler deploy                    # deploy to production
wrangler deploy --env staging      # deploy to named environment
wrangler tail                      # stream live logs
wrangler secret put SECRET_NAME    # set secret interactively
```

### Bindings (KV, R2, D1, Service)

```toml
[[kv_namespaces]]
binding = "MY_KV"
id = "abc123"

[[r2_buckets]]
binding = "MY_BUCKET"
bucket_name = "my-bucket"
```

---

## Pages

### Deploy via Wrangler

```bash
# Build first, then deploy dist/
wrangler pages deploy dist/ --project-name=my-project

# Direct upload (no build step)
wrangler pages deploy ./public --project-name=my-project
```

### CI/CD integration (GitHub Actions example)

```yaml
- name: Deploy to Cloudflare Pages
  uses: cloudflare/pages-action@v1
  with:
    apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
    projectName: my-project
    directory: dist
    gitHubToken: ${{ secrets.GITHUB_TOKEN }}
```

---

## Tunnels (Cloudflare Tunnel / `cloudflared`)

Expose a local or private service to the internet without opening firewall ports.

### Install and authenticate

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Authenticate (browser login)
cloudflared tunnel login
```

### Create and configure a tunnel

```bash
# Create
cloudflared tunnel create my-tunnel

# Create config file at ~/.cloudflared/config.yml
```

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /root/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: app.example.com
    service: http://localhost:3000
  - hostname: api.example.com
    service: http://localhost:8000
  - service: http_status:404
```

```bash
# Add DNS record pointing to the tunnel
cloudflared tunnel route dns my-tunnel app.example.com

# Run
cloudflared tunnel run my-tunnel

# Run as system service
cloudflared service install
```

---

## Zero Trust / Access

Protect internal tools or staging environments behind SSO without a VPN.

### Create an Access Application (via Dashboard or API)

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

Access Policies define who can reach the app (email allowlist, GitHub org, GSuite domain, etc.). Always pair with a Tunnel for self-hosted apps.

---

## WAF & Rate Limiting

### Custom WAF rule (API)

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/phases/http_request_firewall_custom/entrypoint/rules" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "action": "block",
    "expression": "(ip.src in {1.2.3.4}) or (http.request.uri.path contains \"/admin\")",
    "description": "Block known bad IP and protect admin path"
  }'
```

### Rate limiting rule

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rate_limits" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "match": { "request": { "url_pattern": "example.com/api/*" } },
    "threshold": 100,
    "period": 60,
    "action": { "mode": "simulate" }
  }'
```

Start with `"mode": "simulate"` to observe before enforcing.

---

## R2 Object Storage

S3-compatible, no egress fees. Use as a drop-in for S3 when egress costs matter.

```bash
# Create bucket
wrangler r2 bucket create my-bucket

# Upload file
wrangler r2 object put my-bucket/path/to/file.txt --file ./local-file.txt

# Download
wrangler r2 object get my-bucket/path/to/file.txt --file ./local-copy.txt
```

For S3-compatible SDK access, generate an R2 API Token with S3 Auth enabled and use:
- Endpoint: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`
- Auth: AWS Signature v4

---

## KV Store

Globally replicated key-value store. Best for configuration, feature flags, and session data. Not suited for data requiring strong consistency.

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

## Cache Rules

Control what Cloudflare caches per URL pattern.

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/rulesets/phases/http_request_cache_settings/entrypoint/rules" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "action": "set_cache_settings",
    "action_parameters": {
      "cache": true,
      "edge_ttl": { "mode": "override_origin", "default": 3600 },
      "browser_ttl": { "mode": "override_origin", "default": 300 }
    },
    "expression": "(http.request.uri.path wildcard \"/static/*\")",
    "description": "Cache static assets for 1h at edge"
  }'
```

---

## Debugging Checklist

| Symptom | Where to look |
|---------|--------------|
| DNS not resolving | Dashboard → DNS → confirm record exists and TTL propagated |
| SSL error | Dashboard → SSL/TLS → check mode (Full vs Full Strict) |
| Worker not updating | `wrangler tail` for live logs; check deployment status |
| Tunnel unreachable | `cloudflared tunnel info <name>`; check service health |
| Unexpected 403/block | Dashboard → Security → Events (WAF log) |
| Cache not working | Check `CF-Cache-Status` response header; review Cache Rules |
| Rate limit false positives | Switch to `simulate` mode; review Security → Events |

---

## Useful References

- Wrangler CLI: `wrangler --help`
- Cloudflare API docs: `https://developers.cloudflare.com/api`
- Workers docs: `https://developers.cloudflare.com/workers`
- Tunnel docs: `https://developers.cloudflare.com/cloudflare-one/connections/connect-networks`
