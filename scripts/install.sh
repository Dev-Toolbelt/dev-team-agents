#!/bin/bash
# install.sh — Installs or updates dev-team-agents at the PROJECT level.
#
# Run this script from your project root. It installs agents and skills
# into .claude/ inside your project (not globally into ~/.claude/).
#
# Usage (from project root):
#   curl -sSL https://raw.githubusercontent.com/vaironaegos/dev-team-agents/main/install.sh | bash
#   bash <(curl -sSL ...) v1.2.0                       # specific version
#   .claude/dev-team-agents/install.sh latest           # update after first install
#
# What it does:
#   1. Clones or updates the repository into .claude/dev-team-agents/
#   2. Checks out the requested tag
#   3. Symlinks agents/ to .claude/agents/dev-team/
#   4. Symlinks each skill to .claude/skills/<skill-name>/
#   5. Configures the update-check hook in .claude/settings.json
#   6. Records the installed version

set -euo pipefail

REPO_URL="git@github.com:vaironaegos/dev-team-agents.git"
PROJECT_ROOT="$(pwd)"
INSTALL_DIR="$PROJECT_ROOT/.claude/dev-team-agents"
AGENTS_TARGET="$PROJECT_ROOT/.claude/agents"
SKILLS_TARGET="$PROJECT_ROOT/.claude/skills"
SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.json"
VERSION="${1:-latest}"

echo "dev-team-agents installer (project-level)"
echo "========================================="
echo "Project root: $PROJECT_ROOT"
echo ""

# ── Step 1: Clone or update ───────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating existing installation at $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git fetch --tags --quiet
else
    echo "→ Cloning repository to .claude/dev-team-agents/"
    mkdir -p "$PROJECT_ROOT/.claude"
    git clone "$REPO_URL" "$INSTALL_DIR" --quiet
    cd "$INSTALL_DIR"
fi

# ── Step 2: Resolve version ───────────────────────────────────────
if [ "$VERSION" = "latest" ]; then
    RESOLVED=$(git describe --tags "$(git rev-list --tags --max-count=1)" 2>/dev/null || echo "")
    if [ -z "$RESOLVED" ]; then
        echo "→ No tags found. Using main branch."
        git checkout main --quiet 2>/dev/null || git checkout master --quiet
        RESOLVED="main"
    else
        echo "→ Installing latest: $RESOLVED"
        git checkout "$RESOLVED" --quiet
    fi
else
    echo "→ Installing version: $VERSION"
    git checkout "$VERSION" --quiet
    RESOLVED="$VERSION"
fi

# ── Step 3: Create target directories ────────────────────────────
mkdir -p "$AGENTS_TARGET"
mkdir -p "$SKILLS_TARGET"

# ── Step 4: Link agents ───────────────────────────────────────────
AGENTS_LINK="$AGENTS_TARGET/dev-team"
if [ -L "$AGENTS_LINK" ]; then
    rm "$AGENTS_LINK"
fi
ln -s "$INSTALL_DIR/agents" "$AGENTS_LINK"
echo "→ Agents linked: .claude/agents/dev-team/"

# ── Step 5: Link skills ───────────────────────────────────────────
for SKILL_CATEGORY in "$INSTALL_DIR/skills"/*/; do
    for SKILL_DIR in "$SKILL_CATEGORY"*/; do
        [ -d "$SKILL_DIR" ] || continue
        SKILL_NAME=$(basename "$SKILL_DIR")
        SKILL_TARGET_PATH="$SKILLS_TARGET/$SKILL_NAME"
        if [ -L "$SKILL_TARGET_PATH" ]; then
            rm "$SKILL_TARGET_PATH"
        fi
        if [ ! -e "$SKILL_TARGET_PATH" ]; then
            ln -s "$SKILL_DIR" "$SKILL_TARGET_PATH"
        fi
    done
done
echo "→ Skills linked: .claude/skills/"

# ── Step 5b: Link anthropic-skills:frontend-design ───────────────
# The plugin lives in the Claude Code marketplace cache — no network call needed.
FRONTEND_DESIGN_SRC="$HOME/.claude/plugins/marketplaces/claude-plugins-official/plugins/frontend-design/skills/frontend-design"
FRONTEND_DESIGN_DEST="$SKILLS_TARGET/frontend-design"

if [ -d "$FRONTEND_DESIGN_SRC" ]; then
    if [ -L "$FRONTEND_DESIGN_DEST" ]; then rm "$FRONTEND_DESIGN_DEST"; fi
    if [ ! -e "$FRONTEND_DESIGN_DEST" ]; then
        ln -s "$FRONTEND_DESIGN_SRC" "$FRONTEND_DESIGN_DEST"
    fi
    echo "→ frontend-design skill linked: .claude/skills/frontend-design/"
else
    echo ""
    echo "  ┌─ anthropic-skills:frontend-design not found ──────────────────┐"
    echo "  │  The frontend-design plugin is not in the marketplace cache.   │"
    echo "  │  One-time manual step:                                          │"
    echo "  │    1. Open Claude Code                                          │"
    echo "  │    2. Run /plugins → search 'frontend-design' → install        │"
    echo "  │    3. Re-run this installer to pick it up automatically        │"
    echo "  └─────────────────────────────────────────────────────────────────┘"
    echo ""
fi

# ── Step 6: Configure update-check hook in .claude/settings.json ─
UPDATE_HOOK_CMD=".claude/dev-team-agents/scripts/check-updates.sh"

if [ ! -f "$SETTINGS_FILE" ]; then
    cat > "$SETTINGS_FILE" <<EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "$UPDATE_HOOK_CMD"
          }
        ]
      }
    ]
  }
}
EOF
    echo "→ Created .claude/settings.json with update-check hook"
else
    if grep -q "check-updates.sh" "$SETTINGS_FILE" 2>/dev/null; then
        echo "→ Update-check hook already present in .claude/settings.json"
    else
        echo "→ NOTE: .claude/settings.json already exists."
        echo "  Add this hook under PreToolUse to enable update checks:"
        echo "  { \"type\": \"command\", \"command\": \"$UPDATE_HOOK_CMD\" }"
    fi
fi

# ── Step 7: Record installed version ─────────────────────────────
echo "$RESOLVED" > "$INSTALL_DIR/.installed-version"
date +%s > "$INSTALL_DIR/.last-update-check"

# ── Step 8: Make scripts executable ──────────────────────────────
chmod +x "$INSTALL_DIR/scripts/"*.sh

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo "✓ dev-team-agents $RESOLVED installed in this project"
echo ""
echo "Next steps:"
echo "  1. Add .claude/dev-team-agents/ to your .gitignore (or commit it — your choice)"
echo "  2. Run the setup-assistant: \"Help me set up this project with dev-team-agents\""
echo "  3. To update later: .claude/dev-team-agents/install.sh latest"
echo "  4. To pin a version: .claude/dev-team-agents/install.sh v1.0.0"
echo ""
echo "Agents available at: .claude/agents/dev-team/"
echo "Skills available at: .claude/skills/"
