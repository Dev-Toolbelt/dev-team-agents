# QA Report: accounts and licensing (ADR-0029), 2026-10-02

Scope: branch `feat/accounts-auth` vs ADR-0029 and the plan's Definition of Done. Validated on macOS against the loopback fake IdP (`tests/auth_fakes.py`, `DEVTEAM_AUTH_TEST_*`), a disposable `DEVTEAM_HOME` and an enforce-mode copy of `auth-config.json`. No live Supabase project and no Windows were available.

## Test Coverage Summary

| Area | Status | Notes |
|------|--------|-------|
| Sign-in via CLI (email OTP) | Pass (fake IdP) | login, status, check, logout driven end to end |
| Google / GitHub OAuth, password, reset | Not driven by hand | covered by `tests/test_auth_oauth.py` / `test_auth.py`, which pass |
| No enumeration | Pass | `otp start` for a known and an unknown address returned identical JSON |
| Profile (name, link/unlink, change password, delete) | Pass by tests | CLI surface present; last-identity refusal documented |
| Gate, enforce mode | Pass | signed-out `sync`/`list` refused (exit 1); `version`, `path`, `doctor` not blocked; `update` runs core-only with warning |
| Gate, warn mode | Pass | one stderr line, command proceeds |
| Delegated installers (opencode, codex, install-provider opencode/codex) | Pass | enforce + signed out: exit 5, nothing written |
| Installer gate with no CLI / unexpected exit code | Fail | see MAJOR-2 |
| Offline cache 7 days, clock rollback | Pass by tests | python suite |
| Trial off/on, 5 days | Pass | `deno test` 29 passed (entitlement + account-delete) |
| Read-only commands create nothing | Pass | `auth status/check`, `version`, `path`, `list`, `doctor` left DEVTEAM_HOME absent |
| App CSP | Pass | `connect-src 'none'` intact; app suite 1278 passed |
| Telemetry unlinked | Pass | import-graph test passes; no auth module mentions telemetry |
| Packaged CLI (install-cli.sh, Homebrew, Windows CLI) | Fail | see BLOCKER-1 |
| Docs sync | Pass with notes | README pair, CLAUDE.md, cli.md, hooks.md, CHANGELOG present; see notes |
| Repo gates | Mixed | agent-lint, size-limits, orphan scans, 01-lint, 02-readme-sync, 04-packaging, 05-app, 06-bash32 pass; 03-python has 5 failures |

## Issues Found

**[BLOCKER] 1. The installed CLI loses `auth-config.json`, so every gated command fails**
- Steps: `python3 -m unittest tests.test_install_cli` (or `bash scripts/install-cli.sh --from <repo>` then any gated command).
- Expected: the installed CLI reads the compiled identity constants.
- Actual: `devteam: error: auth-config.json is missing or malformed`, `devteam store install failed (exit 3)`. `scripts/install-cli.sh:109-110` copies only `scripts/cli/devteam` and `scripts/lib/devteam/`, not `scripts/lib/auth-config.json`, which `entitlement.py:93` resolves as a sibling of `devteam/`. Same omission by reading in `packaging/homebrew/devteam.rb:63-75` (not executed) and likely the Windows CLI installer (`packaging/windows-cli/`, not verified). Also the formula copies only top-level and `integrations/` `*.py`.
- Failing tests: four in `tests/test_install_cli.py`.

**[MAJOR] 2. Installer gate fails open in enforce mode, contradicting SR-42**
- `scripts/lib/auth-gate.sh` (`ag_gate`): a missing CLI, or any `auth check` exit other than 0/1/3/4, prints a note and returns 0. SR-42 says a missing CLI, non-zero code or unparseable output is a block.
- Fix either the code (block in enforce) or amend SR-42 and the CLAUDE-md/cli.md text, which documents the skip.

**[MAJOR] 3. CI red: design rule violated by the new session code**
- `tests/test_review_regressions.py:553` `test_only_the_credential_resolver_reads_a_secret_backend` fails: `auth_session.py:180` calls `secrets_module.get` directly, bypassing `creds.py`'s scope check and audit line. ADR-0029 SR-16 wants `secrets.py` use; either route it through the resolver or record a justified exception in the rule's allowlist.

**[MINOR] 4. Edge Function tests, config checks and SQL/RLS tests are not wired into CI**
- `deno test` passes locally (29), but no workflow or `.github/scripts/ci/*.sh` references `deno` or `infra/`. SR-7, 11, 12, 14 (config checks), SR-31/32 (SQL tests) and the SR-36 scanner rules could not be verified here (no `supabase` CLI) and have no visible CI gate.

**[MINOR] 5. ADR text is stale on SR-43**
- The hook banner uses in-process `auth_gate.banner_line()` (offline, same `entitlement.evaluate`), not `devteam auth status --json --offline` as SR-43 words it. The intent (one verification path, never blocks) holds; amend the ADR.

**[MINOR] 6. `CLAUDE.md` is 657 lines** (advisory threshold 600, fails at 700). Trim before the next addition.

## NOT VERIFIED (blocked on provisioning or platform)

- Live Supabase: real OTP/SMTP delivery, Google/GitHub OAuth, rate limits (SR-11), OTP length/expiry (SR-12), account linking (SR-14), leaked-password protection, redirect allow-list, RLS/SQL behavior, `pg_cron` purge jobs, ban procedure runbook, real Ed25519 key placeholders (`REPLACE-ME` values make a production build reject every token, as documented).
- Windows: DPAPI backend, Windows CLI installer, Windows app runs.
- Desktop app screens driven by hand (only the automated suite was run).
- Placeholders in PRIVACY.md/TERMS.md (`[YOUR LEGAL ENTITY NAME]`, `[NAME]`) are expected for a draft but must be filled before the enforcing release.

## Definition of Done Check

- [x] Sign-in methods and reset: pass on the fake IdP (OTP driven by hand, others by suite)
- [x] Gate semantics (warn/enforce, exemptions, core self-update)
- [ ] Installed-CLI packaging works (BLOCKER-1)
- [ ] Installer gate matches SR-42 (MAJOR-2)
- [x] No token in argv (parser exposes no code/password flag), CSP unchanged, read-only commands create nothing
- [x] Telemetry unlinked
- [x] Docs present and mostly consistent with the code (exceptions: SR-43 wording, installer skip behavior is documented but contradicts SR-42)
- [ ] Repo gates all green (03-python: 5 failures)
- [ ] Live-Supabase and Windows items: NOT VERIFIED

## Verdict

FAIL: one blocker (packaged CLI cannot read its compiled identity config) and a red CI gate must be resolved before release. Live-provisioning and Windows verification remain open.
