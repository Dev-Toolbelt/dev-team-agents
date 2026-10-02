#!/usr/bin/env bash
# 06-bash32.sh — fail on bash > 3.2 syntax in shipped shell scripts. macOS's
# /bin/bash is 3.2.57 and every installer/hook must run there unmodified.
# Patterns are anchored to command position so a verb named in a string or
# comment (a deny-list, an explanation) is not a hit.
# Usage: bash 06-bash32.sh [root]   (default: repository root)
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"

PATTERN='(^|[;&|({]|\bdo\b|\bthen\b)[[:space:]]*((declare|typeset|local)[[:space:]]+-[a-zA-Z]*[AnN]|mapfile|readarray|coproc)\b|\$\{[A-Za-z_0-9]+(,,|,|\^\^|\^)\}|\$\{[A-Za-z_0-9]+@[UuLlQEPAa]\}|&>>|\|&[[:space:]]|\bwait -n\b|\[\[ -v |\$\{[A-Za-z_0-9]+\[-[0-9]+\]\}'

status=0
while IFS= read -r f; do
  hits=$(grep -nE "$PATTERN" "$f" | grep -vE '^[0-9]+:[[:space:]]*#' || true)
  if [ -n "$hits" ]; then
    echo "bash>3.2 feature in ${f#"$ROOT"/}:" >&2
    echo "$hits" >&2
    status=1
  fi
done < <(find "$ROOT/scripts" -name '*.sh' -not -path '*/node_modules/*' | sort)

[ "$status" -eq 0 ] && echo "bash 3.2 compatibility gate: clean"
exit "$status"
