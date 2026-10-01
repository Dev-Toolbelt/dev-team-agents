#!/usr/bin/env bash
# PreToolUse sub-script: feed the task board (ADR-0018) from the providers' pre-call hook:
#   Codex      `update_plan`  — payload {"tool_name":"update_plan","tool_input":{"plan":[…]}}
#   opencode   `todowrite`    — payload {"tool":"todowrite","args":{"todos":[…]},"sessionID":…}
#   any agent spawn (a task of its own; a review window too when it is a review agent):
#     Claude Code  {"tool_name":"Agent"|"Task","tool_input":{"subagent_type":"qa-specialist",…}}
#     Codex        {"tool_name":"spawn_agent","tool_input":{"agent_type":"code-reviewer",…}}
#     opencode     {"tool":"task","args":{"subagent_type":"qa-specialist",…},"sessionID":…}
# A review agent opens a window and is no task; any other agent is recorded, and the CLI drops
# the provider's built-ins (one list, review_triggers.BUILTIN_AGENTS) — the gate only has to be cheap.
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
# The spawn's own agent type is a review agent (a plugin may namespace it: `team:qa-specialist`).
REVIEW_TYPE_RE='"(subagent_type|agent_type)"[[:space:]]*:[[:space:]]*"([^"]*:)?(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)"'

MODE=""
if [[ "$INPUT" =~ $CODEX_RE ]] || [[ "$INPUT" =~ $OPENCODE_RE ]]; then
    MODE="todo"
elif [[ "$INPUT" =~ $SPAWN_RE ]]; then
    MODE="spawn"
else
    exit 0
fi

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
if [ "$MODE" = "todo" ]; then
    devteam_task_board_record "$INPUT" >/dev/null 2>&1
else
    if [[ "$INPUT" =~ $REVIEW_TYPE_RE ]]; then
        devteam_task_board_has_record "$INPUT" || exit 0
        devteam_task_board_review_open "$INPUT" >/dev/null 2>&1
    else
        devteam_task_board_record "$INPUT" >/dev/null 2>&1
    fi
fi
exit 0
