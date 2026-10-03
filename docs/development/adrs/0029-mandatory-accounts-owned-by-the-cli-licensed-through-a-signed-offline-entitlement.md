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
| Email, passwordless | 8-digit **OTP code** (SR-12) sent by email and typed into the app or the terminal. No magic link: a link is usually opened on another device and cannot return to the desktop. |
| Google | OAuth through Supabase |
| GitHub | OAuth through Supabase, scope `user:email` (the email may be private) |
| Email + password | Sign-up with email confirmation by code. Length 10 to 64 characters and at most 72 UTF-8 bytes (SR-15). Responses are generic, so they never reveal whether an email is registered. |

**Password reset** uses a recovery **code**, not a link: request the code, type it, then set the new
password, all in-app or in the terminal. No web page has to be hosted for it.

Identities with the same verified email are linked to one account. Linking never attaches to an
identity whose email is unconfirmed (SR-14). Google/GitHub client secrets and
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

- Gated: every `devteam` subcommand not on the exempt list. The list is an allowlist matched on
  the parsed command path, so a subcommand added later is gated by default (SR-30).
- Never gated: `auth *`, `version`, `path`, `compat`, `doctor` (diagnosis), the removal paths
  `unbind`, `uninstall` and quarantine restore, `export` of the user's own data, and the hook
  plumbing `tasks *` (a PreToolUse hook runs it on every tool call, and a hook must never wait on
  a lock or the network). `--help` is argparse's, never a command. A user must always be able to
  sign in, diagnose a problem, take their data and leave cleanly. Uninstalling is never blocked.
- **Updates while blocked.** `update` installs the core store even for a blocked user, so a fix to
  a hook reaches them; the project sync it would run is withheld. The gate reports that verdict
  (`CORE_ONLY`) and the `update` handler reads it; the gate never edits the parsed arguments.
- **Warn mode is warn whatever happens.** In the announce-only release a gated command runs even
  when the check itself cannot (a missing or broken config, a lock conflict), and the notice is
  shown only when stderr is a terminal: a script, a hook or the app captures stderr, and the app
  renders its own banner. An unreadable config falls back to `entitlement.DEFAULT_GATE_MODE`, the
  mode the release ships, flipped together with `auth-config.json` (a test holds them equal).
- A gate refusal carries `details.gate = "account"`, so a client can tell it from the exit 1 that
  `doctor` and `cred check` use for findings. In `compat` the account commands are classed
  `STORE_NEUTRAL`: never refused to a declared client, but not called read-only, because they
  write machine-local records and the remote account.

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
| `iss` | The Supabase project URL that issued it; separates `dev` from `prod` |
| `aud` | Fixed `devteam-cli` |
| `v` | Token format version, `1` |
| `iat`, `exp` | Issue time, and expiry = `min(iat + max_offline_days, trial_ends_at)` while a trial runs, else `iat + max_offline_days` |
| `kid` | Signing key id, carried in the token header (SR-21) |

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
- **Clock rollback.** On every accepted token the CLI records `skew = iat - local_now`, and evaluates
  time as `effective_now = local_now + skew`, so a machine whose clock is merely slow is not treated
  as rolled back. It keeps `max_seen_at` = the highest `effective_now` it has observed. If
  `effective_now` reads earlier than `max_seen_at` minus a 5-minute tolerance, the cache is not
  trusted and an online check is required. A successful online check resets `max_seen_at` to the new
  token's `iat`, so a clock that once jumped forward cannot lock the user out permanently (SR-25).
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

Deletion goes through the Edge Function, after a fresh re-authentication code (SR-37): it deletes the
auth user and cascades to `profiles` and `licenses`. One exception for a banned account: a keyed
**HMAC-SHA256** of its normalized email, under a server-only pepper, is kept in `banned_identities`,
so that deleting the account does not lift the ban. A plain SHA-256 is not used: the email space is
small enough to reverse it by dictionary, which would make the "hash" the email itself (SR-38). This
retention is named in PRIVACY.md.

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

The source is MIT and the gate runs on the user's machine. Removing the check, editing the embedded
constants, or using the test seam bypasses every rule above. This risk is **accepted explicitly**,
for the user's own machine only. What is **not** accepted is a third party redirecting a user's
sign-in: the identity endpoint is a compiled constant that no project file, preference or
production environment variable can change, because a cloned repository that could point the CLI
at another server would be a password-harvesting tool (SR-8). Accepting the risk means:

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

