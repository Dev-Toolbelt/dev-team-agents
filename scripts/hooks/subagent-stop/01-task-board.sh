#!/usr/bin/env bash
# SubagentStop sub-script (Codex): the child agent finished. Settle its task by agent id, or, for a
# review/QA agent, fold the review-result marker of its final message (`last_assistant_message`)
# into the review window (ADR-0018). With no session record there is nothing to settle. The
# parent's Stop still settles what this misses (the rollout's FINAL_ANSWER); a task ended by one
# source is never ended again by the other. Never feeds the execution trace. Exits 0 always.
unset BASH_ENV ENV
set -uo pipefail

INPUT="$(cat)"
[[ "$INPUT" == *'"agent_id"'* && "$INPUT" == *'"agent_type"'* ]] || exit 0
REVIEW_TYPE_RE='"agent_type"[[:space:]]*:[[:space:]]*"([^"]*:)?(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)"'
BUILTIN_TYPE_RE='"agent_type"[[:space:]]*:[[:space:]]*"(default|explorer|worker)"'  # mirrors review_triggers.BUILTIN_AGENTS["codex"]

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
devteam_task_board_has_record "$INPUT" || exit 0
if [[ "$INPUT" =~ $REVIEW_TYPE_RE ]]; then
    devteam_task_board_review_result "$INPUT" >/dev/null 2>&1
    exit 0
fi
# A Codex built-in role is no task: no python fork for its settle.
[[ "$INPUT" =~ $BUILTIN_TYPE_RE ]] || devteam_task_board_record "$INPUT" >/dev/null 2>&1
exit 0
