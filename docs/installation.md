# Installation — Advanced Options

This document covers version pinning, updates, language configuration, automatic updates, and notification tuning. For the one-line install, see the [README](../README.md#how-to-install).

> **Scope — the Claude Code install** (`scripts/install.sh`). Claude-specific paths such as `.claude/` and `.claude/settings.json` are correct here and are not the only installation path. For the other supported CLIs see [install-opencode.md](install-opencode.md) and [install-codex.md](install-codex.md).

---

## Install a Specific Version

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash -s v1.0.0
```

Replace `v1.0.0` with any published tag. Available tags are listed on the [GitHub releases page](https://github.com/Dev-Toolbelt/dev-team-agents/releases).

---

## Update to Latest

After the first install, update by running:

```bash
.dev-team-agents/scripts/update.sh
```

The script downloads the latest release tarball, replaces the package directory, and re-creates symlinks. Your `user-data/` directory is never touched during updates.

---

## Pin to a Specific Version / Downgrade

```bash
.dev-team-agents/scripts/update.sh v1.0.0
```

Pass any version tag to install that exact version regardless of what is currently installed.

---

## Automatic Updates (opt-in)

Enable automatic updates so the daily check applies new versions instead of just notifying:

```bash
.dev-team-agents/scripts/update.sh --enable-auto
```

Disable at any time:

```bash
.dev-team-agents/scripts/update.sh --disable-auto
```

You can also toggle this in `.dev-team-agents/user-data/preferences.json`:

```json
{ "auto_update": true }
```

The update check runs once per day. The interval is configurable:

```json
{ "update_check_interval_hours": 24 }
```

---

## Language Preference

During installation the installer asks which language agents should use when talking to you. Plans presented for approval and all direct responses use the configured language. Documents (ADRs, changelogs, code comments) always remain in English.

Update at any time by editing `.dev-team-agents/user-data/preferences.json`:

```json
{ "language": "pt-BR" }
```

Common values: `en` · `pt-BR` · `es` · `fr` · `de` · `ja` · `zh-CN`

---

## Notification System

Agents and hooks emit notifications in the DEV TEAM AGENTS format throughout your sessions:

- **ℹ️ info** — rotating tips and best practices (one per session)
- **⚠️ warning** — context window approaching limit, stale docs, missing config
- **🚨 critical** — context window at limit, broken installation

Configure in `.dev-team-agents/user-data/preferences.json`:

```json
{
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000
}
```

| Key | Default | Purpose |
|-----|---------|---------|
| `context_window_percent_warning` | `55` | % at which a warning is emitted |
| `context_window_percent_limit` | `60` | % at which a critical alert is emitted |
| `suppress_notifications` | `false` | `false` / `true` / `["info"]` |
| `transcript_multiplier` | `1.8` | Deprecated, no longer applied (see below) |
| `model_max_tokens` | `200000` | Context window of the active model |

Set `suppress_notifications` to `true` to silence all notifications, or to `["info"]` to suppress only tips.

Context window warnings read the last transcript usage entry's cache/input token counts (from the Stop hook payload) — the exact size of the context sent on the most recent API call, no multiplier needed. `transcript_multiplier` is kept in the schema for backward compatibility but has no effect. Set `model_max_tokens` to match your model's actual context window if you switch to a non-200k model.

### Worktree & Docker isolation

Control how coding agents isolate their work, in the same `preferences.json`:

```json
{
  "worktree_active": false,
  "worktree_base_branch": null,
  "worktree_commit_action": "ask",
  "worktree_path": ".worktrees",
  "worktree_docker_isolate": true
}
```

| Key | Default | Purpose |
|-----|---------|---------|
| `worktree_active` | `false` | When `true`, agents create a git worktree per task **without asking** |
| `worktree_base_branch` | `null` | Base branch for new worktrees (`null` = auto-detect the repo default branch) |
| `worktree_commit_action` | `"ask"` | What `/devteam:commit` does in an active worktree: `ask`, `finalize`, `rebase`, or `commit-only` |
| `worktree_path` | `".worktrees"` | Where worktrees are created (`<path>/<context>/<title>`) |
| `worktree_docker_isolate` | `true` | With `worktree_active` and a Docker Compose project, spin up an isolated stack per worktree (namespaced containers/volumes/networks, ports not published) |

The per-session file `.dev-team-agents/.worktree-session` overrides these defaults for a single task. On merge, agents rebase onto the base branch, merge, and tear down only the worktree and its isolated Docker stack. All four keys are auto-backfilled with these defaults on every session if missing.

---

## Versioning

This repository uses semantic versioning via git tags (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Updates are released as tags — no auto-update on every commit
- A hook checks for new versions daily via the GitHub API (configured automatically by `install.sh`)
- By default the system only notifies — run `update.sh` to apply, or enable auto-updates as above

**Version bump policy:**
- Breaking changes (agent behavior changes, removed skills) → major
- New agents or skills → minor
- Fixes and clarifications → patch

---

## Directory Layout After Install

```
.claude/
├── dev-team-agents/        ← extracted from tarball (no .git — safe to commit)
├── user-data/              ← user state and config (preserved across updates)
│   ├── preferences.json        ← language, thresholds, notification settings (gitignored)
│   ├── graphify.json           ← Graphify config — commit this one
│   ├── session-summary.md      ← gitignored
│   └── state.json              ← consolidated state markers (installed_version, last_update_check, etc.) — gitignored
├── agents/
│   └── dev-team/           ← symlink → .dev-team-agents/agents/
├── skills/
│   ├── project-context/    ← symlink → skill directory
│   └── ...                 ← one symlink per skill
├── commands/
│   └── devteam/            ← symlink → commands/ (invoke as /devteam:plan etc.)
└── settings.json           ← hook dispatchers configured automatically
```

## Committing the Installation

Because `install.sh` downloads a tarball (not a git clone), `.dev-team-agents/` has no nested `.git` folder. **Commit it directly** so your whole team gets the agents and skills on `git pull`:

```bash
git add .dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

If you prefer each developer to install locally instead:

```gitignore
# Optional: ignore the installation (each developer installs locally)
.dev-team-agents/
.claude/agents/dev-team/
.claude/skills/
.claude/commands/devteam/
.dev-team-agents/.worktree-session
```

### Windows: symlinks in a committed installation

`.claude/agents/dev-team`, `.claude/commands/devteam`, and every `.claude/skills/<name>` are **symlinks** (git mode `120000`). When a teammate on Windows clones or checks out a repo that committed them, git only creates real symlinks if native symlink support is available — **Developer Mode on, an elevated process, or `core.symlinks=true`**. Otherwise git/MSYS writes each link's target path into a plain ~62-byte text file.

This failure is easy to miss: `git-bash`'s `ls -la` still renders the fake links as `lrwxrwxrwx` (MSYS emulation), but Windows and Claude Code see plain files — so the entire dev-team silently fails to load (`/devteam:*`, agents, and skills all vanish). Confirm the real state with `test -L` rather than `ls`:

```bash
test -L .claude/commands/devteam && echo "link" || echo "broken"
```

Repair it with the bundled helper, which auto-fixes when the OS allows and otherwise prints the three remediation options (Developer Mode, elevated terminal, or running Claude Code as administrator):

```bash
bash .dev-team-agents/scripts/fix-symlinks.sh
```

Restart Claude Code after repairing so it re-indexes commands, agents, and skills. Enabling Developer Mode is the durable fix — it also covers future clones of this and other repos without any admin step.

From inside Claude Code you can run the same repair as a command — `/devteam:symlinks` — which detects the OS, runs the helper, and walks you through the OS fix when native symlinks are blocked. If the links are broken enough that `/devteam:` commands don't load at all, run the `fix-symlinks.sh` script directly as shown above.
