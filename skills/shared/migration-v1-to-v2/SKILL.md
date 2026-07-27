---
name: migration-v1-to-v2
description: Detects and migrates projects from dev-team-agents v1 (Claude-only, materialized copies) to v2 (multi-provider, symlinks).
---

# Migration v1 → v2

Load this skill when a project shows signs of v1 installation. Detect, then execute the steps below.

## Detection — Is this v1 or v2?

| Signal | v1 (old) | v2 (current) |
|--------|----------|--------------|
| Agent location | Files in `.claude/agents/` (no subdirectory) | Symlinks at `.claude/agents/dev-team/` → `.dev-team-agents/agents/` |
| Command location | Files directly in `.claude/commands/` | Symlinks at `.claude/commands/devteam/` → `.dev-team-agents/commands/` |
| Skill location | Copied dirs in `.claude/skills/` | Symlinks to `.dev-team-agents/skills/<cat>/<name>/` |
| Project docs | Inside `.claude/docs/` | Inside `docs/` |
| Source root | `.claude/dev-team-agents/` or none | `.dev-team-agents/` |
| Auto-routing | Keyword matching in `CLAUDE.md` | Explicit `/devteam:<name>` commands |
| Provider support | Claude Code only | Claude Code + OpenCode + Codex CLI |
| Updates | Manual re-copy | `git pull` or `/devteam:update` |

## Migration Steps

### 0. Ensure `.dev-team-agents/` exists at project root

```bash
# Install if missing (curl | bash)
if [ ! -d .dev-team-agents ]; then
  curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
fi

# Or migrate from legacy location (v1 stored source in .claude/)
if [ -d .claude/dev-team-agents ] && [ ! -d .dev-team-agents ]; then
  mv .claude/dev-team-agents .dev-team-agents
fi
```

### 1. Move project docs to root

```bash
# Move docs from inside .claude/ to project root
[ -d .claude/docs ] && mv .claude/docs docs
```

### 2. Remove materialized v1 copies

```bash
# Backup project-specific commands first
cp .claude/commands/create-site.md /tmp/ 2>/dev/null || true

# Remove old materialized directories
rm -rf .claude/agents .claude/skills .claude/scripts .claude/templates

# Recreate commands and restore project-specific ones
mkdir -p .claude/commands
mv /tmp/create-site.md .claude/commands/ 2>/dev/null || true
```

### 3. Create symlinks to `.dev-team-agents/`

```bash
# Agents (namespaced under dev-team/)
ln -s ../../.dev-team-agents/agents .claude/agents/dev-team

# Commands (namespaced under devteam/)
ln -s ../../.dev-team-agents/commands .claude/commands/devteam

# Skills (link each individual skill directory)
for cat in .dev-team-agents/skills/*/; do
  for dir in "$cat"*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    ln -s "../../.dev-team-agents/${dir#.dev-team-agents/}" ".claude/skills/${name}"
  done
done

# Templates
ln -s ../../.dev-team-agents/templates .claude/templates

# Scripts (must be copied — hooks need real executables)
cp -R .dev-team-agents/scripts .claude/scripts
```

### 4. Create `.claude/settings.json`

```json
{
  "includeCoAuthoredBy": false,
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-tool-use.sh" }]
    }],
    "Stop": [{
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/stop.sh" }]
    }],
    "SessionStart": [{
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/session-start.sh" }]
    }],
    "PreCompact": [{
      "hooks": [{ "type": "command", "command": "env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-compact.sh" }]
    }]
  }
}
```

### 5. Create `user-data/` directory

```bash
mkdir -p .dev-team-agents/user-data
```

| File | Purpose |
|------|---------|
| `preferences.json` | Language, worktree, project config |
| `session-summary.md` | Session continuity |
| `.installed-version` | Version tracking |

### 6. Re-render OpenCode agents (if applicable)

```bash
python3 .dev-team-agents/scripts/lib/render_provider.py \
  --provider opencode \
  --source-dir .dev-team-agents \
  --target-dir .
```

Merge the generated `commands.snippet.jsonc` into `.opencode/opencode.json` → `command` key.

### 7. Update `CLAUDE.md`

| v1 path | v2 path |
|---------|---------|
| `.claude/docs/` | `docs/` |
| `.claude/dev-team-agents/` | `.dev-team-agents/` |

Replace keyword-based auto-routing sections with the v2 command table.

## Post-Migration Verification

```bash
# Confirm symlinks work
ls -la .claude/agents/dev-team   # should list agents
ls -la .claude/commands/devteam  # should list commands
ls -la .claude/skills/           # should list skill symlinks

# Confirm hooks are wired
grep "dev-team-agents/scripts/hooks" .claude/settings.json
```

## Rollback

```bash
find .claude -type l -delete         # remove symlinks
cp -R .dev-team-agents/scripts .claude/scripts
```
