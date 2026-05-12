#!/usr/bin/env bash
# Dispatcher for all Stop hooks.
# Captures the Claude Code hook payload from stdin and makes it available to
# sub-scripts via the DEVTEAM_HOOK_PAYLOAD env var (path to a temp JSON file).
# Runs each sub-script in alphabetical order; a non-zero exit from any
# sub-script is propagated.
set -euo pipefail

# Capture hook payload from stdin before dispatching to sub-scripts.
HOOK_TMP=$(mktemp /tmp/devteam-stop-payload.XXXXXX.json)
cat > "$HOOK_TMP" || true
export DEVTEAM_HOOK_PAYLOAD="$HOOK_TMP"
trap 'rm -f "$HOOK_TMP"' EXIT

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
