#!/usr/bin/env bash
# Stop sub-script: hard-enforce docs/development/reuse-guidelines.csv against
# the session's diff. Degrades silently when the registry does not exist —
# see skills/shared/reuse-guidelines/SKILL.md.
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
REGISTRY="$REPO_ROOT/docs/development/reuse-guidelines.csv"
[ -f "$REGISTRY" ] || exit 0

# No path gate here by design: any touched file can violate a registered
# reuse rule, so this runs whenever the dispatcher reports session changes.
SCRIPT="$REPO_ROOT/.dev-team-agents/scripts/reuse-lint.sh"
[ -f "$SCRIPT" ] || SCRIPT="$REPO_ROOT/scripts/reuse-lint.sh"
[ -f "$SCRIPT" ] || exit 0

bash "$SCRIPT" --quiet
