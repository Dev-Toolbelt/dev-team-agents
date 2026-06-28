#!/usr/bin/env bash
# Dispatcher for all Stop hooks.
# Captures the Claude Code hook payload from stdin and makes it available to
# sub-scripts via the DEVTEAM_HOOK_PAYLOAD env var (path to a temp JSON file).
# Runs each sub-script in alphabetical order; a non-zero exit from any
# sub-script is propagated.

# Prevent WSL from loading /etc/bash.bashrc (and its start-systemd-namespace
# call) for every bash sub-process spawned by this dispatcher.
unset BASH_ENV ENV

set -euo pipefail

# Capture hook payload from stdin before dispatching to sub-scripts.
HOOK_TMP=$(mktemp /tmp/devteam-stop-payload.XXXXXX.json)
cat > "$HOOK_TMP" || true
export DEVTEAM_HOOK_PAYLOAD="$HOOK_TMP"
trap 'rm -f "$HOOK_TMP"' EXIT

# Fast-path: compute git state once here so sub-scripts 01–03 can skip
# expensive checks when nothing relevant changed in this session.
# DEVTEAM_NO_CHANGES=1 means: no staged/unstaged changes AND no commits today.
DEVTEAM_NO_CHANGES=0
if git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
        TODAY=$(date +%Y-%m-%d)
        if ! git log --oneline --since="${TODAY} 00:00:00" --format="%h" 2>/dev/null | grep -q .; then
            DEVTEAM_NO_CHANGES=1
        fi
    fi
fi
export DEVTEAM_NO_CHANGES

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/stop" && pwd)"
EXIT_CODE=0

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    SCRIPT_EXIT=0
    env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?
    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
