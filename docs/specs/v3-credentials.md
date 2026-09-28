---
touches: [] # CLI/tooling change — none of backend, frontend, database or mobile is involved
depends_on: [v3-global-install]
---

## Spec — credential references, the value store and the read guard (milestone M3)

### User Story
As a developer whose agents need API keys, tokens and passwords, I want the *fact* that a project
needs a credential to be reviewable and the *value* to live outside every repository, so that a
misconfigured `.gitignore` cannot publish a secret, and so that I can see afterwards which agent read
what.

### Context
v2 kept credentials as plaintext JSON at `.dev-team-agents/user-data/credentials.local.json` — inside
the project tree, duplicated per project, with no record of who read what. ADR-0010 splits the
**reference** (purpose, backend, opaque ref, expected readers — non-secret, diffable, portable) from
the **value** (in the OS secret store, never in a repository), and routes every read through
`devteam cred get`, which checks scope and audits. ADR-0013 classifies where each new record lives.
This spec covers milestone **M3** only: the reference layer, the value backends, the
`devteam cred` command surface, the v2 migration, the audit trail, and the `PreToolUse` guard. It is
the milestone `v3-global-install.md` listed as "credentials — later milestone".

### Acceptance Criteria

**Scenario: a reference file can never hold a value**
- Given a credential reference layer, global or project
- When any entry is read or written
- Then the only accepted fields are `purpose`, `source`, `ref` and `scope`
- And a field named `value`, `secret`, `password`, `token`, `api_key` or any other name outside that
  set is refused on read, naming the file and the key
- And a field whose name looks like it holds a secret is refused with a message saying so
  specifically, not merely "unexpected field"
- And every payload any command returns for a reference is built by naming those fields explicitly,
  so a field added to the schema later cannot appear in output by default
- And `source` is refused unless it names a backend this build actually implements

**Scenario: `cred get` writes the value and nothing else**
- Given a registered credential with a value stored
- When `devteam cred get <key>` runs
- Then stdout is exactly the value plus one newline — no banner, no label, no trailing blank line
- And `TOKEN="$(devteam cred get <key>)"` yields the value with no parsing
- And nothing on stdout or stderr repeats the value on any other line

**Scenario: `cred get --json` is refused, not honoured**
- Given the same credential
- When `devteam cred get <key> --json` runs
- Then the command fails as a usage error with exit code 2
- And no value appears on stdout or stderr
- And the error names `devteam cred list --json` as the machine-readable surface for references
- And this is the only `devteam` subcommand that refuses `--json`, and the refusal is recorded as an
  exception in ADR-0010 against the `--json` contract in `CLAUDE-md/cli.md`

**Scenario: a value never reaches a command line**
- Given a developer storing a credential
- When `devteam cred set <key> --purpose ...` runs
- Then the value is read from stdin — prompted without echo on a tty, read whole otherwise
- And there is no flag that accepts the value as an argument
- And a trailing newline contributed by a pipe or a here-doc is stripped, while the value's own
  characters are not
- And an empty value is refused with a usage error naming how to pipe one in
- And no subprocess the backends invoke receives the value as an argument — only the opaque `ref`
  appears in a command line

**Scenario: a value that cannot be stored intact is refused, not mangled**
- Given a value containing a NUL, a carriage return or a newline
- When it is stored through any backend
- Then the write is refused with a message saying multi-line material must be split first
- And nothing is written to any backend
- And the refusal is identical on every platform, so behaviour does not depend on which backend the
  machine happens to default to

**Scenario: the project layer overrides the global one**
- Given the same credential key declared in both `data/credentials/global.json` and
  `data/credentials/<project_id>.json`
- When it is resolved from inside that project
- Then the project entry wins and the result names `project` as the layer it came from
- And `devteam cred list` shows one row for that key, marked `project`
- And a key only the global layer declares is still listed and still resolvable
- And `--global` acts on the shared layer from anywhere, regardless of the current project
- And a key neither layer declares is reported as not registered, which is an error with an
  actionable hint rather than a crash

