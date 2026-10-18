# Comments Policy — Python

## Docstring Style

Choose one style per project and apply it consistently. **Google style** is preferred for new projects.

### Google Style (preferred)

```python
def calculate_discount(base_price: int, discount_rate: float) -> int:
    """Calculate the discounted price after applying the promotional rate.

    Pricing policy §3.2: promotional discounts are capped at 40%.

    Args:
        base_price: Original price in cents (integer, non-negative).
        discount_rate: Discount as a decimal between 0.0 and 0.4.

    Returns:
        Discounted price in cents, rounded down.

    Raises:
        ValueError: If discount_rate exceeds 0.4.
    """
    if discount_rate > 0.4:
        raise ValueError(f"Discount rate {discount_rate} exceeds the 40% cap")
    return int(base_price * (1 - discount_rate))
```

### NumPy Style

```python
def calculate_discount(base_price: int, discount_rate: float) -> int:
    """Calculate the discounted price after applying the promotional rate.

    Parameters
    ----------
    base_price : int
        Original price in cents.
    discount_rate : float
        Discount as a decimal (0.0 – 0.4).

    Returns
    -------
    int
        Discounted price in cents, rounded down.
    """
```

### Sphinx / reStructuredText Style

```python
def calculate_discount(base_price: int, discount_rate: float) -> int:
    """Calculate the discounted price.

    :param base_price: Original price in cents.
    :param discount_rate: Discount as a decimal (0.0 – 0.4).
    :returns: Discounted price in cents.
    :raises ValueError: If discount_rate exceeds 0.4.
    """
```

---

## When to Write Docstrings

| Location | Required? |
|----------|-----------|
| Public module-level functions | Yes |
| Public class and its `__init__` | Yes |
| Public class methods | Yes |
| Private methods (`_name`) | Only if behavior is non-obvious |
| One-liner utilities | No — name is sufficient |

---

## Type Hints as Comments

Python type hints are the native way to document types — use them instead of prose comments:

```python
# BAD — prose for type info
# returns a dict mapping user_id to list of roles
def get_user_roles():
    ...

# GOOD
def get_user_roles() -> dict[str, list[str]]:
    ...
```

For complex shapes not expressible in a type hint alone, a short inline note is acceptable:

```python
# Mapping of ISO 3166-1 alpha-2 code → (tax_rate, currency_symbol)
COUNTRY_CONFIG: dict[str, tuple[float, str]] = {
    "US": (0.0, "$"),
    "BR": (0.12, "R$"),
}
```

---

## Inline Comments

Same core rule: **why**, not **what**.

```python
# BAD
total = base + tax  # add tax to base

# GOOD
# Brazilian ICMS tax is applied after federal PIS/COFINS per regulation 12/2024
total = base + icms_tax + federal_tax
```

---

## AAA Markers in Tests

```python
def test_discount_capped_at_40_percent():
    # Arrange
    base_price = 10000
    rate = 0.4

    # Act
    result = calculate_discount(base_price, rate)

    # Assert
    assert result == 6000
```

---

## What NOT to Do

```python
# BAD — commented-out code
# old_result = legacy_calculate(base_price)

# BAD — obvious noise
x = x + 1  # increment x

# BAD — TODO without ticket
# TODO: fix edge case

# BAD — version control in comments
# Added by João on 2024-01-15
```
