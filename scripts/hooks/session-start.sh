#!/usr/bin/env bash
# SessionStart hook — warns when key project files are stale (>30 days without update)
set -uo pipefail

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
USER_DATA_DIR="${PROJECT_ROOT}/.claude/user-data"
DOCS_DIR="${PROJECT_ROOT}/.claude/docs"

WARN=0
MESSAGES=()

# Check project.md freshness (>30 days without modification)
PROJECT_MD="${DOCS_DIR}/project.md"
if [ -f "$PROJECT_MD" ]; then
    DAYS_OLD=$(( ( $(date +%s) - $(stat -f %m "$PROJECT_MD" 2>/dev/null || stat -c %Y "$PROJECT_MD" 2>/dev/null || echo 0) ) / 86400 ))
    if [ "$DAYS_OLD" -gt 30 ]; then
        WARN=1
        MESSAGES+=("WARNING: .claude/docs/project.md is ${DAYS_OLD} days old — consider running /devteam:architect to refresh.")
    fi
fi

# Check session-summary.md: warn if last entry is >30 days old
SESSION_SUMMARY="${USER_DATA_DIR}/session-summary.md"
if [ -f "$SESSION_SUMMARY" ]; then
    LAST_DATE=$(grep -m1 "^## [0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" "$SESSION_SUMMARY" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2}" | head -1)
    if [ -n "$LAST_DATE" ]; then
        LAST_TS=$(date -d "$LAST_DATE" +%s 2>/dev/null || date -j -f "%Y-%m-%d" "$LAST_DATE" +%s 2>/dev/null || echo 0)
        DAYS_SINCE=$(( ( $(date +%s) - LAST_TS ) / 86400 ))
        if [ "$DAYS_SINCE" -gt 30 ]; then
            WARN=1
            MESSAGES+=("WARNING: session-summary.md last entry is ${DAYS_SINCE} days old — this project may be inactive or the summary needs updating.")
        fi
    fi
fi

if [ "$WARN" -eq 1 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo " PROJECT CONTEXT NOTICE"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for MSG in "${MESSAGES[@]}"; do
        echo " $MSG"
    done
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

exit 0
