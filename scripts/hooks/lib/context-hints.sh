#!/usr/bin/env bash
# context-hints.sh — the context-hints channel (ADR-0047): a per-session queue of short hint lines
# that hooks enqueue and the next UserPromptSubmit drains into the model context.
#
# Not a hook. Source it, then:
#   devteam_hints_init                              resolve CH_ROOT, CH_MAIN and the state dir; 1 when none
#   devteam_hints_enqueue <session> <line>          queue one line (skipped when already delivered)
#   devteam_hints_drain <session> [lines] [chars]   print queued lines within the caps, then forget them
#   devteam_hints_session_id <payload>              the payload's session id ("" when absent or unsafe)
#   devteam_hints_deliver <session> <payload> <lines>
#                                                   emit-now-or-queue for a PostToolUse hook: prints the
#                                                   hookSpecificOutput JSON when the payload names a
#                                                   PostToolUse(Failure) event (Claude Code, Codex), queues
#                                                   the lines otherwise (opencode's plugin payload has none)
#
# Two dot-prefixed records in the machine-local state dir (ADR-0013), so
# paths.is_machine_local_record() already classifies them:
#   .context-hints-<session>   lines waiting for the next prompt
#   .context-shown-<session>   every hint and recall pointer already delivered (one per line)
#
# Two rules this file exists to keep:
#   1. A hook never disturbs the provider — every function returns 0 and a failure prints nothing.
#   2. Caps hold per delivery: at most 5 lines and about 1200 characters, each line shown once per session.

_CH_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "${_CH_LIB_DIR}/data-dirs.sh"

DEVTEAM_HINTS_MAX_LINES=5
DEVTEAM_HINTS_MAX_CHARS=1200
_DEVTEAM_HINT_LINE_MAX=300
CH_STATE_DIR=""
CH_ROOT=""
CH_MAIN=""

devteam_hints_init() {
    local roots common main
    roots="$(git rev-parse --show-toplevel --git-common-dir 2>/dev/null)" || return 1
    # shellcheck disable=SC2034 # CH_ROOT and CH_MAIN are read by 05-recall.sh
    CH_ROOT="$(printf '%s\n' "$roots" | sed -n 1p)"
    common="$(printf '%s\n' "$roots" | sed -n 2p)"
    common="$(cd "$common" 2>/dev/null && pwd -P)" || return 1
    main="$(cd "${common}/.." 2>/dev/null && pwd -P)" || return 1
    # shellcheck disable=SC2034
    CH_MAIN="$main"
    CH_STATE_DIR="$(devteam_state_dir "$main")"
    [ -d "$CH_STATE_DIR" ] || return 1
    return 0
}

