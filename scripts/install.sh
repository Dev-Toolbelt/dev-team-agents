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
USER_DATA_DIR="$PROJECT_ROOT/.claude/user-data"
VERSION="${1:-latest}"

echo "dev-team-agents installer (project-level)"
echo "========================================="
echo "Project root: $PROJECT_ROOT"
echo ""

# ── Prerequisites check ──────────────────────────────────────────
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "  WARNING: not inside a git repository."
    echo "  Run this installer from your project root (where .git lives)."
    echo ""
fi
if ! command -v claude >/dev/null 2>&1; then
    echo "  NOTE: 'claude' command not found."
    echo "  Install Claude Code before using agents: https://claude.ai/code"
    echo ""
fi

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
        | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/' || true)

    # Fallback: tags list (repo has tags but no formal release)
    if [ -z "$RESOLVED" ]; then
        _tags_json=$(HTTP_GET "${GITHUB_API}/tags" 2>/dev/null || true)
        RESOLVED=$(echo "$_tags_json" \
            | grep '"name"' | head -1 \
            | sed 's/.*"name": *"\([^"]*\)".*/\1/' || true)
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
    if [ -f "$USER_DATA_DIR/.installed-version" ]; then
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
[ -f "$USER_DATA_DIR/.last-update-check" ] && PREV_CHECK=$(cat "$USER_DATA_DIR/.last-update-check")

# Replace existing installation (handles tarball and legacy git-clone installs)
# Uses atomic rename so the running script is never deleted mid-execution.
mkdir -p "$(dirname "$INSTALL_DIR")"

# Remove files that do not belong in user project installs
rm -rf "$EXTRACTED_ROOT/.claude"
rm -rf "$EXTRACTED_ROOT/docs"
rm -f "$EXTRACTED_ROOT/CLAUDE.md"
rm -f "$EXTRACTED_ROOT/README.md"
rm -f "$EXTRACTED_ROOT/README.pt-BR.md"
rm -f "$EXTRACTED_ROOT/.gitignore"
rm -f "$EXTRACTED_ROOT/scripts/install.sh"
rm -f "$EXTRACTED_ROOT/scripts/orphan-skill-scan.sh"

if [ -d "$INSTALL_DIR" ]; then
    [ -d "$INSTALL_DIR/.git" ] && echo "→ Legacy git-based installation detected. Converting to tarball install..."
    OLD_INSTALL="${INSTALL_DIR}.old.$$"
    mv "$INSTALL_DIR" "$OLD_INSTALL"
    mv "$EXTRACTED_ROOT" "$INSTALL_DIR"
    rm -rf "$OLD_INSTALL" "$TMP_DIR" || true
else
    mv "$EXTRACTED_ROOT" "$INSTALL_DIR"
    rm -rf "$TMP_DIR" || true
fi

# ── Step 3: Create target directories ────────────────────────────
COMMANDS_TARGET="$PROJECT_ROOT/.claude/commands"
mkdir -p "$AGENTS_TARGET"
mkdir -p "$SKILLS_TARGET"
mkdir -p "$COMMANDS_TARGET"

# ── Step 4: Link agents ───────────────────────────────────────────
AGENTS_LINK="$AGENTS_TARGET/dev-team"
if [ ! -L "$AGENTS_LINK" ] && [ ! -e "$AGENTS_LINK" ]; then
    ln -s "../dev-team-agents/agents" "$AGENTS_LINK"
    echo "→ Agents linked: .claude/agents/dev-team/"
else
    echo "→ Agents already linked: .claude/agents/dev-team/ (skipped)"
fi

# ── Step 5: Link skills ───────────────────────────────────────────
for SKILL_CATEGORY in "$INSTALL_DIR/skills"/*/; do
    for SKILL_DIR in "$SKILL_CATEGORY"*/; do
        [ -d "$SKILL_DIR" ] || continue
        SKILL_NAME=$(basename "$SKILL_DIR")
        SKILL_TARGET_PATH="$SKILLS_TARGET/$SKILL_NAME"
        if [ ! -L "$SKILL_TARGET_PATH" ] && [ ! -e "$SKILL_TARGET_PATH" ]; then
            REL_SKILL="${SKILL_DIR#$INSTALL_DIR/}"
            REL_SKILL="${REL_SKILL%/}"
            ln -s "../dev-team-agents/${REL_SKILL}" "$SKILL_TARGET_PATH"
        fi
    done
done
echo "→ Skills linked: .claude/skills/"

# ── Step 6: Link commands ─────────────────────────────────────────
# Commands are grouped under .claude/commands/devteam/ so they are invoked
# as /devteam:plan, /devteam:backend, etc. — namespaced and separate from
# any project-specific commands at the .claude/commands/ root.
COMMANDS_LINK="$COMMANDS_TARGET/devteam"
if [ ! -L "$COMMANDS_LINK" ] && [ ! -e "$COMMANDS_LINK" ]; then
    ln -s "../dev-team-agents/commands" "$COMMANDS_LINK"
    echo "→ Commands linked: .claude/commands/devteam/ (invoke as /devteam:plan, /devteam:backend, etc.)"
else
    echo "→ Commands already linked: .claude/commands/devteam/ (skipped)"
fi

