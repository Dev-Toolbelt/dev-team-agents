---
name: api-design
description: REST and GraphQL API design — naming, HTTP semantics, versioning, errors, pagination.
---

# API Design

## REST API Principles

### Resource Naming

- Use **nouns**, not verbs: `/users`, `/orders`, not `/getUsers`, `/createOrder`
- Use **plural** for collections: `/products`, `/invoices`
- Use **kebab-case** for multi-word resources: `/fuel-types`, `/gas-stations`
- Nest resources to express ownership (max 2 levels): `/users/{id}/orders`
- Avoid deep nesting — use query parameters instead: `/orders?userId=X`

### HTTP Methods

| Method | Semantics | Idempotent | Safe |
|--------|-----------|-----------|------|
| GET | Read resource(s) | Yes | Yes |
| POST | Create resource | No | No |
| PUT | Replace resource entirely | Yes | No |
| PATCH | Partial update | No | No |
| DELETE | Remove resource | Yes | No |

### HTTP Status Codes

| Code | When to use |
|------|-------------|
| 200 OK | Successful GET, PUT, PATCH |
| 201 Created | Successful POST that created a resource |
| 204 No Content | Successful DELETE or action with no response body |
| 400 Bad Request | Invalid input, validation error |
| 401 Unauthorized | Not authenticated |
| 403 Forbidden | Authenticated but not authorized |
| 404 Not Found | Resource does not exist |
| 409 Conflict | State conflict (duplicate, optimistic lock) |
| 422 Unprocessable Entity | Syntactically valid but semantically invalid |
| 429 Too Many Requests | Rate limit exceeded |
| 500 Internal Server Error | Unexpected server failure |

### Response Envelope

Use a consistent envelope. Recommended: [JSend](https://github.com/omniti-labs/jsend):

```json
{ "status": "success", "data": { ... } }
{ "status": "fail", "data": [{ "field": "message" }] }
{ "status": "error", "message": "Internal error description" }
```

### Pagination

For list endpoints, always paginate:
```json
{
  "status": "success",
  "data": {
    "items": [...],
    "meta": {
      "total": 150,
      "per_page": 20,
      "current_page": 1,
      "last_page": 8
    }
  }
}
```

Use cursor-based pagination for large datasets or real-time feeds.

### Filtering & Sorting

Use query parameters:
```
GET /orders?status=active&sort=created_at&direction=desc
GET /products?category=fuel&min_price=10&max_price=50
```

### Versioning

Prefer URL versioning for clarity and caching:
```
/api/v1/users
/api/v2/users
```

Alternatively: `Accept: application/vnd.myapp.v2+json` header versioning (more REST-pure, harder to test).

- Never remove a field without a major version bump
- Deprecate with `Deprecation` and `Sunset` headers

---

## API Security

- **Always use HTTPS** — no exceptions in production
- **Auth**: prefer stateless JWT (Bearer token) or OAuth 2.0; avoid session cookies for APIs
- **Rate limiting**: apply per-user and per-IP; return 429 with `Retry-After` header
- **Input validation**: validate all query params, body fields, and path params server-side
- **Never expose internal IDs** — use UUIDs or opaque external identifiers in public APIs

---

## GraphQL Schema Conventions

- Types use `PascalCase`: `UserProfile`, `OrderItem`
- Fields use `camelCase`: `firstName`, `totalAmount`
- Queries: descriptive names — `userById`, `activeOrders`
- Mutations: verb + noun — `createUser`, `updateOrderStatus`, `deleteProduct`
- Use `input` types for mutation arguments: `CreateUserInput`, `UpdateProductInput`
- Pagination: use Relay Connection spec (`edges`, `node`, `pageInfo`)
- Errors: use a union type `Result = Success | Error` for explicit error handling

---

## Documentation Standards

Document every endpoint with:
1. **Method + Path**: `POST /api/v1/users`
2. **Description**: what it does, when to use it
3. **Auth required**: yes/no, which role/scope
4. **Request**: headers, body schema with types and required fields
5. **Response**: status codes, response schema with examples
6. **Errors**: possible error codes and their meaning

Generate OpenAPI 3.0 spec for machine-readable documentation.
