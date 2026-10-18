#!/usr/bin/env bash
# Stop sub-script: detect duplicate fingerprint slugs across the report bank
# (docs/reports/_index.md plus every _index-archive-*.md).
#
# Tier 03- (static validation), letter-suffixed because 03-agent-lint.sh already
# holds the number: this is the same class of check — a pure read-only
# validation of committed content, with no repository-integrity or notification
# semantics. It gives the same-session feedback that the CI gate
# (.github/scripts/ci/01-lint.sh) can only give after a push.
#
# Gate: only run when docs/reports/ was touched in this session.
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" 2>/dev/null && pwd)" || exit 0
[ -f "$LIB_DIR/touched-paths.sh" ] || exit 0
# shellcheck source=scripts/hooks/lib/touched-paths.sh
. "$LIB_DIR/touched-paths.sh"

# Consumes DEVTEAM_TOUCHED_PATHS computed once by the dispatcher; recomputes it
# only when this script is run standalone.
devteam_touched_matches '^docs/reports/' || exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
# helpers/ is dev-only — stripped from the installed package — so this is a
# silent no-op in user projects.
SCRIPT="$REPO_ROOT/helpers/check-fingerprint-uniqueness.sh"
[ -f "$SCRIPT" ] || exit 0

# The helper has no --quiet flag: it prints a one-line success summary on stdout
# and the duplicate report on stderr. Capture both and stay silent when clean.
OUTPUT=""
if ! OUTPUT="$(bash "$SCRIPT" 2>&1)"; then
    printf '%s\n' "$OUTPUT" >&2
    cat >&2 <<'EOF'

Duplicate fingerprint slugs break the report bank's uniqueness guarantee.
Rename the newly added slug in docs/reports/_index.md before committing.
EOF
    # Exit 2 so the message is fed back to Claude in the same session, matching
    # stop/01-session-summary.sh — the whole point of this check is same-session
    # feedback instead of a red build after push.
    exit 2
fi

exit 0
