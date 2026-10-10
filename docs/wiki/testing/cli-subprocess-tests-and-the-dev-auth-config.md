# A CLI subprocess test sends real sign-in requests once the dev auth config is filled in

**Origin:** Hosted dev Supabase project wired into the CLI (commit cd58999) | 2026-10-10
**Tags:** scripts/lib/auth-config.json, scripts/lib/auth-config.dev.json, unconfigured_cli, Identity.configured, unconfigured build, shipped_cli, auth_support, devteam_support, subprocess, network leak, test isolation, entitlement

> The checkout's `auth-config.json` points at the real Supabase project, so the checkout CLI counts as configured. A test that runs it as a subprocess and expects an unconfigured build would reach that project. Run the copy from `unconfigured_cli()` instead.

---

## What it is

**Updated 2026-10-10:** one project serves development and production (ADR-0029 amendment). The shipped
`auth-config.json` is real and `auth-config.dev.json` was removed, so the copy now replaces the config with placeholders.
The history below is how the leak was first found, with the dev file.

`scripts/lib/auth-config.dev.json` is repository-only (never packaged, ADR-0029 SR-27). When present,
`entitlement.read_config` merges it in and selects its environment. `Identity.configured` is true when
`supabase_url` has no `REPLACE-ME` and at least one key loads.

## How it works

| Test | Problem before the fix | Fix |
|---|---|---|
| `tests/test_auth.py::test_an_unconfigured_build_refuses_with_a_clear_reason` | Ran the checkout CLI, which was now configured, and sent sign-in requests to the dev project | Runs the shipped copy |
| `tests/test_auth_security.py::test_without_the_seam_nothing_points_the_cli_at_another_server` | Same | Runs the shipped copy |

Fix (commit 349f18c):

- `tests/auth_support.py::shipped_cli()` copies `scripts/cli` and `scripts/lib` once per run into a temp
  directory without `auth-config.dev.json`.
- `AuthTestCase` runs that copy through `run_cli(cli=...)` in `tests/devteam_support.py`, and patches
  `entitlement._DEV_CONFIG_PATH` for in-process calls.
- `tests/test_entitlement.py`'s shipped-config test passes `config_path=ent._CONFIG_PATH`.

## Gotchas

- Today the helper is `tests/auth_support.py::unconfigured_cli()`: it copies `scripts/cli` and `scripts/lib` once per run and
  writes a placeholder `auth-config.json` into the copy. `AuthTestCase` also patches `entitlement._CONFIG_PATH` for in-process calls.
- Tests that launch `devteam_support.CLI` directly, such as `tests/test_client_gate.py`, use the checkout CLI, which is
  configured. A new test that asserts unconfigured behaviour must use `unconfigured_cli()`.
- No environment variable disables the dev file, on purpose. A variable that does so would let the environment
  redirect the CLI to another server, which `test_without_the_seam_nothing_points_the_cli_at_another_server` guards against.

## References

- `scripts/lib/auth-config.dev.json`; `scripts/lib/devteam/entitlement.py` (`read_config`, `Identity.configured`)
- `tests/auth_support.py` (`unconfigured_cli`); `tests/devteam_support.py` (`run_cli`)
- `docs/wiki/security/test-seam-authz.md` (the separate test seam, SR-44)
