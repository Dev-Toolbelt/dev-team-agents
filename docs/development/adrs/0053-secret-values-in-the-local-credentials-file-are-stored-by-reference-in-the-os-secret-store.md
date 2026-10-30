# ADR-0053: Secret values in the local credentials file are stored by reference in the OS secret store

**Date:** 2026-10-30  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Amends:** ADR-0010 (the local file joins the audited value path), ADR-0024 (§ 5 gains leaves and an op, § 6 gains a reserved leaf form), ADR-0046 (`copy-value` resolves a reference)  
**Applies to:** `scripts/lib/devteam/credentials_local.py`, `scripts/lib/devteam/secrets.py`, `skills/shared/credentials/SKILL.md`, `app/src/renderer/credentials/*`

## Context

`credentials.local.json` is the one place a user sees and edits credentials (ADR-0024), and it keeps
every value in plaintext: `$secrets` only hides a value in `show` and in the app. The audited path that
keeps values in the OS secret store — `devteam cred` with the `keychain`, `dpapi` and `insecure`
backends (ADR-0010) — exists beside it, but few users know it, and `cred import` does not accept the
file's nested shape.

Unattended work makes the gap concrete. A release QA run (ADR-0054) has to sign in to staging and
production without a person typing a password, which means the password has to be stored somewhere
a script can reach it. Today the only such place is plaintext on disk, inside the project tree, where
a Docker build context, a synced folder or a zipped project carries it away.

## Decision

**The file stays the only surface the user sees; a secret value moves out of it and a reference takes
its place.**

### 1. A reserved leaf form: `{"$ref": "<ref>"}`

A value may be the one-key object `{"$ref": "<ref>"}`. Three ref kinds exist:

| Ref | Resolved by | Written by |
|-----|-------------|------------|
| `devteam/<project_id>/local/<id>` | `secrets.get(ref, backend)` — the backend recorded at write time | `cred local patch` op `set-secret` |
| `op://<vault>/<item>/<field>` | 1Password CLI, `op read <ref>` | The user, by hand or through the app |
| `bw://<item-uuid>/<field>` | Bitwarden CLI, `bw get item <item-uuid>` then the field; the id must be a UUID so it is never searched or read as an option | The user, by hand or through the app |

`<id>` is a random opaque token, independent of the value's pointer, so a `move` never breaks the
reference. The backend that holds a `devteam/` value is recorded beside the reference as
`{"$ref": "...", "$backend": "keychain"}`; a reader never guesses it.

ADR-0024 § 6 chose sibling marks over wrappers so a value stays a plain string for an agent reading
the file. That reason is exactly what this decision removes: an agent must not read a secret value at
all. Non-secret values stay plain strings and agents keep reading them as before.

### 2. Writing: `set-secret`

`cred local patch` accepts a fourth op, `{op: "set-secret", pointer, value}`. The value travels on
stdin like every other patch value. The CLI pushes it into `secrets.default_backend()`, reads it back
(the existing `cred import` pattern), writes the reference at the pointer and adds the key to the
parent's `$secrets`. Replacing a referenced value reuses its ref. `unset` of a `devteam/` reference
deletes the backend value as well — the user removed the credential; a stranded value in the
keychain is the worse outcome. `op://` and `bw://` values are never touched by `unset`.

### 3. Reading

| Surface | Behaviour |
|---------|-----------|
| `cred local show` | A reference is redacted like any secret, with an additive `stored` field: the backend name, `op`, `bw`, `invalid` for a malformed reference, or `null` for a plaintext secret |
| `cred local copy-value` | Resolves a reference to its value (ADR-0046 path; the renderer still never receives it) |
| `cred local exec <pointer> -- <cmd>` | Resolves every scalar leaf of the object at `<pointer>` and runs `<cmd>` with them as environment variables (`DEVTEAM_<KEY>`, upper snake case); stdio and exit code are the child's. `--json` is refused, as for `cred get`. Under `$production` it also requires `--production` (`details.reason: "production-flag-required"`), which an agent passes only after asking the user |
| Agents reading the file | See `{"$ref": ...}` and never a value; they use `exec` when a command needs one |

