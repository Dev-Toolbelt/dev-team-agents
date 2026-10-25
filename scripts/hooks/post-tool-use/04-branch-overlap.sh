#!/usr/bin/env bash
# PostToolUse sub-script: after a file edit, warns when a teammate's unmerged remote branch changes
# the same lines (ADR-0051). The hint goes out through the context-hints channel (ADR-0047), naming
# the branch and its author, once per session per branch and file: immediately on Claude Code and Codex
# (PostToolUse additionalContext), queued for the next prompt on opencode (`devteam_hints_deliver`).
#   Claude Code  Edit|MultiEdit|Write|NotebookEdit   file_path / notebook_path
#   opencode     edit|write|multiedit (filePath), patch (patchText)
#   Codex        apply_patch — `*** Add|Update|Delete File:` and `*** Move to:` headers
# Reads the cache that scripts/lib/devteam/branch_overlap.py refresh keeps in the machine-local
# state dir and NEVER touches the network. Runs after every edit, so bash gates come first: an edit
# tool, `branch_overlap_active` not false (absent = true), a session id and an existing cache; python
# is forked once, only when all hold, to compare hunks.
# Fail-open: any error or unparseable payload exits 0 and prints nothing.
set -uo pipefail

# Cheap gate: branch_overlap.py's refresher keeps a file in this directory only while a cache holds a
# branch, so with none (most repos, most of the time) the hook leaves before git and the state
# directory are resolved. A glob test forks nothing.
SENTINEL_DIR="${TMPDIR:-/tmp}"
compgen -G "${SENTINEL_DIR%/}/devteam-branch-overlap/*" >/dev/null || exit 0


INPUT="$(head -c 1048577)"
[ "${#INPUT}" -le 1048576 ] || exit 0

EDIT_RE='"(tool_name|tool)"[[:space:]]*:[[:space:]]*"([A-Za-z_]+\.)?(Edit|MultiEdit|Write|NotebookEdit|apply_patch|edit|write|multiedit|patch)"'
# The tool name sits in the head of every provider's payload; the body can be a large file.
[[ "${INPUT:0:4096}" =~ $EDIT_RE ]] || exit 0

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" 2>/dev/null && pwd)" || exit 0
HOOK_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0

# shellcheck source=scripts/hooks/lib/context-hints.sh
. "${HOOK_LIB}/context-hints.sh"
devteam_hints_init || exit 0
CACHE="${CH_STATE_DIR}/.branch-overlap.json"
[ -f "$CACHE" ] || exit 0
SESSION="$(devteam_hints_session_id "$INPUT")"
[ -n "$SESSION" ] || exit 0

# The preferences live in the MAIN checkout only, never in a linked worktree.
if [ -f "$CH_ROOT/.dev-team-agents/resolved/preferences.json" ]; then
    PREFS="$(devteam_prefs_file "$CH_ROOT")"
else
    PREFS="$(devteam_prefs_file "$CH_MAIN")"
fi
if [ -f "$PREFS" ] && grep -qE '"branch_overlap_active"[[:space:]]*:[[:space:]]*false' "$PREFS" 2>/dev/null; then
    exit 0
fi

[ -f "$LIB/python.sh" ] && [ -f "$LIB/devteam/branch_overlap.py" ] || exit 0
# shellcheck source=scripts/lib/python.sh
. "$LIB/python.sh" 2>/dev/null || true
command -v python3 >/dev/null 2>&1 || exit 0

# Target paths, as in 05-readonly-docs-guard.sh. A `\` (a JSON escape, or the `\n` closing a patch
# header) ends the match: the prefix still names the file.
PATHS=()
for RE in '"(file_path|filePath|notebook_path)"[[:space:]]*:[[:space:]]*"([^"\\]+)' \
          '\*\*\* (Add File|Update File|Delete File|Move to): ([^"\\]+)'; do
    REST="$INPUT"
    COUNT=0
    while [ "${#PATHS[@]}" -lt 8 ] && [ "$COUNT" -lt 16 ] && [[ "$REST" =~ $RE ]]; do
        P="${BASH_REMATCH[2]}"
        REST="${REST#*"${BASH_REMATCH[0]}"}"
        COUNT=$((COUNT + 1))
        case "$P" in
            "$CH_ROOT"/*) P="${P#"$CH_ROOT"/}" ;;
            /*) continue ;;
        esac
        PATHS+=("$P")
    done
done
[ "${#PATHS[@]}" -gt 0 ] || exit 0

LINES=""
for P in "${PATHS[@]}"; do
    MATCHES="$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); from devteam import branch_overlap; sys.exit(branch_overlap.main(sys.argv[2:]))' \
        "$LIB" match "$CH_ROOT" "$CH_STATE_DIR" "$P" 2>/dev/null)" || continue
    [ -n "$MATCHES" ] || continue
    while IFS=$'\t' read -r BRANCH AUTHOR; do
        [ -n "$BRANCH" ] || continue
        LINES="${LINES}Branch '${BRANCH}' by '${AUTHOR:-a teammate}' (unmerged) changes lines of ${P} that you are editing — coordinate before both sides diverge."$'\n'
    done <<< "$MATCHES"
done
[ -n "$LINES" ] && devteam_hints_deliver "$SESSION" "$INPUT" "$LINES"
exit 0
