---
name: graphql
description: GraphQL API conventions — schema design, naming, resolver patterns, N+1 prevention with DataLoader, pagination, mutations, subscriptions, and error handling. Load when the project exposes or consumes a GraphQL API.
---

## Detection Signals

- `graphql` or `@graphql-tools/*` in `package.json`
- `.graphql` / `.gql` schema files in the repository
- `apollo-server`, `graphql-yoga`, `strawberry-graphql`, `ariadne`, `gqlgen`, `async-graphql` dependency
- `GRAPHQL_ENDPOINT` env var or `/graphql` route in routing config
- `ApolloClient`, `urql`, or `graphql-request` on the frontend

---

## Schema-First vs Code-First

**Detect which approach the project uses before writing any schema or resolver:**

| Signal | Approach |
|--------|----------|
| `.graphql` / `.gql` files are the source of truth | Schema-first |
| Schema generated from code annotations / decorators | Code-first |

- **Schema-first**: SDL (Schema Definition Language) files are committed; resolvers implement the contract.
- **Code-first**: resolvers are annotated and the schema is generated at build time (e.g. TypeGraphQL, Strawberry, gqlgen).

**Do not mix approaches.** Follow whichever the project already uses.

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Types | `PascalCase` | `User`, `OrderItem` |
| Fields | `camelCase` | `createdAt`, `totalAmount` |
| Queries | `camelCase` verb-noun | `user(id)`, `listOrders` |
| Mutations | `camelCase` action-noun | `createUser`, `updateOrder`, `deleteProduct` |
| Subscriptions | `camelCase` event | `orderStatusChanged`, `messageReceived` |
| Enums | `SCREAMING_SNAKE_CASE` values | `ORDER_STATUS_PENDING` |
| Input types | `[Action][Type]Input` | `CreateUserInput`, `UpdateOrderInput` |

**Never expose internal database column names directly** — map them to clean field names in the schema.

---

## Query Design

```graphql
# Good — explicit, typed arguments
type Query {
  user(id: ID!): User
  users(filter: UserFilterInput, page: Int, perPage: Int): UserConnection!
  order(id: ID!): Order
}

# Bad — catch-all input loses discoverability
type Query {
  users(input: JSON): [User]
}
```

- Mark fields non-null (`!`) only when the server guarantees a value — never lie about nullability
- Use `!` on list fields (`[User!]!`) when neither the list nor its elements can be null
- Input arguments for filtering should use dedicated Input types, not scalars

---

## Mutation Conventions

Wrap mutation arguments in a single `input` object for extensibility and forward-compatibility:

```graphql
type Mutation {
  createUser(input: CreateUserInput!): CreateUserPayload!
  updateOrder(id: ID!, input: UpdateOrderInput!): UpdateOrderPayload!
}

input CreateUserInput {
  email: String!
  name: String!
  role: UserRole!
}

# Payload: return the mutated entity + optional user-facing errors
type CreateUserPayload {
  user: User
  errors: [UserError!]!
}

type UserError {
  field: String        # which field caused the error (null = global error)
  message: String!
  code: String!        # machine-readable code for client handling
}
```

**Rules:**
- Return the mutated object in the payload so clients can update their cache without a refetch
- Use `errors: [UserError!]!` (always-present empty array) instead of nullable `error` — this is the [Errors-as-Data](https://productionreadygraphql.com) pattern
- Reserve top-level GraphQL errors for unexpected failures (auth, server crash), not for business-rule violations

---

## N+1 Prevention — DataLoader

Every resolver that loads related data by ID must use a DataLoader (batching + caching per request):

```ts
// Without DataLoader — fires 1 query per user (N+1)
const resolver = {
  Order: {
    user: (order) => db.users.findById(order.userId),  // ❌
  },
}

// With DataLoader — batches into 1 query for all orders in the request
const userLoader = new DataLoader(async (ids: string[]) => {
  const users = await db.users.findByIds(ids);
  return ids.map(id => users.find(u => u.id === id) ?? null);
});

const resolver = {
  Order: {
    user: (order, _, ctx) => ctx.loaders.user.load(order.userId),  // ✅
  },
}
```

**Rules:**
- Create DataLoaders **per request** (in context), never as singletons — singletons leak data between requests
- One DataLoader per entity type (`userLoader`, `productLoader`, etc.)
- Before writing a resolver that fetches related data, check whether a loader already exists in the context

---

## Pagination

Use **Relay cursor-based pagination** for collections that can grow large. Use offset (`page` / `perPage`) only for small, stable lists.

```graphql
# Relay-style connection pattern
type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type Query {
  users(first: Int, after: String, last: Int, before: String): UserConnection!
}
```

**Rules:**
- Never return unbounded lists (`[User!]!` without pagination args) — always paginate
- `totalCount` is expensive on large tables; make it optional or computed lazily
- Cursors must be opaque to clients (base64-encode the underlying offset or ID)

---

## Subscriptions

```graphql
type Subscription {
  orderStatusChanged(orderId: ID!): OrderStatusEvent!
}

type OrderStatusEvent {
  orderId: ID!
  status: OrderStatus!
  updatedAt: String!
}
```

**Rules:**
- Filter events server-side — never send all events and filter client-side
- Subscriptions must enforce the same auth rules as queries/mutations
- Keep subscription payloads small — include IDs and changed fields; let the client refetch full data if needed
- Always handle connection cleanup (unsubscribe on disconnect) to prevent memory leaks server-side

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

---

## What to Do Before Declaring Done

- [ ] No resolver fetches related data without going through a DataLoader
- [ ] All list fields are paginated
- [ ] Mutation payloads return the mutated entity
- [ ] Business errors use the `errors: [UserError!]!` pattern
- [ ] Subscriptions filter server-side
- [ ] Introspection disabled in production config
- [ ] Depth/complexity limits configured
