#!/usr/bin/env bash
# 02-readme-sync.sh — Verify EN/pt-BR doc pairs have matching section counts
# and roughly equal line counts (50% threshold). Exits non-zero on mismatch.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

check_pair() {
  local en="$1" ptbr="$2"
  local fail=0

  en_count=$(grep -c "^## " "$en" 2>/dev/null || echo 0)
  ptbr_count=$(grep -c "^## " "$ptbr" 2>/dev/null || echo 0)
  if [ "$en_count" != "$ptbr_count" ]; then
    echo "Section mismatch: $en ↔ $ptbr ($en_count vs $ptbr_count sections)"
    fail=1
  fi

  EN_LINES=$(wc -l < "$en")
  PTBR_LINES=$(wc -l < "$ptbr")
  DIFF=$(( EN_LINES - PTBR_LINES ))
  DIFF=${DIFF#-}
  THRESHOLD=$(( EN_LINES / 2 + 1 ))
  if [ "$DIFF" -gt "$THRESHOLD" ]; then
    echo "$en and $ptbr differ by $DIFF lines (>50%). Check for missing content."
    fail=1
  fi

  [ "$fail" -eq 0 ] && echo "Sync OK: $en ↔ $ptbr"
  return $fail
}

FAIL=0
check_pair README.md README.pt-BR.md || FAIL=1
check_pair docs/agents.md docs/agents.pt-BR.md || FAIL=1
check_pair docs/installation.md docs/installation.pt-BR.md || FAIL=1
exit $FAIL