#!/usr/bin/env bash
# PostToolUse sub-script: a confirmed PR/MR creation or merge feeds the task board (ADR-0018,
# PR/MR Created amendment).
#   Bash (Claude Code, Codex) / bash (opencode)   `gh pr create`, `glab mr create`, `gh pr merge`,
#                                                 `glab mr merge`, `git merge`
#   MCP tools ending in create_pull_request / merge_pull_request
# Runs for every Bash call, so it forks nothing unless the call itself names one of those and the
# session already has a task record. Only the call is tested, never its output: the command text
# (the first "command" value; opencode's args.command has the same key) and the tool name in the
# head of the payload (an MCP tool). A payload over 1 MiB is not a PR/merge call worth a fork and is
# dropped whole, never cut mid-string, and a command over 20000 characters (`pr_refs.MAX_COMMAND`)
# is never analysed. The `git … merge` gap is bounded so a long command cannot backtrack. What the
# call means — and whether its RESULT confirms it — is decided by `devteam/pr_refs.py`; this gate
# only avoids a python fork for a call that cannot match. Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(head -c 1048577)"
[ "${#INPUT}" -le 1048576 ] || exit 0

CALL_RE='gh[[:space:]]+pr[[:space:]]+(create|merge)|glab[[:space:]]+mr[[:space:]]+(create|merge)|git[[:space:]][^;|&]{0,200}merge'
MCP_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"[^"]*(create|merge)_pull_request"'
COMMAND_RE='^[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)"'

HEAD="${INPUT:0:4096}"
if ! [[ "$HEAD" =~ $MCP_RE ]]; then
    # The substring test first: `${INPUT#*…}` is quadratic when the key is absent.
    case "$INPUT" in *'"command"'*) ;; *) exit 0 ;; esac
    REST="${INPUT#*\"command\"}"
    [[ "$REST" =~ $COMMAND_RE ]] || exit 0
    COMMAND="${BASH_REMATCH[1]}"
    [ "${#COMMAND}" -le 20000 ] || exit 0
    [[ "$COMMAND" =~ $CALL_RE ]] || exit 0
fi

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
devteam_task_board_has_record "$INPUT" || exit 0
devteam_task_board_event "$INPUT"
exit 0
