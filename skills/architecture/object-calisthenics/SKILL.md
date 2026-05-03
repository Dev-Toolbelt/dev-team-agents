---
name: object-calisthenics
description: Object Calisthenics rules for writing clean, maintainable OOP code. Use when reviewing or writing object-oriented code to enforce discipline around encapsulation, cohesion, and simplicity.
---

# Object Calisthenics

9 rules for better object-oriented code. Apply as many as the project's context justifies — they are constraints, not commandments.

## The 9 Rules

### Rule 1 — Only One Level of Indentation per Method
Each method should have at most one `if`, `for`, `while` nesting level. Extract deeper logic into private methods.

```php
// Bad
function processOrders($orders) {
    foreach ($orders as $order) {
        if ($order->isActive()) {
            foreach ($order->items as $item) {
                // logic here
            }
        }
    }
}

// Good
function processOrders($orders) {
    foreach ($orders as $order) {
        $this->processActiveOrder($order);
    }
}
```

### Rule 2 — Don't Use the `else` Keyword
Use early returns, guard clauses, or strategy pattern instead.

```php
// Bad
if ($user->isAdmin()) {
    return $this->adminView();
} else {
    return $this->guestView();
}

// Good
if ($user->isAdmin()) {
    return $this->adminView();
}
return $this->guestView();
```

### Rule 3 — Wrap All Primitives and Strings
Primitives that have behavior or validation belong in a Value Object.

```php
// Bad: string passed around, validated in multiple places
function sendEmail(string $email) { ... }

// Good: validation lives in the Value Object
function sendEmail(Email $email) { ... }
```

Apply when the primitive has: validation rules, formatting, or business meaning.

### Rule 4 — Use First-Class Collections
A class that contains a collection should have no other instance variables.

```php
// Bad: array mixed with other data
class Order {
    private array $items;
    private string $status;
}

// Good: collection has its own class
class OrderItems {
    private array $items;
    public function totalPrice(): Money { ... }
    public function count(): int { ... }
}
```

### Rule 5 — One Dot per Line (Law of Demeter)
Don't chain calls through multiple objects. Talk only to your immediate neighbors.

```php
// Bad: violates LoD
$city = $order->getCustomer()->getAddress()->getCity();

// Good: ask, don't reach
$city = $order->customerCity();
```

### Rule 6 — Don't Abbreviate
Names should be clear and complete. Abbreviations hide intent.

```php
// Bad
$ord, $usr, $mgr, $calc

// Good
$order, $user, $manager, $calculator
```

If a name is too long, the class might be doing too much.

### Rule 7 — Keep All Entities Small
- Classes: max ~50 lines of behavior (excluding blank lines and comments)
- Methods: max ~5 lines
- Files: max ~100 lines

If a class grows beyond this, extract responsibilities.

### Rule 8 — No Classes with More Than Two Instance Variables
Classes with fewer instance variables have stronger cohesion. This forces decomposition into smaller, focused objects.

```php
// Bad
class Customer {
    private string $name;
    private string $email;
    private string $street;
    private string $city;
    private string $country;
}

// Good
class Customer {
    private Name $name;
    private Email $email;
    private Address $address;
}
```

### Rule 9 — No Getters/Setters (Tell, Don't Ask)
Don't expose internals. Tell objects to do things rather than asking for their data.

```php
// Bad: asking for data, processing outside the object
$discount = $product->getPrice() * $product->getDiscountRate();

// Good: tell the object to calculate its own discount
$discount = $product->calculateDiscount();
```

---

## Applying the Rules

Start with Rules 1, 2, and 6 — they have the highest impact with the least resistance.

Rules 3, 4, and 8 are most valuable in domain-heavy code (business logic, entities, value objects).

Rules 5, 7, and 9 guide long-term architecture — apply gradually.

In code reviews, flag violations by rule number: `[OC-Rule-2] Else clause can be removed with early return`.
