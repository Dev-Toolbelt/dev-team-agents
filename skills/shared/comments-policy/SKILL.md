---
name: comments-policy
description: Code commenting standards — no comments by default; type annotations and AAA markers.
---

# Comments Policy

The guiding principle: **code should be self-documenting through clear naming**. Comments are the exception, not the rule.

---

## Core Principle — Default: No Comments

Code communicates intent through:
- Clear function/method names
- Descriptive variable names
- Small, focused functions
- Proper structure and organization

| ❌ Wrong | ✅ Correct |
|---|---|
| `// Create a new user with the given data` followed by `user = User.create(data)` | Just `user = User.create(data)` — the code is clear |

**Why avoid comments?**
1. Comments become outdated when code changes
2. Comments describe "what" — code already shows "what"
3. The need for a comment often signals unclear code
4. Every comment doubles the maintenance burden

---

## When NOT to Comment

### Don't explain what code does

```typescript
// ❌ TypeScript — obvious comments
// Loop through users
for (const user of users) {
  // Check if active
  if (user.isActive()) {
    user.update({ status: "online" }); // Update status
  }
}

// ✅ Self-documenting
for (const user of users) {
  if (user.isActive()) {
    user.update({ status: "online" });
  }
}
```

```python
# ❌ Python — obvious comments
# Calculate total price
total = sum(item.price for item in cart.items)

# ✅ No comment needed
total = sum(item.price for item in cart.items)
```

### Don't comment bad code — fix it

```go
// ❌ Go — comment masking unclear code
// Check if u was updated in last 24 hours and is not inactive
if u.UA.After(time.Now().Add(-24*time.Hour)) && u.St != "i" {
}

// ✅ Make code self-explanatory
wasRecentlyUpdated := user.UpdatedAt.After(time.Now().Add(-24 * time.Hour))
isActive := user.Status != StatusInactive
if wasRecentlyUpdated && isActive {
}
```

### Don't add noise comments

```typescript
// ❌ Adds no value
/** Get the name */
getName(): string { return this.name; }

// ✅ No annotation needed
getName(): string { return this.name; }
```

### Don't leave commented-out code

```python
# ❌ Dead code
def calculate_risk(device):
    # old_score = device.level * 10
    # return old_score + device.priority
    return self.risk_calculator.calculate(device)

# ✅ Remove dead code — use Git history if needed
def calculate_risk(device):
    return self.risk_calculator.calculate(device)
```

### Don't use version-control comments

```java
// ❌ Git exists for this
/**
 * Updated by Alice on 2025-01-15
 * Fixed null pointer in assignment
 */
public void assignDevice(String id) { ... }

// ✅ Git commit messages track history
public void assignDevice(String id) { ... }
```

---

## When Type Annotations ARE Required

Use language-native type annotation syntax when the type system cannot express the type on its own.

### Typed collections / generics

When a collection carries a specific element type the language can't infer:

```typescript
// TypeScript — explicit generic
function getNames(users: User[]): string[] {
  return users.map(u => u.name);
}
```

```python
# Python — typing module
from typing import List
def get_names(users: List[User]) -> List[str]:
    return [u.name for u in users]
```

```java
// Java — Javadoc for complex generics
/**
 * @param <T> element type
 * @return unmodifiable list of active items
 */
public <T extends Entity> List<T> getActive(List<T> items) { ... }
```

```php
// PHP — PHPDoc for typed arrays (no native syntax)
/** @param User[] $users @return string[] */
public function getNames(array $users): array { ... }
```

### Exceptions / errors thrown

Document what a function can throw when it's not obvious from the signature:

```typescript
/**
 * @throws {UserNotFoundException} when userId doesn't exist
 * @throws {UserAlreadyActiveException} when user is already active
 */
function activateUser(userId: string): User { ... }
```

```python
def activate_user(user_id: str) -> User:
    """
    Raises:
        UserNotFoundException: when user_id doesn't exist
        UserAlreadyActiveException: when user is already active
    """
```

```go
// Go — errors are return values, document the sentinel errors
// Returns ErrUserNotFound or ErrUserAlreadyActive on failure.
func ActivateUser(userID string) (*User, error) { ... }
```

```java
/**
 * @throws UserNotFoundException when userId doesn't exist
 * @throws UserAlreadyActiveException when user is already active
 */
public User activateUser(String userId) { ... }
```

### Class/struct property types (statically-typed languages)

When properties aren't declared with inline types (e.g., dynamic languages or ORM magic properties):

```php
// PHP — ORM-managed properties must be documented
/**
 * @property int $id
 * @property string $email
 * @property StatusEnum $status
 * @property-read Collection<Order> $orders
 */
class User extends Model { ... }
```

```python
# Python dataclasses / Pydantic — prefer inline annotations over docstrings
from dataclasses import dataclass

@dataclass
class User:
    id: int
    email: str
    status: UserStatus
```

### Complex return shapes

When a function returns a structured object that the type system can't describe clearly:

```typescript
/**
 * @returns { success: boolean; data: User | null; error: string | null }
 */
function tryCreateUser(input: unknown): { success: boolean; data: User | null; error: string | null } { ... }
```

---

