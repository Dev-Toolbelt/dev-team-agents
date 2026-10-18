# GraphQL — Resolvers, Errors, and Security Reference

Deep reference for resolver performance, error surfaces, and query-level hardening. Load when writing or reviewing resolvers; the decision-level rules live in `../SKILL.md`.

---

## N+1 Prevention — DataLoader

Every resolver that loads related data by ID must use a DataLoader (batching + caching per request):

```ts
// Without DataLoader — fires 1 query per user (N+1)
const resolver = {
  Order: {
    user: (order) => db.users.findById(order.userId),  // wrong
  },
}

// With DataLoader — batches into 1 query for all orders in the request
const userLoader = new DataLoader(async (ids: string[]) => {
  const users = await db.users.findByIds(ids);
  return ids.map(id => users.find(u => u.id === id) ?? null);
});

const resolver = {
  Order: {
    user: (order, _, ctx) => ctx.loaders.user.load(order.userId),  // correct
  },
}
```

**Rules:**
- Create DataLoaders **per request** (in context), never as singletons — singletons leak data between requests
- One DataLoader per entity type (`userLoader`, `productLoader`, etc.)
- Before writing a resolver that fetches related data, check whether a loader already exists in the context
- The batch function must return results in the **same order** as the input keys, with an explicit `null` for misses — returning a shorter array silently misaligns every result

---

## Error Handling

| Error type | Where it goes | Example |
|---|---|---|
| Business rule violation | `errors` field in payload | "Email already taken" |
| Auth failure | Top-level GraphQL error with `extensions.code: UNAUTHENTICATED` | Token expired |
| Forbidden | Top-level GraphQL error with `extensions.code: FORBIDDEN` | Missing permission |
| Input validation | `errors` field in payload | "Email format invalid" |
| Unexpected server error | Top-level GraphQL error with `extensions.code: INTERNAL_SERVER_ERROR` | DB connection lost |

**Never expose stack traces or internal error details to clients in production.**

```ts
// Include machine-readable codes in extensions for client handling
throw new GraphQLError("Not authenticated", {
  extensions: { code: "UNAUTHENTICATED" },
});
```

---

## Security

- **Depth limiting**: reject queries deeper than a configured threshold (typically 5–7 levels) to prevent deeply nested query attacks
- **Complexity limiting**: assign cost weights to fields; reject queries exceeding a total budget
- **Introspection**: disable in production unless the API is public and introspection is intentional
- **Field authorization**: check permissions per resolver, not just at the operation level — a query can reach sensitive fields through nested types
- **Rate limiting**: apply per-IP or per-user limits on the `/graphql` endpoint, not just on individual resolvers
- **Batching abuse**: a single HTTP request can carry many aliased operations; apply limits to the whole request, not per operation
