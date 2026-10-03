#!/usr/bin/env bash
# UserPromptSubmit sub-script: counts a devteam command invocation in the machine-local record
# `command-usage.json` (ADR-0030 section 5), which drives the banner's "Also try:" line.
# Runs on EVERY prompt, so python is forked only when the start of the prompt names a devteam
# command (`/devteam:<name>` on Claude Code and opencode, `$devteam-<name>` on Codex); the
# module decides whether the name is a real command. Every provider reaches this script through
# its own UserPromptSubmit wiring (Claude settings.json, Codex hooks.json, the opencode plugin's
# `chat.message`), so one script observes command use on all three.
# Exits 0 always, prints nothing.
set -uo pipefail

INPUT="$(cat)"
# Only what follows the "prompt" key is tested (the path fields before it could contain
# "devteam"); the same head-of-payload search 01-task-board.sh uses.
HEAD="${INPUT:0:4096}"
BEFORE="${HEAD%%\"prompt\"*}"
[ "$BEFORE" != "$HEAD" ] || exit 0
TAIL="${INPUT:$((${#BEFORE} + 8)):160}"
case "$TAIL" in
    *devteam*) ;;
    *) exit 0 ;;
esac

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)"
# shellcheck source=scripts/hooks/lib/task-board.sh
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/task-board.sh"
devteam_task_board_init || exit 0

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
# shellcheck source=scripts/lib/python.sh
[ -f "${LIB_DIR}/python.sh" ] && . "${LIB_DIR}/python.sh"

printf '%s' "$INPUT" | PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys
sys.path.insert(0, sys.argv[1])
from devteam import command_usage
command_usage.hook_main(sys.argv[2], sys.stdin)' "$LIB_DIR" "$TB_STATE_DIR" >/dev/null 2>&1
exit 0
