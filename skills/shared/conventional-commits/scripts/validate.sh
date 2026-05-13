#!/usr/bin/env bash
set -euo pipefail

PATTERN='^(feat|fix|docs|refactor|perf|test|ci|build|chore|style|revert)(\(.+\))?(!)?: .{1,72}'

usage() {
  cat <<EOF
Usage: validate.sh [--help] [commit-message]
       echo "commit message" | validate.sh

Exits 0 if the message follows Conventional Commits format; exits 1 with an
error message if it does not.

Pattern checked: $PATTERN
EOF
}

if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -ge 1 ]]; then
  MSG="$1"
else
  MSG="$(cat)"
fi

FIRST_LINE="$(printf '%s' "$MSG" | head -n1)"

if ! printf '%s' "$FIRST_LINE" | grep -qE "$PATTERN"; then
  echo "ERROR: commit message does not follow Conventional Commits format." >&2
  echo "  Got:      $FIRST_LINE" >&2
  echo "  Expected: <type>[(<scope>)][!]: <description> (max 72 chars)" >&2
  echo "  Types:    feat fix docs refactor perf test ci build chore style revert" >&2
  exit 1
fi

# Validate breaking-change consistency:
# If subject has '!' the footer may optionally have BREAKING CHANGE — both are valid.
# If footer has 'BREAKING CHANGE:' but subject lacks '!' that is also valid per spec.
# What we flag: 'BREAKING CHANGE' footer misspelled without the colon.
if printf '%s' "$MSG" | grep -qiE '^BREAKING CHANGE[^:]'; then
  echo "ERROR: breaking change footer must use 'BREAKING CHANGE: <description>'." >&2
  exit 1
fi

echo "OK: commit message is valid."
exit 0
