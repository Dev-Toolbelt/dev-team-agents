---
name: test-pyramid
description: Test pyramid — unit, integration, and E2E patterns with tooling and pitfall guidance.
---

# Test Pyramid — Implementation Patterns

## Unit Tests

### What belongs here
- Pure functions and algorithms
- Business rules (discount calculation, validation logic, state machines)
- Value objects and domain entities
- Error handling branches

### Structure
```
tests/
  unit/
    domain/
      OrderTest
      PricingServiceTest
    utils/
      DateHelperTest
```

### Patterns
```
// Good unit test — isolated, no I/O, fast
function test_calculateDiscount_vipCustomer_gets15Percent() {
    // Arrange
    $pricing = new PricingService();
    $customer = new Customer(tier: CustomerTier::VIP);

    // Act
    $discount = $pricing->calculateDiscount($customer, amount: 100.00);

    // Assert
    assert($discount === 15.00);
}
```

### Common pitfalls
- Using real databases in unit tests (use mocks/stubs for I/O)
- Mocking the class under test
- Testing private methods directly — test through public interface
- Tests that pass only in a specific order (test isolation broken)

---

## Integration Tests

### What belongs here
- Service + repository working together
- HTTP request → response cycle (controller level)
- Database queries and transactions
- Third-party API integrations (with VCR/cassettes or test doubles)
- Queue/event publishing

### Structure
```
tests/
  integration/
    api/
      CreateOrderTest
      GetUserProfileTest
    repositories/
      OrderRepositoryTest
    services/
      PaymentServiceTest
```

### Patterns
```
// Integration test — real DB, real HTTP
function test_createOrder_endpoint_persists_and_returns_201() {
    // Arrange
    $user = User::factory()->create();
    $payload = ['items' => [['product_id' => 'uuid', 'qty' => 2]]];

    // Act
    $response = $this->actingAs($user)->postJson('/api/orders', $payload);

    // Assert
    $response->assertStatus(201);
    $this->assertDatabaseHas('orders', ['user_id' => $user->id]);
}
```

### Common pitfalls
- Database state leaking between tests — use transactions or truncate
- Tests that depend on order of execution
- Overusing mocks for things you could test for real
- Slow tests caused by unnecessary data setup — create only what's needed

---

## E2E Tests

### What belongs here
- Critical user journeys (login → checkout → confirmation)
- Flows that span multiple services or pages
- Smoke tests on production/staging

### Structure
```
tests/
  e2e/
    auth/
      LoginFlowTest
    checkout/
      CompleteOrderTest
    smoke/
      HealthCheckTest
```

### Patterns
```
// E2E test — browser/HTTP client, full stack
test('user can complete checkout', async ({ page }) => {
    // Arrange
    await page.goto('/products');

    // Act
    await page.click('[data-testid="add-to-cart"]');
    await page.click('[data-testid="checkout"]');
    await page.fill('[name="card_number"]', '4242424242424242');
    await page.click('[data-testid="confirm-order"]');

    // Assert
    await expect(page.locator('[data-testid="order-confirmation"]')).toBeVisible();
});
```

### Common pitfalls
- Too many E2E tests — they're slow and fragile
- No retry logic for flaky network calls
- Hardcoded waits (`sleep(2)`) — use `waitFor` / assertions instead
- Testing UI details instead of user outcomes

---

## Test Data Management

| Pattern | When to use |
|---------|-------------|
| Factories | Creating model instances with sensible defaults |
| Fixtures | Static, reusable data sets (e.g., seed a country list) |
| Builders | Complex object graphs with many relationships |
| Fakes | In-memory implementations of repositories/services |

**Principle**: create the minimum data needed for the test. Each test owns its data setup.

---

## Test Performance

- Run unit tests first (fastest, highest signal-to-noise)
- Parallelize integration tests at the file level
- Use DB transactions that rollback after each test instead of truncating
- Cache schema migrations in a snapshot file (avoid running all migrations per test run)
- Mark slow tests explicitly and exclude from default run (`--exclude-group slow`)
