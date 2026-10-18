---
name: frontend-hook-tests
description: Testing React hooks and Vue composables in isolation — renderHook, withSetup, async flows.
---

# Frontend Hook / Composable Tests

When business logic lives in a custom hook (React) or composable (Vue), test it **directly** — not implicitly through a wrapping component. Component tests verify rendering; hook tests verify logic.

---

## Detection — Read Only the Row That Applies

| Signal | Framework | Go to |
|--------|-----------|-------|
| `react` in `package.json`; files under `hooks/`; functions named `use*` returning values | React | [React](#react) |
| `vue` in `package.json`; files under `composables/`; functions named `use*` returning refs | Vue | [Vue](#vue) |
| Both present (monorepo, migration in progress) | Both | Read the section matching the file under test only |
| Neither — logic lives in plain functions/classes | — | Skip this skill; test them as plain units |

Do not install or introduce a hook-testing utility for a framework the project does not use.

---

## Is It Worth a Hook Test?

| The hook… | Test it directly? |
|-----------|-------------------|
| Holds state transitions, derived values, or branching | Yes |
| Wraps async work (fetch, debounce, polling) | Yes |
| Returns callbacks the UI invokes | Yes |
| Only forwards a library call with no added logic | No — test the consumer instead |
| Only reads a constant or context value | No |

---

## React

Use `renderHook` from `@testing-library/react` (React 18+; older projects may still use `@testing-library/react-hooks`).

```ts
// Arrange
const { result } = renderHook(() => useCartTotal(mockItems));
// Act
act(() => result.current.addItem(newItem));
// Assert
expect(result.current.total).toBe(expectedTotal);
```

- Read state through `result.current` **after** the act block — `result.current` is replaced on every render, so never destructure it up front.
- Wrap every state-mutating call in `act()`; wrap async ones in `await act(async () => …)`.
- Hooks that need context or a provider go through the `wrapper` option:

```ts
const { result } = renderHook(() => useSession(), {
  wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
});
```

- Use `rerender(newProps)` to assert reaction to changed inputs, and `unmount()` to assert cleanup (subscriptions closed, timers cleared).

---

## Vue

Composables that call lifecycle hooks or `provide/inject` need an active component instance. Call them inside a thin `withSetup` wrapper:

```ts
const { count, increment } = withSetup(() => useCounter());
increment();
expect(count.value).toBe(1);
```

```ts
// withSetup — minimal test helper
function withSetup<T>(composable: () => T): T {
  let result!: T;
  const app = createApp({ setup() { result = composable(); return () => {}; } });
  app.mount(document.createElement('div'));
  return result;
}
```

- A composable with **no** lifecycle or injection dependency can be called directly — no wrapper needed.
- Assert on `.value` for refs and computed values, not on the ref object itself.
- Use `await nextTick()` (or `flushPromises()`) before asserting on anything that depends on reactivity or a resolved promise.
- Keep a reference to the app instance when the test must assert cleanup, so `app.unmount()` can trigger `onUnmounted`.

---

## Rules (Both Frameworks)

- **Test in isolation** — do not mix hook logic assertions into component tests.
- **Cover the full surface**: every returned value, every returned callback, async success and failure paths, and reset/cleanup behavior.
- **Advance async work explicitly** before asserting — `act()` / `await flushPromises()` / `nextTick()` / fake timers. Never rely on an arbitrary `setTimeout` in the test.
- **Mock at the network boundary**, not the hook's internals — see `skills/testing/decoupled-frontend/SKILL.md`.
- **Do not assert on internal call counts** of the framework (render counts, effect invocations) unless the hook's contract is explicitly about them.

---

## Anti-Patterns

| Anti-pattern | Why it hurts | Do instead |
|---|---|---|
| Rendering a whole component just to reach the hook | Couples logic tests to markup | Render the hook directly |
| Destructuring `result.current` before acting | Captures a stale render | Read `result.current.x` after each act |
| Asserting immediately after an async call | Passes or fails by timing luck | Await the flush helper first |
| Testing a hook that has no logic | Pure maintenance cost | Delete the test; cover the consumer |
| Duplicating an existing component test at hook level | Double maintenance, no new signal | Pick one layer per behavior |