## Test Comments — AAA Pattern (Mandatory)

**All tests must use `// Arrange`, `// Act`, `// Assert` comments** to structure test logic.

```typescript
// TypeScript / Jest
it("assigns a device to a user", () => {
  // Arrange
  const device = buildDevice({ assignedTo: null });
  const user = buildUser();

  // Act
  const result = deviceService.assign(device.id, user.id);

  // Assert
  expect(result.assignedTo).toBe(user.id);
});
```

```python
# Python / pytest
def test_assigns_device_to_user(device_service, build_device, build_user):
    # Arrange
    device = build_device(assigned_to=None)
    user = build_user()

    # Act
    result = device_service.assign(device.id, user.id)

    # Assert
    assert result.assigned_to == user.id
```

```go
// Go
func TestAssignDeviceToUser(t *testing.T) {
    // Arrange
    device := buildDevice(t, WithAssignedTo(""))
    user := buildUser(t)

    // Act
    result, err := svc.Assign(device.ID, user.ID)

    // Assert
    require.NoError(t, err)
    assert.Equal(t, user.ID, result.AssignedTo)
}
```

```java
// Java / JUnit
@Test
void assignsDeviceToUser() {
    // Arrange
    Device device = Device.builder().assignedTo(null).build();
    User user = User.builder().id("u1").build();

    // Act
    Device result = deviceService.assign(device.getId(), user.getId());

    // Assert
    assertEquals(user.getId(), result.getAssignedTo());
}
```

For tests with multiple act/assert cycles, label each pair:

```typescript
// Act — activate user
service.activate(user.id);
// Assert — user is active
expect(repo.findById(user.id).status).toBe("active");

// Act — deactivate user
service.deactivate(user.id);
// Assert — user is inactive
expect(repo.findById(user.id).status).toBe("inactive");
```

---

## Forbidden Comment Types

| Type | Example | Why |
|---|---|---|
| TODO / FIXME | `// TODO: refactor this` | Create an issue tracker ticket instead |
| Dividers | `// === Validation ===` | Use proper class/method structure |
| Journal | `// 2025-01-15: fixed bug` | Use Git commits |
| Attribution | `// Written by Alice` | Use Git blame |
| Closing brace markers | `} // end if` | Refactor to smaller functions |

---

## Self-Documentation Techniques

Prefer these over comments:

**Extract to a named method**
```typescript
// ❌ Comment explaining complex condition
// Check maintenance: overdue + has critical alerts + low uptime
if (device.lastMaintenance < subMonths(6) && device.criticalAlerts > 0 && device.uptime < 95) { ... }

// ✅ Named method
if (this.needsMaintenance(device)) { ... }
private needsMaintenance(device: Device): boolean {
  const isOverdue = device.lastMaintenance < subMonths(6);
  const hasCriticalAlerts = device.criticalAlerts > 0;
  const hasLowUptime = device.uptime < 95;
  return isOverdue && hasCriticalAlerts && hasLowUptime;
}
```

**Use constants instead of magic values**
```python
# ❌
if device.last_maintenance < now() - timedelta(months=6):  # 6 months

# ✅
MAINTENANCE_INTERVAL_MONTHS = 6
if device.last_maintenance < now() - timedelta(months=MAINTENANCE_INTERVAL_MONTHS):
```

**Use enums instead of magic strings**
```go
// ❌
if status == "f" { // f = failed

// ✅
if status == StatusFailed {
```

**Use strong types**
```typescript
// ❌
function process(data: any): void  // comment needed to explain shape

// ✅
function process(data: DevicePayload): void  // shape is in the type
```

---

## When Comments Add Value

These are the **only** cases where a comment is justified:

### Business rule or regulatory constraint
```typescript
// Per contract §3.2: late fees are 5% per month, capped at 25% of original amount
const feePercentage = Math.min(monthsLate * 5, 25);
```

### Non-obvious algorithm with an external reference
```python
# Haversine formula — https://en.wikipedia.org/wiki/Haversine_formula
lat_delta = math.radians(lat2 - lat1)
```

### Workaround for a known external bug
```go
// Workaround for PostgreSQL advisory lock behaviour under high concurrency (TICKET-1234).
// Normal UPDATE causes deadlock; raw statement bypasses the ORM lock path.
db.Exec("UPDATE devices SET sync_status = $1 WHERE id = $2", "synced", device.ID)
```

The test: **does this comment explain WHY, not WHAT?** If it explains WHAT, fix the code instead.

---

## Quick Reference

```
Need to add a comment?
├─ Explaining WHAT code does?      → ❌ Improve the code instead
├─ Explaining WHY (rule/workaround)? → ✅ Add it with context
├─ Type info the language can't express? → ✅ Required — use native annotation syntax
├─ Exceptions / error conditions?  → ✅ Required — use native annotation syntax
└─ Test structure?                 → ✅ Required — use AAA markers
```

**Before adding a comment, ask:**
- Can I make the code clearer with a better name?
- Can I extract a method with a descriptive name?
- Can I use a constant or enum?
- Is this explaining WHAT or WHY? (Only WHY is valid)
- Will this comment become outdated?
- Is this a required type/exception annotation?
