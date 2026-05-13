# Cloudflare DNS, Pages & Tunnels Reference

## DNS Management

### Common Record Operations

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

## Pages Deployment

### Deploy via Wrangler

```bash
# Build first, then deploy dist/
wrangler pages deploy dist/ --project-name=my-project

# Direct upload (no build step)
wrangler pages deploy ./public --project-name=my-project
```

### GitHub Actions Integration

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

### Custom Domains

1. Go to **Pages → your project → Custom domains**
2. Add your domain and follow the DNS verification steps
3. Cloudflare automatically provisions SSL

---

## Tunnels (cloudflared)

Expose a local or private service to the internet without opening firewall ports.

### Install and Authenticate

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Authenticate (browser login)
cloudflared tunnel login
```

### Create and Configure a Tunnel

```bash
# Create
cloudflared tunnel create my-tunnel

# Create config at ~/.cloudflared/config.yml
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

## WAF & Rate Limiting

### Custom WAF Rule

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

### Rate Limiting Rule

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

## Cache Rules

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
