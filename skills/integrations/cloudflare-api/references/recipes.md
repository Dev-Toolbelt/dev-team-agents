# Cloudflare API Recipes

Each write step follows `SKILL.md` § Write Protocol: read, confirm with `AskUserQuestion`, call with `--allow-write`, read back. `cf` below is shorthand for `devteam integration call cloudflare`. Write the full command when running it.

## Point a hostname at a new IP

```bash
cf GET /zones/{zone_id}/dns_records --query name=api.example.com --query type=A --json \
  | jq '.response.result[] | {id, content, proxied, ttl}'
# confirm: api.example.com A 1.2.3.4 → 5.6.7.8 (proxied stays true)
cf PATCH /zones/{zone_id}/dns_records/<record_id> --data '{"content":"5.6.7.8"}' --allow-write --json
cf GET /zones/{zone_id}/dns_records/<record_id> --json | jq '.response.result.content'
```

No record yet → `POST /zones/{zone_id}/dns_records` with `{"type":"A","name":"api","content":"5.6.7.8","ttl":1,"proxied":true}`.

## Purge changed assets after a deploy

```bash
cf POST /zones/{zone_id}/purge_cache \
  --data '{"files":["https://example.com/app.js","https://example.com/app.css"]}' --allow-write --json
```

Prefer `files` or `prefixes` over `purge_everything`. Batch at most 30 URLs per call.

## Block an abusive IP

```bash
cf GET /zones/{zone_id}/firewall/access_rules/rules --query configuration.value=203.0.113.7 --json
cf POST /zones/{zone_id}/firewall/access_rules/rules --allow-write --json \
  --data '{"mode":"block","configuration":{"target":"ip","value":"203.0.113.7"},"notes":"abuse — <ticket>"}'
```

## Add a WAF custom rule without touching the others

```bash
cf GET /zones/{zone_id}/rulesets/phases/http_request_firewall_custom/entrypoint --json \
  | jq '{id: .response.result.id, rules: [.response.result.rules[] | {id, description, expression, action}]}'
cf POST /zones/{zone_id}/rulesets/<ruleset_id>/rules --allow-write --json --data-file rule.json
```

`rule.json`: `{"description":"Block admin outside office","expression":"(http.request.uri.path wildcard \"/admin*\" and not ip.src in {198.51.100.0/24})","action":"block"}`.

For a new rule, propose `"action":"log"` first when the plan allows it, then switch it to `block` with a PATCH once the security events look right.

## Turn on Always Use HTTPS

```bash
cf GET /zones/{zone_id}/settings/always_use_https --json | jq '.response.result.value'
cf PATCH /zones/{zone_id}/settings/always_use_https --data '{"value":"on"}' --allow-write --json
```

## Roll back a Pages deployment

```bash
cf GET /accounts/{account_id}/pages/projects/<project>/deployments --json \
  | jq '.response.result[] | {id, environment, created_on, url, latest_stage: .latest_stage.status}'
cf POST /accounts/{account_id}/pages/projects/<project>/deployments/<deployment_id>/rollback --allow-write --json
```

## Handling Failures

| `details.http_status` / error code | Meaning | Do |
|---|---|---|
| 400, `errors[].code` 1004 / 9xxx | Invalid body or value | Fix the body from `errors[].message`, then re-confirm |
| 401, or `10000` "Authentication error" | Token missing a permission or expired | Name the permission from `skills/devops/cloudflare/SKILL.md` § Credentials Protocol and ask the user to edit the token |
| 403 | Token not scoped to this zone or account | Same as above, naming the resource |
| 404 | Wrong path or id, or the phase has no ruleset yet | Re-check `references/endpoints.md`. Re-read the id |
| 409 / `81057` "record already exists" | Duplicate | GET the existing record and PATCH it instead |
| 429, `details.retry_after` | Rate limited (1200 requests / 5 min per user) | Wait `retry_after` seconds. Never retry in a tight loop |
| Usage error, exit 2 | The CLI refused before sending | Read `error` and `hint`. Nothing was sent |
