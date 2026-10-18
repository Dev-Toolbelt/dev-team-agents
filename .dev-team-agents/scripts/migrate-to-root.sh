#!/usr/bin/env bash
# migrate-to-root.sh — Migrate dev-team-agents from .claude/dev-team-agents/
# to .dev-team-agents/ at the project root.
#
# Usage: bash .claude/dev-team-agents/scripts/migrate-to-root.sh
#
# Run this once AFTER updating to v2.1.0+. It moves the installation,
# re-creates Claude Code symlinks, and updates hook paths in settings.json.
set -euo pipefail

# Git Bash/MSYS: without this, `ln -s` silently writes a copy instead of a link.
case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*) export MSYS=winsymlinks:nativestrict ;; esac

_link() {
  ln -s "$1" "$2"
  [ -L "$2" ] || { echo "✗ Could not create a symlink at $2 (native symlinks unavailable; enable Developer Mode and re-run)." >&2; exit 1; }
}

PROJECT_ROOT="$(pwd)"
OLD_DIR="$PROJECT_ROOT/.claude/dev-team-agents"
NEW_DIR="$PROJECT_ROOT/.dev-team-agents"

if [ ! -d "$OLD_DIR" ]; then
  echo "✓ No legacy .claude/dev-team-agents/ found — nothing to migrate."
  exit 0
fi

if [ -d "$NEW_DIR" ]; then
  echo "✗ Target .dev-team-agents/ already exists. Remove it first, then re-run."
  exit 1
fi

echo "→ Migrating .claude/dev-team-agents/ → .dev-team-agents/"

# 1. Move the installation directory
mv "$OLD_DIR" "$NEW_DIR"
echo "  ✔ Moved to .dev-team-agents/"

# 2. Fix Claude Code symlinks (agents, commands)
# From .claude/agents/dev-team -> ../../.dev-team-agents/agents
if [ -L "$PROJECT_ROOT/.claude/agents/dev-team" ]; then
  rm "$PROJECT_ROOT/.claude/agents/dev-team"
  _link "../../.dev-team-agents/agents" "$PROJECT_ROOT/.claude/agents/dev-team"
  echo "  ✔ Updated .claude/agents/dev-team symlink"
fi

if [ -L "$PROJECT_ROOT/.claude/commands/devteam" ]; then
  rm "$PROJECT_ROOT/.claude/commands/devteam"
  _link "../../.dev-team-agents/commands" "$PROJECT_ROOT/.claude/commands/devteam"
  echo "  ✔ Updated .claude/commands/devteam symlink"
fi

# 3. Update skill symlinks (they pointed to ../dev-team-agents/skills/...)
find "$PROJECT_ROOT/.claude/skills" -type l 2>/dev/null | while read -r link; do
  target="$(readlink "$link")"
  # Old target: ../dev-team-agents/skills/<category>/<name>
  # New target: ../../.dev-team-agents/skills/<category>/<name>
  if [[ "$target" == "../dev-team-agents/skills/"* ]]; then
    new_target="${target/..\/dev-team-agents/../../.dev-team-agents}"
    rm "$link"
    _link "$new_target" "$link"
    echo "  ✔ Updated skill symlink: $(basename "$link")"
  fi
done

# 4. Update .claude/settings.json hook paths
SETTINGS="$PROJECT_ROOT/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
  sed -i.bak 's|\.claude/dev-team-agents/scripts/hooks/|.dev-team-agents/scripts/hooks/|g' "$SETTINGS" && rm -f "$SETTINGS.bak"
  echo "  ✔ Updated hook paths in .claude/settings.json"
fi

# 5. Update update.sh path if it was referenced elsewhere
echo ""
echo "✓ Migration complete. dev-team-agents is now at .dev-team-agents/"
echo ""
echo "Next steps:"
echo "  1. Update .gitignore: replace '.claude/dev-team-agents/' with '.dev-team-agents/'"
echo "  2. Commit the changes:"
echo "     git add .dev-team-agents/ .claude/"
echo "     git commit -m 'chore: migrate dev-team-agents to .dev-team-agents/'"
echo "  3. From now on, use: bash .dev-team-agents/scripts/update.sh"