## Security Requirements

Added by the security design review on 2026-10-02, before any code was written. Every item is a
MUST unless it says otherwise, and each one names how it is tested. `SR-n` refers to item n, numbered across all groups. Implementation agents follow
these as written; a requirement that turns out to be wrong is amended here, not skipped in code.
"Fake IdP" is the loopback test seam of Consequences; "sentinel" is a recognizable fake secret the
fake IdP issues so tests can grep every output for it.

### A. OAuth (system browser, PKCE, loopback)

1. **PKCE flow only.** The CLI uses GoTrue's PKCE flow (`code_challenge_method=s256`), never the
   implicit flow. Tokens arrive only in the body of the `grant_type=pkce` token response, never in a
   URL fragment or query. The `code_verifier` is 32 bytes from `secrets.token_bytes`, base64url
   without padding (43 characters), new per attempt. *Test:* the fake IdP rejects a missing or
   `plain` challenge; the verifier sent at exchange hashes to the challenge sent at authorize.
2. **`state`.** At least 128 bits from `secrets`, carried in the `redirect_to` query, compared with
   `hmac.compare_digest`. A callback with a missing or wrong `state` gets a 400 and does not consume
   the listener. *Test:* a forged callback with the wrong `state` leaves the real one able to complete.
3. **Listener binding.** Bind `127.0.0.1` exactly, never `0.0.0.0`, `::` or `localhost`, on port 0
   (OS-assigned). The `redirect_to` is `http://127.0.0.1:<port>/callback` with the bound port.
   *Test:* the socket's bound address is `127.0.0.1`; no other interface accepts a connection.
4. **Request validation.** Only `GET /callback` is handled; every other path or method gets 404
   without ending the wait. The `Host` header must equal `127.0.0.1:<port>`, which refuses DNS
   rebinding. An `error` parameter ends the attempt with a generic message that does not echo the
   provider's `error_description` verbatim into `--json`. *Test:* one case per rejected shape.
5. **One shot, bounded.** The listener closes after the first `state`-valid callback, or after 300
   seconds, or on Ctrl-C, whichever comes first, and the port is released in every path. *Test:* the
   timeout path exits with the documented environment-error code and the port is free afterwards.
6. **Callback response.** The page returned to the browser is static, inline, loads no external
   resource, and sends `Cache-Control: no-store`, `Referrer-Policy: no-referrer` and
   `Content-Security-Policy: default-src 'none'`. It contains no token and no code. *Test:* header
   assertions on the response.
7. **Supabase redirect allow-list** holds only `http://127.0.0.1:*/callback` (plus the fake IdP in
   `dev`). No `**` wildcard, no `localhost`, no `https` site that the project does not control.
   *Test:* a config check over `supabase/config.toml` in CI.
8. **Fixed identity endpoint.** The Supabase URL, the `anon` key and the entitlement public keys are
   constants in the CLI source. No project file, `preferences.json`, `credentials.local.json`,
   plugin setting or environment variable overrides them, except the test seam (SR-44), which
   accepts only a loopback host. *Test:* setting each of those sources to a remote URL changes
   nothing; the seam with a non-loopback host is refused.

### B. Email OTP, password reset and password policy

9. **Stdin only.** OTP codes, recovery codes and passwords are read with `getpass` from a TTY or as
   one line from stdin, never from argv or an environment variable. The app passes them from the
   main process to the CLI's stdin, never through argv. *Test:* the `ps`-visible argv of a spawned
   CLI contains no sentinel; the parser has no flag that accepts a code or password.
10. **No enumeration.** `auth otp start`, sign-up and `auth password reset` return the same message,
    the same exit code and the same `--json` shape whether or not the email exists, is confirmed or
    is banned. Sign-in failure is one generic "invalid credentials" for unknown email, wrong password
    and unconfirmed account. *Test:* the fake IdP plays each case; outputs are byte-identical apart
    from a timestamp.
11. **Rate limits, server side.** Configure GoTrue: at most one email per address per 60 seconds
    (`smtp max_frequency`), email sends per hour capped at the SMTP provider's safe volume, token
    verifications at most 30 per 5 minutes per IP. The CLI surfaces a 429 as its own documented error
    with the server's retry delay and never retries automatically in a loop. *Test:* a config check in
    CI; the fake IdP's 429 maps to the documented code with no retry.
