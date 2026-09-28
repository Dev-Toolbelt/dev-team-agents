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

> **Amended by implementation (M3).** Three of the four rows above were built; one was not.
> `scripts/lib/devteam/secrets.py` declares `BACKENDS = ("keychain", "dpapi", "insecure")` and
> nothing else, so the reference schema's `source` field — validated against that same tuple in
> `creds._validate` — can only name a backend that exists.
>
> **The `age`/`sops` row is DEFERRED, not built.** It needs a passphrase per run, and this CLI has
> no interaction model for one: every other backend is non-interactive by construction, and
> `devteam cred get` is called from agent context where there is nobody to prompt. It is
> deliberately **absent** from `BACKENDS` rather than present-and-always-unavailable, because a
> declared surface with no implementation drifts — `cred backends` would list a row that can never
> become `yes`, and a reference file could name a `source` no code path can read. What would
> unblock it: a passphrase-caching model with a stated lifetime (an agent session, not a login
> session), and a decision about what happens when the cache is cold in a non-interactive run.
> Until then, a machine with no keychain and no DPAPI falls to `insecure`, which is loud by design
> in `cred set`, `cred import` and `devteam doctor`.
>
> **`dpapi` is implemented but unverified on real Windows hardware.** It was written against the
> documented Win32 `CryptProtectData`/`CryptUnprotectData` ctypes pattern and has never been
> exercised on a Windows host; the development machine is macOS. Every Windows-only symbol sits
> behind a `platform_key() == "win32"` guard, so importing the module elsewhere cannot fail because
> of it — but the platform table above must not be read as three tested backends. It is one tested
> (`keychain`), one tested trivially (`insecure`), and one written carefully and unrun.
>
> **The keychain adapter verifies its own write, because the exit code lies.**
> `security add-generic-password -w` (as the last option) prompts for the value twice on stdin, and
> returns **0 even when the two entries do not match** — storing an **empty** password silently.
> Observed against a real keychain. `_keychain_put` therefore reads the value back immediately and
> raises (after deleting the item) if it does not match, rather than trusting the return code. The
> same framing is why `secrets._validate_value` rejects a value containing NUL, `\n` or `\r`: those
> characters break the two-line stdin framing and reach the same silent-empty-write path. A
> multi-line secret must be split by the caller; it is refused rather than mangled.
>
> **Where a backend that must keep bytes on disk keeps them: `data/machines/<machine-id>/secrets/`**
> (`paths.secrets_dir()`), machine-local, deliberately **not** beside the portable
> `data/credentials/`. The reference layer is portable *precisely because* it holds no value — and
> that portability makes exporting it routine. A value store adjacent to it would ride along in the
> first archive somebody takes. Keeping the two in different subtrees means the classification does
> the work instead of an author remembering to exclude a directory. `dpapi` writes one
> `<sha256(ref)>.bin` JSON envelope per secret there, through `jsonio.write_json_atomic` so the write
> is atomic and `0600` without a second module-local implementation of either; `insecure` writes one
> `insecure.json`. `keychain` writes nothing to disk at all.

**Access goes through `devteam cred get <key>`**, which resolves the layer (project overrides
global), checks the caller's declared `scope`, prints the value on stdout and nothing else, and
appends an audit line — who, when, which key, **never the value** — to
`data/projects/<project_id>/audit.log`. Agents no longer read a credentials file at all.