# ── Step 7: Configure hooks in .claude/settings.json ────────────
PRE_TOOL_USE_HOOK=".claude/dev-team-agents/scripts/hooks/pre-tool-use.sh"
STOP_HOOK=".claude/dev-team-agents/scripts/hooks/stop.sh"

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
            "command": "$PRE_TOOL_USE_HOOK"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$STOP_HOOK"
          }
        ]
      }
    ]
  }
}
EOF
    echo "→ Created .claude/settings.json with hook dispatchers"
else
    # Inject missing hooks into existing settings.json via python3 (safe JSON merge)
    _inject_hook() {
        local hook_type="$1"
        local hook_cmd="$2"
        local check_str="$3"

        if grep -q "$check_str" "$SETTINGS_FILE" 2>/dev/null; then
            echo "→ $hook_type hook already present in .claude/settings.json"
            return
        fi

        if command -v python3 >/dev/null 2>&1; then
            python3 - "$SETTINGS_FILE" "$hook_type" "$hook_cmd" <<'PYEOF'
import sys, json

settings_file, hook_type, hook_cmd = sys.argv[1], sys.argv[2], sys.argv[3]

with open(settings_file, 'r') as f:
    data = json.load(f)

hooks = data.setdefault('hooks', {})
entries = hooks.setdefault(hook_type, [])

new_entry = {"hooks": [{"type": "command", "command": hook_cmd}]}
if hook_type == "PreToolUse":
    new_entry["matcher"] = ".*"

entries.append(new_entry)

with open(settings_file, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
            echo "→ Added $hook_type hook to .claude/settings.json"
        else
            echo "→ NOTE: python3 not found. Add this $hook_type hook manually to $SETTINGS_FILE:"
            echo "  { \"type\": \"command\", \"command\": \"$hook_cmd\" }"
        fi
    }

    _inject_hook "PreToolUse" "$PRE_TOOL_USE_HOOK" "hooks/pre-tool-use.sh"
    _inject_hook "Stop"       "$STOP_HOOK"         "hooks/stop.sh"
fi

# ── Step 8: Record installed version ─────────────────────────────
mkdir -p "$USER_DATA_DIR"
echo "$RESOLVED" > "$USER_DATA_DIR/.installed-version"
if [ -n "$PREV_CHECK" ]; then
    echo "$PREV_CHECK" > "$USER_DATA_DIR/.last-update-check"
else
    date +%s > "$USER_DATA_DIR/.last-update-check"
fi

# ── Step 9: Ensure user-data dir and worktree session are gitignored ─────────
_GITIGNORE="$PROJECT_ROOT/.gitignore"

# Remove legacy individual entries if present (migration to directory pattern)
_LEGACY_ENTRIES=(
    ".claude/user-data/session-summary.md"
    ".claude/user-data/.last-update-check"
    ".claude/user-data/.installed-version"
    ".claude/user-data/.auto-update"
)
if [ -f "$_GITIGNORE" ]; then
    for _LEGACY in "${_LEGACY_ENTRIES[@]}"; do
        # Use a temp file to remove the line in-place (portable, no sed -i -e portability issues)
        grep -vF "$_LEGACY" "$_GITIGNORE" > "$_GITIGNORE.tmp" && mv "$_GITIGNORE.tmp" "$_GITIGNORE" || true
    done
fi

# Add directory-level ignore (covers all user-data files at once)
_add_gitignore() {
    local _entry="$1"
    if [ -f "$_GITIGNORE" ]; then
        grep -qF "$_entry" "$_GITIGNORE" || echo "$_entry" >> "$_GITIGNORE"
    else
        echo "$_entry" >> "$_GITIGNORE"
    fi
}

_add_gitignore ".claude/user-data/"
_add_gitignore "!.claude/user-data/graphify.json"
_add_gitignore ".claude/.worktree-session"

echo "→ .gitignore updated (user-data dir pattern + worktree-session)"

# ── Step 10: Make scripts executable ─────────────────────────────
chmod +x "$INSTALL_DIR/scripts/"*.sh
chmod +x "$INSTALL_DIR/scripts/hooks/"*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/hooks/pre-tool-use/"*.sh 2>/dev/null || true
chmod +x "$INSTALL_DIR/scripts/hooks/stop/"*.sh 2>/dev/null || true

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
echo "  1. Run the setup-assistant in Claude:"
echo "       \"Help me set up this project with dev-team-agents\""
echo "  2. Commit the installation to your project:"
echo "       git add .claude/ && git commit -m \"chore: add dev-team-agents\""
echo "  3. To update later: .claude/dev-team-agents/scripts/update.sh"
echo "  4. To pin a version: .claude/dev-team-agents/scripts/update.sh v1.0.0"
echo ""
echo "Agents available at: .claude/agents/dev-team/"
echo "Skills available at: .claude/skills/"
echo ""
echo "  ┌─────────────────────────────────────────────────────────────────────┐"
echo "  │  Optional: Graphify (knowledge graph for this codebase)              │"
echo "  │                                                                      │"
echo "  │  Graphify indexes your codebase so agents can navigate code without  │"
echo "  │  reading every file — fewer tokens per task, faster responses.       │"
echo "  │                                                                      │"
echo "  │  To enable it, tell Claude:                                          │"
echo "  │    \"Set up Graphify for this project\"                               │"
echo "  └─────────────────────────────────────────────────────────────────────┘"
