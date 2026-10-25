#!/usr/bin/env bash
# UserPromptSubmit sub-script: points the agent at the ADRs, wiki entries and reuse rules the prompt
# touches (ADR-0047), then drains the hints other hooks queued for this session. Output is pointers
# only: `[DEVTEAM:RECALL]` lines from scripts/lib/recall.py, then `[DEVTEAM:HINT]` lines — at most 5
# lines and about 1200 characters together. Claude Code and Codex add this stdout to the model
# context; the opencode plugin captures both prefixes from `chat.message` and adds them to the
# system prompt.
# Runs on EVERY prompt, so python is forked only after cheap bash gates: a prompt of at least 12
# characters, `recall_active` not false, and at least one index file. The hint drain is bash only
# and runs regardless of those gates.
# Exits 0 always.
set -uo pipefail

LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" 2>/dev/null && pwd)" || exit 0
HOOK_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0

INPUT="$(cat)"
# Only what follows the "prompt" key is read, and only a bounded window of it, as in
# 01-task-board.sh: the path fields before it must not match, and a pasted log must not stall prompts.
HEAD="${INPUT:0:4096}"
BEFORE="${HEAD%%\"prompt\"*}"
[ "$BEFORE" != "$HEAD" ] || exit 0
TAIL="${INPUT:$((${#BEFORE} + 8)):16384}"

# shellcheck source=scripts/hooks/lib/context-hints.sh
. "${HOOK_LIB}/context-hints.sh"
SESSION="$(devteam_hints_session_id "$INPUT")"
devteam_hints_init || CH_STATE_DIR=""

MAX_LINES="$DEVTEAM_HINTS_MAX_LINES"
MAX_CHARS="$DEVTEAM_HINTS_MAX_CHARS"
RECALL=""

recall_gates() {
    local root raw prefs docs layouts reuse_paths found reuse
    raw="${TAIL#*\"}"
    raw="${raw%%\"*}"
    # An escaped quote ends the raw cut early; only a cut that is short for real skips the prompt.
    if [ "${#raw}" -lt 12 ]; then
        case "$raw" in *\\) ;; *) return 1 ;; esac
    fi
    root="$CH_ROOT"
    [ -n "$root" ] || return 1
    RECALL_ROOT="$root"
    # The preferences live in the MAIN checkout (the root is a fallback for a plain clone).
    prefs="$(devteam_prefs_file "$CH_MAIN")"
    [ -f "$prefs" ] || prefs="$(devteam_prefs_file "$root")"
    if [ -f "$prefs" ] && grep -qE '"recall_active"[[:space:]]*:[[:space:]]*false' "$prefs" 2>/dev/null; then
        return 1
    fi
    docs="docs"
    if [ -f "$root/.dev-team-agents/project.json" ]; then
        raw="$(grep -m1 -A1 '"context_paths"' "$root/.dev-team-agents/project.json" 2>/dev/null \
            | grep -oE '"[A-Za-z0-9._/-]+"' | sed -n 2p | tr -d '"')"
        [ -n "$raw" ] && docs="$raw"
    fi
    # Any of the sources; recall.py resolves the authoritative paths. The reuse registry sits at a
    # layout-dependent path: both come from scripts/lib/doc-layouts.json (grep, no python fork).
    layouts="$LIB/doc-layouts.json"
    reuse_paths="development/reuse-guidelines.md reuse-guidelines.md"
    if [ -f "$layouts" ]; then
        found="$(grep -A5 '"reuse-guidelines"[[:space:]]*:' "$layouts" 2>/dev/null \
            | grep -E '"(development|gated)"[[:space:]]*:[[:space:]]*"' | sed 's/^[^:]*:[[:space:]]*"//; s/".*$//')"
        [ -n "$found" ] && reuse_paths="$found"
    fi
    for reuse in $reuse_paths; do
        [ -f "$root/$docs/$reuse" ] && return 0
    done
    [ -f "$root/$docs/wiki/README.md" ] \
        || [ -f "$root/$docs/development/adrs/README.md" ] || [ -f "$root/$docs/adr/README.md" ] \
        || [ -f "$root/docs/wiki/README.md" ] || [ -f "$root/docs/development/adrs/README.md" ] \
        || return 1
    return 0
}

if recall_gates && [ -f "$LIB/python.sh" ] && [ -f "$LIB/recall.py" ]; then
    # shellcheck source=scripts/lib/python.sh
    . "$LIB/python.sh" 2>/dev/null || true
    if command -v python3 >/dev/null 2>&1; then
        SHOWN="-"
        [ -n "$SESSION" ] && [ -n "$CH_STATE_DIR" ] && SHOWN="${CH_STATE_DIR}/.context-shown-${SESSION}"
        RECALL="$(printf '%s' "$TAIL" | python3 -I "$LIB/recall.py" "$RECALL_ROOT" "$SHOWN" "$MAX_LINES" "$MAX_CHARS" 2>/dev/null)" || RECALL=""
    fi
fi

if [ -n "$RECALL" ]; then
    printf '%s\n' "$RECALL"
    LINES="$(printf '%s\n' "$RECALL" | wc -l | tr -d ' ')"
    MAX_LINES=$(( MAX_LINES - LINES ))
    MAX_CHARS=$(( MAX_CHARS - ${#RECALL} - 1 ))
fi

if [ "$MAX_LINES" -gt 0 ] && [ "$MAX_CHARS" -gt 0 ]; then
    devteam_hints_drain "$SESSION" "$MAX_LINES" "$MAX_CHARS" | while IFS= read -r hint; do
        printf '[DEVTEAM:HINT] %s\n' "$hint"
    done
fi
exit 0
