#!/usr/bin/env bash
# Stop sub-script: informational nudge toward design tokens for hardcoded px
# values added to style code this session. Never blocks — see
# scripts/design-token-lint.sh.
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

git rev-parse --show-toplevel >/dev/null 2>&1 || exit 0

# Only the lint shipped beside this hook — never a project's own
# `scripts/design-token-lint.sh` (lib/shipped-lint.sh).
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)"
# shellcheck source=scripts/hooks/lib/shipped-lint.sh
. "$LIB_DIR/shipped-lint.sh" 2>/dev/null || exit 0
SCRIPT="$(devteam_shipped_lint design-token-lint.sh)"
[ -n "$SCRIPT" ] || exit 0

# Never --quiet here: this script only ever exits 0, so quiet output would
# make the check invisible. Only prints when it actually found something.
bash "$SCRIPT"
