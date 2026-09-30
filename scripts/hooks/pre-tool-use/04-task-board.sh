#!/usr/bin/env bash
# PreToolUse sub-script: feed the task board (ADR-0018) from the providers' pre-call hook:
#   Codex      `update_plan`  — payload {"tool_name":"update_plan","tool_input":{"plan":[…]}}
#   opencode   `todowrite`    — payload {"tool":"todowrite","args":{"todos":[…]},"sessionID":…}
#   review agent spawns (opens an In Review window):
#     Claude Code  {"tool_name":"Agent"|"Task","tool_input":{"subagent_type":"qa-specialist",…}}
#     Codex        {"tool_name":"spawn_agent","tool_input":{"agent_type":"code-reviewer",…}}
#     opencode     {"tool":"task","args":{"subagent_type":"qa-specialist",…},"sessionID":…}
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
SPAWN_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?(Agent|Task|task|spawn_agent)"'
REVIEW_AGENT_RE='(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)'

MODE=""
if [[ "$INPUT" =~ $CODEX_RE ]] || [[ "$INPUT" =~ $OPENCODE_RE ]]; then
    MODE="todo"
elif [[ "$INPUT" =~ $SPAWN_RE ]] && [[ "$INPUT" =~ $REVIEW_AGENT_RE ]]; then
    MODE="review"
else
    exit 0
fi

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
if [ "$MODE" = "todo" ]; then
    devteam_task_board_record "$INPUT" >/dev/null 2>&1
else
    devteam_task_board_has_record "$INPUT" || exit 0
    devteam_task_board_review_open "$INPUT" >/dev/null 2>&1
fi
exit 0