> **Amended by implementation (M3) — the audit log moved, and `--json` is refused.**
>
> **Placement.** The log is at `data/machines/<machine-id>/projects/<project_id>/audit.log`, not
> under the portable `data/projects/`, and `audit.log` is listed in `paths.MACHINE_LOCAL_RECORDS`.
> It records reads that happened on *this* machine; two machines appending to one portable log would
> need merge semantics nothing here has, and a trail that silently interleaves two hosts is worse
> than two separate ones. ADR-0013's inventory never classified this record — that gap is closed
> there as well as here. Global-layer reads (no bound project) land under the scope `global`, a
> string that cannot collide with a `project_id` because those are always UUID4.
>
> **Format.** Append-only JSONL, one `json.dumps` per line, written through a single
> `os.write` on a descriptor opened `O_APPEND` at mode `0600`. So a crash mid-write can corrupt at
> most the last line, never an earlier one, and ADR-0013's own guidance — a growing log should be
> append-only so two machines' appends could one day merge instead of colliding — is satisfied by
> the one new growing record this milestone adds. Fields: `ts`, `action`, `key`, `layer`, `agent`,
> `outcome`, and an optional `detail`. Never the value, and **nothing derived from it** — no length,
> no hash, no prefix — because an audit trail that teaches you something about the secret is not an
> audit trail.
>
> **Failures are audited, not only successes.** `creds.get_value` writes a line for
> `not-registered`, `scope-refused` and `value-missing` as well as `ok`; `unset` and `import` audit
> too. A refusal is exactly what the trail exists to surface.
>
> **`devteam cred get` refuses `--json`** — a deliberate, documented exception to the `--json`
> contract in `CLAUDE-md/cli.md` ("stdout then carries exactly one JSON document" with an `ok`
> field). This ADR says the command "prints the value on stdout and nothing else"; wrapping a secret
> in a document puts it into a structure a client is likely to log, tee, or hand to `jq -s` and keep.
> So `cmd_cred_get` raises a usage error (exit 2) when `--json` is given, and writes the value with
> `emitter.raw` — exactly the value plus a newline — otherwise, so `TOKEN="$(devteam cred get …)"`
> needs no parser. `devteam cred list --json` is the machine-readable surface for the references.
> The exception is recorded here rather than left implicit: an undocumented exception to a stated
> contract is worse than either choice, because the next person adds `--json` back.
>
> **The value never reaches argv, in either direction.** `cred set` reads it from stdin —
> `getpass` on a tty, `sys.stdin.read()` otherwise — because a value on a command line is in the
> process table for every other user on the machine and in this one's shell history. The keychain
> backend passes it on stdin for the same reason (`-w` as the last option, not `-w <value>`). The
> `ref` is the only credential-shaped string that ever appears as an argument, and it is opaque.

A `PreToolUse` hook refuses shell commands whose obvious effect is to dump a credential store
(`cat`/`grep`/`jq` over the credential paths, `security find-generic-password` outside the
resolver) and warns on echoing a resolved value.

> **Amended by implementation (M3) — what the guard actually catches, stated so nobody mistakes it
> for a boundary.** `scripts/hooks/pre-tool-use/03-credential-guard.sh` exists and does refuse the
> obvious spelling. Its limits are structural, not a backlog item:
>
> - **It matches command *text*.** `c""at`, the path held in a variable, `base64 -d`, a python
>   one-liner, a here-doc, or any of a hundred other spellings walk straight past it. It cannot be
>   fixed by adding patterns; pattern matching is the wrong instrument for the job, and this ADR
>   never claimed otherwise — "an agent with Bash can read anything the user can read."
> - **It sees only Bash tool calls.** The hook returns immediately unless `tool_name` is `Bash`.
>   `Read`, `Grep`, `Glob` and every MCP tool are invisible to it. An agent that reads a value store
>   with `Read` is not refused, not warned, and not audited.
> - **Recall is low by construction, on purpose.** A command is acted on only when it *both* names a
>   real credential-store path (or the `dev-team-agents` keychain namespace) *and* carries a verb
>   that discloses or copies content. The word "credentials" in a path is never enough. The reason is
>   the failure mode that matters: one false positive on a developer's own `grep -r` and the hook
>   gets deleted, after which it buys nothing at all.
> - **`devteam cred …` segments are exempt**, because `cred import <file>` cannot be spelled any
>   other way. Segments are judged separately, so `devteam cred list ; cat <secrets>` is still
>   caught — but `devteam cred list "$(cat <secrets>)"` is not caught at all. Knowingly traded: a
>   bypass costs a bypass that a dozen other spellings already had, whereas a false positive on the
>   one command that migrates a plaintext credential file onto the audited path is what gets the
>   whole hook removed.
> - **There is an escape hatch**, `DEVTEAM_CRED_READ_CONFIRMED=1` as a command prefix, mirroring
>   `02c-full-suite-guard.sh`'s. It exists because the guard cannot tell a deliberate, user-requested
>   inspection from an unprompted one, and an in-band opt-out for one command is strictly better than
>   the alternative a blocked user reaches for, which is deleting the hook.
>
> What it buys is narrow and still worth having: a loud, attributable stop on the spelling an agent
> reaches for by default, and a pointer at the one read path that audits itself. Nothing more.
>
> **A real consequence, and it is not hypothetical.** `docs/prompts/posthog-metrics-report.md` reads
> this repository's root `credentials.local.json` on purpose — the file this ADR names as the proof
> case for why the importer never scans for candidates. That file is still deliberately in place, and
> `credentials.local.json` is matched by basename as a value store, so the prompt's own read is now
> **refused** unless reissued with the `DEVTEAM_CRED_READ_CONFIRMED=1` prefix. The guard is right to
> refuse it — the read genuinely is unaudited — and the prompt is right to exist. This is the cost of
> a guard whose precision is deliberately high: the one legitimate unmigrated reader in the
> repository pays a prefix. Migrating it with `devteam cred import` would remove the prefix and put
> the read on the audited path; it has not been done, because that file is also the standing proof
> that a scanning importer would have broken somebody's working setup.
>
> The guard also carries a documented, narrow exception to the "exit 0 in all normal paths" rule in
> `CLAUDE-md/hooks.md` — the second one, alongside `02c-full-suite-guard.sh`: a refusal exits 2 so
> the dispatcher blocks the tool call. Every other path, including every internal error, exits 0,
> enforced by an `EXIT` trap rather than by discipline, because a hook that breaks the user's tool
> call is worse than one that misses.

