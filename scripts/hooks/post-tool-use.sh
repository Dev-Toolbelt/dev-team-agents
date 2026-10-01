#!/usr/bin/env bash
# Dispatcher for all PostToolUse hooks.
# Reads stdin once (Claude Code sends hook JSON here) and pipes it to each sub-script.
# Sub-scripts run in alphabetical order; a non-zero exit from any sub-script is propagated.
# Registered with a narrow matcher on every provider — Claude Code: the todo tools and the
# subagent tool (`Agent`/`Task`), plus a `PostToolUseFailure` entry for the subagent tool;
# Codex: `spawn_agent` and `wait_agent` only — so it does not run for other tools at all. The sub-scripts still
# gate on the payload themselves.

# Prevent WSL from loading /etc/bash.bashrc for every sub-process spawned here.
unset BASH_ENV ENV

set -euo pipefail

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/post-tool-use" && pwd)"
INPUT=$(cat)
EXIT_CODE=0

# Same filename convention as the PreToolUse and Stop dispatchers.
SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    if [[ ! "$(basename "$script")" =~ $SUBSCRIPT_RE ]]; then
        [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && \
            echo "[devteam:post-tool-use] skipped (name does not match ${SUBSCRIPT_RE}): $(basename "$script")" >&2
        continue
    fi
    SCRIPT_EXIT=0
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:post-tool-use] running: $(basename "$script")" >&2
    printf '%s\n' "$INPUT" | env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:post-tool-use] exit ${SCRIPT_EXIT}: $(basename "$script")" >&2
    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
