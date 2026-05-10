---
name: frontend-patterns
description: Frontend interaction patterns — debounce, double-submission prevention, and error boundaries with framework-specific implementation guidance.
---

## Interaction Patterns

### Debounce

Apply debounce whenever user input triggers expensive side effects (API calls, heavy computation). Without it, every keystroke fires a request — degrading both UX and server load.

**When to use**: search/autocomplete inputs, address or tag lookup, form field validation against an API, resize/scroll event handlers.

**Framework-agnostic pattern** (adapt to the project's stack):
```ts
// Reusable debounce utility — use lodash.debounce, use-debounce, or VueUse's useDebounceFn
function debounce<T extends (...args: unknown[]) => void>(fn: T, delay: number): T {
  let timer: ReturnType<typeof setTimeout>
  return ((...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay) }) as T
}

// Autocomplete example
const searchUsers = debounce(async (query: string) => {
  if (query.length < 2) return
  results.value = await api.users.search(query)
}, 300)
```

**Rules**:
- 150–300 ms is the standard delay for search inputs; 500 ms+ for validation-only fields
- Cancel in-flight requests when a new debounced call fires (use `AbortController`)
- Clear the debounce timer on component teardown to prevent stale state updates

### Double Submission Prevention

Every form submit or action button must be guarded against duplicate submissions. Two clicks = two POST requests = corrupted data, duplicate payments, or duplicate records.

**Rules**:
- Track a boolean `isSubmitting` state; set it `true` on submission start, `false` on completion (success or error)
- Disable the submit button while `isSubmitting` is `true` — never just rely on UX
- The handler must bail early if already in flight:

```ts
// Framework-agnostic guard
async function handleSubmit() {
  if (isSubmitting) return        // ← guard: bail on double-click
  isSubmitting = true
  try {
    await api.createOrder(payload)
  } finally {
    isSubmitting = false           // ← always release, even on error
  }
}
```

- Use `finally` (or equivalent) — releasing the lock only on success is a common bug that permanently disables the form after an error
- For idempotency-critical operations (payments, order placement), also pass an idempotency key from the backend side

---

## Error Boundaries & Global Error Handling

A runtime error in one component must not crash the entire UI. Wrap every route/page-level component in an error boundary that shows a user-facing fallback.

- **React**: class component with `componentDidCatch`, or `react-error-boundary` (`<ErrorBoundary FallbackComponent={...}>`)
- **Vue**: `onErrorCaptured` in a wrapper component, or `app.config.errorHandler` for global handling
- **Angular**: implement `ErrorHandler` and provide it at the root level (`{ provide: ErrorHandler, useClass: AppErrorHandler }`)
- **Svelte**: `<svelte:boundary>` (Svelte 5) or a wrapper component with `onerror`

**Rules:**
- Place boundaries at the **route/page level** at minimum — a broken widget must not take down the entire app
- Always show a user-facing fallback — never a blank screen or a raw JS stack trace
- Register a global `window.addEventListener('unhandledrejection', ...)` to catch uncaught promise rejections and forward them to the project's error tracking service (Sentry, Datadog, etc.)
- **Never swallow errors silently** — catching without logging or reporting creates invisible bugs
