#!/usr/bin/env bash
# Stop sub-script: detect orphan templates.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
SCRIPT="$REPO_ROOT/helpers/orphan-template-scan.sh"

[ -f "$SCRIPT" ] || exit 0

bash "$SCRIPT" --quiet
