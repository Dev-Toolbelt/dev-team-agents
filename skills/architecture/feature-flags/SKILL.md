---
name: feature-flags
description: Feature flags — types, targeting rules, rollout, lifecycle.
---

## Flag Types

| Type | Purpose | Example |
|------|---------|---------|
| Release flag | Hide incomplete or in-progress features from production users | New checkout flow not yet ready |
| Experiment flag | A/B test — split traffic to compare variants | Button color test, pricing copy |
| Ops flag | Kill switch for a feature or integration under load | Disable recommendation engine |
| Permission flag | Gate access by user segment or plan tier | Beta users, enterprise plan |

---

## Targeting Rules

- **User ID** — target specific users or accounts; useful for internal dogfooding
- **Percentage rollout** — canary deploys; start at 1%, increase incrementally
- **Environment** — `dev`, `staging`, `production` — never use prod flags in tests
- **Custom attributes** — region, plan, cohort, device type

Security constraint:
- **Never rely on client-side flags for auth or authorization** — flags are observable in the client; access control must be enforced server-side

---

## LaunchDarkly Integration

- Use the **server-side SDK** for any flag that controls sensitive behavior (pricing, permissions, feature gating)
- **Batch flag evaluations at request start** — resolve all flags needed for a request in one call, not per check; avoids latency spikes and inconsistent states within a request
- Set `offline` mode in tests with fixed values — never call the LaunchDarkly API from test suites
- Store the SDK key in environment variables; never hard-code it
- Use the `allFlagsState` method to return a snapshot for SSR hydration

---

## Unleash Integration

- Self-hosted option; suitable when data residency or vendor lock-in is a concern
- Use **activation strategies** to control rollout:
  - `gradualRollout` — percentage-based, hash-consistent per user
  - `userWithId` — target specific user IDs
  - `remoteAddress` — useful for office/IP gating
  - Custom strategies via the strategy API
- Always define a fallback value in code for when Unleash is unreachable

---

## Flag Lifecycle

```
create → implement → ramp (% rollout) → release (100%) → cleanup
```

| Stage | Action |
|-------|--------|
| create | Define flag in the system with description, owner, and expected cleanup date |
| implement | Wrap code with flag check; test both paths |
| ramp | Gradually increase rollout percentage; monitor error rates |
| release | 100% rollout confirmed stable |
| cleanup | Remove code branch + delete flag from system within 2 sprints |

---

## Cleanup Rule

- Flags at **100% rollout for more than 30 days** must be cleaned up
- Stale flags are tracked as tech debt in the backlog
- Cleanup means: remove the conditional code, delete the dead branch, delete the flag from the system
- Assign flag ownership at creation time; owners are responsible for cleanup

---

## Testing Flags

- Test with flag **ON** and flag **OFF** — both paths must have test coverage
- Never mock the flag system — use real flag evaluation with test environments
- Use fixed flag states in test environments (env var or local config) to ensure deterministic results
- Integration tests should explicitly assert which flag state is being tested

---

## Anti-Patterns

| Anti-pattern | Why it's problematic | Alternative |
|-------------|---------------------|-------------|
| Nested flags | Combinatorial explosion; untestable states | Flatten into a single flag per decision |
| Flags in migrations | Inconsistent schema state across rollback | Use expand/contract migration pattern instead |
| Permanent flags | Becomes undocumented configuration; flags aren't monitored like config | Promote to environment config or app settings |
| Flags for auth | Client-side flags are visible; security bypass risk | Enforce access server-side always |
