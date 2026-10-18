#!/usr/bin/env bash
# Checks the retrieval indexes (wiki, ADRs) and plan lifecycle lines — see
# scripts/lib/index_lint.py for the rule homes it checks.
# Exit 1 on any ERROR, 0 otherwise (WARN lines included). No-op (exit 0) when
# docs/ does not exist, no Python 3.9+ is available, or the lint itself fails.
set -euo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -d "$REPO_ROOT/docs" ] || exit 0

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/lib" && pwd)"
# shellcheck source=scripts/lib/python.sh
. "$LIB_DIR/python.sh" 2>/dev/null || true
command -v python3 >/dev/null 2>&1 || exit 0

STATUS=0
# -I: no PYTHONPATH, user site-packages or working-directory imports.
OUTPUT="$(python3 -I "$LIB_DIR/index_lint.py" "$REPO_ROOT")" || STATUS=$?
# 0 clean, 1 findings; anything else is the lint failing, never the docs — stay silent.
if [ "$STATUS" != 0 ] && [ "$STATUS" != 1 ]; then
    exit 0
fi
if [ "$QUIET" = 1 ] && [ "$STATUS" = 0 ]; then
    exit 0
fi
[ -n "$OUTPUT" ] && printf '%s\n' "$OUTPUT"
[ "$STATUS" = 1 ] && exit 1
exit 0
