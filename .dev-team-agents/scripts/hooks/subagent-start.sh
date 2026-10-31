#!/usr/bin/env bash
# Dispatcher for all SubagentStart hooks (Codex only).
# Codex fires `SubagentStart` for the parent session when a child agent starts running. The payload carries the PARENT's
# `session_id` and the child's `agent_id` / `agent_type`. Reads stdin once and pipes it to each
# sub-script in `subagent-start/`, in alphabetical order; a non-zero exit from any sub-script is propagated.
# Claude Code is deliberately not wired to this event: its `Agent`/`Task` tool calls already reach
# PreToolUse/PostToolUse, so a second source would record every spawn twice. opencode has no
# such event. Exits 0 always on its own, prints nothing.

# Prevent WSL from loading /etc/bash.bashrc for every sub-process spawned here.
unset BASH_ENV ENV

set -uo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/../lib/python.sh"
# shellcheck source=../lib/python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/subagent-start" 2>/dev/null && pwd)" || exit 0
# The payload is fed to each sub-script from a file, never through a pipe: a sub-script that
# exits without reading stdin would otherwise kill the writer with SIGPIPE. Fail open: with no
# temp file the hook does nothing, and stdin is bounded (4 MiB) so a huge payload cannot balloon it.
INPUT_FILE=$(mktemp "${TMPDIR:-/tmp}/devteam-hook-input.XXXXXX" 2>/dev/null) || exit 0
trap 'rm -f "$INPUT_FILE"' EXIT
head -c 4194304 > "$INPUT_FILE" || exit 0
EXIT_CODE=0

# Same filename convention as the other dispatchers.
SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    [[ "$(basename "$script")" =~ $SUBSCRIPT_RE ]] || continue
    SCRIPT_EXIT=0
    env -u BASH_ENV -u ENV bash "$script" < "$INPUT_FILE" || SCRIPT_EXIT=$?
    if [ "$SCRIPT_EXIT" -ne 0 ] && { [ "$EXIT_CODE" -eq 0 ] || { [ "$SCRIPT_EXIT" -eq 2 ] && [ "$EXIT_CODE" -ne 2 ]; }; }; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
