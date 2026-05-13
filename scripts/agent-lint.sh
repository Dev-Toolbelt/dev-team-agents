#!/usr/bin/env bash
# Usage: bash scripts/agent-lint.sh
# Validates YAML frontmatter on all agents/*.md files and skills/**/SKILL.md files.
# Checks for required fields, valid model values, and canonical skill frontmatter.
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

  # Validate tools: Read must be present; all tools must be from the known set
  KNOWN_TOOLS=(Read Write Edit Bash Glob Grep WebSearch)
  local tools_line
  tools_line=$(echo "$frontmatter" | grep -E "^tools:" | sed 's/^tools:[[:space:]]*//' | tr -d '\r')
  if [ -n "$tools_line" ]; then
    if ! echo "$tools_line" | grep -qw "Read"; then
      ERRORS+=("  · ${file}: tools must include 'Read' (every agent needs read access)")
    fi
    while IFS= read -r tool; do
      [ -z "$tool" ] && continue
      local known=false
      for k in "${KNOWN_TOOLS[@]}"; do
        [ "$tool" = "$k" ] && known=true && break
      done
      if [ "$known" = false ]; then
        ERRORS+=("  · ${file}: unknown tool '${tool}' (known: ${KNOWN_TOOLS[*]})")
      fi
    done < <(echo "$tools_line" | tr ',' '\n' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
  fi
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Validate skill frontmatter (name + description only) ─────────────────────
check_skill() {
  local file="$1"

  local first_line
  first_line=$(head -1 "$file")
  if [ "$first_line" != "---" ]; then
    return  # No frontmatter — acceptable for some skills
  fi

  local frontmatter
  frontmatter=$(awk '/^---/{n++; if(n==2) exit} n==1 && !/^---/' "$file")
  [ -z "$frontmatter" ] && return

  # Check required skill fields
  for field in name description; do
    if ! echo "$frontmatter" | grep -qE "^${field}:"; then
      ERRORS+=("  · ${file}: missing skill field: ${field}")
    fi
  done

  # Check for non-canonical keys (only name and description allowed at top level)
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    key=$(echo "$line" | grep -oE '^[a-zA-Z_-]+:' | tr -d ':' || true)
    [ -z "$key" ] && continue
    case "$key" in
      name|description) ;;  # canonical
      *) ERRORS+=("  · ${file}: non-canonical frontmatter key: ${key} (only name/description allowed)") ;;
    esac
  done <<< "$frontmatter"
}

SEPARATOR="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for agent_file in agents/*.md; do
  [ -f "$agent_file" ] || continue
  check_agent "$agent_file"
done

while IFS= read -r skill_file; do
  # Skip references/ subdirectories
  [[ "$skill_file" == *"/references/"* ]] && continue
  check_skill "$skill_file"
done < <(find "$REPO_ROOT/skills" -name "SKILL.md" | sort)

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
