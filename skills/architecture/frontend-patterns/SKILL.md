---
name: frontend-patterns
description: Frontend patterns — debounce, double-submit guard, error boundaries, deferred runtime boot.
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

---

## Deferred Runtime Boot & Failsafes

Applies to any heavy client runtime loaded lazily (animation, scroll, 3D, analytics-driven UI) behind a failsafe that reveals content if the runtime does not start in time.

**Rules:**
- **Never gate the chunk download on `window.load`** — start `import()` as soon as the module runs (deferred module scripts run just before `DOMContentLoaded`) and attach `.catch()` at creation; a rejection applies the failure marker immediately
- Gate only the **initialization**: first of `load` (then idle callback) or a short cap after `DOMContentLoaded` (then immediately); guard against running twice and handle every `document.readyState`
- Skip the download entirely when the runtime is disabled (e.g. `prefers-reduced-motion`)
- Never initialize after the failsafe fired; on success, signal the failsafe so both never act
- **Never lengthen or remove the failsafe** to make the runtime fit — it is the guarantee that content is never left hidden; keep it inline in `<head>`, independent of the module
- **WebKit holds `load` (observed ~2.5 s) for a `<video>` with a WebM/AV1 `<source>`, even with `preload="none"`** — render those sources as `data-src` placeholders hydrated after `load` (near viewport or on play intent), keeping MP4 as the immediate fallback

**Review severity** for a download gated on `load`: `[BLOCKING]` when a fixed-deadline failsafe with a permanent marker can fire before `load` plus download (heavy media, WebM/AV1 sources); otherwise `[SUGGESTION]`.

Symptom, diagnosis checklist, reference implementation, test matrix and manual Safari checks: `references/webkit-motion-boot.md`.
