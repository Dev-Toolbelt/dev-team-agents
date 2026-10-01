# v3 — Global Store, Project Bind and the `devteam` CLI

Companion to [`CLAUDE.md`](../CLAUDE.md). Decisions behind this layout:
[ADR-0007](../docs/development/adrs/0007-global-core-and-data-store-replacing-per-project-vendored-install.md)
(store split), [ADR-0008](../docs/development/adrs/0008-project-identity-via-committed-project-json-and-three-personal-preference-layers.md)
(identity and preference layers), [ADR-0009](../docs/development/adrs/0009-python3-as-the-devteam-cli-runtime-while-hooks-stay-bash.md)
(python3 CLI),
[ADR-0014](../docs/development/adrs/0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md)
(store schemas as the normative write gate, and the `json_contract` deprecation policy).
Acceptance criteria: [`docs/specs/v3-global-install.md`](../docs/specs/v3-global-install.md).

**Milestone status.** M1 (store, CLI, identity, bind, versions/pin, migration), M2 (preference
cascade, memory relocation behind a consented upgrade, `context_paths`, store portability), M2.1
(the portable/machine-local store split, [ADR-0013](../docs/development/adrs/0013-portable-and-machine-local-split-of-the-data-store.md))
and M3 (credentials — see § Credentials, [ADR-0010](../docs/development/adrs/0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md))
are implemented. **M4 is partially done:** `devteam catalog`, the `compat` block in `version --json`,
the `--json` contract test sweep, and the client write gate (§ The client write gate) are in place.
The desktop app, signed release channels (Homebrew, winget), and full M4 are not yet available. The v2
`install.sh` path keeps working for one deprecation cycle.

---

## The two stores

| Store | Holds | Lifetime |
|-------|-------|----------|
| **core** | `versions/<X.Y.Z>/` (agents, commands, skills, scripts, templates) + the `current` pointer | Disposable — an uninstall may remove it, `devteam update` rebuilds it |
| **data** | `machine-id`, `preferences.json`, `credentials/` (references only), `integrations/` (account config), `projects/<project_id>/`, `quarantine/`, `machines/<machine-id>/` (registry, locks, per-project state, `secrets/`, `audit.log`) | Survives uninstall; on Windows it is in the roaming profile, so profile backup covers it |

```
macOS    core  ~/Library/Application Support/dev-team-agents/core
         data  ~/Library/Application Support/dev-team-agents/data
         cache ~/Library/Caches/dev-team-agents
Windows  core  %LOCALAPPDATA%\dev-team-agents\core        data  %APPDATA%\dev-team-agents\data
Linux    core  $XDG_DATA_HOME/dev-team-agents/core        data  $XDG_DATA_HOME/dev-team-agents/data
         cache $XDG_CACHE_HOME/dev-team-agents
```

`$DEVTEAM_HOME` overrides all of it (`<home>/core`, `<home>/data`, `<home>/cache`) and is the seam
the test suite uses — no test touches a real user directory.

**`core/current` is a plain text file, not a symlink.** A symlink there would put the Windows
materialisation failure at the most load-bearing path in the design.

### `data/` is split by what a record says ([ADR-0013](../docs/development/adrs/0013-portable-and-machine-local-split-of-the-data-store.md))

```
data/machine-id                                    this machine's UUID, created once
data/preferences.json                              PORTABLE — the global preference layer
data/projects/<project_id>/preferences.json        PORTABLE — the project preference layer
data/projects/<project_id>/session-summary.md      PORTABLE — the user's own memory
data/credentials/                                  PORTABLE — references only, no values
data/integrations/<name>.json                      PORTABLE — integration account config, no token
data/quarantine/<date>/<project_id>/               PORTABLE
data/machines/<machine-id>/registry.json           MACHINE-LOCAL — absolute paths
data/machines/<machine-id>/locks/                  MACHINE-LOCAL — a lock names a pid
data/machines/<machine-id>/projects/<id>/…         MACHINE-LOCAL — bind-manifest.json, state.json,
                                                   and the dot-markers (caches, ETags, day stamps)
```

**Portable = what the user authored or decided. Machine-local = what this machine observed or
built.** `paths.is_machine_local_record(name)` is the single answer to which side a per-project
record belongs on — dot-prefixed names are machine-local as a class, and so are `state.json`,
`bind-manifest.json`, `telemetry-queue.json`, `audit.log` (this machine's own reads, and a growing
record that two machines appending to would need merge semantics for), and the notification queue
`notifications.jsonl` with its `notifications-seen.json` (what this machine's hooks noticed and this
machine's app has shown), the `task-board/` directory of per-session task-board records (ADR-0018:
what this machine's agent sessions planned), and `integrations-status.json` (the last connection test of each GitHub/Jira integration, from this machine). `credentials.local.json` is machine-local by classification but lives in the project tree at `.dev-team-agents/credentials.local.json`, never in the store (ADR-0024). Never re-derive that rule at a call site.

`devteam export` archives the portable subtree by default (excludes `machine-id`, `machines/`,
`locks/`, `quarantine/`, and every machine-local record at any depth); `--all` includes the
machine subtree for a full-machine backup. Default destination is `$cache/exports/<stamp>.tar.gz`
with mode `0600` (owner-only). A portable archive restored elsewhere is completed with
`devteam bind` per project — the committed `project.json` reconnects it to its memory, and the
registry and manifests are rebuilt locally. An import that carries no machine subtree keeps the
receiving machine's own `machine-id` and `machines/`, or every bound project there would read as
unbound. `devteam import` strips the consent keys (`telemetry`, `auto_update`) from any incoming
`preferences.json`.

`store.adopt_machine_layout()` relocates a store written before the split, once, from `cli.main`
before any command reads the registry. **No synchronisation exists or is implied** — the split is
what makes one possible later.

## What a bound project contains

```
<project>/.dev-team-agents/project.json   COMMITTED — schema, project_id, layout, context_paths
<project>/.dev-team-agents/scripts        link to the resolved version's scripts/ (a copy in copy mode)
<project>/.dev-team-agents/templates      link to the resolved version's templates/ (a copy in copy mode)
<project>/.dev-team-agents/resolved/      generated: preferences.json (the cascade's projection)
<project>/.dev-team-agents/state-dir      generated: one line, absolute path of the machine-local state directory
<project>/.dev-team-agents/memory-dir     generated: one line, absolute path of the portable memory directory
<project>/.dev-team-agents/user-data/     project memory — layout 1 only; gone after `devteam upgrade`
<project>/.claude/settings.json           hook dispatchers, merged — project-owned, committed
<project>/.claude/… .opencode/… .codex/…  bind artifacts — excluded, regenerated by sync
```

**The `scripts` and `templates` links are what make project-relative framework paths work.** The
framework's own text names 138 of them (`.dev-team-agents/scripts/new-adr.sh`,
`…/templates/plan-template.md`, the reuse and design-token lints the Stop hook runs); the links sit
at exactly that path, so nothing is rewritten and `settings.json`'s hook path is the one a v2 install
used. Only these two trees: nothing shipped reads agents, commands or skills through
`.dev-team-agents/` — Claude Code finds those under `.claude/`. They replaced a single `core`
pointer to the whole version, which put every reference one directory too deep; `sync` retires a
leftover `core` and rewrites `core/scripts/hooks` entries in place. `tests/test_runtime_links.py`
binds this repository's real tree and fails on any cited path that does not resolve. A real
directory at either path is a v2 tree: `bind` and `sync` refuse with exit 4 and point at `migrate`.
The v2 tools that now resolve there (`update.sh`, `rollback.sh`, `fix-symlinks.sh`) refuse to run
in a bound project (`scripts/lib/bound-project-guard.sh`) and name the `devteam` command instead.

