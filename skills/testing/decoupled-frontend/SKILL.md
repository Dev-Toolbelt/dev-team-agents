---
name: decoupled-frontend
description: Testing an SPA against a separate API — MSW handlers, async state coverage, factories.
---

# Testing a Decoupled Frontend

Applies when the frontend is a separate deployable consuming a REST or GraphQL API it does not own. The API is a **contract to be mocked faithfully**, not an implementation detail to be stubbed away.

---

## Detection

| Signal | Meaning |
|--------|---------|
| API base URL in env (`VITE_API_URL`, `NEXT_PUBLIC_API_URL`, `REACT_APP_API_URL`) | Frontend talks to an external API |
| `msw` in `devDependencies`, or a `mocks/`/`handlers/` directory | MSW already adopted — extend it, do not add a second mocking layer |
| Generated API client / OpenAPI or GraphQL schema in the repo | Typed contract available — bind mocks to it |
| Backend and frontend in the same deployable (SSR templates, server actions only) | This skill does not apply |

---

## Mock at the Network Layer

Prefer **Mock Service Worker (MSW)** over mocking `fetch`/`axios` or the data-fetching library. MSW intercepts at the network level, so the component, the client, and the serialization all run as they do in production.

**Handler rules**

- Handlers must mirror the real API contract — if an OpenAPI spec or generated types exist, the mock response must satisfy them.
- Organize handlers by domain (`handlers/auth.ts`, `handlers/orders.ts`) so a test can override one domain without redefining the rest.
- Keep the default handler set on the **happy path**; express failures per test with `server.use(...)`.

```ts
// Override for a specific test
server.use(
  http.get('/api/orders', () => HttpResponse.json({ error: 'Unauthorized' }, { status: 401 }))
);
```

- Reset overrides between tests (`server.resetHandlers()` in `afterEach`) so an error case cannot leak into the next test.

---

## State Coverage — Mandatory for Every Async Feature

| State | Must be tested |
|-------|---------------|
| Loading | Skeleton / spinner visible while the request is in flight |
| Success | Data renders correctly |
| Empty | Empty-state UI shown when the response is `[]` or `null` |
| Error | Error message shown on 4xx / 5xx / network failure |
| Optimistic update | UI reflects the change immediately, and rolls back when the server rejects it |

A feature with only a success test is **not covered** — the states users actually complain about are the other four.

---

## Contract Awareness

- Mock responses drift silently. Type them with the same interfaces the production code uses: a type error in a handler is the drift alarm.
- When the backend renames or removes a field, the failing signal should appear in the frontend test suite, not in production.
- For stronger guarantees across teams, escalate to `skills/testing/contract-testing/SKILL.md` (consumer-driven contracts or schema validation in CI).

---

## Test Data Factories

- Build objects with factories (e.g. `fishery`-style builders) rather than inline literals scattered across files.
- A factory takes overrides so each test states **only** what matters to it: `buildOrder({ status: 'cancelled' })`.
- Factories make edge-case variants cheap: long strings, null optionals, maximum item counts, missing optional relations.
- One factory per API resource, colocated with the handlers that return it — the factory and the mock stay in sync by proximity.

---

## Selector Priority (Testing Library convention)

| Priority | Selector | Use for |
|---|---|---|
| 1 | `getByRole` | Accessible role — button, textbox, heading |
| 2 | `getByLabelText` | Form controls with an associated label |
| 3 | `getByText` | Visible, stable text content |
| 4 | `getByTestId` | `data-testid` fallback — E2E and untargetable nodes |
| — | `querySelector`, CSS class selectors, XPath | **Never** |

Reaching for a lower-priority selector is usually an accessibility signal: if no role or label can address the element, users of assistive technology cannot address it either — fix the markup instead of the test.

---

## Visual Regression (Optional)

- Screenshot diffing or a component-explorer snapshot service is worth it for **design-system-level** components only.
- Do not apply it page-by-page — visual baselines are expensive to maintain and noisy on intentional change.
- Details: `skills/testing/visual-regression/SKILL.md`.

---

## Before Declaring Done

- [ ] All five async states covered for every new async feature
- [ ] Handlers typed against the real contract; no `any` responses
- [ ] Default handlers are happy-path; error cases are per-test overrides
- [ ] `server.resetHandlers()` runs between tests
- [ ] No direct mocking of `fetch`/`axios` added alongside MSW
- [ ] Selectors respect the priority table
