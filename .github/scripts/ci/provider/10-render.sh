#!/usr/bin/env bash
# 10-render.sh — Render a provider's output tree into a staging directory.
# Usage: bash 10-render.sh <provider> <repo-root> <staging-dir>
set -euo pipefail

PROVIDER="$1"
SOURCE="$2"
STAGING="$3"

mkdir -p "$STAGING"
rm -rf "${STAGING:?}/.${PROVIDER}" "${STAGING:?}/.claude" 2>/dev/null || true

bash "$SOURCE/scripts/render-provider.sh" \
  --provider "$PROVIDER" \
  --source-dir "$SOURCE" \
  --target-dir "$STAGING"

echo "rendered '$PROVIDER' into $STAGING:"
find "$STAGING" -type f | sort | tail -5
echo "total: $(find "$STAGING" -type f | wc -l | tr -d ' ') files"