# ADR-0046: Copying a local credentials secret goes CLI to main process to clipboard and never reaches the renderer

**Date:** 2026-10-25  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/credentials_local.py`, `app/src/main/secretClipboard.ts`, `app/src/main/ipc.ts`, `app/src/cli/operations.ts`  
**Amends:** [ADR-0024](0024-the-local-credentials-file-lives-at-the-dev-team-agents-root-and-the-app-edits-it-through-the-cli.md) § 5, [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md) § 7, [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) (the secret-command `--json` category), [ADR-0010](0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md); `cred get` and its `--json` refusal are unchanged

## Context

The Credentials tab treats every hidden value as write-only: `cred local show` replaces it with `{secret, set, marked}`, so the app can set or replace a secret but never read it. To use a value elsewhere, people opened `credentials.local.json` by hand, which defeats the point of having an editor.

Copying the value means it has to leave the CLI. ADR-0010 explains the danger: a secret inside a structured document ends up wherever a client logs its documents. The app's generic CLI path (`run()` → `invokeDevteam`) redacts and surfaces stdout, and its results are forwarded to the renderer.

## Decision

1. **One new CLI leaf, `devteam cred local copy-value --pointer P --expect-hash H`.**
   - It returns `{pointer, value}` only for a field `show` hides that has a value. A visible field, an unmarked group, an unset secret, a pointer below a hidden value, a missing pointer, a symlinked file or a stale hash is refused, so the leaf cannot read the file around `show`.
   - A non-string value comes back as JSON text. That includes a group or list marked secret as a whole, which `show` hides as one value and which is copied whole.
   - Human mode prints the value and nothing else, like `cred get`.
   - Each call that reaches the file, refused or not, appends a `local-copy` line to the machine-local audit log, with the pointer and never the value.
   - It is the deliberate exception to ADR-0011's rule that a secret-handling command refuses `--json`: its only client is the app's main process, which logs nothing.
   - It is classified read-only in `compat.READ_ONLY`.
2. **The app's allowlist widens by exactly this leaf.** Only `credentialsLocalCopyValue` runs it. Every failure except a usage, conflict, environment or refusal answer gets a fixed message, so a breach or timeout cannot quote stdout.
3. **The value goes to the clipboard in the main process.**
   - The IPC handler writes the value through `secretClipboard.ts` and answers the renderer with `{clearsInSeconds}` only.
   - After 30 s, and on quit, the clipboard is emptied if it still holds that value. Quitting waits up to 1 s for that clear. A SHA-256 digest is kept for the comparison.
   - Copies and clears run one at a time, and a failed clear is retried.
   - The reply to the renderer is built field by field, so nothing else from the CLI's answer reaches it.
4. **The renderer offers it only for a value as loaded.** The copy button is disabled while there are unsaved edits or after a hash conflict, because a renamed or moved field's pointer would no longer name the value the hash describes.

`cred get` stays forbidden in the app, and ADR-0010's `--json` refusal on it is unchanged.

## Consequences

### Positive
- People can use a stored secret without opening the file by hand.
- The renderer, IPC replies and app logs still never hold a secret value.

### Negative
- A secret now passes through the app's main process and the system clipboard. Other applications can read the clipboard for up to 30 s.
- A clipboard manager or OS clipboard history (Windows Win+V, macOS managers) may keep its own copy past the clear. The value is written as plain text, without the platforms' concealment markers.
- This is the one `--json` payload that carries a secret. Any future client of `cred local copy-value --json` must not log its documents.

### Neutral
- The `--json` contract adds one shape, `cred local copy-value: {pointer, value}`, as an additive change under ADR-0014.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Send the value to the renderer and copy with `navigator.clipboard` | The value would sit in the renderer's memory and cross IPC in a reply that the UI layer handles like any other |
| Raw stdout without `--json`, like `cred get` | The app's invoker is JSON-only by design, and a second raw spawn path would be more surface than one leaf with a narrow payload |
| Have the main process read the file directly | ADR-0015: the app is a pure CLI client and never reads project files |
| Show the value on screen | A visible value can be shoulder-surfed or captured in a screenshot, and copying covers the need |