**Scenario: the scope check refuses and audits — and is not a sandbox**
- Given a credential whose `scope` lists one agent name
- When `devteam cred get <key> --agent <a-different-agent>` runs
- Then the read is refused
- And an audit line is appended with outcome `scope-refused`
- And the refusal message states that scope is hygiene and auditability, not a sandbox
- And an entry with an empty `scope` is readable by any caller
- And a read with no `--agent` is allowed and audited with a null agent, which is what "the caller
  was unidentified" looks like in the trail
- And no criterion in this spec asserts that any mechanism here prevents a process with shell or
  file-read access from reaching a value

**Scenario: the audit trail records failures, and never the value**
- Given any credential read
- When it succeeds, is refused by scope, names an unregistered key, or resolves to a reference whose
  value is missing
- Then one JSONL line is appended for each of those four outcomes
- And the line carries a UTC timestamp, the action, the key, the layer, the agent and the outcome
- And the line carries neither the value nor anything derived from it — no length, no hash, no prefix
- And `unset` and `import` append a line of their own
- And the file is opened append-only at mode 0600 and each line is written in a single call, so an
  interrupted write can damage at most the last line

**Scenario: the audit log and the value store are machine-local; references are portable**
- Given a populated data store
- Then the reference layer is at `data/credentials/` and is portable
- And the audit log is at `data/machines/<machine-id>/projects/<project_id>/audit.log`
- And any value a backend keeps on disk is under `data/machines/<machine-id>/secrets/`
- And `audit.log` is classified machine-local by `paths.is_machine_local_record`, so a portable
  export excludes it at every path depth with no export-side exclusion added for it
- And a portable export carries the references and no value and no audit log
- And a read performed on a second machine appends to that machine's own log, never to the first's

**Scenario: importing a v2 file is copy → verify → retire**
- Given a v2 `credentials.local.json` at an explicitly named path
- When `devteam cred import <file>` runs
- Then every value is pushed into a backend and read back and compared before anything else happens
- And only after every value verifies is the reference file written
- And only after the reference file is written is the original **moved** into
  `data/quarantine/<date>/`, never deleted
- And `work_feedback_active` and `work_feedback_interval_minutes` are carried over as plain values
  without touching a backend, and the report names them separately
- And the report names the reference file, the quarantine destination, and the count stored

**Scenario: a failed import leaves nothing half-migrated**
- Given the same file, where one value cannot be stored or fails to verify
- When the import runs
- Then every value that import already pushed into a backend is deleted again
- And the reference file is unchanged
- And the original file is still at its original path, unmoved
- And the command reports the failure naming the key and the backend, never a value

**Scenario: the importer never scans for candidates**
- Given a repository containing a `credentials.local.json` that is read on purpose by a committed
  prompt — `docs/prompts/posthog-metrics-report.md` in this repository
- When any `devteam` command runs, including `doctor`, `migrate` and `upgrade`
- Then no command discovers, offers, reads or moves that file
- And importing it requires naming its path explicitly
- And the file is still readable at its original path afterwards

**Scenario: `unset` does not take the value with it**
- Given a registered credential with a stored value
- When `devteam cred unset <key>` runs
- Then the reference is removed from the selected layer
- And the value is still in the backend
- And the output says the value was kept and names the flag that would delete it
- And `devteam cred unset <key> --forget-value` removes both, reporting that it did
- And unsetting a key the layer does not declare reports that, rather than failing

**Scenario: backends are probed, never guessed, and the last resort is loud**
- Given any machine
- When `devteam cred backends` runs
- Then exactly the implemented backends are listed — `keychain`, `dpapi`, `insecure` — each with
  available yes/no and, when no, the reason
- And the chosen default is the first available one, and is `insecure` only when it is the only one
- And no listed backend is unavailable by definition on every platform
- And when a value is stored on `insecure`, `cred set` and `cred import` warn, naming the directory
  and saying it is not encrypted
- And `devteam cred check` and `devteam doctor` report every credential on `insecure`, plus every
  reference with no value stored and every unknown `source`
- And `cred check` reports those findings without raising, so one bad entry does not hide the rest

**Scenario: a keychain write is verified by reading it back**
- Given the macOS keychain backend
- When a value is written
- Then the value is read back and compared before the write is reported successful
- And a mismatch removes the item and fails, naming the ref and not the value
- And a zero exit status from the underlying tool is never treated as proof the value was stored

