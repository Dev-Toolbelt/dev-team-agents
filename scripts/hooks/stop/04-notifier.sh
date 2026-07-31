#!/usr/bin/env bash
# Stop sub-script: emits context-window warnings and a rotating tip of session
# using the DEV TEAM AGENTS notification format.
#
# Tip data: tips/tips.en.txt, tips/tips.pt-BR.txt, tips/tips.es.txt — one tip per
# line, 15 lines each, index selected by (day_of_month - 1) % 15. Adding a locale
# means adding a file plus one `case` arm; the tip text never lives in this script.
#
# Context estimation strategy (in order of preference):
#   1. Transcript-based: read token usage from transcript JSONL (more accurate)
#      then apply transcript_multiplier to compensate for system prompt + tools
#      not stored in the transcript.
#   2. Turn-count heuristic: fallback when transcript_path is not available.
set -uo pipefail

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
USER_DATA_DIR="${PROJECT_ROOT}/.dev-team-agents/user-data"
PREFS_FILE="${USER_DATA_DIR}/preferences.json"
SESSION_ID_FILE="${USER_DATA_DIR}/.session-id"
NOTIFIER_STATE_FILE="${USER_DATA_DIR}/.notifier-state"

# Rotating tips live in locale-keyed data files next to this script
# (tips/tips.<lang>.txt, one tip per line, 15 lines each). Only the selected
# locale's file is read, and only when the once-per-day gate at the bottom opens.
TIPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/tips"

# ── Hardcoded defaults (used when prefs file is missing or malformed) ─────────
SUPPRESS="false"
USER_LANG="en"
WARN_PCT=55
CRIT_PCT=60
TRANSCRIPT_MULTIPLIER="1.8"
MODEL_MAX_TOKENS=200000

# ── Read preferences (overrides defaults when file is valid) ──────────────────
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    _pref() {
        python3 -c \
            "import json,sys; d=json.load(open('$PREFS_FILE')); v=d.get('$1',$2); print(str(v).lower() if isinstance(v,bool) else v)" \
            2>/dev/null || echo "$2"
    }
    SUPPRESS=$(_pref suppress_notifications false)
    USER_LANG=$(_pref language en)
    WARN_PCT=$(_pref context_window_percent_warning 55)
    CRIT_PCT=$(_pref context_window_percent_limit 60)
    TRANSCRIPT_MULTIPLIER=$(_pref transcript_multiplier 1.8)
    MODEL_MAX_TOKENS=$(_pref model_max_tokens 200000)
fi

# ── Helper: check suppression ─────────────────────────────────────────────────
_is_suppressed() {
    local type="$1"
    case "$SUPPRESS" in
        true)       return 0 ;;
        false)      return 1 ;;
        *"$type"*)  return 0 ;;
        *)          return 1 ;;
    esac
}

