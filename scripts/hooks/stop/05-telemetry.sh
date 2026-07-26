#!/usr/bin/env bash
# Stop sub-script: queue a session_end telemetry event and flush if TTL reached.
# Exits 0 always — telemetry must never block the Stop hook.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMETRY_SEND="$SCRIPT_DIR/../../helpers/telemetry-send.sh"

# Quiet flag: accepted but telemetry is always silent regardless
[ "${1:-}" = "--quiet" ] && true

# No-op if helper is missing (e.g., dev worktree without helpers/)
[ -f "$TELEMETRY_SEND" ] || exit 0

USER_DATA_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)/user-data"
PREFS_FILE="$USER_DATA_DIR/preferences.json"

# Opt-out guard
_telemetry_enabled() {
    [ -f "$PREFS_FILE" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0
    local val
    val=$(python3 -c \
        "import json; d=json.load(open('$PREFS_FILE')); print(str(d.get('telemetry',True)).lower())" \
        2>/dev/null || echo "true")
    [ "$val" = "true" ]
}

_telemetry_enabled || exit 0

# Extract session metadata from the Stop hook payload (DEVTEAM_HOOK_PAYLOAD)
STOP_REASON=""
if [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ] && command -v python3 >/dev/null 2>&1; then
    STOP_REASON=$(python3 -c \
        "import json; d=json.load(open('$DEVTEAM_HOOK_PAYLOAD')); print(d.get('stop_hook_active',False))" \
        2>/dev/null || echo "false")
fi

# Queue session_end event
PROPS="{\"stop_hook_active\": $( [ "$STOP_REASON" = "True" ] && echo "true" || echo "false" )}"
bash "$TELEMETRY_SEND" --queue "session_end" "$PROPS" 2>/dev/null || true

# Flush if TTL reached or queue is full
bash "$TELEMETRY_SEND" --flush 2>/dev/null || true

exit 0