12. **Code strength.** OTP and recovery codes are **8 digits** (`mailer_otp_length = 8`) and expire in
    **10 minutes** (`mailer_otp_exp = 600`). Requesting a new code invalidates the previous one. A
    6-digit code at the per-IP limit is reachable by a botnet inside its validity window; 8 digits
    multiplies that cost by 100 for no usability loss worth keeping it. *Test:* config check.
13. **After a reset.** A successful password reset or change revokes every other session of the
    account (`signOut` scope `others`) and sends a transactional security notice. *Test:* the fake IdP
    records the revocation call.
14. **Linking.** Automatic linking applies only between identities whose email is confirmed. An
    unconfirmed email-and-password identity is never linked to an incoming OAuth identity, which
    closes pre-account hijacking (an attacker registers the victim's email with a password and waits
    for the victim to sign in with Google). GitHub uses only the primary verified email. Confirm-email
    and secure email change (both addresses confirm) are on; anonymous and phone sign-in are off.
    *Test:* a scripted scenario against the `dev` project before release; config check.
15. **Password policy (NIST SP 800-63B).** Minimum 10 characters, maximum 64 characters and 72 UTF-8
    bytes, because GoTrue hashes with bcrypt, which silently ignores everything past byte 72. No
    composition rules, no forced rotation. Normalize to NFC before sending, so the same password typed
    on two systems is the same bytes. Supabase leaked-password protection is enabled on the paid plan.
    *Test:* boundary cases at 9, 10, 64, 65 characters and at 72/73 bytes with multibyte input.

### C. Session storage and secret hygiene

16. **Refresh token storage.** Stored only through `secrets.py` under the global ref
    `account.session.refresh_token`, on the default backend. When that backend is `insecure` (Linux
    today, or a failed DPAPI probe), `auth login` and `auth status` say so in plain words and in
    `--json` (`secret_backend`), and the file stays mode 0600. The access token is never persisted.
    *Test:* with only `insecure` available, the warning and field appear; no file outside the secrets
    backend contains the sentinel.
17. **Rotation and concurrency.** Refresh token rotation and reuse detection are on in GoTrue. A
    refresh runs under the store lock (`lock.py`); a second process waiting on the lock re-reads the
    stored token instead of refreshing again. Without this, two parallel commands present the same
    rotated token, reuse detection fires and revokes the session. *Test:* two concurrent refreshes
    against the fake IdP produce one token exchange and both succeed.
18. **No secret in any output.** The refresh token, access token, PKCE verifier, OTP, recovery code
    and password never appear in stdout, stderr, `--json`, the audit log, notifications, exception
    text, or the app's main-process log. HTTP errors from auth endpoints carry status and a fixed
    message, never a response body. No debug flag dumps auth request or response bodies. *Test:* run
    every `auth` subcommand in success and failure paths with the sentinel and grep all output and
    every file written under the store for it.
19. **Renderer.** IPC handlers validate the sender frame and the argument schema, return only the
    CLI's `--json` result, and never return or log a code or password. The renderer clears a code or
    password field after submit. The CSP stays `connect-src 'none'`. *Test:* app unit tests assert no
    handler result contains the sentinel.
20. **Logout.** `auth logout` attempts server-side revocation, then always deletes the local refresh
    token and `entitlement.json`, even when the network call fails, and reports which parts succeeded.
    *Test:* with the fake IdP down, both local records are gone afterwards.

### D. The signed entitlement

21. **Format.** `v1.<header>.<payload>.<signature>`, each part base64url without padding. The header
    is `{"kid": ...}` and nothing else is read from it; the algorithm is fixed to Ed25519 by the
    version, never negotiated, so there is no `alg` field to set to `none`. The signature covers the
    ASCII bytes `v1.<header>.<payload>`. The whole token is at most 4 KB. *Test:* a token with an
    added `alg`, a wrong version, an oversized body or a non-base64url character is rejected.
22. **Verify before parse.** The signature is verified over the raw bytes before the payload JSON is
    parsed. The parser rejects duplicate keys, non-object roots and wrong types for every known claim.
    *Test:* a validly signed payload with a duplicate `status` key is rejected.
