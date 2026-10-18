# Comments Policy — Go

## Godoc Conventions

Go documentation is generated from comments that immediately precede a declaration — no blank line between the comment and the declaration.

### Package Comment

Every package must have a package comment:

```go
// Package pricing implements promotional discount logic.
// All discount rates are capped at 40% per pricing policy §3.2.
package pricing
```

For large packages, place the comment in a dedicated `doc.go` file.

### Function / Method Comments

```go
// ApplyDiscount calculates the discounted price after applying the promotional rate.
// The discount rate is capped at 0.4 per pricing policy §3.2.
// Returns the discounted price in cents, rounded down.
func ApplyDiscount(basePrice int, discountRate float64) (int, error) {
    if discountRate > 0.4 {
        return 0, fmt.Errorf("discount rate %.2f exceeds the 40%% cap", discountRate)
    }
    return int(float64(basePrice) * (1 - discountRate)), nil
}
```

**Rules:**
- Start the comment with the declaration name: `// ApplyDiscount ...`
- Use complete sentences ending with `.`
- Document every exported identifier — functions, types, constants, variables
- For unexported identifiers: only comment if behavior is non-obvious

### Type Comments

```go
// UserRole represents the access level granted to a user within a project.
type UserRole int

const (
    RoleViewer UserRole = iota // read-only access
    RoleEditor                 // can create and edit content
    RoleAdmin                  // full access including user management
)
```

### Interface Comments

```go
// Discounter calculates promotional prices. Implementations must respect
// the 40% cap defined in pricing policy §3.2.
type Discounter interface {
    Apply(basePrice int, rate float64) (int, error)
}
```

---

## Inline Comments

Same core rule: **why**, not **what**.

```go
// BAD — explains what
total := base + tax // add tax to base

// GOOD — explains why (with external reference)
// Brazilian ICMS requires post-calculation adjustment per Decree 7.212/2010.
total := applyICMSAdjustment(base + federalTax)
```

Use `//nolint:directive` comments sparingly — always include the reason:

```go
return result //nolint:errcheck // WriteString to bytes.Buffer never errors
```

---

## AAA Markers in Tests

```go
func TestApplyDiscount_CapsAt40Percent(t *testing.T) {
    // Arrange
    basePrice := 10000
    rate := 0.4

    // Act
    result, err := ApplyDiscount(basePrice, rate)

    // Assert
    require.NoError(t, err)
    assert.Equal(t, 6000, result)
}
```

---

## What NOT to Do

```go
// BAD — noise
x := x + 1 // increment x

// BAD — commented-out code
// oldResult := legacyCalculate(basePrice)

// BAD — TODO without ticket
// TODO: fix this

// BAD — missing the declaration name in the comment
// calculates discounts
func ApplyDiscount(...) { ... }  // should start: "// ApplyDiscount ..."
```
