# Type Annotations — Rules and Examples by Language

Use language-native type annotation syntax when the type system cannot express the type on its own.

## Typed Collections / Generics

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

## Exceptions / Errors Thrown

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
// Go — errors are return values; document the sentinel errors
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

## Class/Struct Property Types

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

## Complex Return Shapes

When a function returns a structured object that the type system can't describe clearly:

```typescript
/**
 * @returns { success: boolean; data: User | null; error: string | null }
 */
function tryCreateUser(input: unknown): { success: boolean; data: User | null; error: string | null } { ... }
```
