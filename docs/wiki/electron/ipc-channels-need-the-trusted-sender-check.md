# IPC channels must go through trustedHandler

**Origin:** A rebased app branch added IPC channels that passed linting and tests without the security check; found by grep only | 2026-09-30
**Tags:** electron, IPC, ipcMain.handle, security, trustedHandler, trustedRenderer, app/src/main/security.ts, audit trail

> Every `ipcMain.handle` call must wrap its callback in `trustedHandler(deps.trustedRenderer, …)` from `app/src/main/security.ts`.

---

## What it is

The desktop app (ADR-0015) is a pure CLI client (`devteam` run with `--json`). The only path from user input into the app is IPC from the renderer process. All IPC handlers must check that the request comes from the trusted renderer, not a compromised or injected context.

## How it works

Every IPC channel registration goes through the same security gate:

```typescript
// app/src/main/security.ts
export function trustedHandler(
  trustedRenderer: BrowserWindow | null,
  handler: (event: IpcMainInvokeEvent, ...args: any[]) => Promise<any>
) {
  return async (event: IpcMainInvokeEvent, ...args: any[]) => {
    // Check that event.senderFrame.parent (or Preload context) is the trusted renderer
    // Audit log to machine-local audit.log
    // Call the handler only if trusted
  };
}

// Usage:
ipcMain.handle('channel-name', trustedHandler(deps.trustedRenderer, async (event, arg) => {
  // handler code
}));
```

The wrapper:
- Verifies the sender is the known renderer process
- Logs the call (who, when, which channel, success/failure) to `audit.log`
- Raises only if the sender is untrusted

## Gotchas

- **Linting and tests do not catch unguarded channels.** A branch that added channels before this rule landed compiled, passed `npm run lint`, and passed tests with the channels unguarded. The check was found only by grepping for `ipcMain.handle`.
- **After rebasing app work on main, grep for new `ipcMain.handle` calls.** The pattern is not enforced at lint time.
- **The gate wraps the handler, not the registration.** You still call `ipcMain.handle('name', …)` normally; you just pass a wrapped callback.
- **`deps.trustedRenderer` is set once at startup.** If the renderer crashes or closes, all subsequent channel calls are rejected.

## References

- Security implementation: `app/src/main/security.ts::trustedHandler`
- IPC handler registrations: `app/src/main/*.ts` (search for `ipcMain.handle`)
- Audit log: `.dev-team-agents/audit.log` (machine-local, see ADR-0013)
