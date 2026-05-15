---
name: flutter-state-management
description: Flutter state management — BLoC/Cubit, Riverpod, Provider, GetX decision tree and rules.
---

## Decision Tree

| Complexity | Recommendation | Package |
|-----------|---------------|---------|
| Ephemeral / local UI state | `setState` or `ValueNotifier` | — (built-in) |
| Feature-scoped, testable | **BLoC / Cubit** | `flutter_bloc` |
| Compile-safe DI + reactivity | **Riverpod** | `flutter_riverpod` |
| Simple with DI | **Provider** | `provider` |
| Simple with routing bundled | **GetX** | `get` |

**Detection**: check `pubspec.yaml` for the package name before choosing patterns.

## BLoC / Cubit Rules

- **Cubit** for simple state machines (< 5 states, no events); **BLoC** when event-to-state mapping is complex
- Never put business logic in widgets — emit states from BLoC/Cubit, react in UI
- `BlocProvider` at the route level, not inside widgets
- Always close streams: `BlocProvider` handles disposal automatically; for manual streams, use `StreamSubscription` and cancel in `dispose()`

## Riverpod Rules

- Prefer `AsyncNotifierProvider` over `FutureProvider` for mutable async state
- Use `ref.invalidate()` to refresh data after mutations — never manually set state to trigger refresh
- Keep providers small and composable — avoid god providers
- Use `riverpod_generator` + `@riverpod` annotation for type-safe provider generation
