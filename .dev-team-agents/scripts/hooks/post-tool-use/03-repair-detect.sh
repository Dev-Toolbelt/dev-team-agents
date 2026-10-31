#!/usr/bin/env bash
# PostToolUse sub-script: the repair ledger (ADR-0051, spec docs/specs/repair-ledger.md).
#   A shell tool's result (Claude Code `Bash`, Codex `Bash`/`exec_command`, opencode `bash`; the
#   Claude `PostToolUseFailure` event carries the same tool name) goes to scripts/lib/devteam/repairs.py,
#   which keeps a short window of recent shell calls and records "failed, then the same command
#   succeeded with a delta" in the machine-local repair-ledger.json. A failure whose signature has a
#   recorded repair prints a hint line; this script delivers it:
#     Claude Code, Codex   immediately, as PostToolUse(Failure) additionalContext (ADR-0048)
#     opencode             queued on the context-hints channel, delivered with the next prompt
#   `devteam_hints_deliver` tells them apart by the payload's `hook_event_name`. A shell result's exit
#   code is read from the payload's `exit_code` (opencode's plugin adds it) before any text marker.
# Runs for every shell call, so python is forked only when it can matter: the tool is a shell tool,
# `repair_hints_active` is not false, and either a window already waits for a retry or the payload
# looks like a failure. Exits 0 always; nothing is printed except the Claude hint JSON.
set -uo pipefail

INPUT="$(head -c 1048577)"
[ "${#INPUT}" -le 1048576 ] || exit 0

HEAD="${INPUT:0:4096}"
TOOL_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?(Bash|bash|exec_command|shell|local_shell)"'
[[ "$HEAD" =~ $TOOL_RE ]] || exit 0
case "$INPUT" in *'"command"'*|*'"cmd"'*) ;; *) exit 0 ;; esac

# Cheap gate, decided from the payload alone: python3 and the state directory cost tens of
# milliseconds, so a call that neither failed nor follows an open failure leaves here. "Follows an open
# failure" is a sentinel repairs.py keeps in $TMPDIR while a session's repair window is open.
FAILED_RE='PostToolUseFailure|[Ee]xit code:? ?[1-9]|exited with code [1-9]|"(exit_code|exitCode|returncode|exit)"[[:space:]]*:[[:space:]]*[1-9]|"is_?[eE]rror"[[:space:]]*:[[:space:]]*true'
SESSION_RE='"session_?[iI][dD]"[[:space:]]*:[[:space:]]*"([A-Za-z0-9][A-Za-z0-9._-]{0,127})"'
[[ "$INPUT" =~ $SESSION_RE ]] || exit 0
SESSION="${BASH_REMATCH[1]}"
SENTINEL_DIR="${TMPDIR:-/tmp}"
SENTINEL_DIR="${SENTINEL_DIR%/}"
if [ ! -f "${SENTINEL_DIR:-/tmp}/devteam-repair-open-${SESSION}" ] && ! [[ "$INPUT" =~ $FAILED_RE ]]; then
    exit 0
fi

HOOK_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0
# shellcheck source=scripts/hooks/lib/context-hints.sh
. "${HOOK_LIB}/context-hints.sh"
SESSION="$(devteam_hints_session_id "$INPUT")"
[ -n "$SESSION" ] || exit 0
devteam_hints_init || exit 0

# The preferences live in the MAIN checkout (devteam_prefs_file also honors the v2 user-data fallback).
PREFS="$(devteam_prefs_file "$CH_MAIN")"
[ -f "$PREFS" ] || PREFS="$(devteam_prefs_file "$CH_ROOT")"
if [ -f "$PREFS" ] && grep -qE '"repair_hints_active"[[:space:]]*:[[:space:]]*false' "$PREFS" 2>/dev/null; then
    exit 0
fi

LIB="$(cd "${HOOK_LIB}/../../lib" 2>/dev/null && pwd)" || exit 0
[ -f "$LIB/python.sh" ] && [ -f "$LIB/devteam/repairs.py" ] || exit 0
# shellcheck source=scripts/lib/python.sh
. "$LIB/python.sh" 2>/dev/null || true
command -v python3 >/dev/null 2>&1 || exit 0

HINTS="$(printf '%s' "$INPUT" | python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); from devteam import repairs; sys.exit(repairs.main(sys.argv[2:]))' \
    "$LIB" --state-dir "$CH_STATE_DIR" --session "$SESSION" 2>/dev/null)" || HINTS=""
[ -n "$HINTS" ] || exit 0

devteam_hints_deliver "$SESSION" "$INPUT" "$HINTS"
exit 0
