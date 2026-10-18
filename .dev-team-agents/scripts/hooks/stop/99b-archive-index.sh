#!/usr/bin/env bash
# Stop sub-script: rotate fingerprint sections older than 90 days out of
# docs/reports/_index.md into quarterly archives (helpers/archive-index.sh).
#
# Tier 99- (final/cleanup), letter-suffixed because 99-graphify-refresh.sh
# already holds the number. This is not a check: it MUTATES repository files, so
# it belongs in the cleanup tier and must run after every sub-script that reads
# the bank — in particular 03b-fingerprint-uniqueness.sh, which would otherwise
# be validating a file that is rewritten underneath it in the same Stop.
#
# The rotation is time-based, not change-based, so the gate is a once-per-day
# stamp rather than a touched-path match.
set -euo pipefail

QUIET=false
[ "${1:-}" = "--quiet" ] && QUIET=true

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
# helpers/ is dev-only — stripped from the installed package — so this is a
# silent no-op in user projects.
SCRIPT="$REPO_ROOT/helpers/archive-index.sh"
[ -f "$SCRIPT" ] || exit 0
[ -f "$REPO_ROOT/docs/reports/_index.md" ] || exit 0

# ── Once-per-day gate ─────────────────────────────────────────────────────────
# The stamp is a machine-local marker (ADR-0013): resolve it through the
# state-dir pointer, read from the MAIN checkout (not this worktree's own
# --show-toplevel) since that pointer, like user-data/ before it, lives only
# there.
MAIN_REPO_ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
[ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$REPO_ROOT"
# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "$(dirname "${BASH_SOURCE[0]}")/../lib/data-dirs.sh"
STAMP_DIR="$(devteam_state_dir "$MAIN_REPO_ROOT")"
STAMP_FILE="$STAMP_DIR/.last-archive-index"
TODAY="$(date +%Y-%m-%d)"
if [ -f "$STAMP_FILE" ]; then
    LAST=""
    read -r LAST < "$STAMP_FILE" 2>/dev/null || LAST=""
    [ "$LAST" = "$TODAY" ] && exit 0
fi

# ── Run ───────────────────────────────────────────────────────────────────────
# archive-index.sh has no --quiet flag and always prints at least one line, so
# --quiet is handled here rather than by editing the helper. The helper exits 0
# on every non-fatal path; failures degrade to a skip.
OUTPUT="$(bash "$SCRIPT" 2>&1)" || OUTPUT=""

mkdir -p "$STAMP_DIR" 2>/dev/null || true
printf '%s\n' "$TODAY" > "$STAMP_FILE" 2>/dev/null || true

[ "$QUIET" = true ] && exit 0
[ -n "$OUTPUT" ] || exit 0

# Silent on the no-op path (nothing was older than the 90-day cutoff); report
# only when the index was actually rotated.
if printf '%s\n' "$OUTPUT" | grep -q 'No entries older than'; then
    exit 0
fi

printf '%s\n' "$OUTPUT"
exit 0
