---
name: test-strategy
description: Testing strategy principles for deciding what, when, and how to test. Use when planning test coverage, evaluating whether a test is worth writing, or defining the testing approach for a project or feature.
---

# Test Strategy

## The Testing Decision Framework

Before writing a test, ask:

1. **What could break here?** — If nothing can break, don't test it.
2. **How often will this break?** — High-risk logic needs tests. Config files don't.
3. **How hard is it to detect if broken?** — Silent failures need tests. Runtime errors are visible.
4. **What's the cost of a bug here?** — Payment flows need tests. Admin labels might not.
5. **Is this test maintainable?** — Tests that break on every refactor have negative ROI.

---

## Test Pyramid

```
         /\
        /  \    E2E Tests
       /    \   (few, slow, high confidence)
      /------\
     /        \  Integration Tests
    /          \  (moderate, medium speed)
   /------------\
  /              \  Unit Tests
 /                \  (many, fast, focused)
/------------------\
```

### Unit Tests
- Test a single function/method in isolation
- No database, no network, no filesystem
- Fast: < 10ms each
- Write when: pure business logic, complex algorithms, edge cases in a function

### Integration Tests
- Test how components work together
- May use real database (test DB), real filesystem
- Medium speed: < 1s each
- Write when: service + repository interaction, API request/response cycle, database queries

### E2E Tests
- Test the full user flow through the application
- Runs against a real (or staging) environment
- Slow: seconds to minutes
- Write when: critical user journeys, checkout flows, authentication, core business flows
- Keep minimal — prefer integration tests where possible

---

## Avoid Overengineering Tests

**Do not write tests for:**
- Framework behavior (the framework is already tested)
- Trivial getters/setters with no logic
- Configuration files
- Auto-generated code
- Code that's about to be deleted

**Watch out for:**
- Tests that test implementation details (brittle — breaks on refactor)
- Tests that duplicate the source code logic
- Tests that require extensive mocking just to run (signals the code is hard to test)
- 100% coverage as a goal — coverage measures lines executed, not quality

---

## Testing Testable Code

Code is testable when:
- Dependencies are injected, not instantiated inside
- Functions are pure (same input → same output)
- Side effects are isolated (no mixing DB queries with business logic)
- Classes are small and focused (one responsibility)

When writing production code, prefer patterns that make testing natural — but don't over-engineer the production code just to reach testability.

---

## Coverage Targets by Context

| Context | Coverage Target |
|---------|----------------|
| Business logic / domain layer | 80–90% |
| API controllers | 70–80% (integration level) |
| Infrastructure / repositories | 60–70% |
| UI components | Key paths only |
| Overall | 60–70% is usually healthy |

These are guidelines, not mandates. A 40%-covered codebase with tests on the right things beats a 90%-covered one with tests on the wrong things.

---

## Test Naming Convention

Tests should read like specifications:

```
given_[context]_when_[action]_then_[expected_result]
// or simply:
[method/feature]_[scenario]_[expected outcome]

Examples:
- calculateDiscount_withVIPCustomer_applies15Percent
- createOrder_withOutOfStockItem_throwsUnavailableException
- loginEndpoint_withWrongPassword_returns401
```

---

## AAA Pattern

Every test follows Arrange → Act → Assert:

```
// Arrange — set up the test scenario
// Act — execute the behavior under test
// Assert — verify the outcome
```

Add these as comments in tests where the sections aren't obvious.