This is how an agent uses any secret, in any environment and for any task: a credentials-file secret
through `exec`, web sign-in through `devteam qa auth` (ADR-0054 § 3), and otherwise only through a
connected integration, an MCP server's own tools or the project's local `.env`. A secret the user has
not stored is stored by the user — never typed or pasted into the chat. The closed list lives in
`skills/shared/credentials/SKILL.md` § 3b.

Every resolution — `copy-value`, `exec`, and the QA sign-in of ADR-0054 — appends an audit line to
the machine-local `audit.log` (ADR-0010 format: never the value, nothing derived from it).

**A tracked file resolves nothing.** When `credentials.local.json` is tracked by git, every
resolution is refused with `details.reason: "tracked-file"`. A cloned repository could otherwise
commit the file with a `login.url` it controls and a guessable `op://Private/...` reference, and turn
the user's own vault against them; git checks out a committed copy even when it is ignored. Inside a
repository the check fails closed: when git cannot tell whether the file is tracked, resolution is
refused with `details.reason: "tracked-file-unknown"`.

### 4. Production refuses plaintext

Inside an object with `$production: true` (on it or any ancestor), `patch` refuses a `set` of a plain
string on a secret key — marked in `$secrets` or secret-looking by ADR-0024 § 5's net — with
`details.reason: "plaintext-in-production"`. The app sends `set-secret` instead. The same check runs after every
patch, so a `move`, a `set` of a whole group or a new `$production: true` cannot bring a plaintext
secret — or a reference held by the `insecure` backend — under production either. Values already
in plaintext are not rejected on read; they are reported.

### 5. Existing plaintext values move only with consent

`cred local secure` lists every plaintext secret (pointer, production or not) and changes nothing.
`cred local secure --apply [--pointer P ...]` moves the listed values into the backend and writes
their references, all under one lock, verifying each read-back before the file is rewritten; a
failure leaves the file untouched. Nothing runs it implicitly. `devteam doctor` reports
`plaintext-secret` findings as INFO, which does not change its exit code, because the file worked
this way until now; under `$production` the finding is an error, and so is an `insecure`-backend
reference there.

### 6. Machines without a secret store

On a host with no keychain and no DPAPI, `set-secret` falls to the `insecure` backend, which
`doctor` already reports as `insecure-backend`. It is allowed outside production and refused inside
it with `details.reason: "insecure-backend-in-production"`.

## Consequences

### Positive
- Users keep one editor and one file; the word "keychain" never has to reach them.
- Secret values leave the project tree, so a build context or a zipped project no longer carries them.
- Every value read is audited, including the ones a sign-in script makes.

### Negative
- Agents that read a secret straight from the file (an SSH password, an API token) stop seeing it
  once the value is secured; their skill now routes them through `cred local exec`.
- `op://` and `bw://` need the vendor CLI installed and unlocked; an unlocked vault is the user's
  session, not ours, and resolution fails loudly when it is locked.
- A keychain value is capped at 3072 bytes (ADR-0010); `set-secret` refuses a larger value.
- `cred local exec` prints whatever the child prints. Outside production, only the credentials
  skill keeps an agent from running `env` through it; under production `--production` makes the
  agent ask first, but a granted run can still echo a value.

### Neutral
- `--json` changes are additive: a new op, two new leaves, a new `stored` field.
- `cred get` and the `data/credentials/` reference layer are unchanged.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep plaintext, rely on `0600` and `.gitignore` | The file still leaves the machine with the project folder; it does not survive unattended sign-in |
| Move the local file's secrets into `data/credentials/` references | Two editors for one concept; the free-form nested shape has no home there |
| A sibling mark (`"$stored": ["password"]`) with the value removed | The pointer of the stored value would be implicit, and a `move` would need to rewrite two places |
| Encrypt the file with a passphrase | No non-interactive passphrase model exists (ADR-0010's deferred `age`/`sops` row) |
