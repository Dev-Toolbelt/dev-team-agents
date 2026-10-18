---
name: api-versioning
description: API versioning — compatibility rules and deprecation lifecycle.
---

# API Versioning

## When to Load
Load when designing a new API, planning a breaking change, or reviewing a PR that modifies public API contracts.

## Versioning Strategies

| Strategy | Example | Pros | Cons |
|----------|---------|------|------|
| **URL path** | `/v1/users`, `/v2/users` | Simple; explicit; cacheable | URL pollution; hard to version individual resources |
| **Query param** | `/users?version=2` | No URL change | Easy to ignore; pollutes query strings |
| **Header** | `Accept-Version: 2` | Clean URL; HTTP-idiomatic | Less discoverable; harder to test in browser |
| **Content negotiation** | `Accept: application/vnd.api+json; version=2` | Most REST-correct | Complex; vendor MIME types are opaque |

**Recommended default**: URL path for public APIs (simplest, most debuggable). Header versioning for internal APIs where clients are controlled.

## Backwards-Compatible vs Breaking Changes

### Safe (backwards-compatible)
- Add new optional field to request/response
- Add new endpoint
- Add new enum value at the end (caution: if clients enumerate all values)
- Loosen validation (accept more input)

### Breaking
- Remove or rename a field
- Change field type (string → integer)
- Change required/optional inverse (make optional field required)
- Change HTTP method or status code
- Tighten validation (reject previously-accepted input)
- Change pagination behaviour

**Rule**: if an existing client would break, it is a breaking change → new version required.

## Deprecation Lifecycle

1. **Announce**: publish deprecation notice in docs and via `Deprecation` and `Sunset` response headers
2. **Grace period**: minimum 6 months for external APIs; 3 months for internal
3. **Monitor**: track usage of deprecated endpoints (`/v1/*`) via logs
4. **Remove**: only after usage drops to zero or grace period ends

Response headers:
```
Deprecation: Sat, 01 Jun 2025 00:00:00 GMT
Sunset: Mon, 01 Dec 2025 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

## Version Support Window

| Client type | Minimum support | Reason |
|-------------|-----------------|--------|
| Web browser | 3 months | Can force update |
| Mobile app | 12-18 months | App store review delay; user adoption |
| Third-party integrations | 12 months | Enterprise change management cycles |
| Internal services | 3 months | Can coordinate deploys |

For mobile clients, track app version in `User-Agent` or a custom header to identify when old clients are gone.

## SDK vs API Versioning

- SDK version != API version; a v3 SDK may still call v1 or v2 API endpoints
- Pin SDK-to-API mapping in release notes
- SDK should surface the `Deprecation` header as a warning log to developers

## API Gateway Routing

Route by version at the gateway level:
```
/v1/* → service:v1
/v2/* → service:v2
```
This enables blue/green deployment of API versions without code changes in consumers.

## OpenAPI Evolution

- Maintain separate `openapi-v1.yaml` and `openapi-v2.yaml`
- Use `x-deprecated: true` extension to mark deprecated operations
- Generate a diff with `oasdiff` or `openapi-diff` in CI to detect breaking changes automatically

## Decision Checklist

- [ ] Is the change backwards-compatible? (if yes, no new version needed)
- [ ] If breaking: has a new version path been defined?
- [ ] Are `Deprecation` and `Sunset` headers added to the old version?
- [ ] Is the support window appropriate for the client type?
- [ ] Is the new version documented in OpenAPI?
- [ ] Is the gateway routing configured for both versions?
