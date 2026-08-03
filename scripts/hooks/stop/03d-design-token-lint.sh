#!/usr/bin/env bash
# Stop sub-script: informational nudge toward design tokens for hardcoded px
# values added to style code this session. Never blocks — see
# scripts/design-token-lint.sh.
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

SCRIPT="$REPO_ROOT/.dev-team-agents/scripts/design-token-lint.sh"
[ -f "$SCRIPT" ] || SCRIPT="$REPO_ROOT/scripts/design-token-lint.sh"
[ -f "$SCRIPT" ] || exit 0

# Never --quiet here: this script only ever exits 0, so quiet output would
# make the check invisible. Only prints when it actually found something.
bash "$SCRIPT"
