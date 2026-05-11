#!/usr/bin/env bash
# update.sh — Unified update manager for dev-team-agents.
#
# Modes:
#   --check          Silent TTL-based update check (used by PreToolUse hook)
#   --enable-auto    Enable automatic updates (creates .auto-update flag)
#   --disable-auto   Disable automatic updates (removes .auto-update flag)
#   [latest|vX.Y.Z]  Download the latest install.sh from GitHub and run it

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_DATA_DIR="$(dirname "$INSTALL_DIR")/user-data"
AUTO_UPDATE_FLAG="$USER_DATA_DIR/.auto-update"

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
INSTALL_URL="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/scripts/install.sh"

# ── Rollback mode ─────────────────────────────────────────────────────────────

if [[ "${1:-}" == "--rollback" ]]; then
    PREVIOUS_DIR="${INSTALL_DIR}.previous"
    if [ ! -d "$PREVIOUS_DIR" ]; then
        echo "No previous version to roll back to." >&2
        exit 1
    fi
    rm -rf "$INSTALL_DIR"
    mv "$PREVIOUS_DIR" "$INSTALL_DIR"
    echo "✓ Rolled back to previous version."
    exit 0
fi

# ── Silent check mode — delegates to hook sub-script ─────────────────────────

if [[ "${1:-}" == "--check" ]]; then
    exec bash "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh"
fi

# ── Enable / Disable auto-update ──────────────────────────────────────────────

if [[ "${1:-}" == "--enable-auto" ]]; then
    mkdir -p "$USER_DATA_DIR"
    touch "$AUTO_UPDATE_FLAG"
    echo "✓ Auto-update enabled. dev-team-agents will update automatically when a new version is detected."
    exit 0
fi

if [[ "${1:-}" == "--disable-auto" ]]; then
    rm -f "$AUTO_UPDATE_FLAG"
    echo "✓ Auto-update disabled. You will be notified but updates won't be applied automatically."
    exit 0
fi

# ── HTTP tool detection ────────────────────────────────────────────────────────

if command -v curl >/dev/null 2>&1; then
    HTTP_DL() { curl -fsSL -o "$1" "$2"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_DL() { wget -qO "$1" "$2"; }
else
    echo "✗ Neither curl nor wget found. Cannot download update." >&2
    exit 1
fi

# ── Manual update mode ─────────────────────────────────────────────────────────

VERSION_ARG="${1:-latest}"

TMP_INSTALLER=$(mktemp)
trap 'rm -f "$TMP_INSTALLER"' EXIT

echo "→ Downloading latest installer from GitHub..."
HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL"
bash "$TMP_INSTALLER" "$VERSION_ARG"

echo ""
echo "┌──────────────────────────────────────────────────────────────────┐"
echo "│  Installation complete. Run a health check to verify that all   │"
echo "│  project configuration is up to date with this version:         │"
echo "│    \"Run a health check on this project\"                         │"
echo "└──────────────────────────────────────────────────────────────────┘"
echo ""
