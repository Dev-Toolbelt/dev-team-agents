# Wait for the Data a Control Depends On

**Origin:** App test flakiness in folder management | 2026-10-01
**Tags:** async, flaky test, fixture, wait, disabled control, Radix, DropdownMenu, data loading, ProjectList, folders, sonner, toasts, race condition

> Wait for the readiness signal of the data a control depends on, not for unrelated text that renders earlier. Make races deterministic in fixtures, not with larger timeouts.

---

## What it is

Tests that click controls before their backing data loads can be flaky or deterministic-looking but broken. In the Projects screen, folders are fetched in an effect after the project list renders — controls like "Move <project> to a folder" remain `disabled={!ready}` until the fetch completes. A test that finds the project text and clicks immediately can:

- Hit a disabled Radix `DropdownMenu` trigger (menu never opens → 1 s timeout finding the menuitem)
- Click a row that the regrouping replaces mid-click (click lost; text shows wrong action)
- Appear to pass on an idle machine, then fail under load

## How it works

**The problem:** Tests find unrelated text that renders before the data:

```typescript
// BAD: finds text rendered before folders are ready
await screen.findByText('acme-site');
userEvent.click(screen.getByRole('button', { name: /Folder actions/ }));
```

On an idle machine the fetch completes before the click. Under load, the Radix trigger is still disabled — the click hits dead code.

**The fix — wait for the readiness signal:**

```typescript
// GOOD: waits for the visible signal that folders are ready
await screen.findByRole('button', { name: /New folder/ });
// Now all folder controls are enabled
userEvent.click(screen.getByRole('button', { name: /Folder actions for acme-site/ }));
```

Use a `foldersReady()` helper that waits for the last-to-enable control (e.g., "New folder" button):

```typescript
export async function foldersReady() {
  return screen.findByRole('button', { name: /New folder/ });
}
```

**Make the race deterministic in the fixture:**

```typescript
const FOLDERS_DELAY_MS = 30;

export function withFolders(fixture) {
  return {
    ...fixture,
    projectFolders: async () => {
      await new Promise((r) => setTimeout(r, FOLDERS_DELAY_MS));
      return fixture.projectFolders();
    },
  };
}
```

With a 30 ms delay in the fixture, any test that forgets to wait fails consistently, not sometimes. Caught by every CI run, not reported as intermittent.

## Gotchas

- **Sonner toast store persistence**: Sonner keeps active toasts in a module-level store. When a new `<Toaster>` component mounts, it replays every still-active toast, so one test's toast appears in the next. Fix: add `afterEach(() => toast.dismiss())` in the test setup.
- **jsdom lacks `window.matchMedia`**: Sonner's `Toaster` component reads `window.matchMedia` at render time. jsdom doesn't provide it. Stub it in setup:
  ```typescript
  window.matchMedia ??= (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  });
  ```
- Never raise the timeout to make a flaky test pass — that hides a race. Deterministic waits + fixture delays catch design problems early.

## References

- `app/test/renderer/setup.ts` — test setup, toaster stub, toast cleanup
- `app/test/renderer/projects.test.tsx` — fixture with FOLDERS_DELAY_MS
