#!/usr/bin/env bash
# Usage: bash helpers/agent-lint.sh
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

REQUIRED_FIELDS=("name" "description" "tier")
VALID_TIERS=("reasoning" "backend-exec" "frontend" "repetitive")

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

  # Validate tier value (used by render-provider.sh to pick the model per provider)
  local tier
  tier=$(echo "$frontmatter" | grep -E "^tier:" | sed 's/^tier:[[:space:]]*//' | tr -d '\r')
  if [ -z "$tier" ]; then
    ERRORS+=("  · ${file}: missing field: tier")
  else
    local tier_valid=false
    for t in "${VALID_TIERS[@]}"; do
      [ "$tier" = "$t" ] && tier_valid=true && break
    done
    if [ "$tier_valid" = false ]; then
      local tier_allowed
      tier_allowed=$(IFS=", "; echo "${VALID_TIERS[*]}")
      ERRORS+=("  · ${file}: invalid tier: ${tier} (allowed: ${tier_allowed})")
    fi
  fi

  # Check for quiz-first compliance (AskUserQuestion required for finite-answer prompts)
  if grep -qE "\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)" "$file" 2>/dev/null; then
    local violations
    violations=$(grep -nE "\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)" "$file" | grep -v "^\s*\`\`\`" | grep -cv "^[0-9]*:.*\`" || true)
    if [ "$violations" -gt 0 ]; then
      ERRORS+=("  · ${file}: plain-text yes/no prompt found — use AskUserQuestion tool instead (see skills/shared/interaction-patterns/SKILL.md)")
    fi
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