23. **Claim checks, all required.** `v == 1`; `kid` names an embedded key, otherwise reject (no
    fetching keys); `iss` equals the compiled project URL, so a `dev` token is refused by a `prod`
    CLI; `aud == "devteam-cli"`; `sub` equals the signed-in account's id stored at login; `status` is
    one of the five known values, and an unknown value is treated as not usable; `iat` is no later
    than `effective_now` plus 5 minutes; `exp - iat` is at most **30 days**, a ceiling in code that a
    misconfigured `max_offline_days` cannot raise; `effective_now < exp`. For `trial`, the token is
    also unusable once `effective_now >= trial_ends_at`. Unknown `features` keys are ignored, never
    granted. *Test:* one rejection case per check.
24. **No downgrade.** A token is never replaced in the cache by one with an earlier `iat`.
    `entitlement.json` is written atomically under the store lock. *Test:* writing an older valid
    token leaves the newer one in place.
25. **Clock handling** as § 4 states it: `skew`, `effective_now`, `max_seen_at`, a 5-minute
    tolerance, and a reset of `max_seen_at` on each online success. *Test:* clock slow by 10 minutes
    still works offline; clock rolled back by a day forces an online check; clock jumped forward a
    year and back recovers after one online check.
26. **Replay.** A token copied from another account fails the `sub` check. A token copied to another
    machine together with that account's session is account sharing, which § 8 accepts. A `banned`
    or `trial_expired` token is cached like any other, so offline the block still shows its reason.
27. **Keys.** `dev` and `prod` use different key pairs; a `prod` build embeds only `prod` keys:
    `scripts/lib/auth-config.json` carries the `prod` environment alone, and the `dev` one lives in
    the repository-only `auth-config.dev.json`, which no distribution path copies. The
    private key is generated offline, held only as the Edge Function secret plus an offline backup in
    the maintainers' password manager, and never committed. Rotation: ship the next public key as
    `next` one release ahead, then switch signing. A leaked private key is answered by a release that
    drops its `kid`; tokens it signed stop working at that release, and at most 30 days later on any
    install that does not update. The rotation steps go in a runbook. *Test:* secret scanning (SR-36).

#### Entitlement token wire format

Issued by the `entitlement` Edge Function (`infra/supabase/functions/entitlement`); SR-21 to SR-23 remain the rules.

| Part | Content |
|------|---------|
| Token | `v1.<header>.<payload>.<signature>`, each part base64url without padding, 4 KB at most |
| Header | exactly `{"kid":"<key id>"}` |
| Payload | JSON object with exactly these claims: `iss`, `aud`, `sub`, `v`, `iat`, `exp`, `status`, `features`, and `trial_ends_at` only while `status` is `trial` |
| Signature | Ed25519 over the ASCII bytes `v1.<header>.<payload>` |

- `iat`, `exp` and `trial_ends_at` are integer Unix seconds. `v` is the integer `1`; `features` is an array of strings, possibly empty.
- `iss` is the project origin with no trailing slash and no path, for example `https://<ref>.supabase.co`. `aud` is `devteam-cli`.
- `kid` lives in the header only and is not repeated in the payload. There is no `max_offline_days` claim: the window is already encoded by `exp`.
- The HTTP response is `200 {"token": "<token>"}`. Errors are `{"error": "<code>"}` with the codes `unauthorized` (401), `rate_limited` (429, with `Retry-After`), `reauth_required` (403, `account-delete` only) and `request_failed` (500). The same JSON shape is used for every function.
- Request: `GET` or `POST` to `/functions/v1/entitlement` with `Authorization: Bearer <access JWT>` and the project `apikey` header. The body is ignored.

### E. The vendored Ed25519 verifier

28. **Source and scope.** Port the RFC 8032 § 6 reference code, verify-only. Keep its notice: RFC code
    components are under the Simplified BSD License, which must be reproduced next to the file. No
    signing function exists in the shipped module. *Test:* the module exposes `verify` only.
