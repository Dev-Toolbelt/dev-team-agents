# ADR-0016: The project display name is app-local and never reaches the CLI

**Date:** 2026-09-29
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

The desktop app's Projects screen listed bound projects by absolute path. On a machine with
several checkouts under a common parent — `~/Code/acme-api`, `~/Code/acme-web`,
`~/work/clients/acme-api` — the rows are distinguishable only by reading to the end of the
path, and the end of the path is the part the column truncates. A human-readable label was the
obvious fix, and where to put it was not.

Three existing decisions constrain the answer:

- [ADR-0008](0008-project-identity-via-committed-project-json-and-three-personal-preference-layers.md)
  makes `.dev-team-agents/project.json` the committed identity record — `schema`, `project_id`,
  `context_paths` — and states that **nothing about a preference is committed**. It does not say
  which side of that line a display label falls on, because no label existed.
- [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) splits the data store by
  what a record *is*: what the user authored or decided is portable and lives at the top of the
  store, what this machine observed or built is machine-local. `paths.is_machine_local_record()`
  is the single answer to that question and is never re-derived at a call site.
- [ADR-0011](0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) makes the
  CLI's `--json` output the app's public API, and [ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md)
  makes the app a pure client that adds no capability of its own. A name the app invents is,
  under those two, a thing the app has no obvious right to send anywhere.

The forcing question is therefore not "where is it convenient to keep a string" but **whether a
display label is part of the framework's contract at all**. Answering yes means a `bind --name`
flag, a `name` key in the committed `project.json`, a schema bump, the `--json` contract sweep in
`tests/test_json_contract.py`, and a field every provider and every future client has to agree
about. Answering no means the label is a property of one client's view and stops at that client.

A name is also the first field of its kind. Every other record either identifies a project
(`project_id`), describes its topology (`context_paths`, `layout`), or configures behaviour
(preferences). A label configures nothing and identifies nothing — it exists so a person can
recognise a row. That has no precedent in the store, which is why the question needed deciding
rather than pattern-matching.

## Decision

**The name is the app's record, not the framework's.** It is declared on the app's own request
type, stripped before the CLI is invoked, and stored in the app's `settings.json` only after the
bind succeeds. No CLI surface changes: no flag, no `project.json` key, no schema bump, no
`--json` field.

### 1. It is stripped at the process boundary, not merely unused

`BindRequest.name` exists in `app/src/shared/api.ts` — the frozen contract the renderer and main
process share — so the renderer can send one. `bindProject` in `app/src/main/ipc.ts` copies it
out and builds the CLI argv from the remaining fields. The name is never an argv element, and
`validateBindRequest` treats it as an optional string like any other untrusted input crossing
that boundary.

This is deliberate placement. Leaving `name` on the request and *happening* not to append it to
argv would be one refactor away from a leak; removing it from argv construction explicitly, in
the one function that builds argv, is the reviewable form.

### 2. It is written after `result.ok`, and a write failure is swallowed

`writeProjectName()` in `app/src/main/settings.ts` performs an atomic read-merge-write of
`settings.json` — write to a `0600` temp file with `flag: 'wx'`, then `rename`, removing the temp
file and rethrowing if the rename fails. It runs only when the bind reported success, and
`bindProject` in `ipc.ts` discards its failure in an empty `catch`.

The ordering follows from what each operation costs to undo. The bind mutated the store and the
project directory; the name is a label in one client's file. Failing a completed bind because a
label could not be persisted would report a false negative about the durable operation and
invite the user to retry an action that already happened.

### 3. Absence is a supported state, not a degraded one

`displayName()` in `app/src/renderer/screens/Projects.tsx` falls back to the directory basename.
Every consumer reads through it. There is no migration, no backfill, and no "unnamed" marker —
a project with no stored name is indistinguishable in behaviour from one that never had the
feature, which is what makes the field safe to add to an existing install and safe to remove.

### 4. Under ADR-0013 it would be machine-local even if it were in the store

The name is not in the store, so `MACHINE_LOCAL_RECORDS` does not list it. Recording the
classification anyway, because it is the part that decides any future promotion: a label one
person typed on one machine to recognise one row is closer to *observed by this machine* than to
*authored and portable*. Promoting it to `project.json` would make it committed and shared,
which is a stronger claim than the field's purpose supports.

## Consequences

