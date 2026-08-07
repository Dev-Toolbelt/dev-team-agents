#!/usr/bin/env bash
# DISABLED (2026-08-06) — pending review, see CLAUDE-md/hooks.md § Disabled Hooks.
# Rename back to 04-notifier.sh to re-enable.
# Stop sub-script: emits context-window warnings and a rotating tip of session
# using the DEV TEAM AGENTS notification format.
#
# Tip data: tips/tips.en.txt, tips/tips.pt-BR.txt, tips/tips.es.txt — one tip per
# line, 15 lines each, index selected by (day_of_month - 1) % 15. Adding a locale
# means adding a file plus one `case` arm; the tip text never lives in this script.
#
# Context estimation strategy (in order of preference):
#   1. Transcript-based: reads the LAST assistant usage entry's
#      cache_read_input_tokens + cache_creation_input_tokens + input_tokens —
#      prompt caching means that sum IS the exact context size sent on the most
#      recent API call, so no compensating multiplier is needed. Summing across
#      turns instead would double-count history repeatedly, since each turn's
#      input_tokens already includes everything sent before it.
#   2. Turn-count heuristic: fallback when transcript_path is not available.
#
# transcript_multiplier is read from preferences.json for backward compatibility
# but is no longer applied by method 1 — see notifications.md.
set -uo pipefail

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
USER_DATA_DIR="${PROJECT_ROOT}/.dev-team-agents/user-data"
PREFS_FILE="${USER_DATA_DIR}/preferences.json"
SESSION_ID_FILE="${USER_DATA_DIR}/.session-id"
SESSION_HEAD_FILE="${USER_DATA_DIR}/.session-head"
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
NO_COMMIT_TURNS=8

