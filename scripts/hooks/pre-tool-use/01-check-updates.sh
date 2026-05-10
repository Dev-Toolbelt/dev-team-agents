#!/usr/bin/env bash
# PreToolUse sub-script: silent TTL-based update check.
# Notifies Claude when a new version of dev-team-agents is available.
# Auto-updates if .claude/user-data/.auto-update flag exists.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
USER_DATA_DIR="$(dirname "$INSTALL_DIR")/user-data"
LAST_CHECK_FILE="$USER_DATA_DIR/.last-update-check"
VERSION_FILE="$USER_DATA_DIR/.installed-version"
AUTO_UPDATE_FLAG="$USER_DATA_DIR/.auto-update"
TWENTY_FOUR_HOURS=86400

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"
INSTALL_URL="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/scripts/install.sh"

# TTL: skip if checked within 24h
if [ -f "$LAST_CHECK_FILE" ]; then
    LAST_CHECK=$(cat "$LAST_CHECK_FILE")
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_CHECK))
    if [ "$DIFF" -lt "$TWENTY_FOUR_HOURS" ]; then
        exit 0
    fi
fi

# HTTP tool detection
if command -v curl >/dev/null 2>&1; then
    HTTP_GET() { curl -fsSL --connect-timeout 5 --max-time 10 "$1"; }
    HTTP_DL()  { curl -fsSL --connect-timeout 5 --max-time 30 -o "$1" "$2"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_GET() { wget -qO- "$1"; }
    HTTP_DL()  { wget -qO "$1" "$2"; }
else
    exit 0
fi

# Update timestamp before network call — prevents hammering on bad-network sessions
mkdir -p "$USER_DATA_DIR" || exit 0
date +%s > "$LAST_CHECK_FILE"

# Fetch latest version via GitHub API
API_RESP=$(HTTP_GET "${GITHUB_API}/releases/latest" 2>/dev/null || true)
LATEST=$(printf '%s' "$API_RESP" \
    | grep '"tag_name"' | head -1 \
    | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

if [ -z "$LATEST" ]; then
    API_RESP=$(HTTP_GET "${GITHUB_API}/tags" 2>/dev/null || true)
    LATEST=$(printf '%s' "$API_RESP" \
        | grep '"name"' | head -1 \
        | sed 's/.*"name": *"\([^"]*\)".*/\1/')
fi

[ -n "$LATEST" ] || exit 0

CURRENT=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")
[ "$CURRENT" != "unknown" ] && [ "$LATEST" != "unknown" ] || exit 0
[ "$CURRENT" != "$LATEST" ] || exit 0

# Auto-update mode
if [ -f "$AUTO_UPDATE_FLAG" ]; then
    echo ""
    echo "→ Auto-updating dev-team-agents: $CURRENT → $LATEST"
    TMP_INSTALLER=$(mktemp)
    trap 'rm -f "$TMP_INSTALLER"' EXIT
    HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL"
    bash "$TMP_INSTALLER" latest
    echo ""
    echo "┌──────────────────────────────────────────────────────────────┐"
    echo "│  dev-team-agents updated to $LATEST                         │"
    echo "│  Run a health check to verify the installation:             │"
    echo "│    \"Run a health check on this project\"                     │"
    echo "└──────────────────────────────────────────────────────────────┘"
    echo ""
    exit 0
fi

# Notify only
echo ""
echo "┌──────────────────────────────────────────────────────────────┐"
echo "│  dev-team-agents update available                            │"
echo "│  Current: $CURRENT  →  Latest: $LATEST"
echo "│  Run: .claude/dev-team-agents/scripts/update.sh             │"
echo "│  See .claude/dev-team-agents/CHANGELOG.md for details.      │"
echo "│  To auto-update: update.sh --enable-auto                    │"
echo "└──────────────────────────────────────────────────────────────┘"
echo ""
