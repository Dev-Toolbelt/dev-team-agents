#!/usr/bin/env bash
# UserPromptSubmit sub-script: a review command or an explicit review request in the prompt
# opens an In Review window on the task board (ADR-0018). Runs on EVERY prompt, so it forks
# python only when (1) the prompt text contains something review-shaped, by a cheap
# case-insensitive substring test, and (2) the session already has a task record. The exact
# rules (word boundaries, negation, the command list) live in devteam/review_triggers.py.
# Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
# Only what follows the "prompt" key is tested: the path fields before it (cwd,
# transcript_path) could contain "test" or "review" and would defeat the gate. Every provider
# puts that key within the first few KiB, and bash's prefix removal and `case` are quadratic in
# the text, so the key is searched in the head and only the first 16 KiB after it are glob-tested
# (a pasted log must not stall every prompt). A command sits at the start of the prompt; the
# detector, not this gate, reads the whole of it.
HEAD="${INPUT:0:4096}"
BEFORE="${HEAD%%\"prompt\"*}"
[ "$BEFORE" != "$HEAD" ] || exit 0
TAIL="${INPUT:$((${#BEFORE} + 8)):16384}"

shopt -s nocasematch
case "$TAIL" in
    *review*|*revis*|*qa*|*test*) ;;
    *) exit 0 ;;
esac
shopt -u nocasematch

# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0
devteam_task_board_has_record "$INPUT" || exit 0
devteam_task_board_review_open "$INPUT" >/dev/null 2>&1
exit 0
