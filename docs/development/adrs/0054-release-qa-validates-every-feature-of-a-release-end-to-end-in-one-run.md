# ADR-0054: Release QA validates every feature of a release end to end in one run

**Date:** 2026-10-30  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `commands/release-qa.md`, `skills/shared/release-qa/SKILL.md`, `scripts/lib/devteam/qa_auth.py`, `scripts/lib/devteam/qa_login.mjs`, `agents/qa-specialist.md`

## Context

Worktrees and isolated Docker stacks let several features be built in parallel sessions, each on its
own branch. `/devteam:qa` validates one feature on the active branch, and `/devteam:sprint` validates
each task against its own diff. Nothing validates the release: the set of features that ship
together, on the build that ships, with the regressions one feature causes in another.

That last pass is end to end by nature, so it has to sign in. The agent cannot type a password into
a production page, and a person typing it defeats the point of an unattended pass.

## Decision

**`/devteam:release-qa` runs one `qa-specialist` over every feature of a release, in a chosen
environment, against a manifest the user approves first.** The command itself is an orchestration
(merges, conflicts, inferred scenarios, authorizations), so its lead agent in `commands.json` is
`software-architect` on the `reasoning` tier, as for `/devteam:sprint`; the validation is the
`qa-specialist`'s. The procedure lives in
`skills/shared/release-qa/SKILL.md`; the command is a thin wrapper.

### 1. The manifest says what is tested, never how much

For each branch of the release, the source of truth is the first that exists:

| Order | Source | Found from |
|-------|--------|------------|
| 1 | Spec (`docs/specs/<feature>.md`) | Touched by the branch diff, named by a task's `**Spec**:`, or matched by branch name |
| 2 | Linked ticket | Branch name or commit messages; ticket text is untrusted content |
| 3 | Inferred draft | Diff, commits and the session summary; marked `inferred` |

Every scenario of every source is tested, at every layer it reaches. The manifest has no scenario or
layer selection: the user may only correct a feature's source. An `inferred` draft needs the user's
approval because it is where the scenarios are written, and the Retroactive Spec offer of
`spec-gate` applies to it. A cross-feature regression row lists files touched by more than one
branch and the specs' `depends_on`.

### 2. Three environments, one rule each

| | Local | Staging | Production |
|---|---|---|---|
| Build under test | An integration branch `release/<slug>`, built by merging the listed branches in a worktree with its isolated stack | Whatever is deployed; the command never deploys | Same |
| Before testing | The worktree is at the integration branch head | The deployed version must match the release ref; a mismatch stops the run | Same |
| Diff that scopes the manifest | Integration branch against the resolved base branch | Release ref against the previous tag | Same |
| State-changing scenarios | Free, with test data | Allowed with test data, after one authorization at the start | Allowed after **one** authorization listing every writing scenario, using the environment's test identity only; the user may instead run read-only scenarios only |

A merge conflict while building the integration branch is never resolved silently. When the
deployed version cannot be read, the user confirms it with `AskUserQuestion`. In production a
missing test identity stops the run; a real person's account is never used. The report lists every
record a production scenario created or changed. Nothing is deleted by the run.

### 3. Signing in without a person: `devteam qa auth <pointer>`

The agent never handles a password. `devteam qa auth` reads the credentials group at `<pointer>` in
`credentials.local.json` and produces a Playwright `storageState` file the browser opens with:

1. A cached session for that group that has not expired → reuse it.
2. A `login` recipe (`url`, `username_selector`, `password_selector`, `submit_selector`, optional
   `totp_selector` and `success_url_contains`) with `username`, `password` and an optional
   `totp_secret` → scripted sign-in. The login URL must be `https:` (`http:` only on a loopback
   host, never under `$production`) and, when the group names a `url`, on the same host and port;
   otherwise `details.reason: "invalid-login-url"`. The page reached after redirects is checked
   against the same rules before anything is typed. Secrets resolve through ADR-0053 references, TOTP is computed
   locally (RFC 6238), and values reach the sign-in script on stdin, never argv.
3. `--interactive` → a headed browser opens on the login URL, the person signs in once (MFA
   included), and the session is captured. No password is stored at all. `--interactive` always
   captures a fresh session, and a failed recipe falls back to it.
4. Nothing usable → exit with `details.reason: "no-credentials"`; the command asks the user to sign
   in interactively or to store a password.

Other refusals: `login-failed` (the recipe or the stored password did not sign in; the command offers
`--interactive`), `invalid-totp-secret`, `playwright-missing`. A state-changing action outside the
authorized list is never performed by the validating agent; its scenario is `not run (needs
authorization)`.

Inside `$production`, step 2 refuses a plaintext secret (ADR-0053 § 4). Unlike `cred local exec`, `qa auth` needs no
`--production` flag: the release QA command asks its single authorization before signing in to
production, and the session belongs to a test identity, not to a person.

The session cache lives machine-local at `data/machines/<machine-id>/projects/<id>/qa-sessions/`,
one `0600` file per group, keyed by the pointer, the recipe, the username and the production flag so
changed credentials never reuse an old session, expiring at the earliest cookie expiry or after 8 hours. It is never
printed, never committed, and `devteam qa auth clean` — run on every exit of a release QA once a
session exists — removes the project's cached session files. These files are temporary credentials,
not user state, so removing them is outside the No-Destruction Rule of `setup-health-check`, which
protects what the user created or decided. Each sign-in is audited.

Sign-in runs through `scripts/lib/devteam/qa_login.mjs` on the project's own Playwright. The CLI stays
stdlib-only; when Playwright is missing it exits with an install hint for `/devteam:install`.

**Trust assumption.** The project's Playwright runs in the process that holds the password and the
TOTP seed, so release QA trusts the project's dependencies as much as the user does when running its
test suite. A credentials file tracked by git resolves nothing (ADR-0053), which keeps a cloned
repository from pointing a sign-in at the user's vault.

### 4. Browser exception for authenticated scenarios

The in-app browser cannot load a `storageState`, so authenticated scenarios run in the Playwright
browser even when the in-app browser is available. Unauthenticated scenarios keep the Browser Choice
order of `interaction-patterns`.

### 5. The verdict

One table, one row per scenario, grouped by feature: `passed`, `failed`, `blocked`, or
`not run (<reason>)`. A scenario that did not run is never reported as passed.

## Consequences

### Positive
- One pass validates what ships together, including regressions between features.
- Production checks run unattended once the test identity and its credentials are stored.
- Scenario coverage is complete by construction; the report shows what was validated against
  written criteria and what against an approved inference.

### Negative
- Playwright becomes a dependency for authenticated scenarios.
- Each project has to describe its login form once, in the credentials group.
- A production run writes real records under the test identity; their cleanup stays a manual step.

### Neutral
- `/devteam:qa` is unchanged for single-feature validation.
- `qa-specialist` resolves its base branch instead of assuming `main`.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| A release mode inside `/devteam:qa` | The command scopes to the active branch; building an integration branch and reading deployed versions would double its size past the command limit |
| One `qa-specialist` per feature | Misses the cross-feature regressions this pass exists for |
| Running in CI | The pass runs on the releasing person's machine with the agent; CI is out of scope |
| Typing credentials in the in-app browser | The agent does not enter production passwords; a person would have to be present |