### Positive
- No change to the CLI's public surface. `tests/test_json_contract.py` sweeps every subcommand's
  `--json` shape from the real parser; a field added there is a compatibility obligation, and
  this decision incurs none.
- The feature shipped without coordinating a schema bump, a flag, and a contract sweep.
- Reversible in the only direction that matters. Adding `bind --name` later is additive under
  ADR-0014; the app would prefer a stored name and fall back to its own, and nothing already
  written becomes wrong. Removing a committed `project.json` key after the fact would not be.

### Negative
- **The name does not survive a fresh clone.** It lives in the app's `settings.json`, which is
  machine-local and outside the repository. A second machine binding the same project sees the
  basename.
- **No other client can see it.** An opencode or Codex install, the CLI itself, and `devteam
  list --json` all report the project without it. Two clients on one machine disagree about what
  the project is called.
- **The rename path is asymmetric.** Moving the directory changes the fallback for everyone;
  changing the stored name changes it for one app on one machine. Nothing reconciles the two.
- A user who names ten projects and then re-clones has lost ten labels with no export path and
  no warning that they were local.
- **A failed name write is invisible.** The `catch` in `ipc.ts` is empty — no log line, no
  renderer signal. The bind is correctly reported as succeeded, and the user sees a row that
  fell back to the basename with nothing saying why. Silence is right for the bind's exit code
  and wrong for the user's mental model.
- **A name cannot be cleared through the app.** `writeProjectName` returns early on an empty or
  whitespace-only string, so submitting a blank name leaves the previous one in place. The guard
  exists so a rebind without a name does not blank a good label; the cost is that unnaming needs
  a hand edit of `settings.json`.

### Neutral
- `settings.json` gains a second concern. It held `cliPath` — one explicit answer to "which
  `devteam`?" — and now also holds a `projectNames` map keyed by `project_id`. The file's header
  comment records that `projectNames` is a different kind of field from `cliPath`, so the next
  reader does not infer that everything in it is CLI resolution.
- Keying by `project_id` rather than path means a moved directory keeps its name, which is the
  ADR-0008 identity property working as intended for a record ADR-0008 does not cover.
- The retrieval path for this reasoning is
  [`docs/wiki/electron/project-naming-scope.md`](../../wiki/electron/project-naming-scope.md),
  indexed in the wiki for the reader who hits the surprising behaviour before finding this ADR.

## Risks

| Risk | Mitigation |
|------|------------|
| A user assumes the name is shared, because nothing in the UI says otherwise, and relies on it to coordinate with a teammate | Unmitigated today. The UI does not mark the field as local. This is the first thing to fix if the feature stays as it is |
| The field is promoted to `project.json` later without setting a precedence rule, and a committed name silently loses to a stale local one | A promotion is itself an ADR. The precedence rule — stored name wins, local becomes an override or is migrated — is part of that decision, not an implementation detail |
| A future client adds its own local name in its own file, and the divergence multiplies | The wiki entry states that the name is one client's view; a second client copying the pattern is the signal to promote, not to add a third store |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| `name` in the committed `project.json`, set by a new `bind --name` flag | The portable, shareable answer, and still the likely eventual one. Rejected **for now**, not on principle: it needs a schema bump, a `--json` contract change under ADR-0011, a precedence rule against the local value, and agreement that a display label belongs in the framework's identity record — which ADR-0008 deliberately kept minimal. Shipping the label did not need any of that |
| `name` as a preference, in the ADR-0008 project preference layer | Preferences configure agent behaviour and resolve into `resolved/preferences.json`, which every agent reads. A label no agent consumes would put a pure-presentation string into the file whose cost is paid on every agent invocation |
| Derive a label instead of storing one — parent directory plus basename, or a git remote's `owner/repo` | No storage and no new field, and it disambiguates the common case. Rejected because it is not stable: it changes when the directory moves or the remote is renamed, and a label whose purpose is recognition should be the one thing the user controls. Kept as the *fallback*, in `displayName()` |
| Store the name in the store under `data/projects/<id>/` as a machine-local record | Correct under ADR-0013 and the closest rejected option. It would make the name visible to the CLI and to other clients on the same machine — a real benefit — but the app would be writing directly into the store, which ADR-0015 forbids: the app is a pure client and mutates the store only through CLI commands. Doing this needs a CLI command to write it, at which point the committed-`project.json` alternative above is the better version of the same work |
