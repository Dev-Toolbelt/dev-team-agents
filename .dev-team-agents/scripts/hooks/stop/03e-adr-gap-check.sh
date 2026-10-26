#!/usr/bin/env bash
# Stop sub-script: warns (non-blocking) when the session touched a
# hard-to-reverse signal (new dependency, schema migration, new provider
# config) but added no new ADR file — see CLAUDE.md § ADR Trigger Rule.
# Heuristic only: false positives are expected.
#
# Exit 2 is how a Stop sub-script reaches the agent in the same session. Claude
# Code answers a Stop exit 2 by continuing the turn, so a warning nothing in the
# turn can clear (the user decided no ADR is warranted, and the change stays
# uncommitted) fired after every reply. It now fires once per distinct set of
# signals: the signature is remembered in the machine-local state dir, and the
# same set stays quiet until the signals change.
#
# Who sees it: Claude Code and Codex surface a Stop hook's stderr; the opencode
# plugin ignores it (opencode/plugin/dev-team-agents.ts). The marker is per
# project, not per provider — no provider variable reaches the Stop environment —
# so a Stop in an opencode session records the signature without showing the
# warning, and a later Claude or Codex session on the same change stays quiet.
# Accepted: the check is a nudge, and the same signal reappears on the next
# dependency change.
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
# Both naming schemes, and the `adr-` prefix is optional: `new-adr.sh` emits
# `NNNN-slug.md`, so a pattern requiring the prefix matched no real filename and this
# escape hatch could never fire. The hook then warned about a missing ADR at the very
# session that had just added one — a false positive aimed at the person who did the
# right thing. `scripts/new-adr.sh` (see `adr_files` and the ADR_DIR resolution) owns
# the scheme list and the two directories; keep this in step with it.
# The directory comes from new-adr.sh --dir, which follows the project's docs write
# root (context_paths[0]). Only when it cannot answer are the two default locations
# under docs/ accepted — a stale docs/ ADR in a project that writes elsewhere is not one.
ADR_NAME='((adr|ADR)-)?[0-9]+[^/]*\.md$'
ADR_DIR=""
NEW_ADR="$(dirname "${BASH_SOURCE[0]}")/../../new-adr.sh"
[ -f "$NEW_ADR" ] && ADR_DIR="$(cd "$REPO_ROOT" && bash "$NEW_ADR" --dir 2>/dev/null || true)"
DOCS_ROOT_SH="$(dirname "${BASH_SOURCE[0]}")/../../lib/docs-root.sh"
# shellcheck source=scripts/lib/docs-root.sh
if [ -n "$ADR_DIR" ] && [ -f "$DOCS_ROOT_SH" ] && . "$DOCS_ROOT_SH"; then
    ADR_PATTERN="^$(devteam_regex_escape "$ADR_DIR")/$ADR_NAME"
else
    ADR_PATTERN="(^|/)docs/(development/adrs|adr)/$ADR_NAME"
fi
if printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE "$ADR_PATTERN"; then
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
    # The signature covers what triggered the warning — the signal paths and the
    # manifests' added lines against HEAD, so staging the same change does not
    # count as a new one — and a further dependency warns again while an
    # unrelated edit elsewhere does not.
    SIGNATURE="$(
        {
            printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -E "$DEP_MANIFESTS|(^|/)(migrations?|db/migrate)/|(^|/)(providers?|integrations?)/" || true
            printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -E "$DEP_MANIFESTS" | while IFS= read -r manifest; do
                git -C "$REPO_ROOT" diff HEAD --unified=0 -- "$manifest" 2>/dev/null | grep -E '^\+[^+]' || true
            done
        } | git hash-object --stdin 2>/dev/null || true
    )"
    # shellcheck source=scripts/hooks/lib/warn-once.sh
    . "$LIB_DIR/warn-once.sh"
    devteam_warn_once .adr-gap-warned "$SIGNATURE" || exit 0
    cat >&2 <<EOF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 POSSIBLE ADR GAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 This session touched a signal that often warrants an ADR
 (new dependency, schema migration, or provider config)
 but added no new ADR file (in the directory `new-adr.sh --dir` prints).

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
