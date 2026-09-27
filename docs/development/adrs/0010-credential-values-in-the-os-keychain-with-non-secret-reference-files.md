# ADR-0010: Credential values in the OS keychain with non-secret reference files

**Date:** 2026-09-27
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

v2 stored credentials as plaintext JSON at `.dev-team-agents/user-data/credentials.local.json`,
chmod 600 and gitignored. It works, but it has four problems that get worse with a global store:

1. The value sits in cleartext inside the project tree, one `git add -f` or one misconfigured
   `.gitignore` away from a public repository.
2. There is no separation between *which* credentials a project needs — a fact worth reviewing
   and diffing — and *what they are*, which must never be reviewed or diffed.
3. There is no record of which agent read which credential, and nothing prevents a value from
   being echoed into the transcript.
4. With N projects there are N unrelated files; a token shared across projects is duplicated N
   times and rotated N times.

This repository also demonstrates the blast radius of a naive "clean this up" rule: it carries a
root-level `credentials.local.json` that `docs/prompts/posthog-metrics-report.md:20` reads
deliberately, and the v2 health check reports it as a legacy file to migrate. A credential
design that assumes it knows where every credential belongs will move somebody's working file.

## Decision

Split reference from value.

**Reference** — non-secret, reviewable, diffable, editable by the app, living in
`data/credentials/global.json` and `data/credentials/<project_id>.json`:

```json
{
  "posthog.api_key": {
    "purpose": "Read product metrics for the weekly report",
    "source": "keychain",
    "ref": "devteam/<project_id>/posthog.api_key",
    "scope": ["devops-specialist"]
  }
}
```

**Value** — in the OS secret store, never in a file inside a repository:

| Platform | Backend |
|----------|---------|
| macOS | Keychain via `security add-generic-password` / `find-generic-password` |
| Windows | DPAPI-protected blob in `%APPDATA%\dev-team-agents\data\secrets\` |
| Fallback (no keychain) | `age`/`sops` encrypted file in `data/`, passphrase per session |
| Last resort | mode-600 file, marked `"insecure": true`, reported loudly by the health check |

**Access goes through `devteam cred get <key>`**, which resolves the layer (project overrides
global), checks the caller's declared `scope`, prints the value on stdout and nothing else, and
appends an audit line — who, when, which key, **never the value** — to
`data/projects/<project_id>/audit.log`. Agents no longer read a credentials file at all.

A `PreToolUse` hook refuses shell commands whose obvious effect is to dump a credential store
(`cat`/`grep`/`jq` over the credential paths, `security find-generic-password` outside the
resolver) and warns on echoing a resolved value.

**Migration** is `devteam cred import`: read the existing `credentials.local.json`, push each
value into the keychain, rewrite the file as references, and **move** the original into
`data/quarantine/<date>/` — never delete it, per the No-Destruction Rule. Import is opt-in per
file and never scans the tree for candidates, which is how the root-level file this repository
uses on purpose stays untouched.

**Stated limitation, deliberately not sold as security:** an agent with Bash can read anything
the user can read. `scope` is hygiene and auditability, not a sandbox. The real mitigations are
keeping secrets out of git, out of the transcript, scoped narrowly, short-lived, and separated
per project. Presenting the allowlist as a boundary would be a lie that a future reader would
build on.

## Consequences

### Positive
- No secret value in any file inside a project tree, in any mode.
- "Which credentials does this project use?" becomes a reviewable diff; "what is it?" stops
  being a file at all.
- A token shared across projects lives once in `global.json` and rotates once.
- Every read is attributable after the fact.

### Negative
- Three platform backends to implement and keep working, plus a fallback chain.
- A keychain prompt can block a non-interactive run; the resolver must fail with an actionable
  message instead of hanging.
- More moving parts than one JSON file, for a payoff that is invisible until something leaks.

### Neutral
- `work_feedback_active` and `work_feedback_interval_minutes` are not secrets. They stay in the
  credential file's schema for back-compat and are read without touching the keychain.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep the plaintext JSON, just centralise it in the store | Least work, but the secret stays in cleartext on disk and nothing is gained except deduplication. |
| Encrypted file only (`age`/`sops`), no keychain | One identical path on all platforms and no OS adapters, but requires the tool installed and a passphrase on every agent run that needs a credential. |
| Environment variables only | Nothing at rest, but they leak into process listings and child processes, and there is nowhere to record purpose, scope or rotation. |
| Delete the v2 file after import | Violates the No-Destruction Rule, and this repository is the proof case: its root-level credential file is read on purpose by a committed prompt. |