# ── Helper: emit notification ─────────────────────────────────────────────────
_notify() {
    local type="$1" icon="$2" msg="$3"
    _is_suppressed "$type" && return
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " ${icon}  DEV TEAM AGENTS  ${icon}"
    echo " ${msg}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# ── Session turn counter ──────────────────────────────────────────────────────
SESSION_ID=$(cat "$SESSION_ID_FILE" 2>/dev/null || echo "0")
STATE=$(cat "$NOTIFIER_STATE_FILE" 2>/dev/null || echo "")
STATE_SESSION=$(echo "$STATE" | cut -d: -f1)
STATE_TURNS=$(echo "$STATE" | cut -d: -f2)
STATE_TIP=$(echo "$STATE" | cut -d: -f3)
STATE_DATE=$(echo "$STATE" | cut -d: -f4)
TODAY=$(date +%Y-%m-%d 2>/dev/null || echo "")

if [ "$STATE_SESSION" = "$SESSION_ID" ]; then
    TURNS=$(( ${STATE_TURNS:-0} + 1 ))
    TIP_SHOWN="${STATE_TIP:-0}"
else
    TURNS=1
    TIP_SHOWN=0
fi

printf '%s:%d:%d:%s\n' "$SESSION_ID" "$TURNS" "$TIP_SHOWN" "${STATE_DATE:-}" > "$NOTIFIER_STATE_FILE"

# ── Fast-path: skip expensive processing in purely conversational sessions ────
# If no file changes were detected (DEVTEAM_NO_CHANGES=true) AND the tip for
# today was already shown, there is nothing to emit — exit early.
if [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && [ "${STATE_DATE:-}" = "${TODAY:-}" ]; then
    exit 0
fi

# ── Context window estimation ─────────────────────────────────────────────────
PCT_USED=0
METHOD="turns"

# Attempt 1: transcript-based estimation (more accurate than turn count).
# The hook payload (stdin, saved to DEVTEAM_HOOK_PAYLOAD by stop.sh) contains
# transcript_path — a JSONL file where each line is a conversation turn with
# usage data. We sum all input+output tokens and apply a multiplier to
# estimate the full context (system prompt + tools + messages).
TRANSCRIPT_PATH=""
if [ -n "${DEVTEAM_HOOK_PAYLOAD:-}" ] && [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ] && command -v python3 >/dev/null 2>&1; then
    TRANSCRIPT_PATH=$(python3 -c \
        "import json; d=json.load(open('$DEVTEAM_HOOK_PAYLOAD')); print(d.get('transcript_path',''))" \
        2>/dev/null || true)
fi

if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ] && command -v python3 >/dev/null 2>&1; then
    TRANSCRIPT_TOKENS=$(python3 -c "
import json
total = 0
try:
    with open('${TRANSCRIPT_PATH}') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                usage = (entry.get('usage') or
                         entry.get('message', {}).get('usage') or
                         entry.get('response', {}).get('usage') or {})
                total += usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            except Exception:
                pass
except Exception:
    pass
print(total)
" 2>/dev/null || echo 0)

    if [ "${TRANSCRIPT_TOKENS:-0}" -gt 0 ] 2>/dev/null; then
        PCT_USED=$(python3 -c \
            "print(min(100, round($TRANSCRIPT_TOKENS * $TRANSCRIPT_MULTIPLIER * 100 / $MODEL_MAX_TOKENS)))" \
            2>/dev/null || echo 0)
        METHOD="transcript"
    fi
fi

# Attempt 2: turn-count heuristic (fallback when transcript is unavailable).
# Calibration: 100% ≈ 45 turns (conservative estimate). Scale linearly.
if [ "$METHOD" = "turns" ]; then
    WARN_TURNS=$(python3 -c "print(max(5, round($WARN_PCT * 45 / 100)))" 2>/dev/null || echo 15)
    CRIT_TURNS=$(python3 -c "print(max(8, round($CRIT_PCT * 45 / 100)))" 2>/dev/null || echo 25)
    if [ "$TURNS" -ge "$CRIT_TURNS" ]; then
        PCT_USED=$CRIT_PCT
    elif [ "$TURNS" -ge "$WARN_TURNS" ]; then
        PCT_USED=$WARN_PCT
    fi
fi

# ── Emit context notification ─────────────────────────────────────────────────
if [ "${PCT_USED:-0}" -ge "${CRIT_PCT:-60}" ] 2>/dev/null; then
    if [ "$USER_LANG" = "pt-BR" ] || [ "$USER_LANG" = "pt" ]; then
        _notify "critical" "🚨" "Janela de contexto estimada em ≈${PCT_USED}%! Execute /compact agora ou inicie uma nova sessão para manter a qualidade das respostas."
    elif [ "$USER_LANG" = "es" ]; then
        _notify "critical" "🚨" "Ventana de contexto estimada en ≈${PCT_USED}%. Ejecuta /compact ahora o inicia una nueva sesión para mantener la calidad."
    else
        _notify "critical" "🚨" "Context window estimated at ≈${PCT_USED}%. Run /compact now or start a new session to maintain response quality."
    fi
elif [ "${PCT_USED:-0}" -ge "${WARN_PCT:-55}" ] 2>/dev/null; then
    if [ "$USER_LANG" = "pt-BR" ] || [ "$USER_LANG" = "pt" ]; then
        _notify "warning" "⚠️" "Sua janela de contexto está se aproximando do limite (≈${PCT_USED}%). Considere executar /compact ou iniciar uma nova sessão."
    elif [ "$USER_LANG" = "es" ]; then
        _notify "warning" "⚠️" "Tu ventana de contexto se está aproximando al límite (≈${PCT_USED}%). Considera ejecutar /compact o iniciar una nueva sesión."
    else
        _notify "warning" "⚠️" "Context window approaching limit (≈${PCT_USED}%). Consider running /compact or starting a new session."
    fi
fi

# ── Tip of session (once per session) ────────────────────────────────────────
if [ "${STATE_DATE:-}" != "${TODAY:-}" ] && ! _is_suppressed "info"; then
    DAY=$(date +%-d 2>/dev/null || date +%d | sed 's/^0//')
    TIP_INDEX=$(( (DAY - 1) % 15 ))

    case "$USER_LANG" in
        pt-BR|pt) TIP_FILE="$TIPS_DIR/tips.pt-BR.txt" ;;
        es)       TIP_FILE="$TIPS_DIR/tips.es.txt" ;;
        *)        TIP_FILE="$TIPS_DIR/tips.en.txt" ;;
    esac
    [ -f "$TIP_FILE" ] || TIP_FILE="$TIPS_DIR/tips.en.txt"

    # One tip per line, 15 lines per locale. Only the selected locale's file is
    # read, and only on the day the once-per-day gate above opens.
    TIP=$(sed -n "$((TIP_INDEX + 1))p" "$TIP_FILE" 2>/dev/null || true)

    [ -n "$TIP" ] && _notify "info" "ℹ️" "$TIP"

    printf '%s:%d:1:%s\n' "$SESSION_ID" "$TURNS" "$TODAY" > "$NOTIFIER_STATE_FILE"
fi

exit 0
