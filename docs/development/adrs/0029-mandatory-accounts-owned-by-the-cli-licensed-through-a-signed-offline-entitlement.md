# ADR-0029: Mandatory accounts owned by the CLI, licensed through a signed offline entitlement

**Date:** 2026-10-02  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers

## Context

Until now nothing in dev-team-agents has a user identity. The CLI and the desktop app run with no
account and no server, and the framework works with no network after install. Three needs change
that:

- **Identity** — knowing who is using the framework.
- **Lead collection** — the people who sign up are the product's leads.
- **Licensing** — being able to block a user (trial expired, ban) and to gate premium features.

Data sync was considered and **deferred to a later phase**. Nothing in this ADR stores user content
on a server.

Four existing decisions shape the answer:

- [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) — the app is a
  pure CLI client and is never a prerequisite. Every capability is reachable from the CLI.
- [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md) — the app never
  touches the network. The renderer CSP is `connect-src 'none'` and `img-src 'self' data:`.
- [ADR-0023](0023-integrations-are-account-level-connections-whose-network-calls-live-in-the-cli.md) —
  all network I/O lives in the CLI under one HTTP policy (`integrations/http.py`). Secrets reach the
  CLI on stdin, never argv.
- [ADR-0010](0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md) and
  [ADR-0009](0009-python3-as-the-devteam-cli-runtime-while-hooks-stay-bash.md) — secret values live in
  the OS keychain through `secrets.py`, and the CLI imports only the standard library.

The repository is MIT-licensed, so any client-side check can be removed by anyone who edits the
source. This ADR treats that as an accepted risk (Decision § 8). It does not try to engineer around
it.

## Decision

### 1. Supabase Auth is the identity provider

The identity provider is a managed **Supabase Auth** project (GoTrue) in region `sa-east-1`, with
separate `dev` and `prod` projects. Four sign-in methods are supported:

| Method | Mechanism |
|--------|-----------|
| Email, passwordless | 6-digit **OTP code** sent by email and typed into the app or the terminal. No magic link: a link is usually opened on another device and cannot return to the desktop. |
| Google | OAuth through Supabase |
| GitHub | OAuth through Supabase, scope `user:email` (the email may be private) |
| Email + password | Sign-up with email confirmation by code. Minimum length 10. Responses are generic, so they never reveal whether an email is registered. |

**Password reset** uses a recovery **code**, not a link: request the code, type it, then set the new
password, all in-app or in the terminal. No web page has to be hosted for it.

Identities with the same verified email are linked to one account. Google/GitHub client secrets and
the SMTP credential live only in the Supabase dashboard. The `anon` key and the project URL are
public by design and ship in the CLI. The `service_role` key never ships.

### 2. The CLI owns the session; the app stays offline

`devteam auth {login, logout, status, otp, password, profile, delete}`, each with `--json`, is the
only code that talks to the identity provider.

- **OAuth** opens the **system browser**, never an embedded webview. It uses PKCE (S256) and a
  one-shot loopback listener on `127.0.0.1` with a random port and a validated `state`. No custom URL
  scheme: a scheme needs a registered app, which the unsigned beta (ADR-0027) and a CLI-only machine
  do not have.
- **The refresh token** is stored through `secrets.py` (ADR-0010) as the global-scope entry
  `account.session.refresh_token`. The access token is held in memory only.
- **OTP codes and passwords** reach the CLI on stdin, never argv (ADR-0023 § 4).
- **HTTP** goes through the shared module in `integrations/http.py`, extended with a POST helper
  under the same rules: https only, same-origin redirects, deadlines, body cap, no secret in an error.
- **The app** calls named IPC operations (`authStatus`, `authLogin`, `authOtpStart`, `authOtpVerify`,
  `authPasswordReset`, `authProfileUpdate`, `authLogout`, `authDelete`) that spawn the CLI. The
  renderer never holds a token. Its CSP stays `connect-src 'none'`. The avatar is rendered from the
  user's initials, because a remote image would need `img-src` to widen.

### 3. Accounts are mandatory, for the CLI and for the app

A signed-in account with a usable entitlement (§ 4) is required to run the framework.

**The gate is in the CLI**, so it applies wherever the CLI runs:

- Gated: every `devteam` subcommand.
- Never gated: `auth *`, `version`, `help`, `doctor`, and the removal paths `unbind` and quarantine
  restore. A user must always be able to sign in, diagnose a problem, and leave cleanly. Uninstalling
  is never blocked.

**Delegated providers are enforced too**, under the Provider Parity Rule. The opencode and Codex
installers and `update.sh` reach the user's tree without going through `bind`, so they call
`devteam auth check --json` before they write anything. Tests iterate `ALL_PROVIDERS`.

