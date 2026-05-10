---
name: contract-testing
description: Consumer-driven contract testing — Pact, API contract verification, schema validation, and preventing breaking changes.
---

## What It Solves

Integration tests require a live environment. E2E tests are slow and fragile. Contract testing catches API contract breaks between services **in CI, without a shared environment**, by verifying that the consumer's expectations match what the provider actually returns.

---

## Core Concepts

| Term | Meaning |
|---|---|
| **Consumer** | The service that calls the API (client, frontend, downstream service) |
| **Provider** | The service that serves the API (backend, upstream service) |
| **Pact** | A JSON file describing the interactions the consumer expects |
| **Pact Broker** | Central store for pact files and verification results |
| **Provider state** | Setup instructions telling the provider how to arrange its data for a given test |

---

## Pact Workflow

```
Consumer writes expectations
        ↓
  Pact file generated (JSON)
        ↓
  Published to Pact Broker
        ↓
Provider runs pact:verify in CI
        ↓
  Results published to Broker
        ↓
  Can-I-Deploy check gates the release
```

### Consumer Side

Define each interaction with three parts:

- **`given`** — provider state: `"a user with ID 42 exists"`
- **`upon receiving`** — the request: method, path, headers, body
- **`will respond with`** — expected status, headers, body shape (not exact values — use matchers)

Use **matchers** (type, regex, like) rather than exact values so the contract stays stable across test data changes.

### Provider Side

- Implement a **provider state handler** for each `given` in the pact — sets up the database or mocks needed.
- Run `pact:verify` (or equivalent) in CI on every PR that touches the API.
- A failing verification blocks the merge — never merge a provider change that breaks a pact.
- Publish verification results to the Pact Broker so consumers can check `can-i-deploy`.

---

## When to Use Contract Testing

- Microservices communicating over HTTP or messaging.
- Decoupled frontend/backend teams releasing independently.
- Public or partner-facing APIs where breaking changes have external impact.
- Shared libraries that expose typed interfaces consumed by multiple teams.

Not needed for monoliths where consumer and provider are compiled and deployed together.

---

## Schema Validation as a Lighter Alternative

When Pact is too heavy (small team, simple API, no Pact Broker available):

1. Maintain an **OpenAPI spec** as the contract artifact.
2. In CI, validate request/response payloads against the spec using tools like `dredd`, `schemathesis`, or `openapi-validator`.
3. Fail the build if the running API does not match the spec.
4. Fail the build if a consumer's integration tests use a shape not described in the spec.

This is weaker than Pact (no consumer-driven expectations) but far better than no contract enforcement.

---

## Breaking Change Policy

| Change type | Safe? | Required action |
|---|---|---|
| Add new optional field to response | Yes | None |
| Add new optional query/body parameter | Yes | None |
| Remove a field from response | No | Provider version bump + consumer update cycle |
| Rename a field | No | Provider version bump + consumer update cycle |
| Change field type | No | Provider version bump + consumer update cycle |
| Remove an endpoint | No | Deprecation period + consumer migration |

- Additions are safe; removals and renames are breaking.
- Use **semantic versioning on the API** (`/v1/`, `/v2/`) for major breaking changes.
- Never remove a field in the same release that renames it — two-step: add new, dual-read, remove old.
