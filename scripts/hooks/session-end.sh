#!/usr/bin/env bash
# SessionEnd hook (Claude Code): mark the session ended on the task board and raise
# `tasks.session_abandoned` when it still has open tasks (ADR-0018). A single script, not a
# dispatcher — nothing else listens to this event. Forks python only when the session
# already has a task record. Exits 0 always, prints nothing.
unset BASH_ENV ENV
set -uo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/../lib/python.sh"
# shellcheck source=../lib/python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

INPUT="$(cat)"
# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/lib" && pwd)/task-board.sh"
SESSION="$(devteam_task_board_session_id "$INPUT")"
[ -n "$SESSION" ] || exit 0
devteam_task_board_init || exit 0
devteam_task_board_clear_turn "$SESSION" prompt
[ -f "${TB_STATE_DIR}/task-board/${SESSION}.json" ] || exit 0
devteam_task_board_mark ended "$INPUT" >/dev/null 2>&1
exit 0
