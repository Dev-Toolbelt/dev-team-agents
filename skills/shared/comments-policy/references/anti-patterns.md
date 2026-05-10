# Anti-Patterns — What NOT to Comment

Full examples of bad vs good for each category of unnecessary comment.

## Don't Explain What Code Does

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

## Don't Comment Bad Code — Fix It

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

## Don't Add Noise Comments

```typescript
// ❌ Adds no value
/** Get the name */
getName(): string { return this.name; }

// ✅ No annotation needed
getName(): string { return this.name; }
```

## Don't Leave Commented-Out Code

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

## Don't Use Version-Control Comments

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

## Self-Documentation Techniques (Prefer Over Comments)

### Extract to a Named Method

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

### Use Constants Instead of Magic Values

```python
# ❌
if device.last_maintenance < now() - timedelta(months=6):  # 6 months

# ✅
MAINTENANCE_INTERVAL_MONTHS = 6
if device.last_maintenance < now() - timedelta(months=MAINTENANCE_INTERVAL_MONTHS):
```

### Use Enums Instead of Magic Strings

```go
// ❌
if status == "f" { // f = failed

// ✅
if status == StatusFailed {
```

### Use Strong Types

```typescript
// ❌
function process(data: any): void  // comment needed to explain shape

// ✅
function process(data: DevicePayload): void  // shape is in the type
```
