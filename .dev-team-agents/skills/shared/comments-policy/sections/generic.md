# Comments Policy — Generic (PHP, Ruby, Java, C#, Rust, and others)

Apply this guide when no language-specific section exists. The core policy rules apply universally — this file covers the documentation annotation formats that vary by language.

---

## Language-Specific Documentation Annotations

### PHP

Use **PHPDoc** for public API documentation:

```php
/**
 * Calculates the discounted price after applying the promotional rate.
 *
 * Pricing policy §3.2: promotional discounts capped at 40%.
 *
 * @param int   $basePrice     Original price in cents.
 * @param float $discountRate  Discount as a decimal (0.0 – 0.4).
 * @return int Discounted price in cents, rounded down.
 * @throws InvalidArgumentException If discount rate exceeds 0.4.
 */
public function applyDiscount(int $basePrice, float $discountRate): int
```

Document all public methods and classes. Omit PHPDoc for internal/private methods unless non-obvious.

### Ruby

Use **YARD** for public API documentation:

```ruby
# Calculates the discounted price after applying the promotional rate.
#
# Pricing policy §3.2: promotional discounts capped at 40%.
#
# @param base_price [Integer] Original price in cents.
# @param discount_rate [Float] Discount as a decimal (0.0 – 0.4).
# @return [Integer] Discounted price in cents, rounded down.
# @raise [ArgumentError] If discount_rate exceeds 0.4.
def apply_discount(base_price, discount_rate)
```

Use `#` for single-line comments; `=begin`/`=end` blocks are discouraged.

### Java

Use **Javadoc** for public API documentation:

```java
/**
 * Calculates the discounted price after applying the promotional rate.
 *
 * <p>Pricing policy §3.2: promotional discounts are capped at 40%.</p>
 *
 * @param basePrice     original price in cents (must be non-negative)
 * @param discountRate  discount as a decimal between 0.0 and 0.4
 * @return discounted price in cents, rounded down
 * @throws IllegalArgumentException if discountRate exceeds 0.4
 */
public int applyDiscount(int basePrice, double discountRate) {
```

Document all public classes, interfaces, and methods. Use `{@link ClassName}` for cross-references.

### C#

Use **XML documentation comments** (`///`):

```csharp
/// <summary>
/// Calculates the discounted price after applying the promotional rate.
/// Pricing policy §3.2: promotional discounts capped at 40%.
/// </summary>
/// <param name="basePrice">Original price in cents.</param>
/// <param name="discountRate">Discount as a decimal (0.0 – 0.4).</param>
/// <returns>Discounted price in cents, rounded down.</returns>
/// <exception cref="ArgumentException">Thrown if discountRate exceeds 0.4.</exception>
public int ApplyDiscount(int basePrice, double discountRate)
```

Document all public members. `/// <inheritdoc/>` is acceptable for interface implementations.

### Rust

Use **rustdoc** (`///` for items, `//!` for modules):

```rust
/// Calculates the discounted price after applying the promotional rate.
///
/// Pricing policy §3.2: promotional discounts are capped at 40%.
///
/// # Arguments
///
/// * `base_price` - Original price in cents.
/// * `discount_rate` - Discount as a decimal (0.0 – 0.4).
///
/// # Errors
///
/// Returns `Err` if `discount_rate` exceeds `0.4`.
///
/// # Examples
///
/// ```
/// let result = apply_discount(10000, 0.2)?;
/// assert_eq!(result, 8000);
/// ```
pub fn apply_discount(base_price: u64, discount_rate: f64) -> Result<u64, PricingError> {
```

Include `# Examples` for public functions when practical — they are compiled and run as doctests.

---

## AAA Markers in Tests (universal)

Regardless of language, use AAA section markers in test functions:

```
// Arrange   (or # Arrange, ## Arrange, etc. — use the comment syntax of the language)
// Act
// Assert
```

---

## Universal Inline Comment Rules

```
// Explains WHY ← always valid
// Explains WHAT ← fix the code instead
// Commented-out code ← delete it, git history exists
// TODO without ticket ← create an issue tracker ticket instead
// Attribution / changelog ← use git blame
// Closing brace labels (} // end if) ← refactor to smaller functions
```
