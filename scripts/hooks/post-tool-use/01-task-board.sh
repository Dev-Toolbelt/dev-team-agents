#!/usr/bin/env bash
# PostToolUse sub-script: feed the task board (ADR-0018).
#   todo tools (Claude Code)  TodoWrite, TaskCreate, TaskUpdate        → record
#   an agent's end            Claude Code `Agent`/`Task` (tool_response),
#                             Codex `spawn_agent` (the spawned agent id), `wait_agent`
#                             (tool_response) and `close_agent`, opencode `task` (the plugin adds "output")
#                                                                          → the agent task, and a
#                                                                            review result when it carries one
#   a subagent launch that failed  Claude Code `PostToolUseFailure` on `Agent`/`Task`
#                             (same payload shape, no tool_response)      → task cancelled, review retired as unread
# The settings matcher already narrows the event; the string tests below repeat it so a
# stray registration with a wider matcher forks nothing for another tool.
# Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
TODO_RE='"tool_name"[[:space:]]*:[[:space:]]*"(TodoWrite|TaskCreate|TaskUpdate)"'
SUBAGENT_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"(Agent|Task|task)"'
SPAWN_RE='"tool_name"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?spawn_agent"'
WAIT_RE='"tool_name"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?(wait_agent|close_agent)"'
REVIEW_TYPE_RE='"(subagent_type|agent_type)"[[:space:]]*:[[:space:]]*"([^"]*:)?(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)"'

MODE=""
if [[ "$INPUT" =~ $TODO_RE ]]; then
    MODE="todo"
elif [[ "$INPUT" =~ $SUBAGENT_RE ]] || [[ "$INPUT" =~ $SPAWN_RE ]]; then
    # A spawn that names no agent type is the provider's default agent: nothing to settle.
    [[ "$INPUT" == *'"subagent_type"'* || "$INPUT" == *'"agent_type"'* ]] || exit 0
    MODE="agent"
elif [[ "$INPUT" =~ $WAIT_RE ]]; then
    MODE="agent"
else
    exit 0
fi

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
if [ "$MODE" = "todo" ]; then
    devteam_task_board_record "$INPUT" >/dev/null 2>&1
    exit 0
fi
# An agent's end settles what its spawn recorded: with no record there is nothing to settle.
devteam_task_board_has_record "$INPUT" || exit 0
if [[ "$INPUT" =~ $REVIEW_TYPE_RE ]]; then
    devteam_task_board_review_result "$INPUT" >/dev/null 2>&1
    exit 0
fi
devteam_task_board_record "$INPUT" >/dev/null 2>&1
if [[ "$INPUT" == *review-result* ]]; then
    devteam_task_board_review_result "$INPUT" >/dev/null 2>&1
fi
exit 0
