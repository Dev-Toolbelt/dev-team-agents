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
#   the main session's own work (one "Direct work" card per session, docs/specs/task-board.md
#   § Direct work): an edit tool, or a shell call whose text looks write-shaped —
#     Claude Code  Edit|Write|MultiEdit|NotebookEdit, Bash     Codex  apply_patch, Bash|shell|exec_command
#     opencode     edit|write|patch|multiedit, bash
#   Once a turn's direct work is settled the CLI drops `.direct-<session>` beside the record, and
#   every later call of that turn leaves on a `[ -f ]`. The CLI makes the exact shell decision.
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

EDIT_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"(Edit|Write|MultiEdit|NotebookEdit|apply_patch|edit|write|patch|multiedit)"'
SHELL_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"(Bash|shell|exec_command|bash)"'
# A superset of `tasks.writes()` (tests/test_direct_work.py pins it): every write it accepts must
# pass here, and the common read-only shapes (`2>&1`, `2>/dev/null`, `sed -n`, `git log --grep=reset`)
# must not, or each of them forks python again — the marker is only set once a write is recorded.
# A word starts a command after whitespace, a quote, an operator or an escaped newline (`\n`).
CMD_START="(^|[[:space:]\"';&|(]|\\\\n)"
CMD_END="([[:space:]\"';&|)]|\\\\|\$)"
WRITE_RES=(
    "${CMD_START}(mv|rm|cp|mkdir|rmdir|touch|ln|chmod|chown|tee|truncate|patch|install|dd)${CMD_END}"
    "${CMD_START}(sed|perl)[[:space:]][^|;&]*-[A-Za-z-]*i"
    "${CMD_START}git[^|;&]*[[:space:]](add|am|apply|checkout|cherry-pick|commit|merge|mv|pull|push|rebase|reset|restore|revert|rm|stash|switch|tag|worktree)${CMD_END}"
    "${CMD_START}(npm|pnpm|yarn|bun|pip|pip3|poetry|uv|cargo|go|bundle|gem|composer|brew)[[:space:]]+(install|i|add|remove|rm|uninstall|update|upgrade|get)${CMD_END}"
    # A redirect into a file: not `=>`/`->`, not a descriptor copy (`>&`), not `/dev/...`.
    '(^|[^=-])>>?[[:space:]]*([^&[:space:]/\\"]|/[^d])'
)
SUBAGENT_RE='"(agent_id|parent_id)"[[:space:]]*:[[:space:]]*"[^"]'

writes_shaped() {
    local re
    for re in "${WRITE_RES[@]}"; do
        [[ "$INPUT" =~ $re ]] && return 0
    done
    return 1
}

MODE=""
if [[ "$INPUT" =~ $CODEX_RE ]] || [[ "$INPUT" =~ $OPENCODE_RE ]]; then
    MODE="todo"
elif [[ "$INPUT" =~ $SPAWN_RE ]]; then
    # A spawn that names no agent type is the provider's default agent: no task, no review. Free to
    # skip here, so the common unnamed spawn forks nothing.
    [[ "$INPUT" == *'"subagent_type"'* || "$INPUT" == *'"agent_type"'* ]] || exit 0
    MODE="spawn"
elif [[ "$INPUT" =~ $EDIT_RE ]] || { [[ "$INPUT" =~ $SHELL_RE ]] && writes_shaped; }; then
    # A subagent's work belongs to its agent task (opencode: a child session names its parent). Only
    # the payload's own key counts: inside a tool argument the quotes are escaped and never match.
    [[ "$INPUT" =~ $SUBAGENT_RE ]] && exit 0
    MODE="direct"
else
    exit 0
fi

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
if [ "$MODE" = "direct" ]; then
    SESSION="$(devteam_task_board_session_id "$INPUT")"
    [ -n "$SESSION" ] || exit 0
    [ -f "${TB_STATE_DIR}/task-board/.direct-${SESSION}" ] && exit 0
    devteam_task_board_record "$INPUT" >/dev/null 2>&1
elif [ "$MODE" = "todo" ]; then
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
