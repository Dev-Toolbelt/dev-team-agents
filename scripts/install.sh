#!/bin/bash
# install.sh — Installs or updates dev-team-agents at the PROJECT level.
#
# Run this script from your project root. It installs agents and skills
# into .claude/ inside your project (not globally into ~/.claude/).
#
# Usage (from project root):
#   curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
#   bash <(curl -sSL ...) v1.2.0                       # specific version
#   .claude/dev-team-agents/scripts/install.sh latest  # update after first install
#
# What it does:
#   1. Resolves the requested version via the GitHub API
#   2. Downloads and extracts the release tarball (no .git folder)
#   3. Symlinks agents/ to .claude/agents/dev-team/
#   4. Symlinks each skill to .claude/skills/<skill-name>/
#   5. Configures the update-check hook in .claude/settings.json
#   6. Records the installed version

set -euo pipefail

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"

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

# ── HTTP tool detection ───────────────────────────────────────────
if command -v curl >/dev/null 2>&1; then
    HTTP_GET()      { curl -fsSL "$1"; }
    HTTP_GET_FILE() { curl -fsSL -o "$2" "$1"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_GET()      { wget -qO- "$1"; }
    HTTP_GET_FILE() { wget -qO "$2" "$1"; }
else
    echo "ERROR: curl or wget is required but neither was found." >&2
    exit 1
fi

# ── Step 1: Resolve version via GitHub API ────────────────────────
if [ "$VERSION" = "latest" ]; then
    _releases_json=$(HTTP_GET "${GITHUB_API}/releases/latest" 2>/dev/null || true)
    RESOLVED=$(echo "$_releases_json" \
        | grep '"tag_name"' | head -1 \
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

    # Fallback: tags list (repo has tags but no formal release)
    if [ -z "$RESOLVED" ]; then
        _tags_json=$(HTTP_GET "${GITHUB_API}/tags" 2>/dev/null || true)
        RESOLVED=$(echo "$_tags_json" \
            | grep '"name"' | head -1 \
            | sed 's/.*"name": *"\([^"]*\)".*/\1/')
    fi

    # Fallback: main branch (no tags yet)
    if [ -z "$RESOLVED" ]; then
        echo "→ No tags found. Using main branch."
        RESOLVED="main"
    else
        echo "→ Installing latest: $RESOLVED"
    fi
else
    echo "→ Installing version: $VERSION"
    RESOLVED="$VERSION"
fi

# ── Step 2: Download and extract tarball ──────────────────────────
if [ "$RESOLVED" = "main" ]; then
    TARBALL_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/heads/main.tar.gz"
else
    TARBALL_URL="https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/archive/refs/tags/${RESOLVED}.tar.gz"
fi

TMP_DIR=$(mktemp -d)
TMP_TAR="$TMP_DIR/archive.tar.gz"

if ! HTTP_GET_FILE "$TARBALL_URL" "$TMP_TAR" 2>/dev/null; then
    rm -rf "$TMP_DIR"
    if [ -f "$INSTALL_DIR/.installed-version" ]; then
        echo "→ No network or download failed. Keeping existing install."
        exit 0
    fi
    echo "ERROR: Failed to download $TARBALL_URL" >&2
    exit 1
fi

mkdir -p "$TMP_DIR/extracted"
tar -xzf "$TMP_TAR" -C "$TMP_DIR/extracted"

EXTRACTED_ROOT=$(find "$TMP_DIR/extracted" -maxdepth 1 -mindepth 1 -type d | head -1)
if [ -z "$EXTRACTED_ROOT" ]; then
    rm -rf "$TMP_DIR"
    echo "ERROR: Tarball extraction produced no directory." >&2
    exit 1
fi

# Preserve last-check timestamp across installs
PREV_CHECK=""
[ -f "$INSTALL_DIR/.last-update-check" ] && PREV_CHECK=$(cat "$INSTALL_DIR/.last-update-check")

# Replace existing installation (handles tarball and legacy git-clone installs)
# Uses atomic rename so the running script is never deleted mid-execution.
mkdir -p "$(dirname "$INSTALL_DIR")"
if [ -d "$INSTALL_DIR" ]; then
    [ -d "$INSTALL_DIR/.git" ] && echo "→ Legacy git-based installation detected. Converting to tarball install..."
    OLD_INSTALL="${INSTALL_DIR}.old.$$"
    mv "$INSTALL_DIR" "$OLD_INSTALL"
    mv "$EXTRACTED_ROOT" "$INSTALL_DIR"
    rm -rf "$OLD_INSTALL" "$TMP_DIR"
else
    mv "$EXTRACTED_ROOT" "$INSTALL_DIR"
    rm -rf "$TMP_DIR"
fi

# ── Step 3: Create target directories ────────────────────────────
mkdir -p "$AGENTS_TARGET"
mkdir -p "$SKILLS_TARGET"

# ── Step 4: Link agents ───────────────────────────────────────────
AGENTS_LINK="$AGENTS_TARGET/dev-team"
if [ -L "$AGENTS_LINK" ]; then
    rm "$AGENTS_LINK"
fi
ln -s "../dev-team-agents/agents" "$AGENTS_LINK"
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
            REL_SKILL="${SKILL_DIR#$INSTALL_DIR/}"
            REL_SKILL="${REL_SKILL%/}"
            ln -s "../dev-team-agents/${REL_SKILL}" "$SKILL_TARGET_PATH"
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

# ── Step 5c: Ignore machine-specific symlinks in .claude/skills/ ─────
# frontend-design points to an absolute $HOME path — must not be committed.
SKILLS_GITIGNORE="$SKILLS_TARGET/.gitignore"
if ! grep -qxF "frontend-design" "$SKILLS_GITIGNORE" 2>/dev/null; then
    echo "frontend-design" >> "$SKILLS_GITIGNORE"
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
if [ -n "$PREV_CHECK" ]; then
    echo "$PREV_CHECK" > "$INSTALL_DIR/.last-update-check"
else
    date +%s > "$INSTALL_DIR/.last-update-check"
fi

# ── Step 8: Make scripts executable ──────────────────────────────
chmod +x "$INSTALL_DIR/scripts/"*.sh

# ── Done ──────────────────────────────────────────────────────────
if [ -f "$PROJECT_ROOT/.gitignore" ] && grep -q "dev-team-agents" "$PROJECT_ROOT/.gitignore"; then
    echo ""
    echo "  NOTE: .gitignore contains 'dev-team-agents'."
    echo "  The new installer uses tarballs — no nested .git folder."
    echo "  Consider removing that entry and committing the files instead."
fi

echo ""
echo "✓ dev-team-agents $RESOLVED installed in this project"
echo ""
echo "Next steps:"
echo "  1. Commit .claude/dev-team-agents/ — no nested .git, safe to commit with the project"
echo "  2. Run the setup-assistant: \"Help me set up this project with dev-team-agents\""
echo "  3. To update later: .claude/dev-team-agents/scripts/install.sh latest"
echo "  4. To pin a version: .claude/dev-team-agents/scripts/install.sh v1.0.0"
echo ""
echo "Agents available at: .claude/agents/dev-team/"
echo "Skills available at: .claude/skills/"
echo ""
echo "  ┌─────────────────────────────────────────────────────────────────────┐"
echo "  │  💡 Want to cut your token costs by up to 80%?                      │"
echo "  │                                                                      │"
echo "  │  Graphify builds a knowledge graph of your codebase so Claude        │"
echo "  │  can answer questions and navigate code without reading every file.  │"
echo "  │  Fewer tokens per task. Faster responses. Richer context.            │"
echo "  │                                                                      │"
echo "  │  To activate it, just tell Claude:                                   │"
echo "  │    \"Set up Graphify for this project\"                               │"
echo "  │                                                                      │"
echo "  │  Claude will detect your OS, install all dependencies, and           │"
echo "  │  configure everything automatically. Takes under 2 minutes.          │"
echo "  └─────────────────────────────────────────────────────────────────────┘"
