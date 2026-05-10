#!/usr/bin/env bash
# Dispatcher for all Stop hooks.
# Runs each sub-script in alphabetical order; a non-zero exit from any sub-script is propagated.
set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/stop" && pwd)"
EXIT_CODE=0

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    SCRIPT_EXIT=0
    bash "$script" || SCRIPT_EXIT=$?
    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
