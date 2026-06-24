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

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    SCRIPT_EXIT=0
    echo "$INPUT" | bash "$script" || SCRIPT_EXIT=$?
    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