**The bind registers the hook dispatchers** (`SessionStart`, `Stop`, `PreCompact`,
`PreToolUse`, `PostToolUse`, `SessionEnd`, `UserPromptSubmit`, and `PostToolUseFailure` for a failed
subagent launch) by merging into the project's own `.claude/settings.json`; a stale v2 path is
rewritten in place rather than duplicated, and `unbind` removes only those entries. Without them
the session banner, session-summary enforcement, orphan-skill scan, agent lint and ADR-gap check
do not run in that project at all.

**Files the installers merge into** — `.claude/settings.json`, `.codex/hooks.json`,
`.opencode/opencode.json`, `AGENTS.md` — belong to the project. They are never ignored; the project
commits them, and `unbind` removes only the entries the framework marked (`settings`, `codex-hooks`).

**Every provider's artifacts are files, never the directory that holds them** (ADR-0022). The
project's own agents, commands and skills sit beside them in `.claude/`, `.opencode/` and `.codex/`
and are not claimed, excluded or retired. opencode and Codex artifacts come from their installers,
which answer `--list-targets`; `bind`'s preflight refuses a project-owned path at any target with
exit 4 before the first write, the same as for Claude. A manifest from before ADR-0022 records whole
directories: the next `sync` or `unbind` expands each to the installer's targets under it and never
retires the directory.

Bind artifacts cannot be committed: they carry an absolute path into one developer's store. They are
excluded through **`.git/info/exclude`**, which is local to the clone — a bind links one entry per
skill (152 today), and writing those into a shared `.gitignore` would add ~155 generated lines to a
product repository. `.gitignore` gets only the short project-level block (memory, resolved
preferences, markers, `.worktrees/`), between managed markers.

## Bind modes

| Mode | Artifacts | Default where | Notes |
|------|-----------|---------------|-------|
| `link` | symlinks into `core/versions/<v>` | macOS, Linux | `devteam update` re-points every project at once |
| `copy` | real copies, refreshed by `sync` | Windows without native symlink support | Recorded in `registry.json`, so the fallback is never silent |
| `vendored` | full tree in the project, relative links — v2 behaviour | opt-in | CI, containers, air-gapped, repos that must ship the harness |

**Every mode serves every provider** (Provider Parity Rule). In `vendored` mode the opencode and
Codex installers run too: their agents, command skills, plugin and `.codex/hooks.json` are regular
files, their skills link is relative (`../../.dev-team-agents/skills`), and every hook path points into
the vendored `scripts/`, so the whole tree resolves on any clone. A project-owned path at any
provider target is refused in every mode; vendored re-vendors (quarantines) only its own trees under
`.dev-team-agents/`.

`auto` probes for symlink support rather than guessing from the platform name. An explicit
`--mode=link` on a filesystem that cannot do it **fails** instead of silently downgrading.

**`link` is the mode to recommend a user** — it is the only one where a `devteam update` to the
store reaches every bound project with no further action. `copy` and `vendored` both need an
explicit `devteam sync` (per project) after each update to pick up the change; a user on one of
those modes who skips that step keeps running the version they bound at. This is a recommendation
for a human choosing among the four, not a change to the CLI's own default: `--mode` still
defaults to `auto`, and `auto` already resolves to `link` on any filesystem that supports it — a
plain `devteam bind` on macOS or Linux gets the recommended behaviour without the caller having to
know that. Only a caller for whom `link` is not viable (Windows without symlink privilege, or a
project that intentionally wants `vendored`) has a reason to override it. The app's bind dialog
mirrors this: it pre-selects `link` and labels it recommended, but a user can still choose another
mode.

## Commands

