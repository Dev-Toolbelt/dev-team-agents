#!/usr/bin/env bash
# Stop sub-script: mark the session idle on the task board (ADR-0018), so the board can
# tell "the agent is waiting for me" from "the agent is working". Runs on every Stop, so
# it forks python ONLY when this session already has a task record — a bash `[ -f ]`
# decides. Exits 0 always, prints nothing.
set -uo pipefail

PAYLOAD_FILE="${DEVTEAM_HOOK_PAYLOAD:-}"
[ -n "$PAYLOAD_FILE" ] && [ -f "$PAYLOAD_FILE" ] || exit 0
INPUT="$(cat "$PAYLOAD_FILE" 2>/dev/null)"

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
SESSION="$(devteam_task_board_session_id "$INPUT")"
[ -n "$SESSION" ] || exit 0
devteam_task_board_init || exit 0
[ -f "${TB_STATE_DIR}/task-board/${SESSION}.json" ] || exit 0
devteam_task_board_mark idle "$INPUT" >/dev/null 2>&1
exit 0
