#!/usr/bin/env bash
# DISABLED (2026-08-06) — pending review, see CLAUDE-md/hooks.md § Disabled Hooks.
# Rename back to 02b-telemetry.sh to re-enable.
# WARNING: re-enable together with stop/_disabled-05-telemetry.sh, never alone.
# This script only queues events; 05-telemetry.sh is the only Stop-time flush
# path. Queuing without flushing fills telemetry-queue.json to its 100-event
# cap and silently starts dropping the oldest entries (FIFO trim in
# telemetry-send.sh) with no user-visible warning.
# PreToolUse sub-script: queue telemetry events for agent spawns and devteam commands.
# Reads the Claude Code hook payload from stdin; exits 0 always (never blocks tool use).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMETRY_SEND="$SCRIPT_DIR/../../helpers/telemetry-send.sh"

# No-op if helper is missing
[ -f "$TELEMETRY_SEND" ] || exit 0

USER_DATA_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)/user-data"
PREFS_FILE="$USER_DATA_DIR/preferences.json"

# Read the hook payload (stdin was captured by the dispatcher into DEVTEAM_HOOK_PAYLOAD,
# but PreToolUse dispatcher passes it via stdin directly to each sub-script)
PAYLOAD=""
if [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]; then
    PAYLOAD=$(cat "$DEVTEAM_HOOK_PAYLOAD" 2>/dev/null || true)
elif [ ! -t 0 ]; then
    PAYLOAD=$(cat 2>/dev/null || true)
fi

[ -n "$PAYLOAD" ] || exit 0

# Cheap early-exit BEFORE the consent guard / python3 check below: only Task
# and Bash tool calls are ever queued, so a raw substring check on the
# still-unparsed payload skips the consent subshell and python3 fork entirely
# for every other tool (Read, Edit, Grep, ...) — the majority of calls in a
# session. The match itself also tells us which tool matched, so no separate
# python3 parse of tool_name is needed. The python3 parse of tool_input below
# remains the source of truth for the Bash branch's command string.
case "$PAYLOAD" in
    *'"tool_name":"Task"'*|*'"tool_name": "Task"'*)   TOOL_NAME="Task" ;;
    *'"tool_name":"Bash"'*|*'"tool_name": "Bash"'*)   TOOL_NAME="Bash" ;;
    *) exit 0 ;;
esac

# Consent guard — single definition in scripts/lib/telemetry-guard.sh, fails
# closed. A missing guard file means no consent could be verified: skip.
[ -f "$SCRIPT_DIR/../../lib/telemetry-guard.sh" ] || exit 0
# Path is repo-root-relative on purpose — see scripts/helpers/telemetry-send.sh.
# The directive must sit directly above the `.` line; a guard between the two
# detaches it and the source goes unresolved again.
# shellcheck source=scripts/lib/telemetry-guard.sh
. "$SCRIPT_DIR/../../lib/telemetry-guard.sh"

_telemetry_enabled "$PREFS_FILE" || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

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
