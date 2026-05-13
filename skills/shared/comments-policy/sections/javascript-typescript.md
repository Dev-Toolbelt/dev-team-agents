# Comments Policy — JavaScript / TypeScript

## JSDoc

Use JSDoc for public API surfaces — exported functions, classes, and complex type shapes. Skip it for internal helpers where the signature is self-explanatory.

```typescript
/**
 * Calculates the discounted price after applying the promotional rate.
 * Regulation ref: pricing-policy.md §3.2 — promotional discounts capped at 40%.
 *
 * @param basePrice - Original price in cents (integer)
 * @param discountRate - Discount as a decimal (0.0 – 0.4)
 * @returns Discounted price in cents, rounded down
 */
export function applyDiscount(basePrice: number, discountRate: number): number {
  return Math.floor(basePrice * (1 - discountRate));
}
```

**When to write JSDoc:**
- Exported functions consumed by other modules
- Complex parameter or return shapes
- Business rules or constraints that callers must know

**When to skip:**
- Internal / private functions
- One-liner utilities where the name explains everything

---

## Type Annotations as Comments

TypeScript has native type syntax — prefer it over prose comments for type documentation.

```typescript
// BAD — prose comment for type info
// Returns a map of userId to their roles
function getUserRoles() { ... }

// GOOD — types document the shape
function getUserRoles(): Map<string, Role[]> { ... }
```

For complex generics or conditional types, a short inline comment explaining the intent is acceptable:

```typescript
// Extracts keys of T whose values are assignable to V
type KeysOfType<T, V> = { [K in keyof T]: T[K] extends V ? K : never }[keyof T];
```

---

## Inline Comments

Follow the core policy: explain **why**, not **what**.

```typescript
// BAD — explains what
const timeout = 5000; // set timeout to 5000ms

// GOOD — explains why
// Upstream payment API requires 5s minimum before retry (PCI requirement CP-412)
const PAYMENT_RETRY_DELAY_MS = 5000;
```

---

## AAA Markers in Tests

```typescript
describe("applyDiscount", () => {
  it("caps discount at 40% per pricing policy", () => {
    // Arrange
    const basePrice = 10000;
    const rate = 0.4;

    // Act
    const result = applyDiscount(basePrice, rate);

    // Assert
    expect(result).toBe(6000);
  });
});
```

---

## What NOT to Do

```typescript
// BAD — noise
const x = 1; // set x to 1

// BAD — commented-out code
// const oldFn = () => { ... };

// BAD — TODO without a ticket
// TODO: fix this later

// BAD — closing brace marker
if (condition) {
  doSomething();
} // end if
```
