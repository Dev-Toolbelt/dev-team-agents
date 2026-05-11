#!/usr/bin/env bash
# Gate: only run if agents/ were touched in this session
TOUCHED=$(git status --porcelain agents/ 2>/dev/null | head -1)
TODAY_COMMITS=$(git log --since="$(date +%Y-%m-%d) 00:00:00" --oneline -- agents/ 2>/dev/null | head -1)

if [ -z "$TOUCHED" ] && [ -z "$TODAY_COMMITS" ]; then
    exit 0
fi

exec "$(dirname "${BASH_SOURCE[0]}")/../../agent-lint.sh" --quiet "$@"