**Migration** is `devteam cred import`: read the existing `credentials.local.json`, push each
value into the keychain, rewrite the file as references, and **move** the original into
`data/quarantine/<date>/` — never delete it, per the No-Destruction Rule. Import is opt-in per
file and never scans the tree for candidates, which is how the root-level file this repository
uses on purpose stays untouched.

> **Amended by implementation (M3) — the ordering is copy → verify → retire, and it rolls back.**
> `creds.import_file` pushes every value into a backend **and reads each one back** before the
> reference file is touched or the original is moved. If any value fails to store or fails to verify,
> everything this import already pushed is deleted again and the original file is left exactly where
> it was — the same ordering `upgrade.py` uses, for the same reason: a half-migrated credential set
> with the plaintext original already retired is unrecoverable by the user.
>
> Three details the original text left open: the importer takes an explicit **path argument** and has
> no scanning code path at all, so "never scans" is a property of the surface rather than a promise
> about a default. `work_feedback_active` and `work_feedback_interval_minutes`
> (`creds.NON_SECRET_KEYS`) are carried over verbatim into the reference file instead of being pushed
> through a backend, which is what the Neutral consequence below anticipated. And the original is
> retired through `quarantine.move` under the group `credentials-import`, which is the same
> No-Destruction path everything else in the store uses — note that this deposits a plaintext
> credential file into `data/quarantine/`, which is exactly why ADR-0013 classifies that directory as
> never part of a default export.
>
> **A reference file cannot hold a value, and the refusal is explicit rather than incidental.**
> `creds._ALLOWED_ENTRY_FIELDS` is a closed set — `purpose`, `source`, `ref`, `scope` — and any other
> field is rejected on read, with a distinct error for the ones that look like they carry a secret
> (`value`, `token`, `password`, `api_key`, …). Every payload the module returns is built by naming
> those fields explicitly (`creds._public_view`), never by copying an entry and popping keys, so a
> value-shaped field added to the schema later cannot leak through a code path that forgot to strip
> it. Closed-set validation plus explicit construction, because either alone fails open eventually.

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

## Risks

Added by implementation (M3) — the ADR skill requires this section and the original omitted it.
Every row is a condition that exists in the shipped code, not a hypothetical.

