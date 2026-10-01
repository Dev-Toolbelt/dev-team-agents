# ADR-0024: The local credentials file lives at the `.dev-team-agents/` root, and the app edits it through the CLI

**Date:** 2026-10-01
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

`credentials.local.json` is the plaintext file agents read for staging and production access
(`skills/shared/credentials/SKILL.md`). It had three homes depending on the project's history:
`.dev-team-agents/user-data/` on layout 1, `data/machines/<machine-id>/projects/<id>/` in the store on
layout 2 ([ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md)), and the
**project's own root** on very old v2 installs, which `install.sh` moved *into* `user-data/`.

That spread produced a user-visible bug. `devteam upgrade` moved the real file into the store and
quarantined `user-data/`; the agent-facing skills kept reading the fixed `user-data/` path, found
nothing, and the setup health check "repaired" it by writing a blank template there. The user saw
their credentials vanish and an empty file appear. Four hand-maintained copies of that template had
also drifted (one lacked the `work_feedback_*` keys).

Separately, editing the file meant opening it by hand. The desktop app is the natural place for a
form, but it is a pure CLI client that never reads project files
([ADR-0015](0015-the-desktop-app-s-stack-and-its-operating-rules-as-a-cli-client.md)), and its tests
assert it never runs a `cred` command, because `cred get` prints a secret value
([ADR-0010](0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md)).

## Decision

### 1. One location on every layout

The file lives at **`.dev-team-agents/credentials.local.json`** on layout 1 and layout 2. It stays a
machine-local record (`paths.MACHINE_LOCAL_RECORDS`): never exported, never committed, never synced —
but its home is the project tree, ignored by git, not the store. `upgrade` no longer moves it into
the store.

**Every linked git worktree shares the main checkout's file.** The path is resolved from git's
common dir by `project.main_checkout()`, keeping a monorepo subproject's offset (`repo-wt/apps/x`
resolves to `repo/apps/x`), with inherited `GIT_DIR`-style variables dropped. Outside git, the
project root is used as is.

Both editing paths are first-class and operate on the same file: a developer may edit it by hand,
and the app edits it through the CLI. There is never a second copy.

### 2. Relocation is byte-for-byte and never destructive

`credentials_local.relocate(project_root)` brings a legacy copy (`user-data/`, or the store's
machine-local project folder) to the root without parsing or rewriting it, and sets mode `0600`.
It runs from `devteam doctor`, `sync` (and therefore every update through `sync --all`), `migrate`
and `upgrade`, under the `credentials-local` store lock, and is idempotent. Each command reports
the outcome in an additive `credentials_local` key of its `--json` output
(`{path, changed, moved, quarantined, conflicts}`).

| State | Outcome |
|-------|---------|
| Root absent, one legacy copy | Move it to the root |
| Root present, legacy copy byte-identical | Legacy copy → quarantine |
| Root present, legacy copy equals the blank default template | Legacy copy → quarantine |
| Root equals the blank template, legacy copy has content | Root → quarantine, legacy copy → root |
| Both have different, non-blank content | Touch nothing; `doctor` reports a conflict |

"Blank template" means a copy that parses to exactly the canonical template. Quarantine follows
the No-Destruction Rule (`skills/shared/setup-health-check/SKILL.md`); nothing is deleted.

Guards around the table:

- **Ignored before placed.** The target is unioned into the machine-local
  `$GIT_COMMON_DIR/info/exclude` managed block and checked with `git check-ignore` before anything
  moves; a target git would still track (a negation line) refuses the move. `doctor` and `upgrade`
  do not rewrite the committed `.gitignore` block, so a pinned or older-bound project still gets this.
- **Never through a link.** Candidates are checked with `lstat`; a symlinked legacy copy or root is
  reported as a conflict with reason `symlink` and never read, moved or chmod-ed. A
  `.dev-team-agents` that is itself a symlink, or resolves outside the project, is refused.
- **No clobber.** The move is a hard link plus unlink (copy + verify only across filesystems), so a
  file that appears at the root meanwhile is evaluated, never overwritten.
- **Store copy only when it is this project's.** The store candidate is considered only when the
  registry binds the `project_id` to this checkout: the id comes from a committed file anyone can
  copy.
- **The project's own root is never scanned.** A `credentials.local.json` there stays where it is
  (v3-credentials spec, "the importer never scans for candidates"). Only the v2 `install.sh` moves
  one, as it did before.
