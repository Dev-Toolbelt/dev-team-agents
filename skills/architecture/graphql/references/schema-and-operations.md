# GraphQL — Schema and Operations Reference

Deep reference for writing queries, mutations, pagination, and subscriptions. Load when actually authoring schema or resolvers; the decision-level rules live in `../SKILL.md`.

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
