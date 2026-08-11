#!/usr/bin/env bash
# Stop sub-script: warns (non-blocking) when the session touched a
# hard-to-reverse signal (new dependency, schema migration, new provider
# config) but added no new ADR file — see CLAUDE.md § ADR Trigger Rule.
# Heuristic only: false positives are expected and this never blocks Stop.
set -euo pipefail

[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

LIB_DIR="$(dirname "${BASH_SOURCE[0]}")/../lib"
if [ "${DEVTEAM_TOUCHED_COMPUTED:-0}" != "1" ]; then
    # shellcheck source=scripts/hooks/lib/touched-paths.sh
    . "$LIB_DIR/touched-paths.sh"
    DEVTEAM_TOUCHED_PATHS="$(devteam_compute_touched_paths || true)"
fi
[ -n "${DEVTEAM_TOUCHED_PATHS:-}" ] || exit 0

# A new ADR was already added this session — signal handled, nothing to warn.
if printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE 'docs/development/adrs/adr-[0-9]+.*\.md$'; then
    exit 0
fi

# Dependency-manifest changes: a new package/module name added, not a mere
# version bump. Restricted to added lines in the diff for today's changes.
DEP_MANIFESTS='(^|/)(package\.json|composer\.json|requirements\.txt|go\.mod|Cargo\.toml|Gemfile)$'
NEW_DEP=0
if printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE "$DEP_MANIFESTS"; then
    while IFS= read -r manifest; do
        [ -f "$REPO_ROOT/$manifest" ] || continue
        if git -C "$REPO_ROOT" diff --unified=0 -- "$manifest" 2>/dev/null | grep -qE '^\+[^+]'; then
            NEW_DEP=1
            break
        fi
    done < <(printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -E "$DEP_MANIFESTS")
fi

NEW_MIGRATION=0
printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE '(^|/)(migrations?|db/migrate)/.*\.(sql|rb|py|ts|js)$' && NEW_MIGRATION=1

NEW_PROVIDER_CONFIG=0
printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE '(^|/)(providers?|integrations?)/[^/]+/(config|client)\.[a-z]+$' && NEW_PROVIDER_CONFIG=1

if [ "$NEW_DEP" = 1 ] || [ "$NEW_MIGRATION" = 1 ] || [ "$NEW_PROVIDER_CONFIG" = 1 ]; then
    cat >&2 <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 POSSIBLE ADR GAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 This session touched a signal that often warrants an ADR
 (new dependency, schema migration, or provider config)
 but added no new file under docs/development/adrs/.

 This is a heuristic, not a rule — false positives are
 expected. If this decision is hard to reverse, affects
 multiple components, or has non-obvious reasoning, run:

   bash .dev-team-agents/scripts/new-adr.sh "title of the decision"

 See CLAUDE.md § ADR Trigger Rule.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
    exit 2
fi

exit 0
