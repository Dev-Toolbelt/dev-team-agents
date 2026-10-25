# Electron 44 clipboard calls are async, and quit must await the secret clear

**Origin:** Copy-secret button (ADR-0046) typecheck failure and quit race | 2026-10-25
**Tags:** electron clipboard, clipboard.readText, clipboard.writeText, Promise<string>, before-quit, preventDefault, secret clipboard, ClipboardLike, settleSecretClipboard, Electron 44

> In Electron 44 `clipboard.readText()` and `clipboard.writeText()` return Promises. A synchronous wrapper fails typecheck, and a clear fired without awaiting in `before-quit` can be lost when the process exits.

---

## What it is

Electron 44 (`app/package.json` pins 44.5.1) changed the clipboard API. Older Electron versions returned values and completed writes synchronously. The copy-secret feature (ADR-0046) writes a credential value to the clipboard and clears it after a delay, so both behaviors matter.

## How it works

| Call | Electron 44 signature | Source |
|------|-----------------------|--------|
| `clipboard.readText()` | `Promise<string>` | `node_modules/electron/electron.d.ts` (~line 7035) |
| `clipboard.writeText(text)` | `Promise<void>` | `node_modules/electron/electron.d.ts` (~line 7045) |

Quit path in the main process:

1. `before-quit` fires. `app/src/main/index.ts` checks `secretClipboard.hasPending()`.
2. If a copied secret may still be on the clipboard, the handler calls `event.preventDefault()`.
3. It awaits `settleSecretClipboard(secretClipboard, CLIPBOARD_SETTLE_MS)`, with `CLIPBOARD_SETTLE_MS = 1_000`.
4. It sets `clipboardSettled = true` and calls `app.quit()` again. The second pass lets quit through.

This follows the `settleInFlight` pattern used for CLI writes in the same handler.

## Gotchas

- Type the clipboard port as `Promise`-returning. A synchronous `ClipboardLike` interface fails with TS2345: `Promise<string>` is not assignable to `string`.
- Do not call `void clearNow()` in `before-quit` without holding quit. The process can exit before the clear reaches the clipboard, and the secret stays there.
- The 1 s cap bounds how long quit waits. A clear that is still pending at the cap is abandoned, so the cap is a trade-off, not a guarantee.
- Test doubles for the clipboard must return Promises too. A synchronous fake hides this bug from the test suite.

## References

- `app/src/main/secretClipboard.ts` (`ClipboardLike`, `createSecretClipboard`, `settleSecretClipboard`)
- `app/src/main/index.ts` (`before-quit` handler, `CLIPBOARD_SETTLE_MS`)
- `docs/development/adrs/0046-copying-a-local-credentials-secret-goes-cli-to-main-process-to-clipboard-and-never-reaches-the-renderer.md`
