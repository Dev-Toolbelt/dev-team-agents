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

# Consent guard — single definition in scripts/lib/telemetry-guard.sh, fails
# closed. A missing guard file means no consent could be verified: skip.
[ -f "$SCRIPT_DIR/../../lib/telemetry-guard.sh" ] || exit 0
# Path is repo-root-relative on purpose — see scripts/helpers/telemetry-send.sh.
# The directive must sit directly above the `.` line; a guard between the two
# detaches it and the source goes unresolved again.
# shellcheck source=scripts/lib/telemetry-guard.sh
. "$SCRIPT_DIR/../../lib/telemetry-guard.sh"

_telemetry_enabled || exit 0

# Fast-path: the dispatcher reports a purely conversational Stop (no staged or
# unstaged change, no commit today). Do not record a session_end for a session
# that produced nothing — the Stop hook fires on every assistant turn, so those
# events are pure noise and cost two python3 forks each. The flush still runs:
# it is internally TTL-gated (24h) and is the only delivery path for events
# queued by the PreToolUse hooks, which must not stall in read-only sessions.
if [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ]; then
    bash "$TELEMETRY_SEND" --flush 2>/dev/null || true
    exit 0
fi

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
