#!/usr/bin/env bash
# rollback.sh — Reinstall a previous version of dev-team-agents.
#
# Usage:
#   bash rollback.sh              # roll back to last-known good version (.installed-version.prev)
#   bash rollback.sh v1.2.3       # roll back to a specific version tag
#
# The script re-downloads the requested version via the same install path
# used by update.sh, so network access is required.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_DATA_DIR="$(dirname "$INSTALL_DIR")/user-data"
PREV_VERSION_FILE="$USER_DATA_DIR/.installed-version.prev"
CURRENT_VERSION_FILE="$USER_DATA_DIR/.installed-version"

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
INSTALL_URL="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/scripts/install.sh"

# ── Resolve target version ─────────────────────────────────────────────────────

if [ -n "${1:-}" ]; then
    TARGET="$1"
else
    if [ ! -f "$PREV_VERSION_FILE" ]; then
        echo "✗ No previous version recorded in $PREV_VERSION_FILE" >&2
        echo "  Specify a version explicitly: bash rollback.sh v1.2.3" >&2
        exit 1
    fi
    TARGET=$(cat "$PREV_VERSION_FILE")
fi

CURRENT=""
[ -f "$CURRENT_VERSION_FILE" ] && CURRENT=$(cat "$CURRENT_VERSION_FILE")

echo "→ Rolling back from ${CURRENT:-unknown} to $TARGET ..."

# ── HTTP tool detection ────────────────────────────────────────────────────────

if command -v curl >/dev/null 2>&1; then
    HTTP_DL() { curl -fsSL -o "$1" "$2"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_DL() { wget -qO "$1" "$2"; }
else
    echo "✗ Neither curl nor wget found. Cannot download." >&2
    exit 1
fi

# ── Download and run the installer at the target version ──────────────────────

TMP_INSTALLER=$(mktemp)
trap 'rm -f "$TMP_INSTALLER"' EXIT

echo "→ Downloading installer from GitHub..."
if ! HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL" 2>/dev/null; then
    echo "✗ Failed to download installer. Check network connectivity." >&2
    exit 1
fi

bash "$TMP_INSTALLER" "$TARGET"

# Invalidate context cache after version change
rm -f ".claude/user-data/.context-cache.json" 2>/dev/null || true

echo ""
echo "✓ Rolled back to $TARGET."
echo "  If the issue persists, check the changelog: https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases"
