#!/bin/bash
# install.sh — Installs or updates dev-team-agents.
#
# Usage:
#   ./install.sh              # Install latest version
#   ./install.sh latest       # Install latest version
#   ./install.sh v1.2.0       # Install specific version
#
# What it does:
#   1. Clones or updates the repository
#   2. Checks out the requested tag
#   3. Symlinks agents/ to ~/.claude/agents/dev-team/
#   4. Symlinks skills/ to ~/.claude/skills/dev-team/
#   5. Records the installed version

set -euo pipefail

REPO_URL="https://github.com/YOUR_ORG/dev-team-agents.git"  # Update before publishing
INSTALL_DIR="$HOME/.claude/dev-team-agents"
AGENTS_TARGET="$HOME/.claude/agents"
SKILLS_TARGET="$HOME/.claude/skills"
VERSION="${1:-latest}"

echo "dev-team-agents installer"
echo "========================="

# ── Step 1: Clone or update ───────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "→ Updating existing installation at $INSTALL_DIR"
    cd "$INSTALL_DIR"
    git fetch --tags --quiet
else
    echo "→ Cloning repository to $INSTALL_DIR"
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
echo "→ Agents linked: $AGENTS_LINK → $INSTALL_DIR/agents"

# ── Step 5: Link skills ───────────────────────────────────────────
# Link each skill category individually to avoid conflicting with user's own skills
for SKILL_CATEGORY in "$INSTALL_DIR/skills"/*/; do
    CATEGORY_NAME=$(basename "$SKILL_CATEGORY")
    SKILL_LINK="$SKILLS_TARGET/$CATEGORY_NAME"

    # Link individual skills within the category
    for SKILL_DIR in "$SKILL_CATEGORY"*/; do
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
echo "→ Skills linked to $SKILLS_TARGET"

# ── Step 6: Record installed version ─────────────────────────────
echo "$RESOLVED" > "$INSTALL_DIR/.installed-version"
date +%s > "$INSTALL_DIR/.last-update-check"

# ── Step 7: Make scripts executable ──────────────────────────────
chmod +x "$INSTALL_DIR/scripts/"*.sh

# ── Done ──────────────────────────────────────────────────────────
echo ""
echo "✓ dev-team-agents $RESOLVED installed successfully"
echo ""
echo "Next steps:"
echo "  1. Run the setup-assistant in any project: 'Help me set up this project with dev-team-agents'"
echo "  2. To update later: $INSTALL_DIR/install.sh latest"
echo "  3. To switch versions: $INSTALL_DIR/install.sh v1.0.0"
echo ""
echo "Agents available in ~/.claude/agents/dev-team/"
echo "Skills available in ~/.claude/skills/"
