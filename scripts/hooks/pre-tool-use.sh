#!/usr/bin/env bash
# Dispatcher for all PreToolUse hooks.
# Reads stdin once (Claude Code sends hook JSON here) and pipes it to each sub-script.
# Sub-scripts run in alphabetical order; a non-zero exit from any sub-script is propagated.

# Prevent WSL from loading /etc/bash.bashrc (and its start-systemd-namespace
# call) for every bash sub-process spawned by this dispatcher.
unset BASH_ENV ENV

set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/pre-tool-use" && pwd)"
INPUT=$(cat)
EXIT_CODE=0

# Only files matching the documented sub-script convention are executed:
# NN-name.sh or NNx-name.sh (see CLAUDE.md, "PreToolUse Hook Sub-script
# Convention"). Drafts, backups and half-finished files are ignored instead of
# being auto-run on every single tool call.
SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    if [[ ! "$(basename "$script")" =~ $SUBSCRIPT_RE ]]; then
        [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && \
            echo "[devteam:pre-tool-use] skipped (name does not match ${SUBSCRIPT_RE}): $(basename "$script")" >&2
        continue
    fi
    SCRIPT_EXIT=0
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:pre-tool-use] running: $(basename "$script")" >&2
    echo "$INPUT" | env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:pre-tool-use] exit ${SCRIPT_EXIT}: $(basename "$script")" >&2
    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