| Risk | Mitigation | Residual |
|------|-----------|----------|
| **The design is read as a security boundary.** `scope`, the audit log and the PreToolUse guard all *look* like access control, and the next reader will build on whichever one they saw first. | The limitation is stated in this ADR, restated in `creds.get_value`'s own scope-refusal hint, in the module docstrings of `creds.py` and `secrets.py`, and in a `WHAT THIS IS NOT` banner at the top of the guard. The guard's refusal message itself says it is "telling you the read is unaudited, not that it is impossible." | Nothing enforces it. An agent with `Bash`, or with `Read`, resolves any value the user can resolve, and no artifact here prevents that. The only real mitigations stay the ones in the Decision: out of git, out of the transcript, scoped narrowly, short-lived, separated per project. |
| **A value goes to the `insecure` backend and is treated as equivalent to the other two.** It is a mode-0600 JSON file — readable by anything running as this user, not encrypted. | `secrets.default_backend()` returns `insecure` only when it is the sole available backend; `put` marks the result `insecure: True`; `cred set` and `cred import` emit a warning naming the directory; `creds.check` reports every such entry and `devteam doctor` raises it. Loud on four surfaces. | A user who dismisses four warnings has plaintext secrets on disk. There is no mode in which the CLI refuses to work rather than degrading, and adding one would block the platform this fallback exists for. |
| **`dpapi` is unexercised on Windows.** A defect there is a credential store that either cannot be written or cannot be read back, on the platform with no second option. | Every entry point is guarded by `platform_key() == "win32"`, so the code cannot break the other platforms; `put` verifies through the same `jsonio` atomic write everything else uses; a failure surfaces as a `SecretError` naming the ref and the backend, never the value. | Unknown until someone runs it. The honest fallback on a broken DPAPI path is `insecure`, chosen by the probe — which means the failure mode is silent degradation to plaintext rather than a stop. Worth a real-hardware run before this is described as supported. |
| **A keychain prompt blocks a non-interactive run.** An agent invoking `cred get` on a locked keychain has nobody to answer the dialog. | `security` is invoked with a 10s command timeout and a 5s probe timeout; the resulting `SecretError` says the keychain may be locked and to run it once from an interactive terminal. It fails with an actionable message instead of hanging, which is what the Negative consequence below asks for. | A 10s stall per attempt, and the run still fails. There is no pre-flight "is the keychain unlocked" check, and `list-keychains` succeeding does not imply an item can be read. |
| **The guard refuses a legitimate read and gets deleted.** A disabled hook buys nothing; this is the failure the guard's whole design is bent around. | Precision over recall by construction: both a real store path and a disclosing verb are required, judged per pipeline segment, with `devteam cred …` exempt and `DEVTEAM_CRED_READ_CONFIRMED=1` available in-band. | The one known false-positive-shaped case is real and unresolved: this repository's own `docs/prompts/posthog-metrics-report.md` now needs the prefix. A user who finds the prefix annoying rather than informative still has a hook to delete. |
| **An agent reads a value and reproduces it** — in its reply, a log, a commit, or a file. | The audit log never carries the value; `cred get` writes it to stdout and nothing else and refuses `--json`; the guard warns when `devteam cred get` is piped into `echo`/`printf`/`tee`/`curl`/`wget`/`logger`; the guard's own messages name only the store *kind*, never the path, the contents or the command line. | Nothing observes what the agent writes. A value read into a shell variable and interpolated into a commit message is not detectable by any mechanism here. |
| **A hand-edited reference file smuggles a value in.** The files are editable by design — that is the point of making "which credentials?" reviewable. | `creds._validate` rejects any field outside the closed set on every read, with a specific error for value-shaped names, and `_public_view` never copies an entry. | Validation runs when the CLI reads the file. A value sitting in a field under an unlisted *key* name still reaches `git`-adjacent tooling before the CLI next reads it, and the reference layer is portable, so it would travel in an export. The classification is not a secrets scanner and is not proposed as one — ADR-0013 records the same limit for the store as a whole. |

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep the plaintext JSON, just centralise it in the store | Least work, but the secret stays in cleartext on disk and nothing is gained except deduplication. |
| Encrypted file only (`age`/`sops`), no keychain | One identical path on all platforms and no OS adapters, but requires the tool installed and a passphrase on every agent run that needs a credential. |
| Environment variables only | Nothing at rest, but they leak into process listings and child processes, and there is nowhere to record purpose, scope or rotation. |
| Delete the v2 file after import | Violates the No-Destruction Rule, and this repository is the proof case: its root-level credential file is read on purpose by a committed prompt. |

Added by implementation (M3) — options that only became real once there was code:

| Alternative | Why rejected |
|-------------|-------------|
| Honour `--json` on `cred get`, wrapping the value in the standard `{ok, …}` document | Uniformity is worth a lot and this is the one place it costs more than it buys. A JSON document is something a caller pipes to `jq`, tees to a file, or logs wholesale as a tool result — all three put the secret somewhere it outlives the command. Refusing with a usage error that names `cred list --json` costs one error message; honouring it costs a leak that looks like correct usage. Recorded as an exception rather than left implicit, because the next contributor would otherwise "fix" the gap. |
| Declare `age`/`sops` in `BACKENDS` and have it report itself unavailable | It reads as the tidier shape — the surface matches this ADR's table — but an unavailable-by-definition row means `cred backends` lists something that can never become `yes`, and `creds._validate` would accept a `source` no code path can read, so a hand-edited or imported reference could name it and fail only at read time. A name that exists and never works is worse than a name that does not exist. |
| Have `unset` always delete the value with the reference | The obvious default, and wrong: a `ref` can be pointed at by another reference (or reused after a rename), so deleting the value on every `unset` makes an accidental removal unrecoverable. `unset` removes the reference and keeps the value unless `--forget-value` is passed, and says so in its output. The recoverable direction is the default. |
| Audit only successful reads | Halves the log and loses the half worth having. A scope refusal, a missing value and a read of an unregistered key are precisely the events an audit trail exists to surface; a trail of successes only proves that whatever went wrong left no trace. |
