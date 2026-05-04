#!/bin/bash
# check-updates.sh — Checks if a new version of dev-team-agents is available.
# Runs silently if within 24h of last check. Notifies Claude if a new tag exists.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAST_CHECK_FILE="$INSTALL_DIR/.last-update-check"
VERSION_FILE="$INSTALL_DIR/.installed-version"
TWENTY_FOUR_HOURS=86400

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"

# Check if within TTL window
if [ -f "$LAST_CHECK_FILE" ]; then
    LAST_CHECK=$(cat "$LAST_CHECK_FILE")
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_CHECK))
    if [ "$DIFF" -lt "$TWENTY_FOUR_HOURS" ]; then
        exit 0  # Silent — checked recently
    fi
fi

# Update timestamp before network call — prevents hammering on bad-network sessions
date +%s > "$LAST_CHECK_FILE"

# HTTP tool detection
if command -v curl >/dev/null 2>&1; then
    HTTP_GET() { curl -fsSL "$1"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_GET() { wget -qO- "$1"; }
else
    exit 0  # No HTTP tool — silent
fi

# Fetch latest version via GitHub API
API_RESP=$(HTTP_GET "${GITHUB_API}/releases/latest" 2>/dev/null || true)
LATEST=$(printf '%s' "$API_RESP" \
    | grep '"tag_name"' | head -1 \
    | sed 's/.*"tag_name": *"\([^"]*\)".*/\1/')

# Fallback: tags list (rate-limited or no formal release)
if [ -z "$LATEST" ]; then
    API_RESP=$(HTTP_GET "${GITHUB_API}/tags" 2>/dev/null || true)
    LATEST=$(printf '%s' "$API_RESP" \
        | grep '"name"' | head -1 \
        | sed 's/.*"name": *"\([^"]*\)".*/\1/')
fi

[ -n "$LATEST" ] || exit 0  # No network or rate-limited — silent

# Get versions
CURRENT=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")

if [ "$LATEST" = "unknown" ] || [ "$CURRENT" = "unknown" ]; then
    exit 0
fi

if [ "$CURRENT" != "$LATEST" ]; then
    echo ""
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│  dev-team-agents update available                       │"
    echo "│  Current: $CURRENT  →  Latest: $LATEST                  │"
    echo "│  Run: .claude/dev-team-agents/scripts/install.sh latest │"
    echo "│  See .claude/dev-team-agents/CHANGELOG.md for details.  │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo ""
fi
