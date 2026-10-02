#!/usr/bin/env bash
# Dispatcher for all UserPromptSubmit hooks.
# Reads stdin once (Claude Code sends hook JSON here) and pipes it to each sub-script.
# Sub-scripts run in alphabetical order; a non-zero exit from any sub-script is propagated (exit 2 wins over exit 1).
# Runs on every prompt, so each sub-script must gate cheaply before doing any work.

# Prevent WSL from loading /etc/bash.bashrc for every sub-process spawned here.
unset BASH_ENV ENV

set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/user-prompt-submit" && pwd)"
INPUT=$(cat)
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
    printf '%s\n' "$INPUT" | env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:user-prompt-submit] exit ${SCRIPT_EXIT}: $(basename "$script")" >&2
    # First non-zero exit wins, except that exit 2 (a refusal) is never masked by an earlier
    # exit 1 from another sub-script.
    if [ "$SCRIPT_EXIT" -ne 0 ] && { [ "$EXIT_CODE" -eq 0 ] || { [ "$SCRIPT_EXIT" -eq 2 ] && [ "$EXIT_CODE" -ne 2 ]; }; }; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
