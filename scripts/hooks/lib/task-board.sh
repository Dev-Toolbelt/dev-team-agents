#!/usr/bin/env bash
# task-board.sh — shared logic for every hook that feeds the task board (ADR-0018).
#
# Not a hook. Source it, then:
#   devteam_task_board_init                      resolve root, state dir, CLI; 1 when not in a project
#   devteam_task_board_session_id <payload>      the payload's session id ("" when absent or unsafe)
#   devteam_task_board_record <payload>          fold a todo-tool or agent call into its record; raise session_done
#   devteam_task_board_mark <idle|ended> <payload>   mark a session; raise session_abandoned on `ended`;
#                                                on `idle` also settles a command/prompt review window
#   devteam_task_board_review_open <payload>     open or join a review window (In Review column)
#   devteam_task_board_review_result <payload>   fold a review agent's output into its window
#   devteam_task_board_has_record <payload>      0 when the payload's session has a task record
#
# Two rules this file exists to keep:
#   1. A hook never disturbs the provider — every function returns 0 and prints nothing.
#   2. No python for a call that is not ours. The callers gate on a bash string test
#      (or a `[ -f ]`) BEFORE any function here that forks the CLI.

_TB_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "${_TB_LIB_DIR}/data-dirs.sh"
# shellcheck source=scripts/hooks/lib/notify.sh
. "${_TB_LIB_DIR}/notify.sh"

TB_CLI="${_TB_LIB_DIR}/../../cli/devteam"
TB_ROOT=""
TB_STATE_DIR=""

devteam_task_board_init() {
    local roots common
    roots="$(git rev-parse --show-toplevel --git-common-dir 2>/dev/null)" || return 1
    TB_ROOT="$(printf '%s\n' "$roots" | sed -n 1p)"
    common="$(printf '%s\n' "$roots" | sed -n 2p)"
    # `--git-common-dir` is relative to the working directory (`../.git` from a
    # subdirectory), not to the toplevel, so resolve it from here before walking up.
    common="$(cd "$common" 2>/dev/null && pwd -P)" || return 1
    local main
    main="$(cd "${common}/.." 2>/dev/null && pwd -P)"
    [ -n "$main" ] && TB_ROOT="$main"
    [ -n "$TB_ROOT" ] || return 1
    TB_STATE_DIR="$(devteam_state_dir "$TB_ROOT")"
    [ -d "$TB_STATE_DIR" ] || return 1
    return 0
}