**Scenario: the guard refuses the obvious spelling of dumping a value store**
- Given a bound project
- When a Bash command would `cat`, `grep`, `jq`, `base64`, `cp`, `curl` or redirect from a
  credential value store — `data/machines/<id>/secrets/`, or any `credentials.local.json` — or would
  look up the `dev-team-agents` keychain namespace outside the resolver
- Then the tool call is blocked with exit code 2 and a reason on stderr
- And the reason names the store *kind* only — never the path, the contents, a value, or the command
  line
- And the reason names `devteam cred get` as the sanctioned read and states that the guard is
  hygiene, not a sandbox
- And a command reading the *reference* layer is warned, not blocked
- And the same command prefixed with `DEVTEAM_CRED_READ_CONFIRMED=1` is allowed through

**Scenario: the guard is explicitly not a boundary**
- Given the same project
- When the same read is spelled with a variable, a quoted split (`c""at`), a base64 decode, a here-doc
  or a python one-liner, or is performed with the `Read`, `Grep` or any MCP tool instead of Bash
- Then it is not blocked, and no criterion in this spec claims it should be
- And the guard's own documentation says so, in the file and in ADR-0010
- And the guard blocks only when a command both names a real store path and carries a verb that
  discloses or copies content — the word "credentials" in a path is never sufficient
- And a `devteam cred …` pipeline segment is exempt, so the migration command itself is never refused

**Scenario: the guard never breaks a tool call it did not mean to block**
- Given any Bash command
- When the guard runs, including when it hits an internal error
- Then it exits 0 on every path except a deliberate refusal
- And a non-Bash tool call returns before any parsing
- And a payload naming none of the guard's trigger words returns before any subprocess is forked
- And a warning is emitted as `additionalContext` and exits 0, never blocking

### Out of Scope
- **The `age`/`sops` encrypted backend** listed in ADR-0010's platform table. Deferred, not built,
  and deliberately absent from `secrets.BACKENDS` rather than present-and-unavailable. It needs a
  passphrase per run and this CLI has no interaction model for one. What would unblock it: a
  passphrase-caching model with a stated lifetime, and a decision about a cold cache in a
  non-interactive run
- **Verifying `dpapi` on real Windows hardware.** It is implemented against the documented Win32
  ctypes pattern and has never been run on Windows. The platform table must not be read as three
  tested backends
- **Any coverage of non-Bash tool calls by the guard.** `Read`, `Grep`, `Glob` and MCP tools are
  invisible to a `PreToolUse` Bash hook, and no criterion above pretends otherwise
- **Scanning record *contents* for secrets.** ADR-0013 records the same limit for the store as a
  whole: the classification is allow-portable-by-default and is not a secrets policy
- **Credential rotation, expiry and shared-secret propagation.** The reference schema has no
  rotation field and nothing reminds anyone
- **Migrating this repository's own root `credentials.local.json`.** It stays in place deliberately as
  the standing proof case for the non-scanning importer; the cost is that its committed reader needs
  the `DEVTEAM_CRED_READ_CONFIRMED=1` prefix
- **Per-key classification of `preferences.json`** and the other gaps ADR-0013 records as remaining

### Dependencies
- **Depends on**: `v3-global-install.md` (the store, the bind, `machine-id`, quarantine, the lock and
  atomic-write helpers), ADR-0010, ADR-0013
- **Blocks**: the desktop app, which needs a place to put the credentials it collects

### Amendment Log
- 2026-09-28 | software-architect | Spec written from the M3 implementation, recording four
  decisions ADR-0010 did not cover: the audit log and the value store are machine-local (ADR-0013's
  inventory classified neither); the `age`/`sops` backend is deferred and absent from `BACKENDS`
  rather than declared-and-unavailable; `cred get` refuses `--json` as a documented exception to the
  `--json` contract; and the keychain adapter verifies its write by read-back because
  `security add-generic-password` exits 0 after a failed double-entry prompt and silently stores an
  empty password. | Writing the spec after the code is the wrong order and is acknowledged as such:
  these are implementation findings, not criteria that were satisfied. They are recorded as criteria
  so the next change to this surface has a boundary to check against, and so the four deliberate
  exceptions — a refused `--json`, an absent backend, an unverified platform, and a guard that is
  explicitly not a boundary — cannot be "fixed" by someone who never saw the reason.

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
