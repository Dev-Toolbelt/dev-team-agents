#!/usr/bin/env bash
# Stop sub-script: detect skills that no agent references.
# Gate: only run if agents/ or skills/ were touched in this session.
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0
[ -f "$LIB_DIR/touched-paths.sh" ] || exit 0
# shellcheck source=scripts/hooks/lib/touched-paths.sh
. "$LIB_DIR/touched-paths.sh"

# Consumes DEVTEAM_TOUCHED_PATHS computed once by the dispatcher; recomputes it
# only when this script is run standalone.
devteam_touched_matches '^(agents|skills)/' || exit 0

# helpers/ is dev-only — stripped from the installed package — so this is a
# silent no-op in user projects.
SCRIPT="$(dirname "${BASH_SOURCE[0]}")/../../../helpers/orphan-skill-scan.sh"
[ -f "$SCRIPT" ] || exit 0
exec bash "$SCRIPT" --quiet "$@"
