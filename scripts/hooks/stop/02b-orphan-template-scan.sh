#!/usr/bin/env bash
# Stop sub-script: detect orphan templates and unresolvable template references.
# Gate: only run when a path that can change template orphan-hood was touched —
# templates/ itself, or one of the consumer trees the scan reads
# (agents skills commands scripts | CLAUDE.md CLAUDE-md/ helpers/).
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0
[ -f "$LIB_DIR/touched-paths.sh" ] || exit 0
# shellcheck source=scripts/hooks/lib/touched-paths.sh
. "$LIB_DIR/touched-paths.sh"

# Consumes DEVTEAM_TOUCHED_PATHS computed once by the dispatcher; recomputes it
# only when this script is run standalone.
devteam_touched_matches '^(templates|agents|skills|commands|scripts|CLAUDE-md|helpers)/|^CLAUDE\.md$' || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
# helpers/ is dev-only — stripped from the installed package — so this is a
# silent no-op in user projects.
SCRIPT="$REPO_ROOT/helpers/orphan-template-scan.sh"
[ -f "$SCRIPT" ] || exit 0

bash "$SCRIPT" --quiet
