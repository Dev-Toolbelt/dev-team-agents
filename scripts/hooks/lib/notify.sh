#!/usr/bin/env bash
# notify.sh — the one way a hook raises a notification.
#
# Appends one JSON line to <state-dir>/notifications.jsonl; the desktop app shows it
# (via `devteam notifications watch`, scripts/lib/devteam/notifications.py). Hooks
# used to print a boxed "DEV TEAM AGENTS" banner instead, and no provider shows that
# to the user: SessionStart stdout becomes model context, Stop stdout is not
# displayed. The queue is that channel made real.
#
# Cheap by design — it runs on every Stop: no python, one append, a line count, and
# a grep only when a dedupe key is given.
#
# Not a hook. Source it, then:
#   devteam_notify_init <main-repo-root> <state-dir> <suppress_notifications value>
#   devteam_notify <level> <code> <message> [ttl-seconds] [dedupe-key]
#
#   level       info | warning | critical
#   code        stable identifier, e.g. context.critical — what a client switches on
#   message     already in the user's language
#   ttl         seconds until the notification stops being worth showing; 0 = never
#   dedupe-key  a notification whose key is already in the queue is not written
#               again (e.g. "context.critical:<session>" fires once per session)
#
# The record's keys are the contract `notifications.RECORD_KEYS` checks.

DEVTEAM_NOTIFY_MAX_LINES="${DEVTEAM_NOTIFY_MAX_LINES:-200}"
DEVTEAM_NOTIFY_FILE=""
DEVTEAM_NOTIFY_SUPPRESS="false"
DEVTEAM_NOTIFY_PROJECT_ID=""
DEVTEAM_NOTIFY_SESSION_ID=""

#   devteam_notify_init <root> <state-dir> <suppress> [session-id]
# Pass the session id when the caller already has it: reading it here costs a
# python fork (state_get), which a per-Stop caller cannot afford twice.
devteam_notify_init() {
    local root="$1" state_dir="$2" suppress="${3:-false}" session="${4-__unset__}"
    DEVTEAM_NOTIFY_FILE="${state_dir}/notifications.jsonl"
    DEVTEAM_NOTIFY_SUPPRESS="$suppress"
    DEVTEAM_NOTIFY_PROJECT_ID=""
    local project_json="${root}/.dev-team-agents/project.json"
    if [ -f "$project_json" ]; then
        # One field from a small file we write ourselves — sed, not a python fork.
        DEVTEAM_NOTIFY_PROJECT_ID="$(sed -n 's/.*"project_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$project_json" | head -1)"
    fi
    DEVTEAM_NOTIFY_SESSION_ID=""
    if [ "$session" != "__unset__" ]; then
        DEVTEAM_NOTIFY_SESSION_ID="$session"
    elif command -v state_get >/dev/null 2>&1 && [ -f "${state_dir}/state.json" ]; then
        DEVTEAM_NOTIFY_SESSION_ID="$(state_get session_id "${state_dir}/state.json" 2>/dev/null || true)"
    fi
}

# suppress_notifications is `false`, `true`, or a list of levels (["info"]); a list
# arrives here stringified, so a substring test on the level is the check.
devteam_notify_suppressed() {
    case "$DEVTEAM_NOTIFY_SUPPRESS" in
        true|True)  return 0 ;;
        false|False|"") return 1 ;;
        *"$1"*)     return 0 ;;
        *)          return 1 ;;
    esac
}

_devteam_json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/}"
    s="${s//$'\t'/ }"
    printf '%s' "$s"
}

devteam_notify() {
    local level="$1" code="$2" message="$3" ttl="${4:-0}" dedupe="${5:-}"
    [ -n "$DEVTEAM_NOTIFY_FILE" ] || return 0
    case "$level" in info|warning|critical) ;; *) return 0 ;; esac
    devteam_notify_suppressed "$level" && return 0

    if [ -n "$dedupe" ] && [ -f "$DEVTEAM_NOTIFY_FILE" ] \
        && grep -qF "\"dedupe_key\":\"$(_devteam_json_escape "$dedupe")\"" "$DEVTEAM_NOTIFY_FILE" 2>/dev/null; then
        return 0
    fi

    local now expires id
    now="$(date +%s)"
    expires=0
    [ "${ttl:-0}" -gt 0 ] 2>/dev/null && expires=$(( now + ttl ))
    id="${now}-$$-${RANDOM}${RANDOM}"

    mkdir -p "$(dirname "$DEVTEAM_NOTIFY_FILE")" 2>/dev/null || return 0
    printf '{"id":"%s","ts":%s,"project_id":"%s","session_id":"%s","level":"%s","code":"%s","message":"%s","dedupe_key":"%s","expires_at":%s}\n' \
        "$id" "$now" \
        "$(_devteam_json_escape "$DEVTEAM_NOTIFY_PROJECT_ID")" \
        "$(_devteam_json_escape "$DEVTEAM_NOTIFY_SESSION_ID")" \
        "$level" \
        "$(_devteam_json_escape "$code")" \
        "$(_devteam_json_escape "$message")" \
        "$(_devteam_json_escape "$dedupe")" \
        "$expires" >> "$DEVTEAM_NOTIFY_FILE" 2>/dev/null || return 0

    # Bounded by the writer, never by a reader: the CLI does not rewrite this file,
    # so only the side that appends may trim it. tail + rename keeps a concurrent
    # reader on a complete file.
    local lines
    lines="$(wc -l < "$DEVTEAM_NOTIFY_FILE" 2>/dev/null | tr -d ' ')"
    if [ "${lines:-0}" -gt "$DEVTEAM_NOTIFY_MAX_LINES" ] 2>/dev/null; then
        local tmp="${DEVTEAM_NOTIFY_FILE}.tmp.$$"
        tail -n "$DEVTEAM_NOTIFY_MAX_LINES" "$DEVTEAM_NOTIFY_FILE" > "$tmp" 2>/dev/null \
            && mv -f "$tmp" "$DEVTEAM_NOTIFY_FILE" 2>/dev/null
        rm -f "$tmp" 2>/dev/null
    fi
    return 0
}
