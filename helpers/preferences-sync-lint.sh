#!/usr/bin/env bash
# Usage: bash helpers/preferences-sync-lint.sh [--quiet]
#
# scripts/lib/preferences-defaults.json is the single source of truth for the
# preferences.json schema. Its keys are mirrored (documented, not read) in:
#   - CLAUDE-md/preferences.md
#   - skills/shared/user-preferences/SKILL.md
# Nothing enforces that a key added to the canonical file also lands in both
# docs, so this checks that every canonical key appears (as a backtick-quoted
# field, e.g. `worktree_active`) in both mirrors.
#
# Exits 0 if all keys are present in both mirrors, 1 otherwise.
#
# Flags:
#   --quiet   suppress success output when clean

set -euo pipefail

QUIET=false
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=true ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULTS_JSON="$REPO_ROOT/scripts/lib/preferences-defaults.json"
MIRRORS=(
  "CLAUDE-md/preferences.md"
  "skills/shared/user-preferences/SKILL.md"
)

if [ ! -f "$DEFAULTS_JSON" ]; then
  echo "preferences-sync-lint: scripts/lib/preferences-defaults.json not found — skipping" >&2
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "preferences-sync-lint: python3 not available — skipping" >&2
  exit 0
fi

KEYS=$(python3 -c '
import json, sys
with open(sys.argv[1]) as fh:
    for key in json.load(fh):
        print(key)
' "$DEFAULTS_JSON")

ERRORS=()

for mirror in "${MIRRORS[@]}"; do
  mirror_path="$REPO_ROOT/$mirror"
  if [ ! -f "$mirror_path" ]; then
    ERRORS+=("  · ${mirror}: file not found")
    continue
  fi
  while IFS= read -r key; do
    [ -z "$key" ] && continue
    grep -qE "\`${key}\`" "$mirror_path" || \
      ERRORS+=("  · ${mirror}: missing documented key \`${key}\` (present in scripts/lib/preferences-defaults.json)")
  done <<< "$KEYS"
done

SEPARATOR="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "$SEPARATOR"
  echo " PREFERENCES SYNC LINT"
  echo "$SEPARATOR"
  echo ""
  echo " ERRORS — canonical schema drifted from its documentation mirrors:"
  for err in "${ERRORS[@]}"; do
    echo "$err"
  done
  echo ""
  echo "$SEPARATOR"
  exit 1
fi

if [ "$QUIET" = false ]; then
  echo "preferences-sync-lint: clean ✓ (${#MIRRORS[@]} mirrors checked)"
fi
