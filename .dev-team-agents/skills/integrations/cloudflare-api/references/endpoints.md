# Cloudflare v4 Endpoint Map

Paths are relative to `https://api.cloudflare.com/client/v4` and are passed to `devteam integration call cloudflare <METHOD> <path>`. `{zone_id}` and `{account_id}` are filled by the CLI; every other `<id>` is written in literally. **W** = write (needs the § Write Protocol in `SKILL.md`).

When an endpoint is not listed here, check the official reference at `https://developers.cloudflare.com/api/` before calling. Never guess.

## Token and Account

| Intent | Method | Path |
|---|---|---|
| Verify a user token | GET | `/user/tokens/verify` |
| Verify an account-owned token | GET | `/accounts/{account_id}/tokens/verify` |
| List accounts | GET | `/accounts` |
| Account audit log | GET | `/accounts/{account_id}/audit_logs` (`--query since=<ISO>`) |

Refused by the CLI, with or without `--allow-write`, because the response is a credential: `/user/tokens…` and `/accounts/{account_id}/tokens…` (except `…/verify`), `/user/api_key`, `…/cfd_tunnel/<id>/token`, `…/warp_connector/<id>/token`, `…/access/service_tokens…`, `…/r2/temp-access-credentials`.

## Zones and Settings

| Intent | Method | Path |
|---|---|---|
| List zones / find by name | GET | `/zones` (`--query name=example.com`) |
| Zone details | GET | `/zones/{zone_id}` |
| All zone settings | GET | `/zones/{zone_id}/settings` |
| One setting (`ssl`, `always_use_https`, `min_tls_version`, `development_mode`, …) | GET | `/zones/{zone_id}/settings/<setting>` |
| Change one setting — body `{"value": …}` | PATCH **W** | `/zones/{zone_id}/settings/<setting>` |
| Certificate packs | GET | `/zones/{zone_id}/ssl/certificate_packs` |

## DNS

| Intent | Method | Path |
|---|---|---|
| List records | GET | `/zones/{zone_id}/dns_records` (`--query type=A --query name=www.example.com`) |
| Record details | GET | `/zones/{zone_id}/dns_records/<record_id>` |
| Create — `{"type","name","content","ttl","proxied"}` | POST **W** | `/zones/{zone_id}/dns_records` |
| Change some fields | PATCH **W** | `/zones/{zone_id}/dns_records/<record_id>` |
| Replace a record | PUT **W** | `/zones/{zone_id}/dns_records/<record_id>` |
| Delete | DELETE **W** | `/zones/{zone_id}/dns_records/<record_id>` |
| Several changes atomically — `{"deletes","patches","puts","posts"}` | POST **W** | `/zones/{zone_id}/dns_records/batch` |

`ttl: 1` means automatic. `proxied` applies to A, AAAA and CNAME only.

## Cache

| Intent | Method | Path |
|---|---|---|
| Purge URLs — `{"files": [...]}` (max 30 per call on most plans) | POST **W** | `/zones/{zone_id}/purge_cache` |
| Purge by tag / host / prefix — `{"tags"}`, `{"hosts"}`, `{"prefixes"}` | POST **W** | `/zones/{zone_id}/purge_cache` |
| Purge everything — `{"purge_everything": true}` | POST **W** (high impact) | `/zones/{zone_id}/purge_cache` |

## Rulesets (WAF custom rules, rate limiting, cache, redirects, transforms)

| Phase | Purpose |
|---|---|
| `http_request_firewall_custom` | WAF custom rules |
| `http_ratelimit` | Rate limiting rules |
| `http_request_cache_settings` | Cache rules |
| `http_request_dynamic_redirect` | Single redirect rules |
| `http_request_transform` / `http_response_headers_transform` | URL rewrite / header changes |

