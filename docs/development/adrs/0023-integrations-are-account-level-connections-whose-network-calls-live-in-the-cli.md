# ADR-0023: Integrations are account-level connections whose network calls live in the CLI

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

The desktop app should let a user connect GitHub and Jira once, check that the connection works, and
pick per project which repository or Jira project it maps to. Today the harness reaches Jira only
through the Atlassian MCP inside an agent session, and GitHub only through `gh`; neither is visible to
the app, and neither gives a user a place to store a token, test it, or see why it stopped working.

The obvious vehicle is a plugin ([ADR-0019](0019-plugins-as-manifest-declared-per-project-integrations.md)),
and it does not fit:

- **A plugin has no secret.** Its settings are committed in `plugin-settings/<name>.json`; a token
  cannot live there, and [ADR-0010](0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md)
  already says where secrets go.
- **A plugin is per project; a connection is per account.** One GitHub token serves every project on
  the machine. Only the mapping (which repository, which Jira key) is per project and team-shared.
- **Plugin code is a script the CLI runs blind.** An integration is authentication code specific to
  one REST API — header scheme, test endpoint, error semantics — and it is where a token leaks if
  anything does. That belongs in reviewed CLI code, not in a manifest-declared script.

Two more decisions constrain the answer: the app is a pure CLI client that never touches the network
or filesystem ([ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md)),
and every record is either portable or machine-local
([ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md)).

## Decision

### 1. An integration is a python adapter in the CLI that declares a descriptor

v1 ships two adapters, `github` and `jira`, in `scripts/lib/devteam/`. Each declares a descriptor —
title, auth kind and help text, and `fields[]` with `key`, `scope` (`account` | `project`), `type`
(`string` | `enum`), `required`, `default`, an optional `resource` (a list the CLI can fetch to fill
the field as a picker) and an optional `visible_when` condition. The app renders the Integrations
screens from that descriptor alone and **never names an integration**, the same rule ADR-0019 set for
plugins. Adding a third integration means adding one adapter.

### 2. Four records, four homes

| What | Where | Class |
|------|-------|-------|
| Token value | Secret store via `creds.set_entry(key="integration.<name>.token", project_id=None, …)` — the global credentials layer (ADR-0010) | Value machine-local, reference portable |
| Account config (non-secret: API URL, site, deployment, email) | `data/integrations/<name>.json` → `{"schema":1,"config":{…}}` | Portable |
| Project binding (repository, project key) | `<project>/.dev-team-agents/integration-settings/<name>.json` → `{"schema":1,"config":{…}}`, committed like `plugin-settings/` | Committed, team-shared |
| Last test result | `data/machines/<machine-id>/integrations-status.json` → `{"schema":1,"status":{…}}` | Machine-local — added to `paths.MACHINE_LOCAL_RECORDS` |

The field's declared `scope` decides which file `config set` writes; a project-scope write with no
bound project is a usage error. Every write is locked and atomic. Reading the token goes through
`creds.get_value(..., agent=None)`, so the ADR-0010 audit trail records each use.

### 3. All network I/O is in the CLI, under one HTTP policy

The CLI surface is `devteam integration {list, show, connect, test, disconnect, config {get,set,unset},
resources}`, each with `--json` and `--path`. The app calls named operations in the main process
(`integrationList`, `integrationConnect`, …), never a generic run, and never opens a socket. Every
request goes through one shared HTTP module:

| Rule | Value |
|------|-------|
| Scheme | `https` only. Loopback `http` is allowed only under `DEVTEAM_INTEGRATIONS_TEST_ALLOW_LOOPBACK_HTTP=1`, for tests |
| Token destination | Only the exact scheme + host + port of the configured base URL |
| Redirects | Same origin only; anything else is refused. The redirect guard is extracted from `update.py`'s `_RestrictedRedirects`, not duplicated |
| Limits | 10 s timeout, 2 MB response body cap |
| Error → state | 401, or 403 without a rate-limit signal → `invalid_token`; 403/429 with `X-RateLimit-Remaining: 0` or `Retry-After` → `rate_limited`; URL, DNS, TLS, timeout or undecodable JSON → `unreachable` |
| Secrecy | The token and the `Authorization` header never appear in an exception message, payload, log or audit detail |

