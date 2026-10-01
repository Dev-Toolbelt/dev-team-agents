#!/usr/bin/env bash
# Stop sub-script: session-progress notifications — context window, uncommitted
# progress, and the tip of the day — raised through the notification queue the
# desktop app shows (scripts/hooks/lib/notify.sh).
#
# It used to print a boxed banner to stdout. Stop-hook stdout is not shown to the
# user by any provider, so it was disabled on 2026-08-06 for costing a turn's worth
# of python forks with nothing visible to show for it. Re-enabled with both causes
# removed: the output now reaches the app, and the script forks python at most
# ONCE per Stop — for the preference read and the transcript scan together — and
# not at all when neither exists.
#
# Each notice fires at most once: context warning and critical once per session
# each (dedupe key carries the session id), uncommitted progress once per session,
# the tip once per day. A notice raised on every Stop above a threshold would be a
# notification per turn.
#
# Tip data: tips/tips.<lang>.txt — one tip per line, 15 lines, index
# (day_of_month - 1) % 15. Adding a locale is one file plus one `case` arm.
#
# Context estimate, in order of preference:
#   1. Transcript: the LAST assistant usage entry's input + cache_read +
#      cache_creation tokens — with prompt caching that sum IS the context sent on
#      the most recent call. Scanned incrementally from a cached byte offset.
#   2. Turn count: fallback without a transcript; 100% ≈ 45 turns.
set -uo pipefail