- **`upgrade` refuses on a conflict** before copying or quarantining anything, so the conflicting
  copy is never swept into quarantine with `user-data/`.

`install.sh` (v2) carries the file across its tree swap and moves a `user-data/` or project-root
copy to the new path only when the target is absent, after its `.gitignore` lines are written; it
has no blank-template rule, and `devteam doctor` settles whatever it leaves behind.

### 3. Nothing creates the file implicitly

The canonical template is `scripts/lib/credentials-local-template.json`, the only copy of its
content; documentation points at `devteam cred local init` instead of reproducing it. The file is
created only by an explicit action: `devteam cred local init` or the app's *Create file* button.
`install.sh` and the setup health check no longer create it. With no file, consumers use their
documented defaults (work feedback: active, 5 minutes).

### 4. The managed `.gitignore` block ignores it on both layouts

The bind-managed block carries `.dev-team-agents/credentials.local.json` and
`.dev-team-agents/credentials.local.json.*` (atomic-write temp files) on layout 1 and 2. The
credential guard hook already treats the basename as a secret at any path.

### 5. `devteam cred local` is the app's only window onto the file

| Command | Behaviour | `--json` shape |
|---------|-----------|----------------|
| `cred local show` | Reads the file; never prints a secret value | `{path, exists, valid, error, hash, data, unknown_paths}` |
| `cred local init` | Writes the canonical template; refuses if the file exists | same as `show` |
| `cred local patch --expect-hash H` | Reads `[{op:"set"\|"unset", pointer, value?}]` from **stdin**, applies all ops atomically, refuses on hash mismatch or invalid JSON | same as `show` |

- `error` is `null` or `{message, line, column}` when `valid` is false; `data` is then `null`.
- `hash` is an HMAC-SHA256 of the raw bytes keyed with a random machine-local key
  (`data/machines/<id>/.credentials-local-token-key`, mode `0600`). A plain digest would let anyone
  holding a `show` output rebuild every byte but the secrets and test guesses offline. `patch`
  refuses with a conflict when the file changed since it was read, so a hand edit is never
  overwritten by a stale form.
- Refusals name themselves in `details.reason`: `exists` (`init` on an existing file) and
  `hash-conflict` (`patch` on a moved file). A lock timeout carries no reason, so the app never
  mistakes it for either.
- **Redaction is default-deny.** `data` returns a value only for the two `work_feedback_*` keys
  (when they hold a bool and an int), the `agents` string arrays, and scalar leaves named in the
  explicit `SAFE_LEAF_NAMES` constant (`user`, `host`, `privateKeyPath`, `path`, `type`, `port`,
  `database`, `username`, `appUrl`; a test pins it against the template, so a new template leaf
  stays hidden until it is added on purpose) - and not even those when the key looks secret-ish
  (`pass`, `secret`, `token`, `credential`, `auth`, `dsn`, `apiKey`, `privateKey`) or the value does:
  URL userinfo (`user:pw@`), a URL with a query or fragment, or pasted key material
  (`-----BEGIN`). Every other scalar,
  including every leaf of an unknown or free-form object, is replaced by `{"secret": true, "set":
  <non-empty>}`; structure keys stay. A `set` op on any pointer takes its value from stdin like
  every other op; argv never carries a value.
- `patch` preserves every key it does not touch, including keys unknown to the template, and writes
  two-space-indented JSON with a trailing newline, mode `0600`, atomically.
- `unknown_paths` lists JSON pointers outside the template's known shape so the app can show them
  read-only.

`cred get` stays forbidden to the app. The app's allowlist widens to exactly these three leaves.

## Consequences

- One path for agents, hooks, skills and the app; the blank-file bug cannot recur because no
  automatic flow creates the file.
- ADR-0013 is amended for this one record: machine-local by classification, project tree by location.
- ADR-0015 / ADR-0010 are amended: the app runs `cred local {show,init,patch}` and nothing else under
  `cred`; no output path carries a secret value.
- The plaintext file remains plaintext. On layout 2 it moves from the store (`0700` directories,
  outside any project) into the project tree, where `.gitignore` does not protect it from a Docker
  build context without a `.dockerignore`, a synced folder or a zipped project. Layout 1 already had
  that exposure.
- `devteam cred import` retires string values into the OS secret store; it does not yet accept this
  file's nested `devops`/`app` objects, so for the template's shape the file stays the store.
