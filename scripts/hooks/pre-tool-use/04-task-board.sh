#!/usr/bin/env bash
# PreToolUse sub-script: capture the todo tools of the providers that only expose a
# pre-call hook into the task board (ADR-0018):
#   Codex      `update_plan`  — payload {"tool_name":"update_plan","tool_input":{"plan":[…]}}
#   opencode   `todowrite`    — payload {"tool":"todowrite","args":{"todos":[…]},"sessionID":…}
# Claude Code's todo tools are captured after the call, by post-tool-use/01-task-board.sh.
#
# This runs on EVERY tool call, so the gate is a bash string test on the payload: for any
# other tool nothing is sourced and no python is forked (acceptance criterion 9). The
# patterns need the JSON key immediately followed by the tool name, so a shell command
# that merely mentions `update_plan` (its quotes are escaped in the payload) does not match.
# Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
CODEX_RE='"tool_name"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?update_plan"'
OPENCODE_RE='"tool"[[:space:]]*:[[:space:]]*"todowrite"'
if ! [[ "$INPUT" =~ $CODEX_RE ]] && ! [[ "$INPUT" =~ $OPENCODE_RE ]]; then
    exit 0
fi

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
devteam_task_board_record "$INPUT" >/dev/null 2>&1
exit 0
