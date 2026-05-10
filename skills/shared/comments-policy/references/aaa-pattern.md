# AAA Test Pattern — Detailed Examples

All tests must use `// Arrange`, `// Act`, `// Assert` comments to structure test logic.

## TypeScript / Jest

```typescript
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

## Python / pytest

```python
def test_assigns_device_to_user(device_service, build_device, build_user):
    # Arrange
    device = build_device(assigned_to=None)
    user = build_user()

    # Act
    result = device_service.assign(device.id, user.id)

    # Assert
    assert result.assigned_to == user.id
```

## Go

```go
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

## Java / JUnit

```java
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

## Multiple Act/Assert Cycles

When a test exercises more than one behaviour, label each pair:

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