# The first session key wins, as in task-board.sh: a payload's own id comes before anything a
# tool echoes back.
devteam_hints_session_id() {
    local id
    id="$(printf '%s' "$1" | grep -oE '"session_?[iI][dD]"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n 1 | sed 's/^[^:]*:[[:space:]]*"//; s/"$//')"
    if [[ "$id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
        printf '%s' "$id"
    fi
}

# A short mkdir lock around read-modify-write of the queue. A lock still held after ~1 s is
# taken to be stale (its writer was killed) and broken: a hint is not worth stalling a hook for.
_devteam_hints_lock() {
    local tries=0
    while ! mkdir "$1.lock" 2>/dev/null; do
        tries=$(( tries + 1 ))
        if [ "$tries" -ge 20 ]; then
            rm -rf "$1.lock" 2>/dev/null
            mkdir "$1.lock" 2>/dev/null
            return 0
        fi
        sleep 0.05 2>/dev/null || sleep 1
    done
}

_devteam_hints_unlock() {
    rmdir "$1.lock" 2>/dev/null || true
}

# One line, no control or invisible format characters, bounded: the text becomes model context.
# The Unicode set mirrors tasks._INVISIBLE (UTF-8 byte sequences, so no multibyte locale is needed):
# C1 controls, soft hyphen, ALM, Mongolian vowel separator, U+200B-200F, U+2028-202E, U+2060-2064,
# U+2066-206F and U+FEFF.
_devteam_hints_clean() {
    local s="$1"
    s="$(printf '%s' "$s" | LC_ALL=C tr -d '\000-\037\177' | LC_ALL=C sed \
        -e "s/$(printf '\302')[$(printf '\200')-$(printf '\237\255')]//g" \
        -e "s/$(printf '\330\234')//g" \
        -e "s/$(printf '\341\240\216')//g" \
        -e "s/$(printf '\342\200')[$(printf '\213')-$(printf '\217\250')-$(printf '\256')]//g" \
        -e "s/$(printf '\342\201')[$(printf '\240')-$(printf '\244\246')-$(printf '\257')]//g" \
        -e "s/$(printf '\357\273\277')//g")"
    printf '%s' "${s:0:$_DEVTEAM_HINT_LINE_MAX}"
}

devteam_hints_enqueue() {
    local session="$1" line queue shown
    [ -n "$session" ] || return 0
    line="$(_devteam_hints_clean "$2")"
    [ -n "$line" ] || return 0
    [ -n "$CH_STATE_DIR" ] || devteam_hints_init || return 0
    queue="${CH_STATE_DIR}/.context-hints-${session}"
    shown="${CH_STATE_DIR}/.context-shown-${session}"
    [ -L "$queue" ] && return 0
    [ -f "$shown" ] && [ ! -L "$shown" ] && grep -qxF -- "hint:${line}" "$shown" 2>/dev/null && return 0
    (
        umask 077
        _devteam_hints_lock "$queue"
        trap '_devteam_hints_unlock "$queue"' EXIT
        grep -qxF -- "$line" "$queue" 2>/dev/null || printf '%s\n' "$line" >> "$queue"
    ) 2>/dev/null
    return 0
}

# devteam_hints_drain <session> [max-lines] [max-chars]
# Prints queued lines oldest first until a cap is hit and removes only those printed; the rest
# wait for the next prompt. Each printed line is recorded as delivered, so it never repeats.
devteam_hints_drain() {
    local session="$1" max_lines="${2:-$DEVTEAM_HINTS_MAX_LINES}" max_chars="${3:-$DEVTEAM_HINTS_MAX_CHARS}"
    local queue shown line used=0 count=0 rest=""
    [ -n "$session" ] || return 0
    [ "$max_lines" -gt 0 ] 2>/dev/null || return 0
    [ -n "$CH_STATE_DIR" ] || devteam_hints_init || return 0
    queue="${CH_STATE_DIR}/.context-hints-${session}"
    shown="${CH_STATE_DIR}/.context-shown-${session}"
    [ -f "$queue" ] && [ ! -L "$queue" ] || return 0
    [ -L "$shown" ] && return 0
    (
        umask 077
        _devteam_hints_lock "$queue"
        trap '_devteam_hints_unlock "$queue"' EXIT
        while IFS= read -r line || [ -n "$line" ]; do
            [ -n "$line" ] || continue
            if [ "$count" -lt "$max_lines" ] && [ $(( used + ${#line} + 1 )) -le "$max_chars" ]; then
                printf '%s\n' "$line"
                printf 'hint:%s\n' "$line" >> "$shown"
                count=$(( count + 1 ))
                used=$(( used + ${#line} + 1 ))
            else
                rest="${rest}${line}"$'\n'
            fi
        done < "$queue"
        if [ -n "$rest" ]; then
            printf '%s' "$rest" > "${queue}.tmp.$$" && mv -f "${queue}.tmp.$$" "$queue"
        else
            rm -f "$queue"
        fi
    ) 2>/dev/null
    return 0
}

# devteam_hints_deliver <session> <payload> <newline-separated lines>
# Claude Code (code.claude.com hooks) and Codex (codex-rs/hooks post_tool_use.rs, commit 970111f) both
# send `hook_event_name` and read `hookSpecificOutput.additionalContext` from a PostToolUse hook, so the
# payload shape decides, not an environment variable. opencode's plugin payload carries no event name:
# its lines are queued for the next prompt. A line already delivered this session is not repeated.
devteam_hints_deliver() {
    local session="$1" payload="$2" lines="$3" event="" line shown context="" count=0 chars=0
    [ -n "$session" ] || return 0
    [ -n "$lines" ] || return 0
    local event_re='"hook_event_name"[[:space:]]*:[[:space:]]*"(PostToolUseFailure|PostToolUse)"'
    [[ "$payload" =~ $event_re ]] && event="${BASH_REMATCH[1]}"
    if [ -z "$event" ]; then
        while IFS= read -r line; do
            [ -n "$line" ] && devteam_hints_enqueue "$session" "$line"
        done <<< "$lines"
        return 0
    fi
    [ -n "$CH_STATE_DIR" ] || devteam_hints_init || return 0
    shown="${CH_STATE_DIR}/.context-shown-${session}"
    [ -L "$shown" ] && return 0
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        line="$(_devteam_hints_clean "$line")"
        [ -n "$line" ] || continue
        [ -f "$shown" ] && grep -qxF -- "hint:${line}" "$shown" 2>/dev/null && continue
        # Past the per-delivery cap the line waits for the next prompt instead, as in the drain.
        if [ "$count" -ge "$DEVTEAM_HINTS_MAX_LINES" ] || [ $((chars + ${#line})) -gt "$DEVTEAM_HINTS_MAX_CHARS" ]; then
            devteam_hints_enqueue "$session" "$line"
            continue
        fi
        count=$((count + 1))
        chars=$((chars + ${#line}))
        (umask 077; printf 'hint:%s\n' "$line" >> "$shown") 2>/dev/null
        context="${context}[DEVTEAM:HINT] ${line}"$'\n'
    done <<< "$lines"
    [ -n "$context" ] || return 0
    context="$(printf '%s' "$context" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk 'BEGIN{ORS="\\n"} {print}')"
    printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$event" "$context"
    return 0
}
