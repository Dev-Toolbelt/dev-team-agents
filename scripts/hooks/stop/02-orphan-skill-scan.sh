#!/usr/bin/env bash
# Gate: only run if agents/ or skills/ were touched in this session.
# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

TOUCHED=$(git status --porcelain agents/ skills/ 2>/dev/null | head -1)
TODAY_COMMITS=$(git log --since="$(date +%Y-%m-%d) 00:00:00" --oneline -- agents/ skills/ 2>/dev/null | head -1)

if [ -z "$TOUCHED" ] && [ -z "$TODAY_COMMITS" ]; then
    exit 0
fi

SCRIPT="$(dirname "${BASH_SOURCE[0]}")/../../../helpers/orphan-skill-scan.sh"
[ -f "$SCRIPT" ] || exit 0
exec "$SCRIPT" --quiet "$@"
