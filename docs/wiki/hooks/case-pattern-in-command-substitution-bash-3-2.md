# A Bare case Pattern Inside a Command Substitution Breaks Bash 3.2

**Origin:** task-board audit fix pass, NESTED_GUARD in `scripts/lib/devteam/hooks.py` | 2026-10-20
**Tags:** bash 3.2, case, command substitution, syntax error, macOS /bin/bash, esac, NESTED_GUARD, hooks.py

> Read this first: on macOS `/bin/bash` (3.2), a `case` inside `$(…)` whose pattern has no opening `(` fails to parse. The whole script dies, not only that branch. Open every pattern with `(`.

---

## What it is

Hook shell snippets often assign the result of a `case` to a variable through `$(…)`. Bash 3.2 parses the closing `)` of a bare pattern as the end of the substitution, so the `case` never parses.

## How it works

```bash
# Fails on /bin/bash 3.2
v=$(case "$x" in pat) echo a;; esac)

# Parses on /bin/bash 3.2
v=$(case "$x" in (pat) echo a;; esac)
```

## Gotchas

- The error reads `syntax error near unexpected token ';;'`. It points at the `;;`, not at the `case` that causes it.
- Bash parses the whole script before it runs anything. A bad `case` stops the script even when that branch never executes.
- A newer bash on `PATH` (Homebrew, nvm) hides the failure. Check with `/bin/bash -n <script>`.
- The failure was hit in the NESTED_GUARD shell snippet in `scripts/lib/devteam/hooks.py`.

## References

- `scripts/lib/devteam/hooks.py` (NESTED_GUARD)
- `docs/wiki/hooks/nested-checkout-git-cannot-vouch-for-itself.md`
