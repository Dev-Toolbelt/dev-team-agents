#!/usr/bin/env bash
# SubagentStart sub-script (Codex): link the child's agent id to the agent task its spawn recorded
# (the oldest unlinked one of the same agent type), so the stop below, and the child's own todo
# items, find that task (ADR-0018). A start whose spawn never reached a hook records nothing. A
# review/QA agent is no task: its window opened at the spawn. Never feeds the execution trace.
# Exits 0 always, prints nothing.
unset BASH_ENV ENV
set -uo pipefail

INPUT="$(cat)"
[[ "$INPUT" == *'"agent_id"'* && "$INPUT" == *'"agent_type"'* ]] || exit 0
REVIEW_TYPE_RE='"agent_type"[[:space:]]*:[[:space:]]*"([^"]*:)?(qa-specialist|code-reviewer|backend-reviewer|frontend-reviewer)"'
BUILTIN_TYPE_RE='"agent_type"[[:space:]]*:[[:space:]]*"(default|explorer|worker)"'  # mirrors review_triggers.BUILTIN_AGENTS["codex"]
[[ "$INPUT" =~ $REVIEW_TYPE_RE || "$INPUT" =~ $BUILTIN_TYPE_RE ]] && exit 0

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
devteam_task_board_record "$INPUT" >/dev/null 2>&1
exit 0