**Hooks report; they never block.** `session-start.sh` reads the cached entitlement offline and shows
its state in the banner. No hook fails a coding-agent session because of the gate: a fail-closed hook
locks every user out of their own editor on the first gate bug, and the MIT risk (§ 8) means the hook
would not stop a determined user anyway.

**The app** opens to a sign-in screen when `authStatus` reports no session, and to a block screen
showing the reason when the entitlement is `trial_expired` or `banned`.

### 4. A signed entitlement carries the license, valid offline for a bounded window

After every successful sign-in or token refresh, the CLI calls a Supabase Edge Function,
`entitlement`. It returns a compact token signed with **Ed25519**:

| Claim | Meaning |
|-------|---------|
| `sub` | Account id |
| `status` | `active` · `trial` · `trial_expired` · `premium` · `banned` |
| `features` | Premium feature keys granted (empty today) |
| `trial_ends_at` | Present while a trial is running |
| `iat`, `exp` | Issue time, and expiry = `iat + max_offline_days` |
| `kid` | Signing key id |

The rules for using it:

- **Verification** uses public keys embedded in the CLI, keyed by `kid` (current + next, so a key can
  rotate without a forced update). The private key exists only as an Edge Function secret. Because
  the CLI is standard-library only (ADR-0009), verify-only Ed25519 is a vendored RFC 8032 reference
  implementation, tested against the RFC 8032 test vectors. It never signs.
- **Cache.** The token is stored in the machine-local record `entitlement.json`, added to
  `paths.MACHINE_LOCAL_RECORDS`. It is not a secret: the signature makes it tamper-evident.
- **Offline window.** The token is accepted without revalidation until `exp`. The default window is
  **7 days**, read from server config, so it can change without a release. A ban or trial expiry
  takes effect at the next online check, so offline use can lag it by up to that window.
- **Clock rollback.** The CLI keeps `max_seen_at` = the highest of the local clock and every `iat` it
  has seen. If the local clock reads earlier than `max_seen_at` minus a 5-minute tolerance, the cache
  is not trusted and an online check is required.
- **Network failure.** When the network fails and a valid cached token exists, the command proceeds.
  With no valid cached token it fails as an environment error with a sign-in or connect remedy.

### 5. The trial is configured server-side and starts disabled

Server state lives in three tables, written only through `service_role` (RLS lets users read only
their own rows):

- `app_config` — `trial_enabled` (initially **false**), `trial_days` (**5**), `max_offline_days` (**7**).
- `licenses` — `user_id`, `plan`, `status`, `trial_started_at`, `banned_at`, `ban_reason`.
- `profiles` — the profile data (§ 7).

How the status is derived:

- `trial_started_at` is set by the first entitlement request.
- While `trial_enabled = false`, every non-banned account resolves to `active`. **The trial gate is
  open.** Enabling it is a config change, not a release.
- With the trial enabled, an account past `trial_days` without `premium` resolves to `trial_expired`.

**Ban:** in v1, a maintainer sets `licenses.status = banned` and revokes the account's sessions from
the Supabase dashboard. There is no admin UI. Premium features are checked by key against
`features`; none are defined yet.

### 6. Profile

- **Editable:** display name.
- **Read-only:** email (changing it requires a confirmation code), sign-up method, linked identities
  (link and unlink Google/GitHub).
- **Actions:** change password, and **delete account**.

Deletion goes through the Edge Function: it deletes the auth user and cascades to `profiles` and
`licenses`. One exception for a banned account: a SHA-256 of its normalized email is kept in
`banned_identities`, so that deleting the account does not lift the ban. This retention is named in
PRIVACY.md.

### 7. Registration is the lead; contact is transactional only

The account record is the lead: email, display name, sign-up method, `created_at`, `last_seen_at`.
There is no separate marketing opt-in, so the **LGPD legal basis is execution of contract** (art. 7,
V). That basis permits only **transactional** email: sign-in codes, security notices, and license
state changes. Marketing email requires a future, separate, explicit opt-in (consent, art. 7, I),
recorded per account, with its own ADR.

**Telemetry stays unlinked.** The telemetry anonymous id is never sent to Supabase. The account id is
never added to telemetry. No join between the two exists or may be built. PRIVACY.md's anonymity
promise for telemetry stands unchanged.

### 8. Accepted risk: client-side enforcement is removable

The source is MIT and the gate runs on the user's machine. Removing the check, pointing the CLI at a
different config, or using the test seam bypasses every rule above. This risk is **accepted
explicitly**:

- No relicensing.
- No server-delivered premium features for now.
- No obfuscation.