| Command | Does |
|---------|------|
| `devteam path` | Resolved store locations |
| `devteam version` | Installed versions and the active one |
| `devteam catalog` | Read-only browse — counts, and per-kind listings; see § Catalog below |
| `devteam skills list \| show <name> \| install --source <dir\|zip> \| remove <name>` | The providers' **global** (user-level) skills — Claude, Codex, opencode; see § Global skills below |
| `devteam store list \| install --from <tree> \| use <v> \| gc [--apply]` | Manage the versioned core; `gc` previews by default and never removes `current` or a pinned version |
| `devteam bind [path] [--provider …] [--mode …] [--pin <v>]` | Bind a project; idempotent. **Refuses a v2 vendored install with exit 4** and points at `migrate` — binding over one left the vendored tree tracked in git. `--mode vendored` is exempt, and `sync` never refuses: the check is in the command, not in `bind()`. A **pre-v2.1.0 install at `.claude/dev-team-agents/`** is refused in every mode and pointed at `migrate`. Every collision is checked before the first write, so a refused bind leaves no `project.json` and no `.dev-team-agents/` |
| `devteam unbind [path]` | Remove artifacts, keeping `project.json` and `user-data/` |
| `devteam list` | Bound projects, mode, resolved version, pin drift; each record also carries `preferences` — `{auto_update, worktree_active, suppress_notifications}` resolved for that project (`bool`; `suppress_notifications` is `bool` or a list of muted types), each `null` when the version does not resolve or the layer is unreadable, never a guess. Additive: the app's Projects table reads it instead of one `prefs list` per row |
| `devteam sync [path] [--all]` | Rebuild artifacts from the store |
| `devteam pin <v> \| --release` | Hold a project on a version, or return it to `current`. `<v>` (like `bind --pin`) must be a plain version name (`2.48.0`, optional `v` and `-`/`+` suffix) — anything else exits 2; a bad pin already in the registry is an environment error (exit 3) that `doctor` reports |
| `devteam update [--ref vX.Y.Z] [--check]` | Fetch a release, activate it, sync every unpinned project |
| `devteam migrate [path] [--apply [--untrack]]` | v2 install → bind, in either shape: `root` (vendored at `.dev-team-agents/`) or `pre-root` (at `.claude/dev-team-agents/`, before v2.1.0 — its memory moves to `.dev-team-agents/user-data/`, its `.claude/docs/` stays and joins `context_paths`, its hook entries and links are replaced). Previews unless `--apply`. An unregistered `project.json` (left by a refused bind) is adopted. Reports the paths git still tracks — `git_tracked` (the vendored trees, and memory) and `git_tracked_artifacts` (committed links a bind replaced) — and with `--untrack` runs `git rm -r --cached` on exactly those: the index only, never the working tree, nothing committed (`untracked`, `untrack_problem`). The one command that runs git on the user's repository, and only when asked (ADR-0015 amendment) |
| `devteam prefs list \| get <key> \| set <key> <value> [--scope project] \| unset <key>` | Read and write the preference layers; `list` names the layer each value came from |
| `devteam plugin list \| show <name> \| enable <name> [--force] \| disable <name> \| config get <name> [<key>] \| config set <name> <key> <value> \| config unset <name> <key> \| run <name> <action>` | Manage plugins; see § Plugins below |
| `devteam integration list \| show <name> \| connect <name> [--field k=v]… \| test <name> \| disconnect <name> [--keep-token] \| config get <name> [<key>] \| config set <name> <key> <value> \| config unset <name> <key> \| resources <name> <kind>` | Account-level GitHub and Jira connections; see § Integrations below |
| `devteam cred list \| get <key> \| set <key> \| unset <key> \| import <file> \| check \| backends` | Manage credential references and values; see § Credentials below |
| `devteam cred local show \| init \| patch --expect-hash <H>` | Manage `.dev-team-agents/credentials.local.json` for agents and the app; see § Local Credentials File below |
| `devteam upgrade [path] [--apply]` | Move this project's memory into the store. Previews unless `--apply`; **nothing moves on any other command** |
| `devteam export [--to <path>] [--all]` / `devteam import <archive> [--force]` | Move the data store to another machine; portable by default, `--all` includes this machine's registry and manifests |
| `devteam uninstall [--purge --yes]` | Remove the core; `--purge` also deletes the data store and needs `--yes` |
| `devteam notifications list [--project <id>] [--unseen]` | Live notifications across bound projects: what the hooks queued (`scripts/hooks/lib/notify.sh`), minus the expired, each with `seen` (ADR-0017) |
| `devteam notifications ack <id>… \| --all [--project <id>]` | Mark notifications seen. Writes `notifications-seen.json` under a lock; **never rewrites the queue** a hook may be appending to |
| `devteam notifications watch [--interval <s>]` | Stream the unseen backlog, then each new record, until stdin closes or SIGTERM. `--json` is JSON Lines — see § The `--json` contract |
| `devteam tasks record --project-root <dir> [--provider auto]` | **Hook-only.** Reads a hook payload on stdin and folds a todo-tool call, or an agent spawn/result (docs/specs/task-board.md § Agent spawns are tasks), into its session's record; prints `{recorded, session, all_done, became_all_done}`. Never fails on bad input — exit 0 with `recorded: false` (ADR-0018) |
| `devteam tasks mark --project-root <dir> --state idle\|ended` | **Hook-only.** Marks the payload's session idle or ended; no-op without a record. Prints `{marked, open, review_result, review_window, review_findings, became_all_done}` — on `idle` it also settles a command/prompt review window from the turn's final message |
| `devteam tasks review-open --project-root <dir>` | **Hook-only.** Reads a review trigger on stdin (a review/QA agent spawn, a review command or an explicit request in a prompt) and opens or joins the session's review window. Prints `{recorded, session, window, joined}`. Never fails on bad input |
| `devteam tasks review-result --project-root <dir>` | **Hook-only.** Reads a finished review agent's output on stdin, sums its `<!-- review-result: findings=N -->` markers and records the window's result once every source answered. Prints `{recorded, session, window, result, findings, resolved, all_done, became_all_done}` |
| `devteam tasks list [--project <id>…] [--since <epoch>] [--stale-after S] [--ended-after S]` | The task board: every bound project with ≥ 1 task, sessions, tasks and derived state; see § Task board below |
| `devteam tasks watch [same filters] [--interval <s>]` | Stream `snapshot` events per changed project, then `ready`, `heartbeat`, `end`. `--json` is JSON Lines |
| `devteam doctor [path] [--reassign-identity]` | Diagnose store and bind; reconcile a moved project; report a stale layout, a v2 tree left behind by a bind, and machine-local bind artifacts git still tracks (`bind.MACHINE_LOCAL_KINDS` — `settings` is exempt, it is the project's own file). The same allowlist decides what `bind` writes into `.git/info/exclude`, so `.claude/settings.json` is never hidden from `git add` |

## The `--json` contract

`--json` is accepted before or after the subcommand. stdout then carries exactly one JSON document
with an `ok` field; human text is suppressed and warnings stay on stderr. This is **public API**
defined in [ADR-0011](../docs/development/adrs/0011-two-distribution-channels-and-the-desktop-app-as-a-cli-client.md) —
the desktop app is a client of the CLI, so an output shape change is a breaking change. The contract
is swept across every subcommand by `tests/test_json_contract.py`, which discovers commands from the
real parser rather than a hardcoded list, ensuring new or changed commands are caught before release.

| Exit | Meaning |
|------|---------|
| 0 | success (`plugin run` with `ok: false` in JSON still exits 0) |
| 1 | findings — ran and reported a problem it did not fix |
| 2 | usage error (bad arguments, unknown subcommand, bad plugin name/action/config key/value, **a malformed client declaration** — see § The client write gate) |
| 3 | environment error (no store, no version, unreadable directory, missing plugin requirement, malformed settings file, **a store whose one-time layout migration a declared client may not perform**) |
| 4 | conflict (lock timeout, identity collision, refusing to overwrite, plugin action requires enabled but plugin is disabled, a declared client refused a mutating command — see § The client write gate) |

This table and the module docstring of `scripts/lib/devteam/errors.py` are two halves of one contract:
the docstring names the same declared-client cases on 2, 3 and 4, and the reasoning for each sits with
the function that raises it (`compat.refusal` for 4, `compat.migration_required` for 3). If you change
one, change the other in the same commit — and see ADR-0014 § 2, which makes *changing which exit code
an existing outcome uses* a `json_contract` obligation.

**Exception: `devteam notifications watch --json` is JSON Lines.** It runs until its stdin closes
(or SIGTERM) and writes one compact JSON document per line, each carrying `ok`: every unseen
`notification` already queued, then `ready`, then each new `notification`, a `heartbeat` every
30 s, and `end` (with `reason`: `stdin-closed`, `sigterm`, `interrupted`) last. No final document
follows. **A failure is a line too:** `{"event": "error", "ok": false, "error", "exit_code", …}` —
the usual error keys, compact, plus `event` — and the process exits with that code. That holds for a
failure before parsing ends (a bad `--interval`) as much as after, because an indented document there
reads as a protocol error and hides the exit code that explains it. `--interval` must be at least
0.01 s. It is excluded from the bulk contract sweep and pinned by `tests/test_notifications.py`
against a real stream instead.

**Exception: `devteam cred get` refuses `--json`.** The value is written to stdout and nothing else, so wrapping it in a document would put a secret somewhere a client is likely to log. Use `devteam cred list --json` for the references instead.

## Task board

`devteam tasks` ([ADR-0018](../docs/development/adrs/0018-the-task-board-is-captured-by-hooks-into-a-machine-local-per-session-record.md),
spec `docs/specs/task-board.md`). Hooks capture each provider's todo tool (Claude `TodoWrite` /
`TaskCreate` / `TaskUpdate`, Codex `update_plan`, opencode `todowrite`) into one record per session,
`<state-dir>/task-board/<session-key>.json` — machine-local, one file per session so two sessions never
share a lock. `scripts/lib/devteam/tasks.py` owns it: normalizers (defensive, a payload it cannot read
is a no-op), the per-session lock and atomic write, and every derived field — session `status`,
task `column`, `stale`, `abandoned`, `durations` — which is computed on read and **never stored**.
Nothing deletes a record or a task: a task a replace-style call omits gets `removed_at` and stays.

- `record`, `mark`, `review-open` and `review-result` are **mutating** in `compat.MUTATING` but **hook-safe**: they swallow every
  error and exit 0 with `recorded: false` / `marked: false`, and refuse a session id containing a
  path separator.
