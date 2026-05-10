#!/usr/bin/env bash
# Usage: bash scripts/agent-lint.sh
# Validates YAML frontmatter on all agents/*.md files.
# Checks for required fields and valid model values.
# Exits 0 if all pass, 1 if any errors found.
# Flags:
#   --quiet   suppress success output when clean

set -euo pipefail

QUIET=false
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=true ;;
  esac
done

VALID_MODELS=(
  "claude-opus-4-7"
  "claude-sonnet-4-6"
  "claude-haiku-4-5-20251001"
)
REQUIRED_FIELDS=("name" "description" "model" "tools")

ERRORS=()

check_agent() {
  local file="$1"
  local basename
  basename=$(basename "$file")

  # Check frontmatter block exists
  local first_line
  first_line=$(head -1 "$file")
  if [ "$first_line" != "---" ]; then
    ERRORS+=("  · ${file}: missing frontmatter (file must start with ---)")
    return
  fi

  # Extract frontmatter (between first and second ---)
  local frontmatter
  frontmatter=$(awk '/^---/{n++; if(n==2) exit} n==1 && !/^---/' "$file")

  if [ -z "$frontmatter" ]; then
    ERRORS+=("  · ${file}: empty or malformed frontmatter block")
    return
  fi

  # Check required fields
  for field in "${REQUIRED_FIELDS[@]}"; do
    if ! echo "$frontmatter" | grep -qE "^${field}:"; then
      ERRORS+=("  · ${file}: missing field: ${field}")
    fi
  done

  # Validate model value
  local model
  model=$(echo "$frontmatter" | grep -E "^model:" | sed 's/^model:[[:space:]]*//' | tr -d '\r')

  if [ -n "$model" ]; then
    local valid=false
    for m in "${VALID_MODELS[@]}"; do
      if [ "$model" = "$m" ]; then
        valid=true
        break
      fi
    done
    if [ "$valid" = false ]; then
      local allowed
      allowed=$(IFS=", "; echo "${VALID_MODELS[*]}")
      ERRORS+=("  · ${file}: invalid model: ${model} (allowed: ${allowed})")
    fi
  fi
}

SEPARATOR="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for agent_file in agents/*.md; do
  [ -f "$agent_file" ] || continue
  check_agent "$agent_file"
done

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo "$SEPARATOR"
  echo " AGENT LINT"
  echo "$SEPARATOR"
  echo ""
  echo " ERRORS — Fix before merging:"
  for err in "${ERRORS[@]}"; do
    echo "$err"
  done
  echo ""
  echo "$SEPARATOR"
  exit 1
fi

if [ "$QUIET" = false ]; then
  echo "agent-lint: clean ✓"
fi
