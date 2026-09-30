#!/usr/bin/env bash
# PostToolUse sub-script: feed the task board (ADR-0018).
#   todo tools (Claude Code)  TodoWrite, TaskCreate, TaskUpdate        → record
#   a review agent's report   Claude Code `Agent`/`Task` (tool_response),
#                             Codex `wait_agent` (tool_response),
#                             opencode `task` (the plugin adds "output")  → review result
# The settings matcher already narrows the event; the string tests below repeat it so a
# stray registration with a wider matcher (Codex uses `*`) forks nothing for another tool.
# Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
TODO_RE='"tool_name"[[:space:]]*:[[:space:]]*"(TodoWrite|TaskCreate|TaskUpdate)"'
SUBAGENT_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"(Agent|Task|task)"'
WAIT_RE='"tool_name"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?wait_agent"'
REVIEW_AGENT_RE='(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)'

MODE=""
if [[ "$INPUT" =~ $TODO_RE ]]; then
    MODE="todo"
elif [[ "$INPUT" =~ $SUBAGENT_RE ]] && { [[ "$INPUT" == *review-result* ]] || [[ "$INPUT" =~ $REVIEW_AGENT_RE ]]; }; then
    MODE="review"
elif [[ "$INPUT" =~ $WAIT_RE ]] && [[ "$INPUT" == *review-result* ]]; then
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
    devteam_task_board_review_result "$INPUT" >/dev/null 2>&1
fi
exit 0
