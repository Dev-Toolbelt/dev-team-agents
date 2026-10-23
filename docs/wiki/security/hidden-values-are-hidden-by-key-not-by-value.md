# Hidden Values Are Hidden by Key, Not by Value

**Origin:** /devteam:learn consolidation, `cred local` move disclosure | 2026-10-23
**Tags:** cred local show, redaction, $secrets, move, rename, hidden value, _apply_move, _marked, credentials.local.json, disclosure

> A `move` or rename can expose a secret in plain text, because the hiding decision depends on the key name, not only on the value.

---

## What it is

`devteam cred local show` (`scripts/lib/devteam/credentials_local.py`) prints the credentials file with secrets redacted. The `_Redactor` hides a value for one of three independent reasons:

| Reason | Check | Scope |
|--------|-------|-------|
| Marked | A `$secrets` mark on the value's key, or on any object above it (`_marked`) | The whole subtree |
| Secret-looking key | The key name matches `_secret_ish` | That value |
| Secret-looking value | The value matches `_hidden_string` | That value, wherever it sits |

## How it works

- A value hidden by its key stops being hidden once it moves to a plain name, unless `_apply_move` re-marks it. A `move` is therefore a disclosure risk, not only a rename.
- Value-based hiding follows the value. It needs no re-mark.
- `_apply_move` rules:
  1. A value hidden by a key on its path stays hidden.
  2. The new name joins the destination's `$secrets`, unless the name looks secret itself.
  3. The move is refused when step 2 cannot be done: the destination is a list, `$secrets` is malformed, the name fails `_marked` validation, or the new name is `$secrets` or `$production`.
- A stale mark left on the source parent is accepted. It can only hide more.

## Gotchas

- Do not treat a rename as cosmetic when the source key was hidden.
- A value that shows in plain text after a rename means `_apply_move` did not re-mark it. Check the destination's `$secrets`.

## References

- `scripts/lib/devteam/credentials_local.py` (`_Redactor`, `_secret_ish`, `_marked`, `_hidden_string`, `_apply_move`)
