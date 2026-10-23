# Preload Bridge Copies Op Fields One by One

**Origin:** /devteam:learn consolidation, Credentials tab move op | 2026-10-23
**Tags:** preload, contextBridge, ipcRenderer, credentialsLocalPatch, move op, from, silent drop, JSON pointer, Credentials tab, bridge copy

> A new field on a credentials op is dropped inside the preload bridge, so the save fails with a pointer message that looks like a validator bug.

---

## What it is

The preload script exposes the credentials patch call to the renderer. `credentialsLocalPatch` in `app/src/preload/index.ts` does not forward the op object as received. It rebuilds each op by copying known fields one at a time: `op`, `pointer`, `value`.

## How it works

1. The renderer builds an op, for example `{ op: "move", pointer: "/a/old", from: "/b/new" }`.
2. The bridge copies `op`, `pointer` and `value` into a new object. `from` is not copied.
3. Main runs `credentialsOpsProblem` (`app/src/cli/operations.ts`) on the rebuilt op.
4. Main refuses the save with: an edit's pointer is a JSON pointer starting with "/".

## Gotchas

- A new op field, such as `from` on `move`, is dropped with no error.
- Sets and unsets still work, because they use only the copied fields. Renames and moves fail.
- The message names the pointer, but the pointer is valid. Check the bridge before the validator.
- Fix: forward the new field in the bridge.
- The regression test in `app/test/preloadBridge.test.ts` must pass the op through the real bridge into `credentialsOpsProblem`.
- When the op shape changes, change the bridge and the bridge test in the same commit.

## References

- `app/src/preload/index.ts` (`credentialsLocalPatch`)
- `app/src/cli/operations.ts` (`credentialsOpsProblem`)
- `app/test/preloadBridge.test.ts`
