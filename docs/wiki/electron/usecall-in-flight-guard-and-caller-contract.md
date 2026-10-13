# useCall.run Returns null on a Duplicate Submit: the Caller Contract

**Origin:** ADR-0029 account login and sign-up QA, double-submit fix in the app account screens | 2026-10-13
**Tags:** useCall, double submit, in-flight guard, pending ref, inFlight, disabled, fireEvent.submit, PasswordChange, DeleteAccount, Profile, SignIn, account

> Read this first: `useCall.run` returns `null` while a call is in flight. Treat `null` as "did not run or failed", and never perform a side effect after `run` without checking its result.

---

## What it is
`useCall` (`app/src/renderer/account/support.tsx`) wraps a CLI account operation and exposes `busy`, `error`, `run`, and `inFlight()`. A `pending` ref guards `run` against re-entry.

## How it works
1. `run` checks the `pending` ref. If a call is already in flight, it returns `null` before it touches `busy` or `error`.
2. Otherwise it sets the ref, runs the CLI operation, and clears the ref in `finally`. A retry after a failure therefore still works.
3. `busy` drives `disabled` on the controls, but only after the next render.

## Gotchas
- `disabled={call.busy}` is not a guard. Two synchronous submits in the same tick both pass before React re-renders. The ref is the guard.
- Caller contract, by call site:
  - `PasswordChange.submit` clears its fields only on success. Do not clear them unconditionally.
  - `DeleteAccount.submit` clears the code only on success.
  - `Profile.link` and `Profile.unlink` call `setWorking(null)` only when `run` returned a result.
- Code that changes UI state **before** calling `run` must check `call.inFlight()` first. `SignIn.signInWith` calls `setOauth` before `run`. Without the check, a duplicate submit clears the pending call's state.
- Click-based tests cannot tell `disabled` from the guard. Only a synchronous `fireEvent.submit` exercises the guard.

## How to test it
- See `describe('double submit')` in `app/test/renderer/account.test.tsx`.
- Fire `fireEvent.submit` twice in the same tick and assert the CLI operation ran once.
- Add a retry case: fail once, submit again, and assert the second call runs.

## References
- `app/src/renderer/account/support.tsx` (`useCall`)
- `app/src/renderer/account/PasswordChange.tsx`, `DeleteAccount.tsx`, `Profile.tsx`, `SignIn.tsx`
- `app/test/renderer/account.test.tsx`
- ADR-0029
