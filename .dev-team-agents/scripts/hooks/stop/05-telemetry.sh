#!/usr/bin/env bash
# Stop sub-script: queue a session_end telemetry event, queue per-agent token/
# model usage (see ../lib/agent-usage.sh), and flush if TTL reached.
# Coupled with pre-tool-use/02b-telemetry.sh — this is the only Stop-time
# flush path. Do not disable one without the other: disabling this alone
# leaves PreToolUse events queued with nothing to flush them.
# Exits 0 always — telemetry must never block the Stop hook.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TELEMETRY_SEND="$SCRIPT_DIR/../../helpers/telemetry-send.sh"

# Quiet flag: accepted but telemetry is always silent regardless
[ "${1:-}" = "--quiet" ] && true

# No-op if helper is missing (e.g., dev worktree without helpers/)
[ -f "$TELEMETRY_SEND" ] || exit 0

# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "$SCRIPT_DIR/../lib/data-dirs.sh"
# telemetry-queue.json, state.json and .agent-usage-cache are machine-local
# (ADR-0013): resolve through the `state-dir` pointer instead of the old
# hardcoded in-project path. Resolved via git, like session-start.sh and the
# other hooks — NOT via a fixed number of `..` hops from SCRIPT_DIR, which
# breaks under the `link` bind mode (default on macOS/Linux):
# `.dev-team-agents/scripts` is a symlink into the store, so hops from a
# physically resolved SCRIPT_DIR land in the store version rather than in the
# project.
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
        'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("stop_hook_active",False))' \
        "$DEVTEAM_HOOK_PAYLOAD" 2>/dev/null || echo "false")
fi

# Queue session_end event
PROPS="{\"stop_hook_active\": $( [ "$STOP_REASON" = "True" ] && echo "true" || echo "false" )}"
bash "$TELEMETRY_SEND" --queue "session_end" "$PROPS" 2>/dev/null || true

# Queue per-agent token/model usage — see lib/agent-usage.sh for the
# transcript-scan approach and its documented dedup tradeoff.
if [ -f "$SCRIPT_DIR/../lib/agent-usage.sh" ] && [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ]; then
    # shellcheck source=scripts/hooks/lib/agent-usage.sh
    . "$SCRIPT_DIR/../lib/agent-usage.sh"
    devteam_queue_agent_usage "$DEVTEAM_HOOK_PAYLOAD" "$USER_DATA_DIR" "$TELEMETRY_SEND" 2>/dev/null || true
fi

# Flush if TTL reached or queue is full
bash "$TELEMETRY_SEND" --flush 2>/dev/null || true

exit 0
