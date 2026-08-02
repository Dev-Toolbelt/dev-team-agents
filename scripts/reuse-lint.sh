#!/usr/bin/env bash
# Enforces docs/development/reuse-guidelines.md against the working diff.
# No-op (exit 0) when the registry does not exist — absence means no rule
# registered, not a failure. See skills/shared/reuse-guidelines/SKILL.md.
#
# Only `code-pattern` and `path-convention` rows are mechanically checked.
# `design-rule` rows are parsed and skipped on purpose — they have no regex,
# by design, and are enforced only by the review gate (see the skill).
set -euo pipefail

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
REGISTRY="$REPO_ROOT/docs/development/reuse-guidelines.md"
[ -f "$REGISTRY" ] || exit 0

DIFF_RANGE="${REUSE_LINT_DIFF_RANGE:-}"
if [ -z "$DIFF_RANGE" ]; then
  BASE_BRANCH="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#origin/##')"
  BASE_BRANCH="${BASE_BRANCH:-main}"
  DIFF_RANGE="${BASE_BRANCH}...HEAD"
fi

VIOLATIONS=0

# Strip surrounding backticks/whitespace a Markdown table cell may carry.
_clean() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  s="${s#\`}"
  s="${s%\`}"
  printf '%s' "$s"
}

# Parse table rows into three parallel arrays, skipping header/separator.
PATTERN_NAMES=() PATTERN_REGEX=() PATTERN_REF=()
PATH_NAMES=() PATH_GLOB=() PATH_DIR=() PATH_REF=()

while IFS='|' read -r _ f_name f_type f_rule f_detect f_ref _; do
  name="$(_clean "$f_name")"
  [ -z "$name" ] && continue
  [ "$name" = "name" ] && continue
  case "$name" in *---*) continue ;; esac

  type="$(_clean "$f_type")"
  detection="$(_clean "$f_detect")"
  ref="$(_clean "$f_ref")"

  case "$type" in
    code-pattern)
      PATTERN_NAMES+=("$name")
      PATTERN_REGEX+=("$detection")
      PATTERN_REF+=("$ref")
      ;;
    path-convention)
      name_glob="${detection#path:}"
      name_glob="${name_glob%%=>*}"
      required_dir="${detection#*=>}"
      PATH_NAMES+=("$name")
      PATH_GLOB+=("$name_glob")
      PATH_DIR+=("$required_dir")
      PATH_REF+=("$ref")
      ;;
    design-rule|*)
      : # not mechanically checked — review gate only
      ;;
  esac
done < <(grep '^|' "$REGISTRY")

DIFF_OUTPUT="$(git diff --unified=0 "$DIFF_RANGE" -- . 2>/dev/null || git diff --unified=0 -- .)"

CURRENT_FILE=""
while IFS= read -r line; do
  case "$line" in
    "+++ b/"*)
      CURRENT_FILE="${line#+++ b/}"
      [ "$CURRENT_FILE" = "/dev/null" ] && CURRENT_FILE=""

      # path-convention: check the file's own path once per touched file.
      if [ -n "$CURRENT_FILE" ]; then
        base="$(basename "$CURRENT_FILE")"
        for i in "${!PATH_NAMES[@]}"; do
          if [[ "$base" == ${PATH_GLOB[$i]} ]] && [[ "$CURRENT_FILE" != ${PATH_DIR[$i]}* ]]; then
            VIOLATIONS=$((VIOLATIONS + 1))
            [ "$QUIET" = "1" ] || echo "[reuse-lint] BLOCKED — $CURRENT_FILE: violates '${PATH_NAMES[$i]}' path-convention, must live under ${PATH_DIR[$i]}"
          fi
        done
      fi
      ;;
    "+"*)
      [ -z "$CURRENT_FILE" ] && continue
      ADDED_TEXT="${line#+}"
      for i in "${!PATTERN_NAMES[@]}"; do
        if echo "$ADDED_TEXT" | grep -Eq "${PATTERN_REGEX[$i]}"; then
          VIOLATIONS=$((VIOLATIONS + 1))
          [ "$QUIET" = "1" ] || echo "[reuse-lint] BLOCKED — $CURRENT_FILE: matches '${PATTERN_NAMES[$i]}' rule, use ${PATTERN_REF[$i]} instead"
        fi
      done
      ;;
  esac
done <<< "$DIFF_OUTPUT"

[ "$VIOLATIONS" -gt 0 ] && exit 1
exit 0
