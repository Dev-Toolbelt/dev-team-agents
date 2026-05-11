#!/usr/bin/env bash
# PreToolUse sub-script: silent TTL-based update check.
# Notifies Claude when a new version of dev-team-agents is available.
# Auto-updates if .claude/user-data/.auto-update flag exists.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
USER_DATA_DIR="$(dirname "$INSTALL_DIR")/user-data"
LAST_CHECK_FILE="$USER_DATA_DIR/.last-update-check"
VERSION_FILE="$USER_DATA_DIR/.installed-version"
PREFS_FILE="$USER_DATA_DIR/preferences.json"

# Read update_check_interval_hours from preferences.json (default: 24h)
UPDATE_INTERVAL_HOURS=24
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    UPDATE_INTERVAL_HOURS=$(python3 -c \
        "import json; d=json.load(open('$PREFS_FILE')); print(d.get('update_check_interval_hours',24))" \
        2>/dev/null || echo 24)
fi
TWENTY_FOUR_HOURS=$(( UPDATE_INTERVAL_HOURS * 3600 ))

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

ETAG_FILE="$USER_DATA_DIR/.last-releases-etag"

# HTTP tool detection
if command -v curl >/dev/null 2>&1; then
    HTTP_GET() { curl -fsSL --connect-timeout 5 --max-time 10 "$1"; }
    HTTP_DL()  { curl -fsSL --connect-timeout 5 --max-time 30 -o "$1" "$2"; }
else
    # wget path: ETag not supported; fall through without ETag caching
    if command -v wget >/dev/null 2>&1; then
        HTTP_GET() { wget -qO- "$1"; }
        HTTP_DL()  { wget -qO "$1" "$2"; }
    else
        exit 0
    fi
fi

# Update timestamp before network call — prevents hammering on bad-network sessions
mkdir -p "$USER_DATA_DIR" || exit 0
date +%s > "$LAST_CHECK_FILE"

# Fetch latest version via GitHub API (with ETag caching when curl is available)
TMP_HEADERS=$(mktemp)
TMP_BODY=$(mktemp)
trap 'rm -f "$TMP_HEADERS" "$TMP_BODY"' EXIT

RELEASES_URL="${GITHUB_API}/releases/latest"
HTTP_STATUS=""

if command -v curl >/dev/null 2>&1; then
    # Build ETag conditional request header if we have a cached ETag
    ETAG_HEADER=""
    if [ -f "$ETAG_FILE" ]; then
        CACHED_ETAG=$(cat "$ETAG_FILE" 2>/dev/null || true)
        [ -n "$CACHED_ETAG" ] && ETAG_HEADER="-H \"If-None-Match: ${CACHED_ETAG}\""
    fi

    HTTP_STATUS=$(eval curl -sS --connect-timeout 5 --max-time 10 \
        -D "$TMP_HEADERS" \
        -o "$TMP_BODY" \
        -w "%{http_code}" \
        "$ETAG_HEADER" \
        "\"${RELEASES_URL}\"" 2>/dev/null || echo "000")

    if [ "$HTTP_STATUS" = "304" ]; then
        # Not Modified — no new release since last check
        exit 0
    fi

    if [ "$HTTP_STATUS" = "200" ]; then
        # Save new ETag for next check
        NEW_ETAG=$(grep -i '^etag:' "$TMP_HEADERS" | head -1 | sed 's/^[Ee][Tt][Aa][Gg]: *//;s/\r//' || true)
        [ -n "$NEW_ETAG" ] && printf '%s' "$NEW_ETAG" > "$ETAG_FILE"
    fi

    API_RESP=$(cat "$TMP_BODY" 2>/dev/null || true)
else
    API_RESP=$(HTTP_GET "${RELEASES_URL}" 2>/dev/null || true)
fi

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

# Auto-update mode: check preferences.json first, fall back to legacy flag file
AUTO_UPDATE=false
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    AUTO_UPDATE=$(python3 -c \
        "import json; d=json.load(open('$PREFS_FILE')); print(str(d.get('auto_update',False)).lower())" \
        2>/dev/null || echo false)
fi
# Legacy flag file support (migration period)
[ -f "${USER_DATA_DIR}/.auto-update" ] && AUTO_UPDATE=true

if [ "$AUTO_UPDATE" = "true" ]; then
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
