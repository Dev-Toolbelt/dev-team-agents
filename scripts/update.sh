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
LAST_CHECK_FILE="$USER_DATA_DIR/.last-update-check"
VERSION_FILE="$USER_DATA_DIR/.installed-version"
AUTO_UPDATE_FLAG="$USER_DATA_DIR/.auto-update"
TWENTY_FOUR_HOURS=86400

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"
INSTALL_URL="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/main/scripts/install.sh"

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

# ── HTTP tool detection (shared by both modes) ─────────────────────────────────

if command -v curl >/dev/null 2>&1; then
    HTTP_GET() { curl -fsSL "$1"; }
    HTTP_DL()  { curl -fsSL -o "$1" "$2"; }
elif command -v wget >/dev/null 2>&1; then
    HTTP_GET() { wget -qO- "$1"; }
    HTTP_DL()  { wget -qO "$1" "$2"; }
else
    [[ "${1:-}" == "--check" ]] && exit 0  # Hook mode: silent
    echo "✗ Neither curl nor wget found. Cannot download update." >&2
    exit 1
fi

# ── Silent check mode (PreToolUse hook) ────────────────────────────────────────

if [[ "${1:-}" == "--check" ]]; then
    # TTL: skip if checked within 24h
    if [ -f "$LAST_CHECK_FILE" ]; then
        LAST_CHECK=$(cat "$LAST_CHECK_FILE")
        NOW=$(date +%s)
        DIFF=$((NOW - LAST_CHECK))
        if [ "$DIFF" -lt "$TWENTY_FOUR_HOURS" ]; then
            exit 0
        fi
    fi

    # Update timestamp before network call — prevents hammering on bad-network sessions
    mkdir -p "$USER_DATA_DIR"
    date +%s > "$LAST_CHECK_FILE"

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

    [ -n "$LATEST" ] || exit 0

    CURRENT=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")
    [ "$CURRENT" != "unknown" ] && [ "$LATEST" != "unknown" ] || exit 0
    [ "$CURRENT" != "$LATEST" ] || exit 0

    # Auto-update mode: download installer, run it, clean up
    if [ -f "$AUTO_UPDATE_FLAG" ]; then
        echo ""
        echo "→ Auto-updating dev-team-agents: $CURRENT → $LATEST"
        TMP_INSTALLER=$(mktemp)
        trap 'rm -f "$TMP_INSTALLER"' EXIT
        HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL"
        bash "$TMP_INSTALLER" latest
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
    exit 0
fi

# ── Manual update mode ─────────────────────────────────────────────────────────

VERSION_ARG="${1:-latest}"

TMP_INSTALLER=$(mktemp)
trap 'rm -f "$TMP_INSTALLER"' EXIT

echo "→ Downloading latest installer from GitHub..."
HTTP_DL "$TMP_INSTALLER" "$INSTALL_URL"
bash "$TMP_INSTALLER" "$VERSION_ARG"