# One git fork for both roots (this runs on every Stop). Outside a work tree it
# fails and the script exits.
_ROOTS="$(git rev-parse --show-toplevel --git-common-dir 2>/dev/null)" || exit 0
PROJECT_ROOT="$(printf '%s\n' "$_ROOTS" | sed -n 1p)"
_COMMON="$(printf '%s\n' "$_ROOTS" | sed -n 2p)"
case "$_COMMON" in /*) ;; *) _COMMON="${PROJECT_ROOT}/${_COMMON}" ;; esac
MAIN_REPO_ROOT="$(cd "${_COMMON}/.." 2>/dev/null && pwd)"
[ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$PROJECT_ROOT"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
LIB_DIR="${SCRIPT_DIR}/../lib"
# shellcheck source=scripts/lib/state.sh
. "${SCRIPT_DIR}/../../lib/state.sh"
# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "${LIB_DIR}/data-dirs.sh"
# shellcheck source=scripts/hooks/lib/notify.sh
. "${LIB_DIR}/notify.sh"

STATE_DIR="$(devteam_state_dir "$MAIN_REPO_ROOT")"
[ -d "$STATE_DIR" ] || exit 0
STATE_FILE="${STATE_DIR}/state.json"
PREFS_FILE="$(devteam_prefs_file "$MAIN_REPO_ROOT")"
NOTIFIER_STATE_FILE="${STATE_DIR}/.notifier-state"
TRANSCRIPT_CACHE_FILE="${STATE_DIR}/.notifier-transcript-cache"
TIPS_DIR="${SCRIPT_DIR}/tips"

# ── Defaults (used when a preference or the transcript is unavailable) ────────
SUPPRESS="false"
USER_LANG="en"
WARN_PCT=55
CRIT_PCT=60
MODEL_MAX_TOKENS=200000
NO_COMMIT_TURNS=8
TRANSCRIPT_PATH=""
TRANSCRIPT_TOKENS=0
SESSION_ID=""
SESSION_HEAD=""

CACHED_PATH="" CACHED_OFFSET=0 CACHED_CONTEXT=0
if [ -f "$TRANSCRIPT_CACHE_FILE" ]; then
    IFS=$'\x1f' read -r CACHED_PATH CACHED_OFFSET CACHED_CONTEXT < "$TRANSCRIPT_CACHE_FILE" 2>/dev/null || true
fi

# ── The one python fork: preferences, session state and the transcript scan ───
PAYLOAD="${DEVTEAM_HOOK_PAYLOAD:-}"
if command -v python3 >/dev/null 2>&1; then
    RESULT=$(python3 - "$PREFS_FILE" "$PAYLOAD" "$CACHED_PATH" "${CACHED_OFFSET:-0}" "${CACHED_CONTEXT:-0}" "$STATE_FILE" <<'PY' 2>/dev/null || true
import json, sys
prefs_file, payload_file, cached_path, cached_offset, cached_context, state_file = sys.argv[1:7]
try:
    prefs = json.load(open(prefs_file))
except Exception:
    prefs = {}
try:
    state = json.load(open(state_file))
except Exception:
    state = {}
def s(v):
    return str(v).lower() if isinstance(v, bool) else str(v)
values = [s(prefs.get(k, d)) for k, d in (
    ("suppress_notifications", False), ("language", "en"),
    ("context_window_percent_warning", 55), ("context_window_percent_limit", 60),
    ("model_max_tokens", 200000), ("session_no_commit_turns", 8))]
path, offset, context = "", 0, 0
try:
    path = json.load(open(payload_file)).get("transcript_path", "") or ""
except Exception:
    path = ""
if path:
    start = int(cached_offset) if path == cached_path else 0
    context = int(cached_context) if path == cached_path else 0
    offset = start
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            if start > f.tell():
                start, context = 0, 0
            f.seek(start)
            data = f.read()
        # Only past complete lines: a partial trailing line is still being written.
        cut = data.rfind(b"\n")
        done = data[:cut + 1] if cut != -1 else b""
        offset = start + len(done)
        for line in done.decode("utf-8", "ignore").splitlines():
            try:
                entry = json.loads(line)
            except Exception:
                continue
            usage = (entry.get("usage") or (entry.get("message") or {}).get("usage")
                     or (entry.get("response") or {}).get("usage") or {})
            total = (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                     + usage.get("cache_creation_input_tokens", 0)) if isinstance(usage, dict) else 0
            if total > 0:
                context = total
    except Exception:
        pass
print("\x1f".join(values + [path, str(offset), str(context),
                            str(state.get("session_id", "")), str(state.get("session_head", ""))]))
PY
)
    if [ -n "$RESULT" ]; then
        IFS=$'\x1f' read -r SUPPRESS USER_LANG WARN_PCT CRIT_PCT MODEL_MAX_TOKENS NO_COMMIT_TURNS \
            TRANSCRIPT_PATH NEW_OFFSET TRANSCRIPT_TOKENS SESSION_ID SESSION_HEAD <<< "$RESULT"
        if [ -n "$TRANSCRIPT_PATH" ]; then
            printf '%s\x1f%s\x1f%s\n' "$TRANSCRIPT_PATH" "${NEW_OFFSET:-0}" "${TRANSCRIPT_TOKENS:-0}" \
                > "$TRANSCRIPT_CACHE_FILE" 2>/dev/null || true
        fi
    fi
fi

devteam_notify_init "$MAIN_REPO_ROOT" "$STATE_DIR" "$SUPPRESS" "$SESSION_ID"
_NOW="$(date '+%Y-%m-%d %d' 2>/dev/null || echo "")"
TODAY="${_NOW% *}"
DAY="${_NOW#* }"; DAY="${DAY#0}"
# No session id (python or state.json unavailable): fall back to a per-day key. A fixed
# `0` made every "once per session" notice fire once and then never again, since its
# dedupe key stayed in the queue until 200 newer lines trimmed it out.
SESSION_ID="${SESSION_ID:-day-${TODAY}}"

# ── Session turn counter ──────────────────────────────────────────────────────
STATE_SESSION="" STATE_TURNS=0
if [ -f "$NOTIFIER_STATE_FILE" ]; then
    IFS=: read -r STATE_SESSION STATE_TURNS _ < "$NOTIFIER_STATE_FILE" 2>/dev/null || true
fi
if [ "$STATE_SESSION" = "$SESSION_ID" ]; then
    TURNS=$(( ${STATE_TURNS:-0} + 1 ))
else
    TURNS=1
fi
printf '%s:%d\n' "$SESSION_ID" "$TURNS" > "$NOTIFIER_STATE_FILE" 2>/dev/null || true

_msg() { devteam_msg "$USER_LANG" "$@"; }  # _msg <en> <pt-BR> <es>; devteam_msg is in lib/notify.sh

# ── Context window ────────────────────────────────────────────────────────────
PCT_USED=0
if [ "${TRANSCRIPT_TOKENS:-0}" -gt 0 ] 2>/dev/null && [ "${MODEL_MAX_TOKENS:-0}" -gt 0 ] 2>/dev/null; then
    PCT_USED=$(( TRANSCRIPT_TOKENS * 100 / MODEL_MAX_TOKENS ))
    [ "$PCT_USED" -gt 100 ] && PCT_USED=100
else
    WARN_TURNS=$(( WARN_PCT * 45 / 100 )); [ "$WARN_TURNS" -lt 5 ] && WARN_TURNS=5
    CRIT_TURNS=$(( CRIT_PCT * 45 / 100 )); [ "$CRIT_TURNS" -lt 8 ] && CRIT_TURNS=8
    if [ "$TURNS" -ge "$CRIT_TURNS" ]; then PCT_USED=$CRIT_PCT
    elif [ "$TURNS" -ge "$WARN_TURNS" ]; then PCT_USED=$WARN_PCT
    fi
fi

CONTEXT_TTL=7200  # a context notice from a session two hours gone is not worth showing
if [ "$PCT_USED" -ge "$CRIT_PCT" ] 2>/dev/null; then
    devteam_notify "critical" "context.critical" "$(_msg \
        "Context window at ≈${PCT_USED}%. Run /compact now or start a new session to keep answers reliable." \
        "Janela de contexto em ≈${PCT_USED}%. Execute /compact agora ou inicie uma nova sessão para manter a qualidade das respostas." \
        "Ventana de contexto en ≈${PCT_USED}%. Ejecuta /compact ahora o inicia una nueva sesión para mantener la calidad.")" \
        "$CONTEXT_TTL" "context.critical:${SESSION_ID}"
elif [ "$PCT_USED" -ge "$WARN_PCT" ] 2>/dev/null; then
    devteam_notify "warning" "context.warning" "$(_msg \
        "Context window approaching its limit (≈${PCT_USED}%). Consider /compact or a new session." \
        "A janela de contexto está se aproximando do limite (≈${PCT_USED}%). Considere /compact ou uma nova sessão." \
        "La ventana de contexto se acerca al límite (≈${PCT_USED}%). Considera /compact o una nueva sesión.")" \
        "$CONTEXT_TTL" "context.warning:${SESSION_ID}"
fi

# ── Uncommitted progress (once per session) ──────────────────────────────────
# Many turns, HEAD unmoved since session start, a dirty tree: the state a crash,
# /clear or a compaction loses the most from. The git calls run only once the turn
# threshold is reached.
if [ "$TURNS" -ge "$NO_COMMIT_TURNS" ] 2>/dev/null; then
    if [ -n "$SESSION_HEAD" ] && [ "$SESSION_HEAD" = "$(git rev-parse HEAD 2>/dev/null)" ] \
        && [ -n "$(git status --porcelain 2>/dev/null | head -1)" ]; then
        devteam_notify "info" "session.uncommitted" "$(_msg \
            "${TURNS} turns of work this session and no commit yet. Consider committing so the progress is not lost." \
            "${TURNS} turnos de trabalho nesta sessão e nenhum commit. Considere commitar para não perder o progresso." \
            "${TURNS} turnos de trabajo en esta sesión y ningún commit. Considera hacer commit para no perder el progreso.")" \
            "$CONTEXT_TTL" "session.uncommitted:${SESSION_ID}"
    fi
fi

# ── Tip of the day ────────────────────────────────────────────────────────────
if [ -n "$TODAY" ] && ! devteam_notify_suppressed "info"; then
    TIP_INDEX=$(( (${DAY:-1} - 1) % 15 ))
    case "$USER_LANG" in
        pt-BR|pt*) TIP_FILE="$TIPS_DIR/tips.pt-BR.txt" ;;
        es*)       TIP_FILE="$TIPS_DIR/tips.es.txt" ;;
        *)         TIP_FILE="$TIPS_DIR/tips.en.txt" ;;
    esac
    [ -f "$TIP_FILE" ] || TIP_FILE="$TIPS_DIR/tips.en.txt"
    # Dedupe before reading the file: after the first Stop of the day this is a
    # single grep and the tip file is never opened.
    if ! grep -qF "\"dedupe_key\":\"tip:${TODAY}\"" "$DEVTEAM_NOTIFY_FILE" 2>/dev/null; then
        TIP=$(sed -n "$((TIP_INDEX + 1))p" "$TIP_FILE" 2>/dev/null || true)
        [ -n "$TIP" ] && devteam_notify "info" "tip.daily" "$(_msg "Tip: " "Dica: " "Consejo: ")${TIP}" 86400 "tip:${TODAY}"
    fi
fi

exit 0
