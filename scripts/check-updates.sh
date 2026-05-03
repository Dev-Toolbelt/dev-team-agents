#!/bin/bash
# check-updates.sh — Checks if a new version of dev-team-agents is available.
# Runs silently if within 24h of last check. Notifies Claude if a new tag exists.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAST_CHECK_FILE="$INSTALL_DIR/.last-update-check"
VERSION_FILE="$INSTALL_DIR/.installed-version"
TWENTY_FOUR_HOURS=86400

# Check if within TTL window
if [ -f "$LAST_CHECK_FILE" ]; then
    LAST_CHECK=$(cat "$LAST_CHECK_FILE")
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_CHECK))
    if [ "$DIFF" -lt "$TWENTY_FOUR_HOURS" ]; then
        exit 0  # Silent — checked recently
    fi
fi

# Update timestamp
date +%s > "$LAST_CHECK_FILE"

# Fetch latest tags (quiet, non-blocking)
cd "$INSTALL_DIR"
if ! git fetch --tags --quiet 2>/dev/null; then
    exit 0  # No network — fail silently
fi

# Get versions
CURRENT=$(cat "$VERSION_FILE" 2>/dev/null || git describe --tags HEAD 2>/dev/null || echo "unknown")
LATEST=$(git describe --tags "$(git rev-list --tags --max-count=1)" 2>/dev/null || echo "unknown")

if [ "$LATEST" = "unknown" ] || [ "$CURRENT" = "unknown" ]; then
    exit 0
fi

if [ "$CURRENT" != "$LATEST" ]; then
    echo ""
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│  dev-team-agents update available                       │"
    echo "│  Current: $CURRENT  →  Latest: $LATEST                  │"
    echo "│  Run: ~/.claude/dev-team-agents/install.sh latest       │"
    echo "│  See CHANGELOG.md for what changed.                     │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo ""
fi
