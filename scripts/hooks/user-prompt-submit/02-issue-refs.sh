#!/usr/bin/env bash
# UserPromptSubmit sub-script: an issue reference in the prompt (a Jira key, `owner/repo#N`,
# `fixes #N`, an issue URL) is remembered on the session's task board record (ADR-0018, PR/MR
# Created amendment). Runs on EVERY prompt, so it forks python only when (1) the prompt text has
# something reference-shaped, (2) the project binds an integration at all (a reference needs a
# connected account AND the project's binding; no binding file means none can match). A session's
# first prompt has no record yet and is still processed: the CLI starts a task-less record when the
# prompt carries a valid reference, and the first task recorded later inherits it. The exact rules
# live in `devteam/pr_refs.py`; the gates here only avoid a fork. Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
# Same windowing as 01-task-board.sh: only what follows the "prompt" key is tested, and only its
# first 16 KiB, so a pasted log cannot stall every prompt.
HEAD="${INPUT:0:4096}"
BEFORE="${HEAD%%\"prompt\"*}"
[ "$BEFORE" != "$HEAD" ] || exit 0
TAIL="${INPUT:$((${#BEFORE} + 8)):16384}"

case "$TAIL" in
    *-[0-9]*|*"#"[0-9]*|*/issues/*|*/browse/*) ;;
    *) exit 0 ;;
esac

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
SETTINGS="${TB_ROOT}/.dev-team-agents/integration-settings"
[ -f "${SETTINGS}/jira.json" ] || [ -f "${SETTINGS}/github.json" ] || exit 0
devteam_task_board_event "$INPUT"
exit 0