29. **Strict decoding.** Public key exactly 32 bytes, signature exactly 64. Reject `S >= L`
    (malleability), reject a point encoding with `y >= p` or with `x == 0` and the sign bit set, reject
    a point not on the curve. Use the cofactorless equation `[S]B == R + [k]A` with `k =
    SHA-512(R || A || M) mod L`, comparing in projective coordinates. Constant time is not required:
    every input is public. *Test:* the RFC 8032 § 7.1 vectors that can be reproduced offline pass
    (TEST 1024's message is not, and stays a skipped test naming why); negative vectors fail — each
    byte of a valid signature flipped, `S + L`, non-canonical `R` and `A`, small-order `A`. The
    Wycheproof categories (all eight torsion points as `A` and `R`, `S` at and past `L`, non-canonical
    `y` and sign-bit-on-zero, mixed order, empty and all-`0xff` input) are **built at test time with a
    test-only signer** rather than vendored, because no offline copy of the Wycheproof file exists for
    this repository to pin.

### F. The gate, and Supabase: RLS, Edge Functions, secrets

30. **Gate allowlist.** The exempt list in § 3 is matched on the parsed command path, never on an
    argv string prefix, and anything not on it is gated. Exempt commands write nothing that a gated
    command could not; `doctor` stays diagnostic, and any mode of it that writes into a project tree
    beyond repairing the framework's own state is gated. Gated commands called by hooks fail with the
    documented gate exit code, and hooks treat that code as non-fatal. *Test:* a parametrized test
    walks the real parser (as `test_json_contract.py` does) and asserts every leaf is gated except the
    list.
31. **RLS everywhere.** RLS is enabled on every table in an exposed schema, including tables with no
    client access. `profiles`: select and update own row only (`user_id = (select auth.uid())`), and
    column-level `UPDATE` granted on `display_name` alone, so a client cannot write any other column.
    `licenses`: select own row only; no insert, update or delete for `anon` or `authenticated`.
    `app_config` and `banned_identities`: no policy and `REVOKE ALL` from `anon` and `authenticated`.
    `licenses` is granted **column by column**: a client never reads `ban_reason` or `banned_at`.
    *Test:* pgTAP in `infra/supabase/tests/database/`, run by the `supabase-db` CI job against a local
    Supabase (`supabase test db`), asserts that a second user reads nothing of the first, that
    `display_name` is the only writable column, that the moderation columns and the service tables
    return permission errors, and that the rate limiter is service-role only.
32. **Database functions.** Any trigger or function that is `SECURITY DEFINER` sets
    `search_path = ''` and schema-qualifies every name. Views use `security_invoker = true`.
    *Test:* a CI query over `pg_proc` and `pg_class` options.
33. **Edge Function auth.** `entitlement` and `account-delete` run with JWT verification on, and derive
    the user id from the verified JWT, never from the request body or query. They read `service_role`
    only from their environment and never return it or any other user's data. Errors are generic.
    No CORS headers are sent; only the CLI calls them. *Test:* function tests with no JWT, an expired
    JWT, and a body naming another user id.
34. **Issuance checks.** Each entitlement issuance re-reads `licenses`, `app_config` and the
    HMAC ban list (SR-38) for the caller's current email, so a banned identity that re-registers is
    banned again. Issuance is rate-limited per user. *Test:* re-registering a banned email yields
    `banned`.
35. **Ban procedure.** A ban is one call to the service-role-only `ban-user` Edge Function, so no step
    can be skipped: it sets `licenses.status = banned`, sets the auth user's `banned_until` to a
    far-future date (never `infinity`, which GoTrue cannot scan), revokes all sessions (the SQL
    function `public.ban_user`), and writes the email HMAC (SR-38), which survives a later deletion.
    The function is the only holder of the pepper. *Test:* the function's own tests.
36. **`service_role` never ships.** It exists only in the Supabase dashboard and as Edge Function
    environment. CI secret scanning carries rules for a legacy JWT whose payload has
    `"role":"service_role"` and for `sb_secret_` keys (`.github/scripts/ci/secret_scan.py`, run by the
    packaging gate over the repository and over the tree `apply_strip` produces); the same gate fails
    if the repository-only `auth-config.dev.json` reaches the package (SR-27). *Test:* seeded positives
    built at runtime in `tests/test_secret_scan.py`, so no credential-shaped string is committed.

### G. Account deletion, ban list and LGPD

37. **Deletion re-authenticates.** `auth delete` requires a fresh code from GoTrue's reauthenticate
    endpoint, typed on stdin, then calls the function, then removes the local session and
    `entitlement.json`. GoTrue exposes no endpoint that verifies a reauthentication nonce on its own, so `account-delete`
    judges freshness from the access JWT: its newest `amr` entry must be at most 300 seconds old. The CLI
    therefore obtains the fresh code by signing in again with an email OTP (`verifyOtp`), whose session
    carries that `amr` entry, and calls the function with that access token. A refreshed token keeps its
    original `amr` timestamp, so a stolen long-lived session cannot pass. The newest `amr` entry must
    also be method `otp`: a fresh password or OAuth sign-in is not enough, or a stolen session could
    link the attacker's own provider, get a fresh entry and delete the account. *Test:* the function
    refuses a stale entry and a fresh non-`otp` one.
38. **Ban list is a keyed HMAC.** `banned_identities.email_hmac = HMAC-SHA256(pepper,
    normalize(email))`, with the pepper as an Edge Function secret, never in the database. `normalize`
    is trim, NFC, lowercase. Plus-addressing and Gmail dots are **not** folded: folding risks banning
    an innocent address and is left open below. The row stores the reason and `banned_at`, nothing
    else. *Test:* the stored value differs from `SHA-256(email)` and is stable across case and
    whitespace.
39. **Trial reset by deletion.** Before `trial_enabled` is ever turned on, deleting an account must
    not reset its trial: keep the same HMAC with reason `trial_consumed` for at most 12 months. It is
    written **when the trial starts**, under the address it started with, so changing the address
    before deleting buys nothing; an account deleted before any trial started leaves no marker. Named
    in PRIVACY.md under legitimate interest in fraud prevention (LGPD art. 7, IX). *Test:* delete, then
    re-register with the same email, resolves the trial as already started.
40. **LGPD obligations.** PRIVACY.md and the Terms ship in the release that announces the
    requirement, not the one that enforces it. They name: the controller and the encarregado contact;
    Supabase and the email provider as processors and any transfer outside Brazil (art. 33); what is
    collected (§ 7) and that `last_seen_at` is kept at day precision; retention — account data while
    the account exists, deletion on request; the HMAC list and its retention; the rights of art. 18
    and how each is exercised (`auth profile --json` for access, profile edit for correction,
    `auth delete` for deletion); incident notification (art. 48). Supabase auth audit logs, which hold
    IP addresses, are purged after 90 days by a scheduled job. Only transactional email is sent (§ 7).
41. **Telemetry unlinked.** No `auth` module imports telemetry and no telemetry module imports `auth`.
    Auth requests carry no telemetry id, including in `User-Agent`. *Test:* an import-graph test, and
    a test that the telemetry payload schema has no `sub`, email or account field.

### H. Delegated providers and hooks

42. **Installers check by exit code.** `install-opencode.sh`, `install-codex.sh`,
    `install-provider.sh` and `update.sh` run `devteam auth check --json` and decide on its exit code.
    A missing CLI, a non-zero code outside the documented set or unparseable output is a block in
    `enforce` mode; in the announce-only (`warn`) release it skips with a stderr note. Tests iterate `ALL_PROVIDERS` with a per-provider fixture map.
43. **Hooks never verify on their own.** `session-start.sh` gets the state in-process from
    `auth_gate.banner_line()`, which is cache-only (no network, no file write) and evaluates the cache
    with the same pure `entitlement.evaluate` as `auth status`; it never parses `entitlement.json`
    itself, so there is one verification code path. It never blocks (§ 3).

### I. Test seam

44. **Seam bounds.** `DEVTEAM_AUTH_TEST_*` is read from the environment only, never from a project
    file or preference. It accepts only a loopback IdP URL and a test public key with `kid` prefix
    `test-`, a prefix a `prod` key never uses. When active, every command prints a one-line warning
    to stderr and `auth status --json` reports `"test_seam": true`. The bypass it gives the local user
    is the risk § 8 accepts. An optional `DEVTEAM_AUTH_TEST_ANON_KEY` replaces the public `apikey`
    only while the seam is valid, so a local `supabase start` gateway accepts the requests; on its
    own it changes nothing. *Test:* a non-loopback URL with the seam on is refused; the warning and
    field are present; the anon key is ignored without a valid seam.

### Open points

- **Updates for blocked users.** Decided (§ 3): the core store updates itself while blocked; `sync`
  and the delegated installers stay gated.
- **Email quota.** `email_sent` is project-wide, so one IP spraying addresses can use the hour's
  quota for everyone. CAPTCHA is not an option (the CLI cannot render one); the mitigation is sizing
  `email_sent` to the SMTP provider's volume and the per-IP `sign_in_sign_ups` limit. Revisit with an
  edge throttle if abuse appears.
- **Email folding for the ban list.** Folding Gmail dots and `+tag` would catch more re-registration,
  at the risk of false bans. Left unfolded (SR-38) until abuse shows it is needed.
- **Headless OAuth.** Printing the authorize URL for use on another device cannot work with a
  loopback redirect. Email OTP is the headless path; device-code OAuth is not offered by GoTrue.

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
