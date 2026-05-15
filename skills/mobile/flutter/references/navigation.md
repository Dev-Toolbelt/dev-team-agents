---
name: flutter-navigation
description: Flutter navigation patterns — go_router, Navigator 1.0, auto_route, and deep link testing.
---

## Navigation Options

| Approach | Package | Use when |
|----------|---------|---------|
| Declarative + deep links | **go_router** | New projects; web support needed |
| Imperative (legacy) | `Navigator 1.0` | Simple apps; no deep links |
| Auto-generated routes | **auto_route** | Large apps; type-safe route arguments |

## go_router Rules (most common)

- Define all routes in a single `GoRouter` instance, injected via `Provider`/`Riverpod`
- Use `ShellRoute` for persistent bottom navigation bars
- Always handle `redirect` for auth guards — never use `Navigator.push` to block access to protected routes
- Test deep links with:
  - Android: `adb shell am start -a android.intent.action.VIEW -d "myapp://path"`
  - iOS: `xcrun simctl openurl booted "myapp://path"`
