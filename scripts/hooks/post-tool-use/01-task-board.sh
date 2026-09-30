#!/usr/bin/env bash
# PostToolUse sub-script: capture Claude Code's todo tools (TodoWrite, TaskCreate,
# TaskUpdate) into the task board (ADR-0018). The settings matcher already narrows the
# event to those tools; the string test below repeats it so a stray registration with a
# wider matcher still forks nothing for another tool. Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
TOOL_RE='"tool_name"[[:space:]]*:[[:space:]]*"(TodoWrite|TaskCreate|TaskUpdate)"'
[[ "$INPUT" =~ $TOOL_RE ]] || exit 0

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
devteam_task_board_record "$INPUT" >/dev/null 2>&1
exit 0
