# The test seam's anon key applies only with a valid seam

**Origin:** Local Supabase stack for the account service | 2026-10-02
**Tags:** test seam, SR-44, DEVTEAM_AUTH_TEST_URL, DEVTEAM_AUTH_TEST_KID, DEVTEAM_AUTH_TEST_PUBKEY, DEVTEAM_AUTH_TEST_ANON_KEY, entitlement, loopback

> `DEVTEAM_AUTH_TEST_ANON_KEY` is read only when the whole seam (`_URL`, `_KID`, `_PUBKEY`) is valid; on its own, or beside an invalid seam, it is ignored and the compiled anon key is used.

---

## What it is

The CLI test seam (ADR-0029 SR-44) points `devteam auth` at a loopback account service and trusts one
extra signing key. It needs all three of:

| Variable | Constraint |
|---|---|
| `DEVTEAM_AUTH_TEST_URL` | Loopback URL only |
| `DEVTEAM_AUTH_TEST_KID` | Must start with `test-` |
| `DEVTEAM_AUTH_TEST_PUBKEY` | base64url Ed25519 public key |

`DEVTEAM_AUTH_TEST_ANON_KEY` is optional. A local Supabase gateway has its own anon key, so without it
every request to the local stack is refused.

## How it works

`entitlement.load_identity()` validates the seam first. Only when that yields a test URL does it take the
anon key from the environment (`(test_url and env.get(SEAM_ANON_KEY_ENV)) or section["anon_key"]`).
An incomplete or invalid seam is ignored rather than fatal, so the CLI keeps talking to the real service
with the real key.

## Gotchas

- Setting only `DEVTEAM_AUTH_TEST_ANON_KEY` changes nothing and prints nothing.
- The seam cannot point at a non-loopback host, and its key cannot pose as a production kid (the
  `test-` prefix), so a leaked environment cannot redirect a real user's sign-in.
- The desktop app's child environment does not pass `DEVTEAM_AUTH_TEST_*` to the CLI, so the app cannot
  use the local stack yet; opening that is a separate security decision.

## References

- `scripts/lib/devteam/entitlement.py` (`SEAM_ENVS`, `SEAM_ANON_KEY_ENV`, `load_identity`)
- `tests/test_entitlement.py`; ADR-0029 SR-44; `CLAUDE-md/cli.md` § Account → Test seam
