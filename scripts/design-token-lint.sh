#!/usr/bin/env bash
# Reports hardcoded px magic numbers added in style code, as a nudge toward
# design tokens / CSS variables. Informational only — never blocks: breakpoints,
# z-index, and one-off values are legitimate too often to hard-fail on a regex.
# See skills/shared/reuse-guidelines/SKILL.md (design-rule rows cover the same
# ground for review-time, project-specific patterns; this is the generic,
# always-on nudge that needs no registry).
set -euo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

DIFF_RANGE="${DESIGN_TOKEN_LINT_DIFF_RANGE:-}"
if [ -z "$DIFF_RANGE" ]; then
  BASE_BRANCH="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##' || true)"
  BASE_BRANCH="${BASE_BRANCH:-main}"
  DIFF_RANGE="${BASE_BRANCH}...HEAD"
fi

DIFF_OUTPUT="$(cd "$REPO_ROOT" && { git diff --unified=0 "$DIFF_RANGE" -- '*.css' '*.scss' '*.less' '*.tsx' '*.jsx' '*.vue' '*.svelte' 2>/dev/null || git diff --unified=0 -- '*.css' '*.scss' '*.less' '*.tsx' '*.jsx' '*.vue' '*.svelte'; })"
[ -z "$DIFF_OUTPUT" ] && exit 0

MATCHES=0
CURRENT_FILE=""
while IFS= read -r line; do
  case "$line" in
    "+++ b/"*)
      CURRENT_FILE="${line#+++ b/}"
      [ "$CURRENT_FILE" = "/dev/null" ] && CURRENT_FILE=""
      ;;
    "+"*)
      [ -z "$CURRENT_FILE" ] && continue
      ADDED_TEXT="${line#+}"
      # A 2+ digit px value not already wrapped by var(--...) or inside a
      # media query breakpoint context is a candidate magic number.
      if echo "$ADDED_TEXT" | grep -Eq '[0-9]{2,}px' \
        && ! echo "$ADDED_TEXT" | grep -Eq 'var\(--[a-zA-Z0-9-]+\)' \
        && ! echo "$ADDED_TEXT" | grep -Eq '@media|min-width|max-width'; then
        MATCHES=$((MATCHES + 1))
        [ "$QUIET" = "1" ] || echo "[design-token-lint] $CURRENT_FILE: hardcoded px value — consider a design token: ${ADDED_TEXT#"${ADDED_TEXT%%[![:space:]]*}"}"
      fi
      ;;
  esac
done <<< "$DIFF_OUTPUT"

[ "$MATCHES" -gt 0 ] && [ "$QUIET" = "0" ] && echo "[design-token-lint] $MATCHES hardcoded px value(s) found — informational only, not blocking"

exit 0
