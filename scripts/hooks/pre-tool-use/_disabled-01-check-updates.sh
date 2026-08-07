#!/usr/bin/env bash
# PreToolUse sub-script: silent TTL-based update check.
# Notifies Claude when a new version of dev-team-agents is available.
# Auto-updates when auto_update is enabled (or the legacy .auto-update flag exists).
#
# This file is the orchestrator only — preference reads, TTL cache, HTTP tool
# detection, ETag-cached release fetch, notification format and the auto-update
# trigger all live in ../lib/update-check.sh.
#
# Hot path (checked within the TTL window) is pure bash: no subprocess is
# spawned at all. This hook runs on EVERY tool call.
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
LIB_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/update-check.sh"
[ -f "$LIB_FILE" ] || exit 0
# shellcheck source=scripts/hooks/lib/update-check.sh
. "$LIB_FILE"

USER_DATA_DIR="$INSTALL_DIR/user-data"
LAST_CHECK_FILE="$USER_DATA_DIR/.last-update-check"
VERSION_FILE="$USER_DATA_DIR/.installed-version"
PREFS_FILE="$USER_DATA_DIR/preferences.json"
INTERVAL_CACHE_FILE="$USER_DATA_DIR/.update-check-interval"
ETAG_FILE="$USER_DATA_DIR/.last-releases-etag"
# Cached latest-version string, paired with the ETag. On a 304 (release
# unchanged) it is reused, so a local install that is behind the still-latest
# release is not silently treated as up to date.
VERSION_CACHE_FILE="$USER_DATA_DIR/.last-releases-version"

GITHUB_OWNER="Dev-Toolbelt"
GITHUB_REPO="dev-team-agents"
GITHUB_API="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}"
# The installer URL is deliberately NOT built here. Auto-update resolves it via
# scripts/lib/installer-fetch.sh so the unattended path gets the same ref
# pinning and payload verification as the manual `update.sh`.

# ── TTL gate (hot path — must stay fork-free) ─────────────────────────────────
NOW=$(uc_now_epoch)
INTERVAL_HOURS=$(uc_interval_hours "$PREFS_FILE" "$INTERVAL_CACHE_FILE")
uc_ttl_fresh "$LAST_CHECK_FILE" "$INTERVAL_HOURS" "$NOW" && exit 0

# ── Cold path: network check ──────────────────────────────────────────────────
uc_setup_http || exit 0

# Update the timestamp before the network call — prevents hammering on
# bad-network sessions.
mkdir -p "$USER_DATA_DIR" || exit 0
printf '%s\n' "$NOW" > "$LAST_CHECK_FILE"

LATEST=$(uc_fetch_latest "$GITHUB_API" "$ETAG_FILE" "$VERSION_CACHE_FILE")
[ -n "$LATEST" ] || exit 0

CURRENT=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")
if [ "$CURRENT" = "unknown" ]; then
    echo "→ dev-team-agents: could not determine the installed version" \
         "($VERSION_FILE missing or unreadable). Update checks are paused" \
         "until it is restored — run /devteam:health-check to repair it." >&2
    exit 0
fi
[ "$LATEST" != "unknown" ] || exit 0
[ "$CURRENT" != "$LATEST" ] || exit 0

# ── Notify / auto-update ──────────────────────────────────────────────────────
LANG_PREF="en"
UC_SUPPRESS="false"
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    LANG_PREF=$(python3 -c \
        "import json; d=json.load(open('$PREFS_FILE')); print(d.get('language','en'))" \
        2>/dev/null || echo "en")
    UC_SUPPRESS=$(python3 -c \
        "import json,sys; d=json.load(open('$PREFS_FILE')); v=d.get('suppress_notifications',False); print('true' if v is True else ('false' if v is False else ','.join(v)))" \
        2>/dev/null || echo "false")
fi
export UC_SUPPRESS

if uc_auto_update_enabled "$PREFS_FILE" "$USER_DATA_DIR"; then
    if uc_perform_auto_update "$CURRENT" "$LATEST" "$INSTALL_DIR"; then
        uc_notify "info" "$(uc_message updated "$LANG_PREF" "$CURRENT" "$LATEST")"
    else
        uc_notify "warning" "$(uc_message available "$LANG_PREF" "$CURRENT" "$LATEST")"
    fi
    exit 0
fi

uc_notify "warning" "$(uc_message available "$LANG_PREF" "$CURRENT" "$LATEST")"
exit 0
