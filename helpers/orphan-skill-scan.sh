#!/usr/bin/env bash
# Scans for orphaned skills and broken skill references across agents/, commands/.
#
# Orphaned  — skill exists in skills/ but no consumer file loads it (by path or name).
# Broken    — a consumer file references a skills/.../SKILL.md path that does not exist.
#
# Broken references are auto-fixed (removed from the consumer file).
# Orphaned skills produce an ACTION REQUIRED block for Claude to act on.
#
# Usage:
#   bash helpers/orphan-skill-scan.sh                # full scan + auto-fix
#   bash helpers/orphan-skill-scan.sh --quiet        # suppress output when clean
#   bash helpers/orphan-skill-scan.sh --errors-only  # suppress WARN/ACTION SUGGESTED; show ACTION REQUIRED only
set -euo pipefail

ERRORS_ONLY=false
for arg in "$@"; do
    [ "$arg" = "--errors-only" ] && ERRORS_ONLY=true
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/agents"
COMMANDS_DIR="$REPO_ROOT/commands"
SKILLS_DIR="$REPO_ROOT/skills"
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"

# ── Parse user-invocable skills (excluded from orphan check) ─────────────────
# Reads the "User-Invocable Skills" table from CLAUDE.md.
USER_INVOCABLE=()
if [ -f "$CLAUDE_MD" ]; then
    while IFS= read -r line; do
        if [[ "$line" =~ ^\|[[:space:]]*\`([a-zA-Z0-9_-]+)\`[[:space:]]*\| ]]; then
            USER_INVOCABLE+=("${BASH_REMATCH[1]}")
        fi
    done < <(awk '/User-Invocable Skills/{found=1} found && /^\|/{print} found && /^### /{found=0}' "$CLAUDE_MD")
fi

is_user_invocable() {
    local name="$1"
    local inv
    for inv in "${USER_INVOCABLE[@]:-}"; do
        [ "$inv" = "$name" ] && return 0
    done
    return 1
}

# ── Collect consumer files (agents + commands) ──────────────────────────────
CONSUMER_FILES=()
while IFS= read -r f; do
    CONSUMER_FILES+=("$f")
done < <(find "$AGENTS_DIR" "$COMMANDS_DIR" -name "*.md" 2>/dev/null | sort)

# ── Phase 1: Auto-fix broken path references in consumer files ───────────────
FIXED_MSGS=()

for consumer_file in "${CONSUMER_FILES[@]}"; do
    broken_refs=()
    while IFS= read -r ref; do
        [ -z "$ref" ] && continue
        [ ! -f "$REPO_ROOT/$ref" ] && broken_refs+=("$ref")
    done < <(grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md' "$consumer_file" 2>/dev/null || true)

    for ref in "${broken_refs[@]:-}"; do
        [ -z "$ref" ] && continue
        # shellcheck disable=SC2016
        escaped_ref=$(printf '%s\n' "$ref" | sed 's/[[\.*^$()+?{|]/\\&/g; s/\//\\\//g')
        if sed -i.bak "/$escaped_ref/d" "$consumer_file" 2>/dev/null; then
            rm -f "${consumer_file}.bak"
            rel_consumer="${consumer_file#"$REPO_ROOT"/}"
            FIXED_MSGS+=("  · $rel_consumer: removed broken ref → $ref")
        fi
    done
done

# ── Phase 2: Detect orphaned skills ──────────────────────────────────────────
# Pre-build a single combined consumer text so Phase 2 needs only 2 greps per
# skill instead of 2 × N_consumers greps (O(skills) vs O(skills × consumers)).
COMBINED_TMP=$(mktemp /tmp/devteam-consumers.XXXXXX)
trap 'rm -f "$COMBINED_TMP"' EXIT
if [ ${#CONSUMER_FILES[@]} -gt 0 ]; then
    cat "${CONSUMER_FILES[@]}" > "$COMBINED_TMP" 2>/dev/null || true
fi

ORPHAN_MSGS=()
DUPLICATE_MSGS=()

while IFS= read -r skill_file; do
    rel_path="${skill_file#"$REPO_ROOT"/}"
    skill_dir="$(dirname "$skill_file")"
    skill_name="$(basename "$skill_dir")"

    # Skip entries inside references/ or sections/ subdirectories
    [[ "$rel_path" == *"/references/"* ]] && continue
    [[ "$rel_path" == *"/sections/"* ]] && continue

    # Skip user-invocable skills
    is_user_invocable "$skill_name" && continue

    referenced=false
    if grep -q "$rel_path" "$COMBINED_TMP" 2>/dev/null; then
        referenced=true
    elif grep -qE "\`${skill_name}\`|[^a-zA-Z0-9_-]${skill_name}[[:space:]]+(skill|Skill)|[Ss]kill[[:space:]]+\`?${skill_name}\`?" \
             "$COMBINED_TMP" 2>/dev/null; then
        referenced=true
    fi

    if [ "$referenced" = false ]; then
        category="$(echo "$rel_path" | cut -d'/' -f2)"
        case "$category" in
            shared)       suggested="all coding agents or commands" ;;
            architecture) suggested="software-architect, backend-developer, or frontend-developer" ;;
            testing)      suggested="backend-test-specialist or frontend-test-specialist" ;;
            security)     suggested="security-specialist or qa-specialist" ;;
            design)       suggested="ui-ux-designer or frontend-developer" ;;
            devops)       suggested="devops-specialist" ;;
            integrations) suggested="backend-developer or devops-specialist (inspect skill content to decide)" ;;
            ui-libraries) suggested="frontend-developer or ui-ux-designer" ;;
            *)            suggested="(inspect skill content to determine the right agent)" ;;
        esac
        ORPHAN_MSGS+=("  · $rel_path\n    → Suggested consumer: $suggested\n    → Add a load reference matching the existing skill-loading pattern")
    fi
done < <(find "$SKILLS_DIR" -name "SKILL.md" | sort)

# ── Phase 3: Detect duplicate skill loads in same consumer file ──────────────
for consumer_file in "${CONSUMER_FILES[@]}"; do
    rel_consumer="${consumer_file#"$REPO_ROOT"/}"
    while IFS= read -r dup_path; do
        [ -z "$dup_path" ] && continue
        DUPLICATE_MSGS+=("  · $rel_consumer loads $dup_path more than once")
    done < <(
        grep -v '^\s*|' "$consumer_file" 2>/dev/null \
          | grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md' \
          | sort | uniq -d || true
    )
done

# ── Output ────────────────────────────────────────────────────────────────────
EFFECTIVE_DUPLICATE_COUNT=0
[ "$ERRORS_ONLY" = false ] && EFFECTIVE_DUPLICATE_COUNT=${#DUPLICATE_MSGS[@]}

if [ ${#FIXED_MSGS[@]} -eq 0 ] && [ ${#ORPHAN_MSGS[@]} -eq 0 ] && [ "$EFFECTIVE_DUPLICATE_COUNT" -eq 0 ]; then
    [[ "${1:-}" != "--quiet" && "${1:-}" != "--errors-only" ]] && echo "orphan-skill-scan: clean ✓"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ORPHAN SKILL SCAN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#FIXED_MSGS[@]} -gt 0 ]; then
    echo ""
    echo " AUTO-FIXED — Broken references removed from agents:"
    for msg in "${FIXED_MSGS[@]}"; do
        echo "$msg"
    done
fi

if [ ${#ORPHAN_MSGS[@]} -gt 0 ]; then
    echo ""
    echo " ACTION REQUIRED — Skills with no agent reference:"
    for msg in "${ORPHAN_MSGS[@]}"; do
        printf "%b\n" "$msg"
    done
    echo ""
    echo " Fix: add a reference in the suggested agent file."
    echo " Use the full path form or name form already present"
    echo " in that agent's skill-loading section."
fi

if [ ${#DUPLICATE_MSGS[@]} -gt 0 ] && [ "$ERRORS_ONLY" = false ]; then
    echo ""
    echo " ACTION SUGGESTED — duplicate skill loads detected:"
    for msg in "${DUPLICATE_MSGS[@]}"; do
        echo "$msg"
    done
    echo "  Suggested fix: Edit <file>, find the duplicate load reference, and remove"
    echo "  the redundant occurrence (keep the first/canonical one in the skill gate)."
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
