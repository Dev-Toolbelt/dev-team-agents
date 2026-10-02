## User Data Directory

**Layout 1 (legacy)** — When a project is installed with layout 1, the installer creates two sibling directories:

| Directory | Purpose |
|-----------|---------|
| `.dev-team-agents/` | Package files — replaced entirely on every update |
| `.dev-team-agents/user-data/` | User state and config — **never touched by the installer** |

**Layout 2 (current)** — After `devteam upgrade`, user data is split into two parts stored in the global data store, accessible via pointer files:

| Pointer | Resolves to | Holds |
|---------|-------------|-------|
| `.dev-team-agents/state-dir` | `data/machines/<machine-id>/projects/<project_id>/` | Machine-local state: `state.json`, dot-markers, caches, `telemetry-queue.json`, `audit.log`, `notifications.jsonl`, `notifications-seen.json`, `task-board/` |
| `.dev-team-agents/memory-dir` | `data/projects/<project_id>/` | Portable memory: `preferences.json`, `session-summary.md` |
| `.dev-team-agents/core-dir` | `core/` (the store's, forward-slashed) | Not a data directory: lets a hook wrapper find `scripts/hooks/lib/self-heal.sh` when the project's `scripts` link is gone |

On layout 1, both pointers resolve to `.dev-team-agents/user-data/` for backward compatibility.

A **pre-v2.1.0** project kept this directory at `.claude/user-data/`. `devteam migrate` moves it to
`.dev-team-agents/user-data/` — moved, never quarantined — so the project lands on layout 1 and
`devteam upgrade` takes it into the store from there.

**Files in `user-data/` (layout 1 only; on layout 2 they live in the store under the pointers above):**

Portable (migrated to `data/projects/<project_id>/` on upgrade):
- `preferences.json` — user preferences (language, thresholds, notifications) (**gitignored** by installer)
- `session-summary.md` — per-session notes written by agents (**gitignored** by installer)
- `graphify.json` — *Legacy location; migrated to `plugin-settings/graphify.json` — see below*

Machine-local (migrated to `data/machines/<machine-id>/projects/<project_id>/` on upgrade):
- `state.json` — consolidated small scalar state markers, read/written via `scripts/lib/state.sh` (`state_get`/`state_set`). Holds `installed_version`, `installed_version_prev`, `last_health_check`, `last_update_check`, `update_check_interval`, `graphify_last_run` (legacy: the graph's build marker is now `graphify-out/.build-commit`, per checkout; `graphify-refresh.sh` reads this key only as a fallback in the main checkout), `session_id`, `session_head` — one file replacing what used to be eight separate dotfiles (`.installed-version`, `.installed-version.prev`, `.last-health-check`, `.last-update-check`, `.update-check-interval`, `.graphify-last-run`, `.session-id`, `.session-head`). Existing installs are migrated automatically and silently by `state_migrate_legacy`, called from `session-start.sh` and `install.sh` on every run; the old dotfiles are renamed to `<name>.pre-migration.bak`, never deleted (**gitignored** by installer)
- `.last-releases-etag` / `.last-releases-version` — conditional-request ETag and the version string it resolved to, so a `304 Not Modified` still yields the latest tag (**gitignored** by installer)
- `.last-archive-index` — date stamp gating `stop/99b-archive-index.sh` to at most one run per day (**gitignored** by installer)
- `.notifier-state` — notifier turn counter and tip-shown flag (**gitignored** by installer)
- `.context-cache.json` — short-lived current-context detection cache, TTL 300s (**gitignored** by installer)
- `telemetry-queue.json` — anonymous telemetry buffer; contains the installation's anonymous ID, last flush timestamp, and pending events. Only written when `preferences.json` carries `"telemetry": true` — the gate in `scripts/lib/telemetry-guard.sh` fails closed (**gitignored** by installer)
- `audit.log` — append-only JSONL audit trail of credential reads (who, when, which key — never the value). Machine-local because two machines appending to one portable log would need merge semantics this design does not have (ADR-0010)
- `notifications.jsonl` — the notification queue: one JSON line per notice a hook raised through `scripts/hooks/lib/notify.sh`, capped at 200 lines by that writer. Read by `devteam notifications list|watch`, shown by the desktop app (ADR-0017). Machine-local: a context warning from this machine's session means nothing on another
- `notifications-seen.json` — which of those this machine's app has shown; written only by `devteam notifications ack`, under a lock. Separate from the queue so the CLI never rewrites a file a hook is appending to
- `integrations-status.json` — the last connection test per integration (`{"schema":1,"status":{"<name>":{state,checked_at,summary,facts}}}`), written by `devteam integration connect|test|disconnect|config set|unset` under the `integrations` lock, atomically. Lives directly in `data/machines/<machine-id>/`. Machine-local: a token that worked from this machine says nothing about another
- `task-board/<session-key>.json` — the task board's per-session record (ADR-0018): the todo list the session's provider tool produced, each task with its status history. One file per session so two sessions never share a lock. Written only by `devteam tasks record|mark`, under a per-session lock, atomically; never deleted by any command. Machine-local: a session id means nothing on another host

Other directories under `.claude/` created by agents:
- `docs/audit/` — project audit reports generated by `setup-assistant` on first run and on health checks. Versioned by default; add to `.gitignore` only if the team prefers not to track audit snapshots.

`install.sh` adds `.dev-team-agents/user-data/` (entire directory), the legacy `!.dev-team-agents/user-data/graphify.json` exception and `.dev-team-agents/.worktree-session` to `.gitignore`. Plugin settings files (e.g. `.dev-team-agents/plugin-settings/graphify.json`) are **not** gitignored — they are committed and shared by the team. Projects with old per-file entries in `.gitignore` will be migrated automatically by the health check or next installer run.

**Rule:** any file that must survive an update must live in `.dev-team-agents/user-data/`, not inside `.dev-team-agents/`. Never store user config or state inside the package directory. Plugin settings are the exception: they live in `.dev-team-agents/plugin-settings/` and are committed (see § Plugin settings below).

**Under v3 layout 2 this directory's contents are split two ways** (ADR-0013). `devteam upgrade` copies `preferences.json` and `session-summary.md` into the portable subtree (`data/projects/<project_id>/`), and `state.json`, every dot-marker, and `telemetry-queue.json` into the machine subtree (`data/machines/<machine-id>/projects/<project_id>/`). `credentials.local.json` stays in the project tree at `.dev-team-agents/credentials.local.json` (ADR-0024); legacy copies are relocated there byte-for-byte by `doctor`, `sync`, `migrate`, and `upgrade`. **No legacy graphify.json migration happens on upgrade** — instead, `bind` and `sync` detect the old location and move it to the new one (ADR-0019): they read `.dev-team-agents/user-data/graphify.json` if the new settings file does not exist, create `.dev-team-agents/plugin-settings/graphify.json` with the content, and unlink the old file. The new file is written first, then the old one is removed, so the content is never held in one place only.

### Integration settings

GitHub and Jira bindings live in `.dev-team-agents/integration-settings/<name>.json` — **committed**, like plugin settings (`paths.PROJECT_OWNED_RECORDS`). Shape: `{ "schema": 1, "config": { "repository": "owner/name" } }`. Only project-scope fields are stored here; the token and the account fields (API URL, site URL, email) are account-level and never enter the project.

### Plugin settings

Plugins store per-project configuration in `.dev-team-agents/plugin-settings/<name>.json`. These files are **committed** and shared by the team (unlike user-data, which is personal state).

```json
{ "schema": 1, "enabled": true, "config": { "targetPaths": ["src"], "auto_refresh": false } }
```

Each plugin's settings file has:
- `schema`: format version (always 1 for now)
- `enabled`: whether the plugin is active
- `config`: effective config overrides (defaults from the manifest are merged at read time, so only differing keys are stored)

**Legacy migration:** The CLI reads `.dev-team-agents/user-data/graphify.json` as `{enabled: true, config: <file>}` when no settings file exists (Graphify's legacy location). `bind` and `sync` move it (the health check fixes it by running `devteam sync`): the new file is written first, then the old one removed. Until then `devteam plugin show graphify --json` reports `source: "legacy"`; when both files exist neither is touched and the skip is reported as a warning. The legacy gitignore negation stays until the next major.

The rule for adding a file therefore has three answers, not two, and `scripts/lib/devteam/paths.py` holds all of them:

| The file is… | Where it goes | How to declare it |
|---|---|---|
| something the **project** owns — committed, shared by the whole team | stays in the project | add it to `paths.PROJECT_OWNED_RECORDS` |
| something **this machine observed or built** | machine subtree | add it to `paths.MACHINE_LOCAL_RECORDS`, or give it a leading dot, which classifies it machine-local as a class |
| something the **user authored** | portable subtree | nothing — portable is the default |

A file that is none of the three is a sign it does not belong in memory at all. `credentials.local.json` is machine-local by classification because it holds values (ADR-0024), but its location is the project tree (`.dev-team-agents/credentials.local.json`), not the portable or machine-local store subtrees. The references that replace it via `devteam cred import` (ADR-0010) are portable precisely because they do not hold values.

**Package exclusions:** The following are stripped from the extracted tarball before it is placed in the project:

| Stripped path | Mechanism | Reason |
|---------------|-----------|--------|
| `CLAUDE.md` | allowlist (not in `KEEP_ROOT`) | Authoring rules for this repo — not for end-users |
| `README.md` | allowlist (not in `KEEP_ROOT`) | Replaced by the installed package's own README if present |
| `README.pt-BR.md` | allowlist (not in `KEEP_ROOT`) | Same as README.md |
| `CHANGELOG.md` | allowlist (not in `KEEP_ROOT`) | Release history for this repo — not for user projects |
| `CONTRIBUTING.md` | allowlist (not in `KEEP_ROOT`) | Contribution guide for this repo — not for user projects |
| `LICENSE` | allowlist (not in `KEEP_ROOT`) | Repo license file — not for user projects |
| `SECURITY.md` | allowlist (not in `KEEP_ROOT`) | Vulnerability disclosure policy — not for user projects |
| `PRIVACY.md` | allowlist (not in `KEEP_ROOT`) | Telemetry/privacy policy for this repo — not for user projects |
| `docs/` | allowlist (not in `KEEP_ROOT`) | Repository-level reports and internal docs irrelevant to users |
| `CLAUDE-md/` | allowlist (not in `KEEP_ROOT`) | Companion sections of this repo's `CLAUDE.md` — authoring rules, not for end-users |
| `.gitignore` | explicit `rm -f` (dotfile strip) | Repo-level gitignore — not for user projects |
| `.claude/` | explicit `rm -rf` (dotfile strip) | Repo-level Claude config, including the `agent-creator` and `release-prep` skills — not for user projects |
| `.github/` | explicit `rm -rf` (dotfile strip) | Repo-level GitHub config (templates, CODEOWNERS, CI scripts) — not for user projects |
| `helpers/` | explicit `rm -rf` | Root-level authoring tools for this repo (linting, scanning, archiving) — not for user projects. **Not** `scripts/helpers/`, which ships. |
| `opencode/` | explicit `rm -rf` | opencode provider-plugin source — fetched on demand by `install-opencode.sh` / `install-provider.sh` |
| `scripts/install.sh` | explicit `rm -f` | Accessed exclusively via `curl` — never bundled |

`KEEP_ROOT` (in `scripts/install.sh`) is `agents scripts skills templates commands`; everything else at the repo root is removed by the allowlist pass before `apply_strip` runs. The cross-CLI plumbing (`render-provider.sh`, `install-opencode.sh`, `install-codex.sh`, `install-provider.sh`, `scripts/lib/`) is deliberately **kept** so providers can be added offline.
