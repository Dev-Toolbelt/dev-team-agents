# Installation — Advanced Options

This document covers version pinning, updates, language configuration, automatic updates, and notification tuning. For the one-line install, see the [README](../README.md#how-to-install).

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
.claude/dev-team-agents/scripts/update.sh
```

The script downloads the latest release tarball, replaces the package directory, and re-creates symlinks. Your `user-data/` directory is never touched during updates.

---

## Pin to a Specific Version / Downgrade

```bash
.claude/dev-team-agents/scripts/update.sh v1.0.0
```

Pass any version tag to install that exact version regardless of what is currently installed.

---

## Automatic Updates (opt-in)

Enable automatic updates so the daily check applies new versions instead of just notifying:

```bash
.claude/dev-team-agents/scripts/update.sh --enable-auto
```

Disable at any time:

```bash
.claude/dev-team-agents/scripts/update.sh --disable-auto
```

You can also toggle this in `.claude/user-data/preferences.json`:

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

Update at any time by editing `.claude/user-data/preferences.json`:

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

Configure in `.claude/user-data/preferences.json`:

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
| `transcript_multiplier` | `1.8` | Multiplier applied to transcript token count to estimate full context |
| `model_max_tokens` | `200000` | Context window of the active model |

Set `suppress_notifications` to `true` to silence all notifications, or to `["info"]` to suppress only tips.

Context window warnings use transcript token counts (from the Stop hook payload) multiplied by `transcript_multiplier`. Adjust `transcript_multiplier` up if warnings fire too early, or down if they fire too late. Set `model_max_tokens` to match your model's actual context window if you switch to a non-200k model.

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
│   ├── .installed-version      ← gitignored
│   └── .last-update-check      ← gitignored
├── agents/
│   └── dev-team/           ← symlink → .claude/dev-team-agents/agents/
├── skills/
│   ├── project-context/    ← symlink → skill directory
│   └── ...                 ← one symlink per skill
├── commands/
│   └── devteam/            ← symlink → commands/ (invoke as /devteam:plan etc.)
└── settings.json           ← hook dispatchers configured automatically
```

## Committing the Installation

Because `install.sh` downloads a tarball (not a git clone), `.claude/dev-team-agents/` has no nested `.git` folder. **Commit it directly** so your whole team gets the agents and skills on `git pull`:

```bash
git add .claude/dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

If you prefer each developer to install locally instead:

```gitignore
# Optional: ignore the installation (each developer installs locally)
.claude/dev-team-agents/
.claude/agents/dev-team/
.claude/skills/
.claude/commands/devteam/
.claude/.worktree-session
```

### Windows: symlinks in a committed installation

`.claude/agents/dev-team`, `.claude/commands/devteam`, and every `.claude/skills/<name>` are **symlinks** (git mode `120000`). When a teammate on Windows clones or checks out a repo that committed them, git only creates real symlinks if native symlink support is available — **Developer Mode on, an elevated process, or `core.symlinks=true`**. Otherwise git/MSYS writes each link's target path into a plain ~62-byte text file.

This failure is easy to miss: `git-bash`'s `ls -la` still renders the fake links as `lrwxrwxrwx` (MSYS emulation), but Windows and Claude Code see plain files — so the entire dev-team silently fails to load (`/devteam:*`, agents, and skills all vanish). Confirm the real state with `test -L` rather than `ls`:

```bash
test -L .claude/commands/devteam && echo "link" || echo "broken"
```

Repair it with the bundled helper, which auto-fixes when the OS allows and otherwise prints the three remediation options (Developer Mode, elevated terminal, or running Claude Code as administrator):

```bash
bash .claude/dev-team-agents/scripts/fix-symlinks.sh
```

Restart Claude Code after repairing so it re-indexes commands, agents, and skills. Enabling Developer Mode is the durable fix — it also covers future clones of this and other repos without any admin step.
