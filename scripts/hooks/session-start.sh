#!/usr/bin/env bash
# SessionStart hook — surfaces language preference and warns when key project
# files are stale or user preferences are missing.

# Prevent WSL from loading /etc/bash.bashrc (and its start-systemd-namespace
# call) for every bash sub-process spawned by this script.
unset BASH_ENV ENV

set -uo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
USER_DATA_DIR="${PROJECT_ROOT}/.dev-team-agents/user-data"
DOCS_DIR="${PROJECT_ROOT}/docs"
PREFS_FILE="${USER_DATA_DIR}/preferences.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFS_DEFAULTS_FILE="${SCRIPT_DIR}/../lib/preferences-defaults.json"

# ── Health-check backfill ─────────────────────────────────────────
# Ensure preferences.json has every key from the canonical default schema.
# Missing keys are written with their defaults; existing user values are never
# overwritten. No-op (no write) when the file is already complete. This
# self-heals installs that predate a newly added preference key.
#
# Exception — CONSENT_KEYS. This file already exists, so its owner never saw
# the installer prompt for a field added after they installed. Backfilling the
# schema's enabled default would switch telemetry or auto-update on without
# anyone agreeing to it, so those two are backfilled as false. The user opts in
# by editing preferences.json (or re-running the installer on a fresh install).
if [ -f "$PREFS_FILE" ] && [ -f "$PREFS_DEFAULTS_FILE" ] && command -v python3 >/dev/null 2>&1; then
    python3 - "$PREFS_FILE" "$PREFS_DEFAULTS_FILE" <<'PYEOF' 2>/dev/null || true
import sys, json
prefs_file, defaults_file = sys.argv[1], sys.argv[2]
try:
    with open(defaults_file) as f:
        defaults = json.load(f)
    with open(prefs_file) as f:
        prefs = json.load(f)
except (json.JSONDecodeError, IOError):
    sys.exit(0)
CONSENT_KEYS = ("telemetry", "auto_update")
missing = {k: v for k, v in defaults.items() if k not in prefs}
for k in CONSENT_KEYS:
    if k in missing:
        missing[k] = False
if missing:
    prefs.update(missing)
    with open(prefs_file, 'w') as f:
        json.dump(prefs, f, indent=2)
        f.write('\n')
    print("[DEVTEAM:PREFS_BACKFILL] added: " + ", ".join(sorted(missing)))
PYEOF
fi

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

# ── Check: broken (materialized) dev-team-agents symlinks ─────────
# On Windows without Developer Mode / core.symlinks=true, git/MSYS writes
# the .claude/ links as plain text files. git-bash's `ls -la` still shows
# them as lrwxrwxrwx (MSYS emulation), but Claude Code sees files — so the
# whole dev-team silently disappears. A link is "materialized" when it
# exists, is NOT a symlink, and is NOT a directory.
_is_materialized() { [ -e "$1" ] && [ ! -L "$1" ] && [ ! -d "$1" ]; }

BROKEN_LINKS=0
_is_materialized "${PROJECT_ROOT}/.claude/agents/dev-team"   && BROKEN_LINKS=$((BROKEN_LINKS + 1))
_is_materialized "${PROJECT_ROOT}/.claude/commands/devteam"  && BROKEN_LINKS=$((BROKEN_LINKS + 1))
if [ -d "${PROJECT_ROOT}/.claude/skills" ]; then
    for _sp in "${PROJECT_ROOT}/.claude/skills"/*; do
        [ -e "$_sp" ] || continue
        _is_materialized "$_sp" && BROKEN_LINKS=$((BROKEN_LINKS + 1))
    done
fi

if [ "$BROKEN_LINKS" -gt 0 ]; then
    echo ""
    echo "[DEVTEAM:SYMLINK_BROKEN] ${BROKEN_LINKS} link(s)"
    echo "dev-team-agents links were materialized as plain files instead of symlinks"
    echo "(the Windows 'no native symlink support' condition). The dev-team is not"
    echo "loaded — /devteam:* commands, agents, and skills are invisible to Claude Code."
    echo "Fix it now by running:"
    echo "  bash .dev-team-agents/scripts/fix-symlinks.sh"
    echo "It auto-repairs when the OS allows, and otherwise prints the 3 remediation"
    echo "options to offer the user interactively. Restart Claude Code after a fix."
    echo ""
fi

# ── Check: project.md freshness ───────────────────────────────────
PROJECT_MD="${DOCS_DIR}/project.md"
if [ -f "$PROJECT_MD" ]; then
    DAYS_OLD=$(_days_since_modified "$PROJECT_MD")
    if [ "$DAYS_OLD" -gt "$STALE_DAYS" ]; then
        WARN=1
        MESSAGES+=("⚠️  docs/project.md is ${DAYS_OLD} days old — consider running /devteam:architect to refresh.")
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
