#!/usr/bin/env bash
# SessionStart hook — surfaces language preference and warns when key project
# files are stale or user preferences are missing.
set -uo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
USER_DATA_DIR="${PROJECT_ROOT}/.claude/user-data"
DOCS_DIR="${PROJECT_ROOT}/.claude/docs"
PREFS_FILE="${USER_DATA_DIR}/preferences.json"

# ── Read preferences ──────────────────────────────────────────────
STALE_DAYS=30
USER_LANG="en"
SUPPRESS="false"

if [ -f "$PREFS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    _read_pref() {
        python3 -c \
            "import json,sys; d=json.load(open('$PREFS_FILE')); v=d.get('$1',$2); print(str(v).lower() if isinstance(v,bool) else v)" \
            2>/dev/null || echo "$2"
    }
    STALE_DAYS=$(_read_pref docs_stale_after_days 30)
    USER_LANG=$(_read_pref language en)
    SUPPRESS=$(_read_pref suppress_notifications false)
fi

# ── Write session ID for the notifier turn counter ────────────────
mkdir -p "$USER_DATA_DIR"
date +%s > "${USER_DATA_DIR}/.session-id"

# ── Helper: check if a type is suppressed ─────────────────────────
_is_suppressed() {
    local type="$1"
    case "$SUPPRESS" in
        true)  return 0 ;;
        false) return 1 ;;
        *"$type"*) return 0 ;;
        *) return 1 ;;
    esac
}

# ── Helper: emit a DEV TEAM AGENTS notification ───────────────────
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

# ── Check: preferences.json ───────────────────────────────────────
if [ ! -f "$PREFS_FILE" ]; then
    echo ""
    echo "[DEVTEAM:FIRST_TIME_SETUP]"
    echo "preferences.json not found — this appears to be your first time using dev-team-agents on this machine."
    echo ""
fi

# ── Language banner (always shown when language is non-English) ───
if [ -f "$PREFS_FILE" ] && [ "$USER_LANG" != "en" ] && [ "$USER_LANG" != "" ]; then
    echo "→ Conversation language: $USER_LANG (from preferences.json)"
fi

# ── Cross-platform date diff helper ──────────────────────────────
_days_since_modified() {
    local file="$1"
    local file_ts
    file_ts=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null || echo 0)
    echo $(( ( $(date +%s) - file_ts ) / 86400 ))
}

_days_since_date_str() {
    local date_str="$1"
    local ts
    ts=$(date -d "$date_str" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$date_str" +%s 2>/dev/null || echo 0)
    echo $(( ( $(date +%s) - ts ) / 86400 ))
}

WARN=0
MESSAGES=()

# ── Check: project.md freshness ───────────────────────────────────
PROJECT_MD="${DOCS_DIR}/project.md"
if [ -f "$PROJECT_MD" ]; then
    DAYS_OLD=$(_days_since_modified "$PROJECT_MD")
    if [ "$DAYS_OLD" -gt "$STALE_DAYS" ]; then
        WARN=1
        MESSAGES+=("⚠️  .claude/docs/project.md is ${DAYS_OLD} days old — consider running /devteam:architect to refresh.")
    fi
fi

# ── Check: session-summary.md staleness ───────────────────────────
SESSION_SUMMARY="${USER_DATA_DIR}/session-summary.md"
if [ -f "$SESSION_SUMMARY" ]; then
    LAST_DATE=$(grep -m1 "^## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" "$SESSION_SUMMARY" \
        | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1)
    if [ -n "$LAST_DATE" ]; then
        DAYS_SINCE=$(_days_since_date_str "$LAST_DATE")
        if [ "$DAYS_SINCE" -gt "$STALE_DAYS" ]; then
            WARN=1
            MESSAGES+=("⚠️  session-summary.md last entry is ${DAYS_SINCE} days old — this project may be inactive or the summary needs updating.")
        fi
    fi
fi

# ── Emit stale-docs notification ──────────────────────────────────
if [ "$WARN" -eq 1 ] && ! _is_suppressed "warning"; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " ⚠️  DEV TEAM AGENTS  ⚠️"
    for MSG in "${MESSAGES[@]}"; do
        echo " $MSG"
    done
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

exit 0