A failed `test` is a result, not a CLI error: exit 0 with `test.ok = false` and the state above.
Missing token or config is a usage error; `resources` failing on the network is an environment error.

### 4. The token reaches the CLI on stdin, never argv

`devteam integration connect <name>` reads the token from stdin and strips the trailing newline. argv
is visible to every process on the machine and lands in shell history; stdin is neither. Empty stdin
keeps a stored token, so the app can change account fields without re-sending it; empty stdin with no
stored token is a usage error. The app's secret input is write-only — never pre-filled, it shows only
"Stored in <backend>" with Replace and Remove.

### 5. The JSON contract is additive

`integration` is a new command group with its own payloads (`IntegrationView`, `TestResult`) and new
schema-numbered records. Nothing existing changes shape, so under
[ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md)
this is an additive change; the app declares the new schemas before it writes, like any other client.

## Consequences

- A token is entered once per machine and serves every project; rotating it is one `connect`.
- Mapping a project to a repository or Jira key is a committed change the whole team gets on pull,
  as with plugin settings. GitHub's `repository` is also offered as `detected` from `git remote`.
- `disconnect` removes the token value and reference (unless `--keep-token`) and the status record,
  and keeps the account config, so reconnecting needs only the token.
- **User-configured base URLs are an SSRF-shaped risk.** `api_url` and `site_url` are free text, so
  the CLI will send an authenticated request to any https host the user types. This is accepted: the
  URL is set by the user on their own machine, with their own token, and self-hosted GitHub
  Enterprise and Jira Data Center make an allowlist impossible. What the policy does guarantee is
  that the token never travels to a host other than the one configured — not by redirect, not over
  plain http. The account config is portable, not committed, so a cloned repository cannot choose
  where a user's token is sent.
- Two adapters are the first HTTP clients in the CLI besides the update check; the shared policy
  module is where the next one must go.

**Token-origin binding.** A token is bound to the origin it was stored for: every token write
records `token_origin` (`scheme://host:port` of `api_url` / `site_url`) in the account config, and
any request whose current origin differs, or that finds none recorded, is refused. Editing the URL
therefore cannot redirect a stored token to another host; it leaves the token stale (`auth.stale`)
until the user reconnects with a new one. The keychain value is kept, per the No-Destruction Rule.

## Provider Parity

Out of scope for this ADR, deliberately: nothing provider-facing changes. No agent, command, skill,
hook, installer or render output is touched; the change is the CLI and the app. **Follow-up:** the
agents and skills that talk to these services today — the `jira` skill, `setup-assistant`'s
issue-tracker step — should consume `devteam integration` (config, binding, resources) instead of
asking the user again, and that change must land for `claude`, `opencode` and `codex` together.

## Alternatives Considered

- **A plugin with a `secret` config field type.** Rejected: plugin settings are committed and
  per project, so the secret would need a second storage path bolted onto the manifest, the account
  layer would still be missing, and per-API auth would run as an unreviewed script.
- **The app calling the REST APIs from the Electron main process.** Rejected by ADR-0015: it would
  make the app a second client with its own network and token handling, invisible to agents and to
  the CLI's audit trail, and the app would have to read the token value, which ADR-0015 §7 forbids.
- **OAuth device flow instead of personal tokens.** Deferred, not rejected. It needs a registered
  OAuth app per service, refresh-token storage, and a different path for GitHub Enterprise and Jira
  Data Center. Personal tokens cover both deployment shapes today; `auth.kind` in the descriptor
  leaves room for a second kind later without changing the contract.
