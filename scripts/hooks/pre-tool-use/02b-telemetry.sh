#!/usr/bin/env bash
# PreToolUse sub-script: queue telemetry events for agent spawns and devteam commands.
# Coupled with stop/05-telemetry.sh — this script only queues events; that one
# is the only Stop-time flush path. Do not disable one without the other:
# queuing without flushing fills telemetry-queue.json to its 100-event cap and
# silently starts dropping the oldest entries (FIFO trim in telemetry-send.sh).
# Reads the Claude Code hook payload from stdin; exits 0 always (never blocks tool use).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMETRY_SEND="$SCRIPT_DIR/../../helpers/telemetry-send.sh"

# No-op if helper is missing
[ -f "$TELEMETRY_SEND" ] || exit 0

# Read the hook payload (stdin was captured by the dispatcher into DEVTEAM_HOOK_PAYLOAD,
# but PreToolUse dispatcher passes it via stdin directly to each sub-script)
PAYLOAD=""
if [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]; then
    PAYLOAD=$(cat "$DEVTEAM_HOOK_PAYLOAD" 2>/dev/null || true)
elif [ ! -t 0 ]; then
    PAYLOAD=$(cat 2>/dev/null || true)
fi

[ -n "$PAYLOAD" ] || exit 0

# Cheap early-exit BEFORE the state-dir resolution, consent guard and python3
# check below: only Task and Bash tool calls are ever queued, so a raw
# substring check on the still-unparsed payload skips all of that for every
# other tool (Read, Edit, Grep, ...) — the majority of calls in a session. The
# match itself also tells us which tool matched, so no separate python3 parse
# of tool_name is needed. The python3 parse of tool_input below remains the
# source of truth for the Bash branch's command string.
case "$PAYLOAD" in
    *'"tool_name":"Task"'*|*'"tool_name": "Task"'*)   TOOL_NAME="Task" ;;
    *'"tool_name":"Bash"'*|*'"tool_name": "Bash"'*)   TOOL_NAME="Bash" ;;
    *) exit 0 ;;
esac

# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "$SCRIPT_DIR/../lib/data-dirs.sh"
# telemetry-queue.json and state.json are machine-local (ADR-0013): resolve
# through the `state-dir` pointer instead of the old hardcoded in-project
# path, so this queues to the store once a project has run `devteam upgrade`.
# Resolved via git, like session-start.sh and the other hooks — NOT via a
# fixed number of `..` hops from SCRIPT_DIR, which breaks under the `link`/
# `copy` bind modes (default on macOS/Linux): those insert an extra `core/`
# symlink segment (.dev-team-agents/core/scripts/hooks/...) that a hardcoded
# hop count does not account for.
MAIN_REPO_ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
[ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$(pwd)"
USER_DATA_DIR="$(devteam_state_dir "$MAIN_REPO_ROOT")"
# preferences.json is a separate, PORTABLE record (unlike state.json/queue
# above): follow the resolved preference cascade projection when present,
# falling back to the legacy in-project file otherwise. See devteam_prefs_file
# in data-dirs.sh.
PREFS_FILE="$(devteam_prefs_file "$MAIN_REPO_ROOT")"
# Propagated so telemetry-send.sh (scripts/helpers/, not sourced here) resolves
# its own queue/state files against the same machine-local directory, and its
# own consent check against the same resolved preferences file, instead of its
# script-relative defaults, which are always the old co-located in-project path.
export DEVTEAM_USER_DATA_DIR="$USER_DATA_DIR"
export DEVTEAM_PREFS_FILE="$PREFS_FILE"

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