- `list` and `watch` are read-only. `watch` is JSON Lines like `notifications watch` (same stdin-EOF /
  SIGTERM / 30 s heartbeat lifecycle); because "stale" moves with the clock, it recomputes every
  project every 30 s and emits a `snapshot` only when the view differs from the last one sent.
- **In Review** is an optional fourth column inferred from *review windows* stored in the record
  (`reviews`, absent on older files). `review_triggers.py` decides what opens a window and reads the
  marker; `tasks.py` owns the window lifecycle (open/join, result, Stop scan, fix rule, re-review rule,
  reopen) and the derived `column: "in_review"`, task `review`, `counts.in_review`, project
  `with_findings` and `durations.in_review` — all additive to the `--json` contract. `session_done`
  requires every task in the Done column, so it waits for the review to resolve.
- **Agent spawns are tasks.** `record` also takes an agent call (Claude `Agent`/`Task`, Codex `spawn_agent`/`wait_agent`/`close_agent`,
  opencode `task`): a spawn is an `in_progress` task with `kind: "agent"` (text `<agent>: <description>`, id = the spawn's
  own id, owner = the spawning agent); its result completes it, Claude `PostToolUseFailure` cancels it with `failed: true`,
  a background launch stays open until its transcript hand-back at `Stop` (`tasks mark --state idle`), and a Codex
  `wait_agent` settles each agent id it reports, matched through the `agent_ref` the `spawn_agent` response gave. A result
  never starts a record. Built-ins (`review_triggers.BUILTIN_AGENTS`, one list keyed by provider) and review/QA agents are
  no tasks. `tasks mark --state idle` settles a foreground agent task left open as `cancelled` + `interrupted: true`, and a background hand-back's `<status>` of `failed`/`killed`/`error` fails the task. `became_all_done` for an agent's end is raised only at `Stop`, never with a `failed`/`interrupted` task visible. A task's `kind`, `failed`, `interrupted` and `worktree` (`{path, branch}` of the linked worktree it was started in, else null) are additive in `--json`; an agent task is hidden on read (columns, counts,
  `all_done`) when its owner also keeps `Step N:` plan tasks.
- `sessions_active` counts sessions whose status is not `ended` (active **or** idle).
- `tasks watch` is excluded from the bulk contract sweep and pinned by `tests/test_tasks.py`.

## Catalog

`devteam catalog` is a read-only browse surface for the framework's agents, skills, and commands
in the version the project is bound to.

**Three deliberate behaviors:**

1. **It reads from the bound version, never from the working tree.** If you stand in a project with a
   pin or a stale checkout, catalog shows what that pin resolves to. This is load-bearing for the desktop
   app, which must never report the harness in two different states depending on where the user was
   standing when they asked.
2. **It creates nothing, including not minting a machine identity.** Same discipline as `devteam path`
   and `devteam doctor` — read-only commands leave the store untouched.
3. **Malformed files are flagged, never fatal.** A skill with invalid YAML in the frontmatter is
   listed as `malformed` with its path, so the user can locate and fix it. A catalog that exits on
   one bad file is useless for finding the bad file.

**Subcommands:**

- `devteam catalog` — Summary: installed version, project identity, counts per kind, and malformed counts
- `devteam catalog agents|skills|commands` — Every entry of that kind, with name/tier/model/path/description
- `devteam catalog show <name>` — One entry's metadata plus body; resolves a bare name across all three kinds. When a name is ambiguous, lists the candidates instead

**Flags:**

- `--path <dir>` — Read from a different project (default: current one)
- `--json` — Output JSON with entries in their full structure

**Payload shapes (JSON output):**

- `devteam catalog`: `{version, project_id, counts: {agents, skills, commands}, malformed: {agents, skills, commands}}`
- `devteam catalog agents|skills|commands`: `{version, project_id, <kind>: [{name, tier, model, description, path, version}, …], count}`
- `devteam catalog show`: adds `kind` and `body` to the entry

## Global skills

`devteam skills` manages the skills each provider reads from the user's home — outside every
project and outside the store (ADR-0020). `scripts/lib/global-skill-roots.json` is the single map
of those directories; its unit is the physical **root**, each listing the providers that read it:

| Root | Directory | Read by | Install target for |
|------|-----------|---------|--------------------|
| `claude` | `~/.claude/skills` | claude, opencode | claude |
| `agents` | `~/.agents/skills` | codex, opencode | codex |
| `codex` | `~/.codex/skills` | codex | — (listed, never written; `--root codex` is refused) |
| `opencode` | `~/.config/opencode/skills` | opencode | opencode — used only when no other chosen root already covers opencode |

