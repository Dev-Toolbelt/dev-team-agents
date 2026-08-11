#!/usr/bin/env bash
# SessionStart hook — surfaces language preference and warns when key project
# files are stale or user preferences are missing.

# Prevent WSL from loading /etc/bash.bashrc (and its start-systemd-namespace
# call) for every bash sub-process spawned by this script.
unset BASH_ENV ENV

set -uo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
# user-data/ is shared state that lives only in the main worktree (it is
# gitignored, so a linked worktree never has its own copy). Resolve it via
# --git-common-dir so a session started inside .worktrees/<name>/ still reads
# the same preferences.json / session-summary.md as the main checkout.
MAIN_REPO_ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
[ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$PROJECT_ROOT"
USER_DATA_DIR="${MAIN_REPO_ROOT}/.dev-team-agents/user-data"
DOCS_DIR="${PROJECT_ROOT}/docs"
PREFS_FILE="${USER_DATA_DIR}/preferences.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFS_DEFAULTS_FILE="${SCRIPT_DIR}/../lib/preferences-defaults.json"

# ── Consolidated state (state.json) ────────────────────────────────
# Dir must exist before state_migrate_legacy can look for legacy dotfiles
# to import, and before any state_set call can write state.json.
mkdir -p "$USER_DATA_DIR" 2>/dev/null || true
# shellcheck source=scripts/lib/state.sh
. "${SCRIPT_DIR}/../lib/state.sh"
STATE_FILE="${USER_DATA_DIR}/state.json"
[ -d "$USER_DATA_DIR" ] && state_migrate_legacy "$USER_DATA_DIR"

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
    # Single fork reading all three keys at once (was 3 separate python3
    # subprocess calls) — same defaults, same fallback-to-default on
    # malformed/missing file.
    _ALL_PREFS=$(python3 -c "
import json
try:
    d = json.load(open('$PREFS_FILE'))
except Exception:
    d = {}
def s(v):
    return str(v).lower() if isinstance(v, bool) else str(v)
print('\x1f'.join([s(d.get('docs_stale_after_days', 30)), s(d.get('language', 'en')), s(d.get('suppress_notifications', False)), s(d.get('auto_update', False)), s(d.get('worktree_active', False))]))
" 2>/dev/null || true)
    if [ -n "$_ALL_PREFS" ]; then
        IFS=$'\x1f' read -r STALE_DAYS USER_LANG SUPPRESS AUTO_UPDATE WORKTREE_ACTIVE <<< "$_ALL_PREFS"
    fi
fi
AUTO_UPDATE="${AUTO_UPDATE:-false}"
WORKTREE_ACTIVE="${WORKTREE_ACTIVE:-false}"

# ── Write session ID for the notifier turn counter ────────────────
state_set session_id "$(date +%s)" "$STATE_FILE"

# ── Record the commit HEAD was at when this session started ───────
# stop/_disabled-04-notifier.sh compares the current HEAD against this to
# detect a session with real turn count but zero commits — see that script.
_session_head_sha="$(git rev-parse HEAD 2>/dev/null || true)"
[ -n "$_session_head_sha" ] && state_set session_head "$_session_head_sha" "$STATE_FILE"

# ── Update check (moved from pre-tool-use/01-check-updates.sh) ────
# Runs once per session instead of on every tool call. TTL-gated internally —
# most sessions land inside the interval window and this is a no-op fork-free
# check (see uc_ttl_fresh in update-check.sh). Errors degrade to a silent skip;
# a SessionStart hook must never block the session.
UC_LIB_FILE="${SCRIPT_DIR}/lib/update-check.sh"
if [ -f "$UC_LIB_FILE" ]; then
    # shellcheck source=scripts/hooks/lib/update-check.sh
    . "$UC_LIB_FILE"

    UC_INSTALL_DIR="${MAIN_REPO_ROOT}/.dev-team-agents"
    # last_update_check / installed_version / update_check_interval now live
    # as keys in state.json (STATE_FILE) instead of standalone dotfiles.
    UC_ETAG_FILE="${USER_DATA_DIR}/.last-releases-etag"
    UC_VERSION_CACHE_FILE="${USER_DATA_DIR}/.last-releases-version"
    UC_GITHUB_API="https://api.github.com/repos/Dev-Toolbelt/dev-team-agents"

    UC_NOW=$(uc_now_epoch)
    UC_INTERVAL_HOURS=$(uc_interval_hours "$PREFS_FILE" "$STATE_FILE")
    if ! uc_ttl_fresh "$STATE_FILE" "$UC_INTERVAL_HOURS" "$UC_NOW"; then
        if uc_setup_http; then
            state_set last_update_check "$UC_NOW" "$STATE_FILE"
            UC_LATEST=$(uc_fetch_latest "$UC_GITHUB_API" "$UC_ETAG_FILE" "$UC_VERSION_CACHE_FILE")
            UC_CURRENT=$(state_get installed_version "$STATE_FILE")
            [ -n "$UC_CURRENT" ] || UC_CURRENT="unknown"
            if [ -n "$UC_LATEST" ] && [ "$UC_LATEST" != "unknown" ] \
                && [ "$UC_CURRENT" != "unknown" ] && [ "$UC_CURRENT" != "$UC_LATEST" ]; then
                export UC_SUPPRESS="$SUPPRESS"
                if uc_auto_update_enabled "$PREFS_FILE" "$USER_DATA_DIR"; then
                    if uc_perform_auto_update "$UC_CURRENT" "$UC_LATEST" "$UC_INSTALL_DIR"; then
                        uc_notify "info" "$(uc_message updated "$USER_LANG" "$UC_CURRENT" "$UC_LATEST")"
                    else
                        uc_notify "warning" "$(uc_message available "$USER_LANG" "$UC_CURRENT" "$UC_LATEST")"
                    fi
                else
                    uc_notify "warning" "$(uc_message available "$USER_LANG" "$UC_CURRENT" "$UC_LATEST")"
                fi
            fi
        fi
    fi
fi

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

# ── Scoped test execution reminder (always shown, every session) ──
# skills/shared/scoped-test-execution/SKILL.md is normally loaded via
# project-context's mandatory load inside /devteam:* agent routing. A
# session working outside that routing (plain main-loop work) never
# triggers that load, so the rule below is injected unconditionally here
# as the structural fix for that gap. pre-tool-use/02b-full-suite-guard.sh
# is the complementary per-command safety net.
echo ""
echo "[DEVTEAM:TEST_SCOPE_RULE] Run only tests covering touched code; full suite only on explicit user request this session (see skills/shared/scoped-test-execution/SKILL.md)."
echo ""

# ── Session banner (always shown, once per session) ───────────────
# Fallback chain for version: an installed project has installed_version in
# state.json; this repo's own self-hosted install does not, so fall back to
# the first released entry in CHANGELOG.md (the [Unreleased] header is skipped).
DT_VERSION="$(state_get installed_version "$STATE_FILE")"
if [ -z "$DT_VERSION" ]; then
    DT_VERSION="$(grep -m1 -oE '^## \[[0-9]+\.[0-9]+\.[0-9]+\]' "${PROJECT_ROOT}/CHANGELOG.md" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
fi
[ -n "$DT_VERSION" ] || DT_VERSION="unknown"
case "$DT_VERSION" in v*) ;; *) DT_VERSION="v${DT_VERSION}" ;; esac

