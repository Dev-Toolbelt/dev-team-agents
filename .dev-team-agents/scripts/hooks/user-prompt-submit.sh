#!/usr/bin/env bash
# Dispatcher for all UserPromptSubmit hooks.
# Reads stdin once (Claude Code sends hook JSON here) and pipes it to each sub-script.
# Sub-scripts run in alphabetical order; a non-zero exit from any sub-script is propagated (exit 2 wins over exit 1).
# Runs on every prompt, so each sub-script must gate cheaply before doing any work.

# Prevent WSL from loading /etc/bash.bashrc for every sub-process spawned here.
unset BASH_ENV ENV

set -euo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/../lib/python.sh"
# shellcheck source=../lib/python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/user-prompt-submit" && pwd)"
INPUT=$(cat)
# The payload is fed to each sub-script from a file, never through a pipe: a
# sub-script that exits without reading stdin would otherwise kill the writer
# with SIGPIPE (141) on payloads larger than the pipe buffer.
INPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/devteam-hook-input.XXXXXX")
trap 'rm -f "$INPUT_FILE"' EXIT
printf '%s\n' "$INPUT" > "$INPUT_FILE"
EXIT_CODE=0

# Same filename convention as the PreToolUse and Stop dispatchers.
SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    if [[ ! "$(basename "$script")" =~ $SUBSCRIPT_RE ]]; then
        [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && \
            echo "[devteam:user-prompt-submit] skipped (name does not match ${SUBSCRIPT_RE}): $(basename "$script")" >&2
        continue
    fi
    SCRIPT_EXIT=0
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:user-prompt-submit] running: $(basename "$script")" >&2
    env -u BASH_ENV -u ENV bash "$script" < "$INPUT_FILE" || SCRIPT_EXIT=$?
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:user-prompt-submit] exit ${SCRIPT_EXIT}: $(basename "$script")" >&2
    # First non-zero exit wins, except that exit 2 (a refusal) is never masked by an earlier
    # exit 1 from another sub-script.
    if [ "$SCRIPT_EXIT" -ne 0 ] && { [ "$EXIT_CODE" -eq 0 ] || { [ "$SCRIPT_EXIT" -eq 2 ] && [ "$EXIT_CODE" -ne 2 ]; }; }; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
