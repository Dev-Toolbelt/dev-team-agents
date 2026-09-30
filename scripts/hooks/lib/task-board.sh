#!/usr/bin/env bash
# task-board.sh — shared logic for every hook that feeds the task board (ADR-0018).
#
# Not a hook. Source it, then:
#   devteam_task_board_init                      resolve root, state dir, CLI; 1 when not in a project
#   devteam_task_board_session_id <payload>      the payload's session id ("" when absent or unsafe)
#   devteam_task_board_record <payload>          fold a todo-tool call into its record; raise session_done
#   devteam_task_board_mark <idle|ended> <payload>   mark a session; raise session_abandoned on `ended`
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
    id="$(printf '%s' "$1" | sed -n 's/.*"session[_]\{0,1\}[iI][dD]"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
    if [[ "$id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ ]]; then
        printf '%s' "$id"
    fi
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

_tb_msg() {  # _tb_msg <lang> <en> <pt-BR> <es>
    case "$1" in
        pt-BR|pt*) printf '%s' "$3" ;;
        es*)       printf '%s' "$4" ;;
        *)         printf '%s' "$2" ;;
    esac
}

_tb_notify() {  # _tb_notify <level> <code> <session> <en> <pt-BR> <es>
    local level="$1" code="$2" session="$3" lang
    lang="$(_tb_pref language en)"
    devteam_notify_init "$TB_ROOT" "$TB_STATE_DIR" "$(_tb_suppress)" "$session"
    devteam_notify "$level" "$code" "$(_tb_msg "$lang" "$4" "$5" "$6")" 86400 "${code}:${session}"
}

devteam_task_board_record() {
    local payload="$1" out session
    [ -f "$TB_CLI" ] || return 0
    out="$(printf '%s' "$payload" | python3 "$TB_CLI" tasks record --project-root "$TB_ROOT" --json 2>/dev/null)" || return 0
    printf '%s' "$out" | grep -q '"became_all_done": true' || return 0
    session="$(printf '%s' "$out" | sed -n 's/.*"session": "\([^"]*\)".*/\1/p' | head -1)"
    local short="${session:0:8}"
    _tb_notify info "tasks.session_done" "$session" \
        "Session ${short}: every task is done." \
        "Sessão ${short}: todas as tarefas foram concluídas." \
        "Sesión ${short}: todas las tareas están completas."
    return 0
}

devteam_task_board_mark() {
    local state="$1" payload="$2" out open session
    [ -f "$TB_CLI" ] || return 0
    out="$(printf '%s' "$payload" | python3 "$TB_CLI" tasks mark --project-root "$TB_ROOT" --state "$state" --json 2>/dev/null)" || return 0
    [ "$state" = "ended" ] || return 0
    printf '%s' "$out" | grep -q '"marked": true' || return 0
    open="$(printf '%s' "$out" | sed -n 's/.*"open": \([0-9]*\).*/\1/p' | head -1)"
    [ "${open:-0}" -gt 0 ] 2>/dev/null || return 0
    session="$(devteam_task_board_session_id "$payload")"
    local short="${session:0:8}"
    _tb_notify warning "tasks.session_abandoned" "$session" \
        "Session ${short} ended with ${open} task(s) still open." \
        "A sessão ${short} terminou com ${open} tarefa(s) em aberto." \
        "La sesión ${short} terminó con ${open} tarea(s) abierta(s)."
    return 0
}