DT_AUTO_UPDATE_LABEL="No"
[ "$AUTO_UPDATE" = "true" ] && DT_AUTO_UPDATE_LABEL="Yes"
DT_WORKTREE_LABEL="No"
[ "$WORKTREE_ACTIVE" = "true" ] && DT_WORKTREE_LABEL="Yes"

echo "[DEVTEAM:SESSION_BANNER]"
echo "DevTeam Agents • ${DT_VERSION} (github.com/Dev-Toolbelt/dev-team-agents)"
echo "─────────────────────────────────────────────────"
echo "Language: ${USER_LANG} | Auto Update: ${DT_AUTO_UPDATE_LABEL} | Worktree: ${DT_WORKTREE_LABEL}"
echo ""

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

# ── Check: health check staleness ─────────────────────────────────
LAST_HEALTH_CHECK="$(state_get last_health_check "$STATE_FILE")"
if [ -n "$LAST_HEALTH_CHECK" ]; then
    HC_DATE=$(printf '%s' "$LAST_HEALTH_CHECK" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1)
    if [ -n "$HC_DATE" ]; then
        DAYS_SINCE_HC=$(_days_since_date_str "$HC_DATE")
        if [ "$DAYS_SINCE_HC" -gt "$STALE_DAYS" ]; then
            WARN=1
            MESSAGES+=("⚠️  Last /devteam:health-check was ${DAYS_SINCE_HC} days ago — run it to catch drift (broken symlinks, stale config, missing scripts).")
        fi
    fi
else
    # No marker at all: either never run, or an install that predates this
    # check. Only nag once things are otherwise in motion (a project.md or
    # session-summary.md already exists) — a brand-new install already gets
    # a setup flow and doesn't need a second, redundant prompt.
    if [ -f "$PROJECT_MD" ] || [ -f "$SESSION_SUMMARY" ]; then
        WARN=1
        MESSAGES+=("⚠️  No /devteam:health-check has been recorded for this project — run it once to verify the installation.")
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