The gate exists to make the default path licensed and to identify users, not to resist a determined
user. Revisit this if premium features ever carry value that must not be freely obtainable. The
answer then is to deliver them from a server, not to harden the client.

### 9. Relation to earlier ADRs

- **ADR-0011 — amended.** "The app is never a prerequisite" **still holds**: sign-in is reachable
  from the CLI, so a user without the app loses nothing but the screens. What is superseded is the
  assumption the ADR made throughout without stating it: that the framework runs **with no account
  and no network**. The CLI now needs a network connection at first sign-in and at least once per
  offline window, and it needs a signed-in account to run gated commands. ADR-0011 carries a forward
  marker to this ADR.
- **ADR-0015 / ADR-0023 — stand unchanged.** The app still never touches the network. All identity
  traffic is CLI network I/O under the existing HTTP policy.
- **ADR-0010 — stands.** The session secret is one more global keychain entry.

## Consequences

### Positive
- The project gets an identity, a lead list and a license lever without running a server of its own,
  and with an exit path: GoTrue is open source and self-hostable.
- The app's security posture is unchanged: no token in the renderer, CSP still `connect-src 'none'`.
- Sign-in works on headless and SSH machines through the email OTP code in the terminal.
- Trial length, offline window and the trial switch are server config, changed without a release.

### Negative
- **Supabase becomes a hard runtime dependency** for first sign-in and for every offline window. An
  outage blocks new sign-ins; the 7-day cache bounds the damage for existing users. Production needs
  a paid Supabase plan, because the free tier pauses idle projects.
- **This is a breaking change for every existing install.** `devteam update` would start requiring
  sign-in. Under the Immutability Contract it ships with a deprecation cycle: one minor release in
  which the session-start banner and the CLI announce the requirement without enforcing it, then the
  minor that enforces it. Both are called out in the README release notes.
- **The Provider Parity Rule applies in full.** The gate must be enforced for `claude` (natively, in
  `bind`/`sync`), and for `opencode` and `codex` through `install-opencode.sh`, `install-codex.sh`,
  `install-provider.sh` and `update.sh`. Tests iterate `ALL_PROVIDERS` with a per-provider fixture
  map, following `tests/test_provider_ownership.py`. A delegated installer that skips the check is the
  ADR-0022 gap again.
- The repository's own test suite and CI need a test seam: a loopback fake IdP and a test signing key,
  enabled by `DEVTEAM_AUTH_TEST_*` environment variables, mirroring
  `DEVTEAM_INTEGRATIONS_TEST_ALLOW_LOOPBACK_HTTP`. That seam is also a bypass, which § 8 already
  accepts.
- New personal-data obligations: PRIVACY.md must name the controller, a contact for the data
  protection officer (encarregado), Supabase and the email provider as processors, retention, the
  `banned_identities` hash, and deletion rights. Terms of Use must be published.
- A vendored Ed25519 verifier is code this repository now maintains. It is small, and pinned by the
  RFC test vectors.

### Neutral
- The `--json` contract grows by one command family. That is additive; `tests/test_json_contract.py`
  discovers it from the parser.
- ADR-0011 gets a one-line forward marker. Its Decision text is not rewritten.
- The infrastructure-as-code for the Supabase projects (migrations, `config.toml`, the Edge Function)
  is dev-only and must stay out of the package (`install.sh` KEEP_ROOT, `strip-tarball.sh`).

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Auth0 or Clerk | Built for the web: Clerk handles a non-browser client poorly. Pricier as usage grows, and more lock-in, with no capability the four methods need beyond Supabase. |
| Firebase Auth | Locks identity to Google, gives no Postgres for profiles and licenses, and offers weaker control over email templates. |
| Self-hosted IdP (Keycloak, Ory, Authentik) | A server, patching, backups and SMTP to run for a beta with no budget for operations. GoTrue keeps self-hosting available later. |
| The app talks to Supabase directly | Breaks ADR-0015 and the CSP, puts tokens in the renderer, and duplicates the session logic that the CLI needs anyway. |
| Magic link for passwordless email | The link is often opened on a phone and cannot complete a desktop or terminal sign-in. |
| Custom URL scheme (`devteam://`) for OAuth | Needs a registered app, which is fragile unsigned (ADR-0027) and impossible on a CLI-only machine. |
| Online check on every command (no offline window) | Turns every network blip into a blocked command. The bounded signed cache gives the same control with one check per window. |
| Hooks that block the agent session when unlicensed | One gate bug locks every user out of their own editor, and § 8 means it does not stop a determined user. |
| `cryptography` package for Ed25519 | Breaks the standard-library-only rule (ADR-0009) and the one-line brew/winget dependency it protects. |
| Relicensing, or server-delivered premium, to make enforcement real | Explicitly declined for now (§ 8). |