- `list [--provider claude|codex|opencode|all]` and `show <name> [--root <id>]` are read-only and
  create nothing. Dot-entries (Codex's `.system/`) are not skills; a folder without a valid
  `SKILL.md` is reported `malformed`, never fatal.
- `install --source <dir|.md|.zip|.skill> [--provider …] [--root …] [--replace] [--link]`:
  - **Source kinds** (`source_kind` in the payload): a folder; an archive; or a `.md` file.
    A `SKILL.md` stands for its folder only when that folder carries the skill's `name`.
    Any other `.md`, such as a `SKILL.md` loose in Downloads, is a single-file skill: only that
    file is copied. A copied folder is capped like an archive, so a mistaken pick cannot copy
    a whole directory tree. A source that cannot be installed is exit 2 with
    `details.reason = "invalid-source"`.
  - **Validation:** checks the frontmatter and installs under the frontmatter `name`.
  - **Fewest roots:** covers the chosen providers with as few roots as possible. Claude plus
    opencode writes to `~/.claude/skills` only.
  - **Conflicts:** checks every target before writing any. A conflict is exit 4 with
    `details.reason` set to `exists` or `managed`.
  - **Writing:** stages a copy in every root, then swaps each into place. A failure rolls back
    the roots already swapped, and leftover `.devteam-staging-*` directories are quarantined on
    the next install.
  - **Archives:** validated before extraction. Absolute, `..`, backslash, drive-letter, symlink
    and encrypted members are refused, with limits of 2000 entries and 50 MB. Permission bits
    are kept, except setuid, setgid and sticky, and `__MACOSX/` is skipped.
  - **`--link`:** refuses a source inside the core store or inside a target root.
- `remove <name> [--root <id>]` **never deletes**. A directory goes to the store's quarantine
  (`global-skills/<root>`), and a symlink is unlinked, with its target reported. Anything that
  resolves into the core store is `managed` and refused.
- `show` and `remove` match the name among a root's real children. `.`, `..`, separators, NUL
  and dot-names are refused.
- `install` and `remove` are in `compat.MUTATING`; `$DEVTEAM_USER_HOME` overrides `~` (the test
  seam `StoreTestCase` pins).

**Payload shapes (JSON output):**

- `skills list`: `{provider, roots: [{id, path, exists, providers, install_target_for}], skills: [{name, description, root, root_path, path, providers, is_symlink, link_target, managed, status, error}], count}`
- `skills show`: a `skills list` record plus `body`, `files`, `files_truncated`
- `skills install`: `{name, description, source, linked, source_kind, installed: [{root, path, providers, replaced, quarantined_to}], also_present: [{root, path}]}`
- `skills remove`: `{name, root, path, providers, action: "unlinked"|"quarantined", quarantined_to, link_target}`

## Compatibility block in `version`

`devteam version --json` now includes a `compat` block that reports the JSON contract version and
the store schema numbers:

Keys are alphabetical because `output.py` dumps with `sort_keys=True`. This is a real emission,
captured from `devteam version --json` against a throwaway store — **`store_schemas` carries every
shape the store has, and a client that is silent about one of them is treated as not understanding
it** (see the write gate below), so an example listing a subset would teach the opposite rule:

```json
{
  "compat": {
    "json_contract": 1,
    "min_app_version": null,
    "store_schemas": {
      "bind_manifest": 1,
      "credentials": 1,
      "plugin_settings": 1,
      "project": 1,
      "project_layout": 2,
      "registry": 1
    }
  },
  "core": "/path/to/core",
  "current": null,
  "installed": [],
  "ok": true
}
```

A client (the desktop app, for example) reads this before writing to the store: if it does not
understand a schema number in `store_schemas`, it downgrades to read-only mode. `min_app_version`
is `null` until a desktop release ships; it will then carry the minimum app version that understands
the current contract. This is ADR-0011's "compatibility is declared, not assumed" — the alternative
is inferring compatibility from the framework's release version, which moves for reasons that have
nothing to do with the contract.

## The client write gate

`devteam compat` *answers* "may this client write?". The gate is what makes that answer **binding** for
a caller that identified itself. Decided in
[ADR-0014](../docs/development/adrs/0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md);
the reasoning behind each judgment call is recorded in `scripts/lib/devteam/compat.py` beside the code
and is not restated here.

**Declaring.** Two seams, both naming a JSON file holding the same object `devteam compat
--client-file` accepts — every shape `store_schemas` reports, since an omitted one counts as
unsupported:

| Seam | Form |
|------|------|
| `--client-schemas <PATH>` | global — accepted before or after the subcommand, like `--json` |
| `DEVTEAM_CLIENT_SCHEMAS` | the same path in the environment, exported once for a client session |

**The flag wins over the variable.** The flag is on the invocation in front of you; the variable is
ambient and inherited, so a wrapper that exported it once must not override what this call says about
itself. An empty or whitespace-only variable is treated as *unset*, not as an empty declaration —
`export DEVTEAM_CLIENT_SCHEMAS=` is a shell saying "no value", and reading it as `{}` would refuse
every write in that session.

**An empty flag is the opposite case: `--client-schemas ""` is exit 2, not the anonymous path.** The
asymmetry is deliberate. A shell cannot distinguish an absent variable from an empty one, so empty means
unset *there and only there*; a flag with an empty value is a caller that passed a value and got it
wrong — almost always `--client-schemas "$SCHEMAS"` with `SCHEMAS` unset, the ordinary idiom a client
wrapper has. Downgrading that to silence would drop the gate on exactly the invocation that meant to
declare. Asserted in both directions by `tests/test_client_gate.py::EmptyFlagValueIsNotSilenceTest`,
including against `compat.client_declaration` itself so the rule is pinned as a rule and not only as an
exit code.

One parser (`compat.parse_client_schemas` / `compat.load_client_schemas`)
serves both seams **and** `devteam compat`'s own `--client`/`--client-file`, so the two cannot disagree
about what a valid declaration is. A bare `devteam compat` with no `--client`/`--client-file` falls back
to the same seam, so an exported declaration gets a `may_write` without restating the file.

**Every rejection names the seam that carried the path**, not just the path: `--client-schemas …`,
`--client-file …` or `DEVTEAM_CLIENT_SCHEMAS …`. A client whose wrapper exported the variable three
layers up has to be told which seam is at fault rather than handed a path it never typed. Asserted for
all three seams by `tests/test_client_gate.py::…test_a_declaration_file_names_the_seam_that_carried_it`.

**A malformed declaration is a malformed question — exit 2 on every seam, including `devteam compat`.**
`json.loads` has two failure modes that are not `JSONDecodeError` and `Path.read_text` one that is not
`OSError`: a file that is not valid UTF-8, and input nested too deeply to parse. Both are `UsageError`
now, so `devteam compat --client-file <undecodable-or-too-deep>` is **exit 2**; it was exit 3 before,
reached through `cli.main`'s catch-all as *"unexpected UnicodeDecodeError / RecursionError"*, which is a
crash reported as an environment problem. Exactly one document still goes out on stdout under `--json`,
and no traceback reaches the shell — `tests/test_client_gate.py::UnreadableDeclarationIsADocumentNotATracebackTest`
asserts both on all three seams plus `devteam compat`, and exercises `cli.main`'s remaining catch-all
directly so the net itself is not the untested part.

**When it runs.** A declaration is resolved — and therefore validated — on every invocation that
carries one, including a read-only one: a corrupt declaration file is a broken client installation, and
reporting it on the first call rather than on the first *write* removes the window in which the gate
silently is not there. The refusal itself applies only to a **mutating** command, and it happens in
`cli.main` after the parse and **before `store.adopt_machine_layout()`**, which is itself a store
mutation — so a refused command leaves the store byte-identical. That ordering is not a comment any
more: `tests/test_client_gate.py::PreSplitStoreTest` fabricates a pre-split store and asserts the store
is byte-identical after a refusal, for `bind` and then across the whole of `compat.MUTATING`. Before it
existed, moving the gate block below `adopt_machine_layout()` left every test green.

| Caller | Mutating command | Read-only command |
|--------|------------------|-------------------|
| declares nothing | runs | runs |
| declares, understands every shape | runs | runs |
| declares, is behind on or silent about a shape | **refused, exit 4** | runs — except on a store that has not been relocated, see below |
| declaration file missing, empty, malformed, not UTF-8 or nested too deeply | usage error, exit 2 | usage error, exit 2 |

A client *ahead* of the store is not refused — an older store read by a newer client is the direction
that works.

**Exit 4, not 1.** `devteam compat` exits 1 for an incompatible client because there the negative is a
*finding*: the question ran and answered. A refused write ran nothing, and exit 1 in this CLI always
means "ran and reported a problem it did not fix". Exit 2 stays reserved for a malformed question,
which is what a broken declaration file already raises; exit 3 says the environment cannot support the
command, and for a refused **write** the environment is fine — the client is the party that is behind.
Exit 3 does have one declared-client use, and it is the opposite case: a read-only command whose
*environment* is not ready, described below.

The refusal is an ordinary error document, and its `details` carry the comparison so a client branches
on data rather than on the wording of a sentence. Below is a **real emission**, not an illustration:
`devteam bind --json --client-schemas client-schemas.json` in a throwaway store, against a declaration
naming three of the store's five shapes and one of those a version behind
(`{"project": 1, "project_layout": 2, "registry": 0}`). Keys are alphabetical because the emitter dumps
with `sort_keys=True` (`output.py`), so this is the on-the-wire order, not a tidied one:

```json
{
  "details": {
    "client_schemas": {
      "project": 1,
      "project_layout": 2,
      "registry": 0
    },
    "command": "bind",
    "declaration_source": "client-schemas.json",
    "declared_by": "--client-schemas",
    "may_write": false,
    "store_schemas": {
      "bind_manifest": 1,
      "credentials": 1,
      "plugin_settings": 1,
      "project": 1,
      "project_layout": 2,
      "registry": 1
    },
    "unsupported": {
      "bind_manifest": {
        "client": null,
        "store": 1
      },
      "credentials": {
        "client": null,
        "store": 1
      },
      "registry": {
        "client": 0,
        "store": 1
      }
    }
  },
  "error": "bind would write to this store, and the client declared via --client-schemas does not understand 3 shape(s) it uses: bind_manifest (store=1, client=(not declared)), credentials (store=1, client=(not declared)), registry (store=1, client=0)",
  "exit_code": 4,
  "hint": "Upgrade the client, or run `devteam compat --client-file client-schemas.json` for the full comparison. Read-only commands still work. Dropping the declaration is not a fix — it only hides the mismatch.",
  "ok": false
}
```

Read what that payload is actually saying, because a shorter example would teach the wrong rule. The
store carries **five** shapes (`project`, `project_layout`, `registry`, `bind_manifest`, `credentials`).
This declaration named three, so `unsupported` has **three** entries, not one: `registry` is a version
behind, and `bind_manifest` and `credentials` were never mentioned — silence is not a claim of support,
so both are reported with `"client": null` and render as `client=(not declared)` in the human message.
A client that declares a subset is refused for every shape it left out.

`declaration_source` is the path exactly as the caller passed it — relative here, because the invocation
passed a relative path. `declared_by` names the seam actually used, so a client whose wrapper three
layers up exported `DEVTEAM_CLIENT_SCHEMAS` is told about the variable rather than about a flag it never
passed. This refusal always sets `hint`, so a client parsing `details` should expect it — but `hint` is a
*conditional* key of the error envelope generally (`errors.DevteamError.payload()` emits it only when
set), never a fixed key of any command. The seven `details` keys are the pinned part, held by
`tests/test_client_gate.py::RefusalDetailsAreThePinnedContractTest` in both directions — it fails on an
added key as loudly as on a removed one, and prints the two sets so the next reader decides rather than
silences.

**The one-time machine-layout relocation is suppressed for an incompatible client, and one read-only
command is refused instead — exit 3.** `store.adopt_machine_layout()` moves a pre-ADR-0013 store's
machine-local records to the split paths. It **writes `registry` and `bind_manifest`** — precisely the
shapes an incompatible client just declared it cannot read — so it does not run on that caller's behalf.
A terminal invocation, any anonymous caller and any *compatible* declaration still perform it, so no
store is stranded by this.

With the relocation skipped, a read-only command answers against the layout actually on disk. Every
read-only command answers the same on both layouts **except `devteam list`**, which is why
`compat.NEEDS_MACHINE_LAYOUT` holds exactly that one entry. `paths.registry_file()` resolves only the
post-split path, so `list` read no registry at all and reported *every* bound project as unbound — exit
0, `projects: []`, no error anywhere, the same silent failure mode as the stranded `state-dir` pointer
that made `state_get` return an empty string for every key. The other read-only commands resolve through
the project's own pointers or through the core store rather than through the registry, so the layout
never reaches their answer.

**That membership was measured, not reasoned about.**
`tests/test_client_gate.py::PreSplitStoreTest.test_a_read_only_command_answers_the_pre_split_truth_or_is_refused`
runs every leaf of `compat.READ_ONLY` twice under the same incompatible declaration — once on the split
store, once after de-splitting — and requires each to answer identically or be refused, then asserts the
refused set **equals** `compat.NEEDS_MACHINE_LAYOUT`. A command that starts reading the registry fails
there rather than joining the wrong side quietly. (`cred get` is the one exclusion, and not for
convenience: it appends an audit line, so two runs differ by construction, and it refuses `--json` by
design so there is no document to compare.)

So `list` under an incompatible declaration on a pre-split store is **exit 3, not 4**. Nothing is being
refused *as a write* — this caller is entitled to read, and ADR-0011's rule is that an incompatible
client degrades to read-only. What is not ready is the **environment**: the store is in a shape this
command cannot read, and the one thing that would fix it is a write the caller said it cannot
understand. A clear refusal beats a wrong answer, because a client told `projects: []` would offer to
bind a project that is already bound. `compat.migration_required` raises it, carrying the refusal's seven
`details` keys **plus `machine_layout_pending: true`**, and its `hint` names the fix that does not
require upgrading the client: run any `devteam` command from a terminal without a declaration. The hint's
own escape hatches — `devteam compat`, `version` and `path` — are asserted to answer on a pre-split
store, so the guidance is not a dead end for the caller it is written for.

**Where the classification lives.** `compat.MUTATING` and `compat.READ_ONLY` in
`scripts/lib/devteam/compat.py` — 19 and 16 entries, covering all 35 parser leaves — keyed by the same
path tuples `tests/test_json_contract.py`'s discovery walk produces, with the reason beside every
entry. `compat.is_mutating()` **fails closed**: a command in neither table counts as mutating, so
forgetting to classify a new one cannot open a hole. `tests/test_client_gate.py` (52 tests) walks the real
parser and fails on any unclassified leaf, any leaf in both tables, and any entry naming a command that no
longer exists. A third, much smaller table sits beside them — `compat.NEEDS_MACHINE_LAYOUT`, one entry,
described above — and its membership is swept rather than trusted.

Six entries are judgment calls rather than readings of a name. Five of them carry their reason in the
table; the sixth is noted below because it does not:

- `cred get` is **read-only**. Its audit line is the framework's own record *about* the caller, not one
  of the shapes `store_schemas()` declares; gating it would turn a write gate into a read denial and
  replace its documented `--json` exit-2 refusal with an exit 4.
- `doctor` is **mutating** — it repairs directory pointers and can reassign identity.
- `export` is **mutating** — it creates a restorable archive of shapes the declaring client just said
  it cannot read.
- `store gc` and `migrate` are **mutating** by what the command can do, not by which flag one
  invocation passed — both say exactly that in the table, because both are read-only without `--apply`.
- `upgrade` is **mutating** for the same per-command reason, and its table entry does **not** state it —
  it reads only "relocates this project's memory into the store". It is also gated on `--apply`, so a
  reader comparing it against `store gc` and `migrate` finds the rationale missing from the one entry
  where the flag is most likely to invite re-deciding it from the invocation.

**An anonymous caller keeps its full write access.** No detection, no warning, no log entry: the gate
binds only callers that identify themselves, and omitting the declaration is a complete bypass. That is
deliberate — an anonymous invocation is byte-for-byte a human at a terminal, and the human's CLI is the
one thing this gate may not touch. ADR-0014 § 3 records the boundary, why identification is not
authentication, and the two conditions that would justify reopening it.

## Credentials

Credential **references** (purpose, scope, backend) are portable and reviewed — stored in `data/credentials/global.json` (shared across projects) or `data/credentials/<project_id>.json` (per-project, overrides global). Values stay out of git entirely: the macOS `security` keychain, Windows DPAPI, or a machine-local encrypted store. See [ADR-0010](../docs/development/adrs/0010-credential-values-in-the-os-keychain-with-non-secret-reference-files.md).

### Commands

| Command | What it does | Flags |
|---------|------|-------|
| `devteam cred list` | Every declared credential — references only, never a value | `--path <dir>`, `--global` |
| `devteam cred get <key>` | Print one value on stdout and nothing else — use this for the sanctioned read path (audited) | `--path <dir>`, `--global`, `--agent <name>` |
| `devteam cred set <key>` | Declare a credential and store the value; reads from stdin (never argv) | `--path <dir>`, `--global`, `--purpose <text>` (required), `--scope <agents>` (comma-separated), `--backend <name>` |
| `devteam cred unset <key>` | Remove a reference; the value stays unless `--forget-value` is passed | `--path <dir>`, `--global`, `--forget-value` |
| `devteam cred import <file>` | Migrate a v2 `credentials.local.json` into references and move the file to quarantine | `--path <dir>`, `--global` |
| `devteam cred check` | Report references with no stored value, or any credential on an insecure backend | `--path <dir>`, `--global` |
| `devteam cred backends` | Which secret stores this machine has available (and why, if any are unavailable) | none |

Shared flags (on all but `backends`): `--path <dir>` targets a different project directory (default: the current one); `--global` acts on the global layer instead of the project's.

### Store layout

**Portable** (in archives by default; reviewed in git):

```
data/credentials/global.json                    References used across projects
data/credentials/<project_id>.json              References for one project (overrides global)
```

**Machine-local** (never in archives; never in git):

```
data/machines/<machine-id>/secrets/             Where a backend keeps values on disk (mode 0600, last resort)
data/machines/<machine-id>/projects/<id>/audit.log   Append-only read audit trail — machine-local because two machines appending to one log would need merge semantics we do not have
```

When a reference exists but its value is missing, `devteam cred check` reports it; `devteam cred get` fails cleanly.

### Backends

| Backend | Availability | Behavior |
|---------|--------------|----------|
| `keychain` | macOS only, via `security` CLI | System keychain; service `dev-team-agents`, account `devteam/<project_id>/<key>`. Encrypted by OS. |
| `dpapi` | Windows only, via ctypes | Windows Data Protection API; key derivation from machine identity. Implemented but unverified on real hardware — testers needed. |
| `insecure` | All platforms (fallback only) | **Not encrypted.** A mode-0600 JSON file at `data/machines/<machine-id>/secrets/`. Last resort when no native store is available. `devteam cred check` reports every value on this backend. Never use in production; suitable for test/CI environments where the value lifetime is seconds. |

A value is stored on the first-available backend by default; `--backend` on `devteam cred set` overrides the probed default. When a backend becomes unavailable (e.g., upgrading to a different OS), values stay on the machine that wrote them — move them across machines with `devteam export --all` → `devteam import`. A reference without a value is not an error; it documents what a project needs even if the value has not been set yet.

### Special behaviors

**Stdin rule:** `devteam cred set` reads the value from stdin, never from a command-line argument. A value in `argv` is in the process table for every other user on the machine, and in the shell history of the user running the command. Interactively, it prompts without echo; non-interactively, pipe it: `printf %s "$TOKEN" | devteam cred set mykey --purpose "an API key"`.

**Scope field:** `--scope` restricts which agents can read the value via `devteam cred get --agent <name>`. Agents not listed get a clear error; comma-separated, no spaces. The scope is **hygiene and auditability, not a sandbox** — an agent with Bash can read anything the user can read. Its value is auditing read paths and reporting scope violations in the audit log.

**`credentials.local.json` migration:** The v2 plaintext file is opt-in, never scanned for. `devteam cred import /path/to/credentials.local.json` reads it, migrates values to the secret store, writes references to the reference layer, and moves the original file to quarantine — a one-way, confirmed operation. Non-secret fields (TTL thresholds, notification prefs) are kept as plain values in the reference layer.

## Local Credentials File

`.dev-team-agents/credentials.local.json` is a plaintext file for staging and production access (see [docs/credentials.local.md](../docs/credentials.local.md) for the schema and [ADR-0024](../docs/development/adrs/0024-the-local-credentials-file-lives-at-the-dev-team-agents-root-and-the-app-edits-it-through-the-cli.md)). One file, shared by every linked worktree of the checkout: developers edit it by hand, agents read it with the Read tool (they get its path from `devteam cred local show`), and the desktop app edits it only through `devteam cred local`.

### Commands

| Command | What it does | Output (success, `ok: true`) |
|---------|------|-------|
| `devteam cred local show` | Read the file; never prints a secret value | `{path, exists, valid, error, hash, data, unknown_paths}` |
| `devteam cred local init` | Write the canonical template; refuses (exit 4) if the file exists | same as `show` |
| `devteam cred local patch --expect-hash <H>` | Apply JSON Pointer ops from stdin atomically; refuses (exit 4) on hash conflict | same as `show` |

**Redaction is default-deny** (ADR-0024 § 5): `data` keeps a value only for the two `work_feedback_*` keys, `agents` string arrays and the leaves named in `credentials_local.SAFE_LEAF_NAMES`, and hides even those when the value looks secret (URL userinfo, a URL query or fragment, pasted key material). Everything else becomes `{"secret": true, "set": <boolean>}`. On `patch`, every value travels on stdin; argv never carries one.

**Hash conflict:** `hash` is an HMAC of the file's bytes keyed with a machine-local key, not a plain digest. If it differs from `--expect-hash`, no change is made and exit 4 is returned with `details.reason: "hash-conflict"`; `init` on an existing file returns exit 4 with `details.reason: "exists"`.

**Relocation:** `doctor`, `sync`, `migrate --apply` and `upgrade --apply` move a legacy copy (`user-data/`, or the store copy of a project the registry binds here) to the root byte-for-byte, after making sure git ignores the target, and report it in an additive `credentials_local` key `{path, changed, moved, quarantined, conflicts}`. Symlinks are reported, never followed; a file at the project's own root is never scanned for; `upgrade` refuses while two different copies exist.

**The app's allowlist:** `devteam cred local show`, `devteam cred local init`, and `devteam cred local patch` are the only `cred` commands the desktop app is allowed to run. `devteam cred get` stays forbidden, as it prints secret values.

## Integrations

`devteam integration` connects the account to GitHub and Jira. An integration is **not** a plugin: the
token is account-level, and all network I/O happens in the CLI (the desktop app never touches the
network, ADR-0015). Each adapter (`scripts/lib/devteam/integrations/`) declares a descriptor — fields, scope, picker
resource — and the `IntegrationView` in `--json` carries it, so a client renders generically.

| What | Where |
|---|---|
| token | secret store, `creds` key `integration.<name>.token`, global layer; read through `creds.get_value` (audited), never in a payload, exception or log |
| account config | `data/integrations/<name>.json` — `{"schema":1,"config":{…}}` (portable) |
| project binding | `<project>/.dev-team-agents/integration-settings/<name>.json` (committed); a file that cannot be read is treated as unset and reported in the view's `project_problem` |
| last test result | `data/machines/<machine-id>/integrations-status.json` (machine-local) |

`connect` reads the token from **stdin** (empty stdin keeps the stored one) and `--field key=value` sets
account-scope fields. A failing test (bad token, unreachable, rate-limited) is a result — exit `0`,
`test.ok=false` — not a CLI error. `resources` failures are an environment error (exit `3`).
Two store schemas (`compat.store_schemas()`), each declared by a client before it writes:
`integrations` (the account file) and `integration_settings` (the committed binding). The
machine-local status file is a CLI-only cache with its own number, outside the declaration.
HTTP policy (`integrations/http.py`): https only, the token goes only to the configured origin and
a redirect elsewhere is refused, 10 s socket timeout, 20 s total deadline, 2 MB response cap. The
test suite alone can allow loopback http through `DEVTEAM_INTEGRATIONS_TEST_ALLOW_LOOPBACK_HTTP`; it
is a test hook, not a user setting, and nothing outside `tests/` should set it.

**The token is bound to its origin.** Every token write records `token_origin`
(`scheme://host:port` of `api_url` / `site_url`) as a reserved, non-field key in the account config.
A request is refused, and the token sent nowhere, when the configured origin differs or none was
recorded. Changing the URL with `config set/unset` or `connect --field` and no new token makes the
token **stale**: the keychain value stays (No-Destruction), `auth.stale` is `true`, `connected` is
`false`, `status.state` is `not_connected` with a summary asking for a new token, and `test` /
`resources` fail with a usage error until `connect` supplies one. `connect` adds a top-level
`warning` string to its payload only when the token landed in the `insecure` backend.
Each descriptor field carries `binds_token` (true on the origin field), so a client knows which edit
needs a new token. Storing a token writes, under the lock, the account file without `token_origin`,
then the token, then the new origin and a fresh `token_generation`: a failure in between leaves the
token stale. `test` and `resources` re-read the account file after reading the token and refuse when
it changed. A reference whose value is not on this machine makes `test` answer `not_connected`.
`connect` checks the required account fields before it prompts for a token.
Read-modify-write of the account and binding files, and `disconnect`, hold the `integrations` lock
(outer; `creds`' lock nests inside it); no lock is held across a network call.

## Plugins

See `plugins/README.md` and `docs/development/adrs/0019-plugins-as-manifest-declared-per-project-integrations.md`.

Per-project plugin settings live in `.dev-team-agents/plugin-settings/<name>.json` (committed). The CLI discovers plugins from the manifests in `plugins/` and supports enable/disable toggling, config editing, and running actions.

| Command | What it does | Flags |
|---------|------|-------|
| `devteam plugin list` | Every plugin shipped in the core, its enable status, requirements, and config | `--path`, `--json` |
| `devteam plugin show <name>` | One plugin's full details | `--path`, `--json` |
| `devteam plugin enable <name> [--force]` | Enable and optionally seed config via detect action; `--force` enables despite missing requirements | `--path`, `--json` |
| `devteam plugin disable <name>` | Disable and keep config and artifacts | `--path`, `--json` |
| `devteam plugin config get <name> [<key>]` | Read effective config (defaults merged) or one value | `--path`, `--json` |
| `devteam plugin config set <name> <key> <value>` | Write one config key (parsed by its declared type) | `--path`, `--json` |
| `devteam plugin config unset <name> <key>` | Remove a key override; it reverts to manifest default | `--path`, `--json` |
| `devteam plugin run <name> <action>` | Execute an action and return its output (or tail on failure) | `--path`, `--json` |

Behaviour worth knowing before calling it:

- `plugin list` also returns `invalid: [{name_or_dir, problem}]` — a manifest that fails validation is reported, never silently dropped (human mode prints a `warning:` line each).
- Every settings write (`enable`, `disable`, `config set/unset`) holds the `plugin-settings` lock across the whole read-modify-write, and completes a pending legacy `graphify.json` move in the same write. `config set` refuses values over 64 KiB, oversized integers and over-deep JSON with exit 2.
- `plugin run` starts the script in its own process group and stops that group on timeout (exit 124) and when the CLI itself receives SIGTERM/SIGINT — SIGTERM first so the script's own cleanup runs, SIGKILL after a 3 s grace — so an app timeout or quit never orphans it. The app cancels only `plugin run` on quit; in-flight writes get up to 5 s to finish.

Settings are stored with `plugin_settings: 1` schema version. Hooks are dispatched by `scripts/hooks/pre-tool-use/02d-plugins.sh` and `scripts/hooks/stop/99a-plugins.sh`, receiving environment variables documented in `CLAUDE-md/hooks.md` § Plugin Hook Environment Contract.

## Layout, memory and preferences

`project.json` carries **`layout`**, distinct from `schema`: `schema` is the file's format, `layout`
is where the project's own state lives. `1` means `.dev-team-agents/user-data/` (every v2 and M1
project); `2` means the data store — portable memory in `data/projects/<project_id>/` and machine-local state
in `data/machines/<machine-id>/projects/<project_id>/`. A bind that finds no `user-data/` creates the
project on the current layout, so a new project is clean from the start. `devteam upgrade` splits the
v2 directory between the two as it copies.

**Nothing relocates memory except `devteam upgrade`.** `bind`, `sync`, `update` and `migrate` report
a stale layout and stop. The one file `bind` and `sync` do take out of `user-data/` is
`preferences.json`, because the cascade never read it there: its declared, well-typed keys are copied into
the project layer, read back, and the file is moved to quarantine (`imported-preferences`). A value the
project layer already holds wins; unknown or ill-typed keys are reported, not imported. The result is
`preferences_import` in the `bind`/`sync` payload — `null` when there was no file — with `imported`,
`unchanged`, `conflicts`, `ignored`, `quarantined` and `problem`. A file that is not a JSON object, or a
write that does not read back, is left in place with `problem` set. The upgrade is copy → verify by sha256 → retire the original to quarantine,
and it refuses a populated destination before copying anything. See
[ADR-0012](../docs/development/adrs/0012-project-layout-version-and-a-consented-structure-upgrade.md).

`.dev-team-agents/state-dir` holds the absolute path of the state directory so `scripts/lib/state.sh`
resolves it in one file read — a CLI call would put a python subprocess inside every hook. It names
the **machine-local** directory (`project.state_dir()`), because `state.json` is what reads through
it; `project.memory_dir()` is the portable sibling and has no pointer, since nothing in bash reads
it yet.

**Preferences cascade in three personal layers** (defaults → global → project) and are resolved on
write into `.dev-team-agents/resolved/preferences.json`. Agents read that one file; nothing merges at
read time. Canonical contract: `skills/shared/user-preferences/SKILL.md`. `context_paths` is **not**
a preference — it is committed topology in `project.json`, read per
`skills/shared/project-context/SKILL.md` § Context Loading Order.

## Rules for contributors

- **No-Destruction Rule** — canonical home `skills/shared/setup-health-check/SKILL.md`, including
  the one named exception this CLI has (a symlink artifact is unlinked, since `sync` regenerates
  it). Implemented by `scripts/lib/devteam/quarantine.py`; every real file or directory goes to
  `data/quarantine/<date>/<project_id>/`. `require_inside` in `bind.py` must be called before
  every write and every removal — three separate data-loss defects were one missing call to it.
- **Every store mutation takes a lock** (`scripts/lib/devteam/lock.py`) and writes through
  `jsonio.write_json_atomic` — two sessions in two bound projects mutate the same registry.
- **Standard library only**, and **python 3.9 or newer** — the floor is enforced in
  `scripts/cli/devteam` and tested as its own CI matrix leg. No third-party dependency, no
  virtualenv, no lockfile.
- **Path containment is compared component-wise on resolved paths** (`_is_inside` in `bind.py`).
  `startswith` on unresolved paths is wrong twice: `/var` vs `/private/var` on macOS, and a
  sibling named `core-backup` reading as inside `core`.
- **Tests are the gate.** `python3 -m unittest discover -s tests -t tests`, run by
  `.github/scripts/ci/03-python.sh` as a blocking CI step. `tests/` is stripped from the package.
