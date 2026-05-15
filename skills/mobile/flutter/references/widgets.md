---
name: flutter-widgets
description: Flutter widget best practices — const usage, decomposition, rebuilds, and platform-adaptive UI.
---

## `const` Everywhere

- Mark every widget `const` when all constructor arguments are compile-time constants — this prevents unnecessary rebuilds
- Use `const` constructors for padding, text styles, colors, and spacers: `const SizedBox(height: 16)`

## Widget Size and Decomposition

- A widget file should not exceed ~150 lines — extract into smaller private widgets or dedicated files
- Avoid deep nesting (> 4–5 levels) — extract to named widgets or use helper methods returning `Widget`
- Prefer `StatelessWidget` unless local state is truly needed

## Rebuilds

- Use `RepaintBoundary` around widgets with frequent repaints (animations, live counters) to isolate their paint layer
- Never call `setState` from a `build()` method
- Use `const` `Text`, `Icon`, and `SizedBox` to reduce the rebuild scope

## Platform-Adaptive UI

```dart
// Use Cupertino widgets on iOS when matching native feel matters
if (Platform.isIOS) {
  return CupertinoButton(...);
} else {
  return ElevatedButton(...);
}
// Or use adaptive constructors: Switch.adaptive(), CircularProgressIndicator.adaptive()
```

## Performance

- **Profile on a physical device in release mode** — debug mode has significant overhead that does not reflect production performance
- Use Flutter DevTools (Performance tab) to identify expensive builds and repaints
- **Avoid `Opacity` widget** for animations — use `AnimatedOpacity` or `FadeTransition` (they use the GPU layer, not CPU)
- Cache network images with `cached_network_image` — never use `Image.network` for frequently displayed images
- Lazy-load lists with `ListView.builder` — never `ListView` with a fixed `children` list for dynamic data
- `AutomaticKeepAliveClientMixin` on tab content that should not rebuild on tab switch