# ── Read preferences (overrides defaults when file is valid) ──────────────────
if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    # Single fork reading all seven keys at once (was 7 separate python3
    # subprocess calls) — same defaults, same fallback-to-default behavior.
    _ALL_PREFS=$(python3 -c "
import json
try:
    d = json.load(open('$PREFS_FILE'))
except Exception:
    d = {}
def s(v):
    return str(v).lower() if isinstance(v, bool) else str(v)
keys = [
    ('suppress_notifications', False),
    ('language', 'en'),
    ('context_window_percent_warning', 55),
    ('context_window_percent_limit', 60),
    ('transcript_multiplier', 1.8),
    ('model_max_tokens', 200000),
    ('session_no_commit_turns', 8),
]
print('\x1f'.join(s(d.get(k, dv)) for k, dv in keys))
" 2>/dev/null || true)
    if [ -n "$_ALL_PREFS" ]; then
        # shellcheck disable=SC2034  # TRANSCRIPT_MULTIPLIER read for backward compatibility only, see comment above
        IFS=$'\x1f' read -r SUPPRESS USER_LANG WARN_PCT CRIT_PCT TRANSCRIPT_MULTIPLIER MODEL_MAX_TOKENS NO_COMMIT_TURNS <<< "$_ALL_PREFS"
    fi
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
STATE_NOCOMMIT=$(echo "$STATE" | cut -d: -f5)
TODAY=$(date +%Y-%m-%d 2>/dev/null || echo "")

if [ "$STATE_SESSION" = "$SESSION_ID" ]; then
    TURNS=$(( ${STATE_TURNS:-0} + 1 ))
    TIP_SHOWN="${STATE_TIP:-0}"
    NOCOMMIT_WARNED="${STATE_NOCOMMIT:-0}"
else
    TURNS=1
    TIP_SHOWN=0
    NOCOMMIT_WARNED=0
fi

_save_state() {
    printf '%s:%d:%d:%s:%d\n' "$SESSION_ID" "$TURNS" "$TIP_SHOWN" "${STATE_DATE:-}" "$NOCOMMIT_WARNED" > "$NOTIFIER_STATE_FILE"
}
_save_state

# ── Uncommitted-progress check (once per session) ──────────────────────────────
# A session can accumulate real work — many turns, files changed — without a
# single commit landing. That is exactly the state in which a crash, a
# /clear, or a context-window compaction loses the most. Fires at most once
# per session: TURNS reached the threshold, HEAD hasn't moved since
# session-start.sh recorded it, and the working tree actually has changes.
if [ "$NOCOMMIT_WARNED" -eq 0 ] 2>/dev/null \
    && [ "$TURNS" -ge "$NO_COMMIT_TURNS" ] 2>/dev/null \
    && [ -f "$SESSION_HEAD_FILE" ] \
    && command -v git >/dev/null 2>&1 \
    && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    SESSION_HEAD=$(cat "$SESSION_HEAD_FILE" 2>/dev/null || echo "")
    CURRENT_HEAD=$(git rev-parse HEAD 2>/dev/null || echo "")
    if [ -n "$SESSION_HEAD" ] && [ "$SESSION_HEAD" = "$CURRENT_HEAD" ] \
        && [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        NOCOMMIT_WARNED=1
        _save_state
        if [ "$USER_LANG" = "pt-BR" ] || [ "$USER_LANG" = "pt" ]; then
            _notify "warning" "⚠️" "${TURNS} turnos de trabalho nesta sessão sem nenhum commit. Considere commitar o progresso para não arriscar perdê-lo."
        elif [ "$USER_LANG" = "es" ]; then
            _notify "warning" "⚠️" "${TURNS} turnos de trabajo en esta sesión sin ningún commit. Considera confirmar el progreso para no arriesgarte a perderlo."
        else
            _notify "warning" "⚠️" "${TURNS} turns of work this session with no commit yet. Consider committing your progress to avoid losing it."
        fi
    fi
fi

# ── Fast-path: skip only the once-per-day tip in purely conversational sessions
# Context-window estimation must still run every Stop regardless of
# DEVTEAM_NO_CHANGES — context grows from conversation turns, not from file
# edits, so a no-file-change session is exactly where the warning matters most.
# Only the once-per-day tip (already shown today) is safe to skip here.
SKIP_TIP=0
if [ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && [ "${STATE_DATE:-}" = "${TODAY:-}" ]; then
    SKIP_TIP=1
fi

# ── Context window estimation ─────────────────────────────────────────────────
PCT_USED=0
METHOD="turns"

# Attempt 1: transcript-based estimation (more accurate than turn count).
# The hook payload (stdin, saved to DEVTEAM_HOOK_PAYLOAD by stop.sh) contains
# transcript_path — a JSONL file where each line is a conversation turn with
# usage data. Anthropic's prompt caching means each assistant usage entry's
# input_tokens is only the NEW delta for that turn — the rest of the
# conversation already sent shows up as cache_read_input_tokens /
# cache_creation_input_tokens. Summing input_tokens across turns therefore
# double-counts the same history repeatedly and grows unboundedly.
# The actual current context size is the LAST assistant usage entry's
# cache_read + cache_creation + input tokens — that IS what was sent to the
# API on the most recent call. No compensating multiplier is needed once the
# real value is read directly.
TRANSCRIPT_PATH=""
if [ -n "${DEVTEAM_HOOK_PAYLOAD:-}" ] && [ -f "${DEVTEAM_HOOK_PAYLOAD:-}" ] && command -v python3 >/dev/null 2>&1; then
    TRANSCRIPT_PATH=$(python3 -c \
        "import json; d=json.load(open('$DEVTEAM_HOOK_PAYLOAD')); print(d.get('transcript_path',''))" \
        2>/dev/null || true)
fi

# Incremental scan cache: transcripts only grow (append-only JSONL), so a
# Stop hook that already scanned up to byte N last time never needs to
# re-read bytes [0, N) again — only what was appended since. Cache file
# holds transcript_path\x1foffset\x1flast_context. A path mismatch (new
# session) or an offset past EOF (transcript rotated/truncated) invalidates
# the cache and falls back to a full scan, same as before this change.
TRANSCRIPT_CACHE_FILE="${USER_DATA_DIR}/.notifier-transcript-cache"
CACHED_PATH="" CACHED_OFFSET=0 CACHED_CONTEXT=0
if [ -f "$TRANSCRIPT_CACHE_FILE" ]; then
    IFS=$'\x1f' read -r CACHED_PATH CACHED_OFFSET CACHED_CONTEXT < "$TRANSCRIPT_CACHE_FILE" 2>/dev/null || true
fi

if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ] && command -v python3 >/dev/null 2>&1; then
    FILE_SIZE=$(stat -f %z "$TRANSCRIPT_PATH" 2>/dev/null || stat -c %s "$TRANSCRIPT_PATH" 2>/dev/null || echo 0)
    START_OFFSET=0
    LAST_CONTEXT_SEED=0
    if [ "$CACHED_PATH" = "$TRANSCRIPT_PATH" ] \
        && [ "${CACHED_OFFSET:-0}" -le "${FILE_SIZE:-0}" ] 2>/dev/null; then
        START_OFFSET="${CACHED_OFFSET:-0}"
        LAST_CONTEXT_SEED="${CACHED_CONTEXT:-0}"
    fi

    SCAN_RESULT=$(python3 -c "
import json
path = '${TRANSCRIPT_PATH}'
start_offset = ${START_OFFSET}
last_context = ${LAST_CONTEXT_SEED}
new_offset = start_offset
try:
    with open(path, 'rb') as f:
        f.seek(start_offset)
        data = f.read()
    # Only advance the offset past complete lines — a partial trailing line
    # (transcript still being appended) is re-read next time instead of
    # being split across two scans, which would otherwise corrupt it.
    newline_idx = data.rfind(b'\n')
    processed = data[:newline_idx + 1] if newline_idx != -1 else b''
    new_offset = start_offset + len(processed)
    for line in processed.decode('utf-8', errors='ignore').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            usage = (entry.get('usage') or
                     entry.get('message', {}).get('usage') or
                     entry.get('response', {}).get('usage') or {})
            if not usage:
                continue
            context = (usage.get('input_tokens', 0) +
                       usage.get('cache_read_input_tokens', 0) +
                       usage.get('cache_creation_input_tokens', 0))
            if context > 0:
                last_context = context
        except Exception:
            pass
except Exception:
    pass
print(f'{new_offset}\x1f{last_context}')
" 2>/dev/null || printf '%s\x1f%s' "$START_OFFSET" "$LAST_CONTEXT_SEED")

    IFS=$'\x1f' read -r NEW_OFFSET TRANSCRIPT_TOKENS <<< "$SCAN_RESULT"
    printf '%s\x1f%s\x1f%s\n' "$TRANSCRIPT_PATH" "${NEW_OFFSET:-0}" "${TRANSCRIPT_TOKENS:-0}" > "$TRANSCRIPT_CACHE_FILE" 2>/dev/null || true

    if [ "${TRANSCRIPT_TOKENS:-0}" -gt 0 ] 2>/dev/null; then
        PCT_USED=$(python3 -c \
            "print(min(100, round($TRANSCRIPT_TOKENS * 100 / $MODEL_MAX_TOKENS)))" \
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
if [ "$SKIP_TIP" -eq 0 ] && [ "${STATE_DATE:-}" != "${TODAY:-}" ] && ! _is_suppressed "info"; then
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

    TIP_SHOWN=1
    STATE_DATE="$TODAY"
    _save_state
fi

exit 0