# A session id that is safe to use as a filename without the CLI's rewriting. Anything
# else is left to the CLI (record) or skipped (mark, which only checks a file exists).
devteam_task_board_session_id() {
    local id
    # The FIRST session key wins: a payload's own id comes before anything a tool echoes back,
    # and a greedy match would take the last one, from inside the tool's arguments or output.
    id="$(printf '%s' "$1" | grep -oE '"session_?[iI][dD]"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n 1 | sed 's/^[^:]*:[[:space:]]*"//; s/"$//')"
    if [[ "$id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
        printf '%s' "$id"
    fi
}

# 0 when this payload's session already has a task record. A review can only involve tasks
# that exist, so a session without a record never forks python for a review trigger.
devteam_task_board_has_record() {
    local session
    session="$(devteam_task_board_session_id "$1")"
    [ -n "$session" ] && [ -f "${TB_STATE_DIR}/task-board/${session}.json" ]
}

_tb_pref() {  # _tb_pref <key> <default>
    local file value
    file="$(devteam_prefs_file "$TB_ROOT")"
    value=""
    [ -f "$file" ] && value="$(sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\{0,1\}\([^\",}]*\).*/\1/p" "$file" | head -1)"
    printf '%s' "${value:-$2}"
}

_tb_suppress() {
    local file raw
    file="$(devteam_prefs_file "$TB_ROOT")"
    raw=""
    [ -f "$file" ] && raw="$(sed -n 's/.*"suppress_notifications"[[:space:]]*:[[:space:]]*//p' "$file" | head -1 | sed 's/[,}].*//')"
    printf '%s' "${raw:-false}"
}

_tb_notify() {  # _tb_notify <level> <code> <session> <en> <pt-BR> <es> [dedupe-suffix]
    local level="$1" code="$2" session="$3" lang key
    lang="$(_tb_pref language en)"
    key="${code}:${session}${7:+:$7}"
    devteam_notify_init "$TB_ROOT" "$TB_STATE_DIR" "$(_tb_suppress)" "$session"
    devteam_notify "$level" "$code" "$(devteam_msg "$lang" "$4" "$5" "$6")" 86400 "$key"
}

# How a message names the session: its title as the provider shows it, quoted and already cut
# by the CLI (`title_short`, free of quotes and backslashes), else the first 8 characters of its id.
_tb_label() {  # _tb_label <session> <cli-json>
    local title
    title="$(_tb_str "$2" title_short)"
    if [ -n "$title" ]; then
        printf '"%s"' "$title"
    else
        printf '%s' "${1:0:8}"
    fi
}

_tb_notify_done() {  # _tb_notify_done <session> <cli-json>
    local label
    label="$(_tb_label "$1" "$2")"
    _tb_notify info "tasks.session_done" "$1" \
        "Session ${label}: every task is done." \
        "Sessão ${label}: todas as tarefas foram concluídas." \
        "Sesión ${label}: todas las tareas están completas."
}

_tb_notify_findings() {  # _tb_notify_findings <session> <window> <count> <cli-json>
    local label
    label="$(_tb_label "$1" "$4")"
    _tb_notify warning "tasks.review_findings" "$1" \
        "Session ${label}: the review found ${3} issue(s); the tasks stay in review." \
        "Sessão ${label}: a revisão encontrou ${3} problema(s); as tarefas continuam em revisão." \
        "Sesión ${label}: la revisión encontró ${3} problema(s); las tareas siguen en revisión." \
        "$2"
}

_tb_int() {  # _tb_int <json> <key>  → the integer value of "key": N, or empty
    printf '%s' "$1" | sed -n "s/.*\"$2\": \([0-9][0-9]*\).*/\1/p" | head -1
}

_tb_str() {  # _tb_str <json> <key>  → the string value of "key": "v", or empty
    printf '%s' "$1" | sed -n "s/.*\"$2\": \"\([^\"]*\)\".*/\1/p" | head -1
}

devteam_task_board_record() {
    local payload="$1" out session
    [ -f "$TB_CLI" ] || return 0
    out="$(printf '%s' "$payload" | python3 "$TB_CLI" tasks record --project-root "$TB_ROOT" --json 2>/dev/null)" || return 0
    printf '%s' "$out" | grep -q '"became_all_done": true' || return 0
    session="$(_tb_str "$out" session)"
    _tb_notify_done "$session" "$out"
    return 0
}

devteam_task_board_mark() {
    local state="$1" payload="$2" out open session
    [ -f "$TB_CLI" ] || return 0
    out="$(printf '%s' "$payload" | python3 "$TB_CLI" tasks mark --project-root "$TB_ROOT" --state "$state" --json 2>/dev/null)" || return 0
    printf '%s' "$out" | grep -q '"marked": true' || return 0
    if [ "$state" = "idle" ]; then
        _tb_review_outcome "$out" review_result review_window review_findings "$payload"
        # A background agent's hand-back can finish the last task with no review window involved.
        if ! printf '%s' "$out" | grep -q '"review_result": true' && printf '%s' "$out" | grep -q '"became_all_done": true'; then
            _tb_notify_done "$(devteam_task_board_session_id "$payload")" "$out"
        fi
        return 0
    fi
    open="$(printf '%s' "$out" | sed -n 's/.*"open": \([0-9]*\).*/\1/p' | head -1)"
    [ "${open:-0}" -gt 0 ] 2>/dev/null || return 0
    session="$(devteam_task_board_session_id "$payload")"
    local label
    label="$(_tb_label "$session" "$out")"
    _tb_notify warning "tasks.session_abandoned" "$session" \
        "Session ${label} ended with ${open} task(s) still open." \
        "A sessão ${label} terminou com ${open} tarefa(s) em aberto." \
        "La sesión ${label} terminó con ${open} tarea(s) abierta(s)."
    return 0
}

# A review-window result, from `mark idle` (keys review_*) or `review-result` (keys result/window/findings).
# `mark idle` can close several windows in one Stop and lists each in `review_results`: one
# findings notification per window, its own dedupe suffix; `became_all_done` is computed by the
# CLI after every outcome, so session_done is raised once.
_tb_review_outcome() {  # _tb_review_outcome <json> <result-key> <window-key> <findings-key> <payload>
    local out="$1" session window findings pairs
    printf '%s' "$out" | grep -q "\"$2\": true" || return 0
    session="$(devteam_task_board_session_id "$5")"
    [ -n "$session" ] || session="$(_tb_str "$out" session)"
    pairs=""
    if printf '%s' "$out" | grep -q '"review_results"'; then
        pairs="$(printf '%s' "$out" | python3 -c '
import json, sys
for r in json.load(sys.stdin).get("review_results") or []:
    print(r.get("window") or "w", r.get("findings") or 0)
' 2>/dev/null)"
    fi
    if [ -z "$pairs" ]; then
        window="$(_tb_str "$out" "$3")"
        pairs="${window:-w} $(_tb_int "$out" "$4")"
    fi
    while read -r window findings; do
        if [ "${findings:-0}" -gt 0 ] 2>/dev/null; then
            _tb_notify_findings "$session" "${window:-w}" "$findings" "$out"
        fi
    done <<< "$pairs"
    if printf '%s' "$out" | grep -q '"became_all_done": true'; then
        _tb_notify_done "$session" "$out"
    fi
    return 0
}

devteam_task_board_review_open() {
    [ -f "$TB_CLI" ] || return 0
    printf '%s' "$1" | python3 "$TB_CLI" tasks review-open --project-root "$TB_ROOT" --json >/dev/null 2>&1
    return 0
}

devteam_task_board_review_result() {
    local payload="$1" out
    [ -f "$TB_CLI" ] || return 0
    out="$(printf '%s' "$payload" | python3 "$TB_CLI" tasks review-result --project-root "$TB_ROOT" --json 2>/dev/null)" || return 0
    _tb_review_outcome "$out" result window findings "$payload"
    return 0
}
