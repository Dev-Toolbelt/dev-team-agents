#!/usr/bin/env bash
# Usage: bash helpers/agent-lint.sh
# Validates YAML frontmatter on all agents/*.md files and skills/**/SKILL.md files.
# Checks for required fields, valid model values, and canonical skill frontmatter.
# Also validates skill identity (name == directory basename, names unique) and
# warns on over-budget skill descriptions.
# Exits 0 if all pass, 1 if any errors found. Warnings never affect the exit code.
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

# Skill `description` feeds the always-loaded skill index across every skill in
# the repo, so it is the highest-leverage per-character cost in the tree.
SKILL_DESC_LIMIT=95
# Descriptions feed the always-loaded skill index across every skill in the tree,
# so length here is the highest-leverage per-character cost in the repo. All
# violators were trimmed on 2026-07-31, so this is enforced. Keep it `true`:
# cut meta-narrative (which agent loads it, "authoritative", exhaustive lists),
# never the routing signal that tells an agent when to load the skill.
SKILL_DESC_STRICT=true

# Quiz-first Rule (CLAUDE.md): plain-text prompts are forbidden for ANY finite
# answer set — yes/no *and* 2–4 option multiple choice.
#   Pattern 1 — yes/no parentheticals, matched anywhere on the line.
QUIZ_YESNO_RE='\([yY]es[/ ][nN]o\)|\(y[/]n\)|\(yes\|no\)|\( yes / no \)'
#   Pattern 2 — multiple-choice prompts: a question mark immediately followed by
#   a short slash-separated option list. Anchoring on the `?` (rather than on any
#   parenthesised slash) keeps descriptive prose such as the provider list
#   "(Claude / opencode / Codex)" out of the match.
QUIZ_OPT='[A-Za-z0-9][A-Za-z0-9 ._-]{0,19}'
QUIZ_MC_RE="\\?[[:space:]\"'\`*]*\\([[:space:]]*${QUIZ_OPT}([[:space:]]*/[[:space:]]*${QUIZ_OPT})+\\)"

ERRORS=()
WARNINGS=()

# "<name><TAB><file>" entries, scanned for duplicates after all skills are read.
SKILL_NAMES=()

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
  check_quiz_first "$file" "$QUIZ_YESNO_RE" "plain-text yes/no prompt found"
  check_quiz_first "$file" "$QUIZ_MC_RE" "plain-text multiple-choice prompt found"
}

# Flags plain-text prompts that should be an AskUserQuestion call.
# Lines inside fenced blocks or containing inline code are skipped, matching the
# original yes/no check: those are documentation of the pattern, not a live prompt.
check_quiz_first() {
  local file="$1" regex="$2" label="$3"

  local violations
  violations=$(grep -nE "$regex" "$file" 2>/dev/null | grep -v "^[0-9]*:[[:space:]]*\`\`\`" | grep -cv "^[0-9]*:.*\`" || true)
  [ -z "$violations" ] && violations=0

  if [ "$violations" -gt 0 ]; then
    ERRORS+=("  · ${file}: ${label} — use AskUserQuestion tool instead (see skills/shared/interaction-patterns/SKILL.md)")
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

  local rel="${file#"$REPO_ROOT"/}"

  # ── name must equal the directory basename ─────────────────────────────────
  # The render engine resolves opencode skills by frontmatter `name`, while the
  # installers symlink by directory. If the two disagree, the skill is
  # unreachable under one of the two providers.
  local name dir_name
  name=$(echo "$frontmatter" | grep -E "^name:" | head -1 | sed 's/^name:[[:space:]]*//' | tr -d '\r' | sed 's/^["'"'"']//; s/["'"'"']$//; s/[[:space:]]*$//')
  dir_name=$(basename "$(dirname "$file")")
  if [ -n "$name" ]; then
    if [ "$name" != "$dir_name" ]; then
      ERRORS+=("  · ${rel}: name '${name}' does not match directory '${dir_name}' (they must be identical)")
    fi
    SKILL_NAMES+=("${name}"$'\t'"${rel}")
  fi

  # ── description budget (warning — see SKILL_DESC_STRICT) ───────────────────
  local desc
  desc=$(echo "$frontmatter" | grep -E "^description:" | head -1 | sed 's/^description:[[:space:]]*//' | tr -d '\r' | sed 's/^["'"'"']//; s/["'"'"']$//; s/[[:space:]]*$//')
  if [ -n "$desc" ] && [ "${#desc}" -gt "$SKILL_DESC_LIMIT" ]; then
    if [ "$SKILL_DESC_STRICT" = true ]; then
      ERRORS+=("  · ${rel}: description is ${#desc} chars (budget: ${SKILL_DESC_LIMIT})")
    else
      # "<length><TAB><path>" so the report can rank worst offenders first.
      WARNINGS+=("${#desc}"$'\t'"${rel}")
    fi
  fi
}

# ── Skill names must be globally unique ───────────────────────────────────────
# Agent bodies and helpers/orphan-skill-scan.sh reference skills by bare name,
# so two skills in different categories sharing a name make both references
# ambiguous.
check_skill_name_uniqueness() {
  [ ${#SKILL_NAMES[@]} -eq 0 ] && return

  local dup files
  while IFS= read -r dup; do
    [ -z "$dup" ] && continue
    files=$(printf '%s\n' "${SKILL_NAMES[@]}" | awk -F'\t' -v n="$dup" '$1 == n { printf "%s%s", sep, $2; sep = ", " }')
    ERRORS+=("  · duplicate skill name '${dup}' declared in: ${files}")
  done < <(printf '%s\n' "${SKILL_NAMES[@]}" | cut -f1 | sort | uniq -d)
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

check_skill_name_uniqueness

# Warnings are reported only in verbose mode — they are non-blocking and would
# otherwise fire on every Stop-hook run.
SHOW_WARNINGS=false
if [ ${#WARNINGS[@]} -gt 0 ] && [ "$QUIET" = false ]; then
  SHOW_WARNINGS=true
fi

if [ ${#ERRORS[@]} -gt 0 ] || [ "$SHOW_WARNINGS" = true ]; then
  echo "$SEPARATOR"
  echo " AGENT LINT"
  echo "$SEPARATOR"
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo ""
  echo " ERRORS — Fix before merging:"
  for err in "${ERRORS[@]}"; do
    echo "$err"
  done
fi

if [ "$SHOW_WARNINGS" = true ]; then
  echo ""
  echo " WARN — ${#WARNINGS[@]} skill description(s) over the ${SKILL_DESC_LIMIT}-char budget (non-blocking):"
  printf '%s\n' "${WARNINGS[@]}" \
    | sort -rn \
    | head -5 \
    | awk -F'\t' -v lim="$SKILL_DESC_LIMIT" '{ printf "  · %s: description is %s chars (budget: %s)\n", $2, $1, lim }'
  if [ ${#WARNINGS[@]} -gt 5 ]; then
    echo "  … and $(( ${#WARNINGS[@]} - 5 )) more over budget"
  fi
fi

if [ ${#ERRORS[@]} -gt 0 ] || [ "$SHOW_WARNINGS" = true ]; then
  echo ""
  echo "$SEPARATOR"
fi

if [ ${#ERRORS[@]} -gt 0 ]; then
  exit 1
fi

if [ "$QUIET" = false ]; then
  if [ ${#WARNINGS[@]} -gt 0 ]; then
    echo "agent-lint: no errors ✓ (${#WARNINGS[@]} warning(s))"
  else
    echo "agent-lint: clean ✓"
  fi
fi
