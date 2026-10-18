#!/usr/bin/env bash
# Session rename (opencode only, from the plugin's `session.updated` event): write the session's
# new title into its task-board record, so the board shows it without waiting for a turn. Claude
# Code and Codex need no hook — the CLI re-reads their own title files at view time
# (`tasks.live_title`). Forks python only when the session already has a record. Exits 0 always,
# prints nothing.
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
[ -f "${TB_STATE_DIR}/task-board/${SESSION}.json" ] || exit 0
devteam_task_board_retitle "$INPUT"
exit 0
