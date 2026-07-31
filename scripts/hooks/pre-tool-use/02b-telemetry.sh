#!/usr/bin/env bash
# PreToolUse sub-script: queue telemetry events for agent spawns and devteam commands.
# Reads the Claude Code hook payload from stdin; exits 0 always (never blocks tool use).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMETRY_SEND="$SCRIPT_DIR/../../helpers/telemetry-send.sh"

# No-op if helper is missing
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
command -v python3 >/dev/null 2>&1 || exit 0

# Read the hook payload (stdin was captured by the dispatcher into DEVTEAM_HOOK_PAYLOAD,
# but PreToolUse dispatcher passes it via stdin directly to each sub-script)
PAYLOAD=""
if [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]; then
    PAYLOAD=$(cat "$DEVTEAM_HOOK_PAYLOAD" 2>/dev/null || true)
elif [ ! -t 0 ]; then
    PAYLOAD=$(cat 2>/dev/null || true)
fi

[ -n "$PAYLOAD" ] || exit 0

# Extract tool_name and relevant input fields
TOOL_NAME=$(python3 -c \
    "import json,sys; d=json.loads(sys.argv[1]); print(d.get('tool_name',''))" \
    "$PAYLOAD" 2>/dev/null || echo "")

[ -n "$TOOL_NAME" ] || exit 0

case "$TOOL_NAME" in
    Task)
        # An agent was spawned via the Task tool.
        # Description text is not logged — it may contain sensitive context.
        bash "$TELEMETRY_SEND" --queue "agent_spawned" '{}' 2>/dev/null || true
        ;;
    Bash)
        # Check if a /devteam:* command was invoked via Bash
        COMMAND=$(python3 -c \
            "import json,sys; d=json.loads(sys.argv[1]); i=d.get('tool_input',{}); print(i.get('command',''))" \
            "$PAYLOAD" 2>/dev/null || echo "")
        # Extract /devteam:<name> pattern from the command string
        DEVTEAM_CMD=$(printf '%s' "$COMMAND" | grep -oE '/devteam:[a-zA-Z0-9_-]+' | head -1 || true)
        if [ -n "$DEVTEAM_CMD" ]; then
            CMD_NAME=$(printf '%s' "$DEVTEAM_CMD" | sed 's|/devteam:||')
            PROPS="{\"command\": \"$CMD_NAME\"}"
            bash "$TELEMETRY_SEND" --queue "command_invoked" "$PROPS" 2>/dev/null || true
        fi
        ;;
esac

exit 0