| Intent | Method | Path |
|---|---|---|
| Read a phase's rules | GET | `/zones/{zone_id}/rulesets/phases/<phase>/entrypoint` |
| Add one rule — `{"expression","action","description",…}` | POST **W** | `/zones/{zone_id}/rulesets/<ruleset_id>/rules` |
| Change one rule | PATCH **W** | `/zones/{zone_id}/rulesets/<ruleset_id>/rules/<rule_id>` |
| Delete one rule | DELETE **W** | `/zones/{zone_id}/rulesets/<ruleset_id>/rules/<rule_id>` |
| Replace the whole phase | PUT **W** (high impact) | `/zones/{zone_id}/rulesets/phases/<phase>/entrypoint` |

Get `<ruleset_id>` from the entrypoint GET (`response.result.id`). A 404 on the entrypoint means the phase has no ruleset yet. Only then is the PUT the right call.

| Intent | Method | Path |
|---|---|---|
| IP access rules (allow/block/challenge an IP, range, ASN, country) | GET / POST **W** | `/zones/{zone_id}/firewall/access_rules/rules` |
| Delete an IP access rule | DELETE **W** | `/zones/{zone_id}/firewall/access_rules/rules/<rule_id>` |

## Workers and Pages

| Intent | Method | Path |
|---|---|---|
| List Worker scripts | GET | `/accounts/{account_id}/workers/scripts` |
| Worker routes on a zone | GET | `/zones/{zone_id}/workers/routes` |
| Add a route — `{"pattern","script"}` | POST **W** | `/zones/{zone_id}/workers/routes` |
| Delete a route | DELETE **W** | `/zones/{zone_id}/workers/routes/<route_id>` |
| Delete a Worker | DELETE **W** (irreversible) | `/accounts/{account_id}/workers/scripts/<script_name>` |
| List Pages projects | GET | `/accounts/{account_id}/pages/projects` |
| Pages deployments | GET | `/accounts/{account_id}/pages/projects/<project>/deployments` |
| Retry a deployment | POST **W** | `/accounts/{account_id}/pages/projects/<project>/deployments/<deployment_id>/retry` |
| Roll back to a deployment | POST **W** | `/accounts/{account_id}/pages/projects/<project>/deployments/<deployment_id>/rollback` |

Uploading a script, deploying Pages and setting Worker secrets are **not** done here (multipart bodies or a secret in the body). Use `wrangler`.

## Storage

| Intent | Method | Path |
|---|---|---|
| KV namespaces | GET | `/accounts/{account_id}/storage/kv/namespaces` |
| KV keys | GET | `/accounts/{account_id}/storage/kv/namespaces/<namespace_id>/keys` (`--query prefix=…`) |
| KV bulk write — `[{"key","value"}]` | PUT **W** | `/accounts/{account_id}/storage/kv/namespaces/<namespace_id>/bulk` |
| KV bulk delete — `["key", …]` | POST **W** | `/accounts/{account_id}/storage/kv/namespaces/<namespace_id>/bulk/delete` |
| R2 buckets | GET | `/accounts/{account_id}/r2/buckets` |
| Create an R2 bucket — `{"name"}` | POST **W** | `/accounts/{account_id}/r2/buckets` |
| D1 databases | GET | `/accounts/{account_id}/d1/database` |
| D1 query — `{"sql","params"}` | POST **W** | `/accounts/{account_id}/d1/database/<database_id>/query` |

A D1 query is a POST even for a `SELECT`. It still goes through the Write Protocol: the confirmation shows the SQL.

## Tunnels

| Intent | Method | Path |
|---|---|---|
| List tunnels | GET | `/accounts/{account_id}/cfd_tunnel` (`--query is_deleted=false`) |
| Tunnel ingress config | GET | `/accounts/{account_id}/cfd_tunnel/<tunnel_id>/configurations` |
| Replace ingress — `{"config":{"ingress":[…]}}` | PUT **W** (high impact) | `/accounts/{account_id}/cfd_tunnel/<tunnel_id>/configurations` |

`…/cfd_tunnel/<tunnel_id>/token` is refused by the CLI: its response is the tunnel's secret.
