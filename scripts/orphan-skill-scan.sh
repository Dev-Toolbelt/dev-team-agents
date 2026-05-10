#!/usr/bin/env bash
# Scans for orphaned skills and broken skill references across agents/*.md.
#
# Orphaned  — skill exists in skills/ but no agent loads it (by path or name).
# Broken    — agent references a skills/.../SKILL.md path that does not exist.
#
# Broken references are auto-fixed (removed from the agent file).
# Orphaned skills produce an ACTION REQUIRED block for Claude to act on.
#
# Usage:
#   bash scripts/orphan-skill-scan.sh          # full scan + auto-fix
#   bash scripts/orphan-skill-scan.sh --quiet  # suppress output when clean
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="$REPO_ROOT/agents"
SKILLS_DIR="$REPO_ROOT/skills"
CLAUDE_MD="$REPO_ROOT/CLAUDE.md"

# ── Parse user-invocable skills (excluded from orphan check) ─────────────────
# Reads the "User-Invocable Skills" table from CLAUDE.md.
# Uses awk to extract table rows between the section heading and the next ###.
USER_INVOCABLE=()
if [ -f "$CLAUDE_MD" ]; then
    while IFS= read -r line; do
        # Match first backtick-quoted cell in a table row: | `skill-name` | ...
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

# ── Collect agent files ───────────────────────────────────────────────────────
AGENT_FILES=()
while IFS= read -r f; do
    AGENT_FILES+=("$f")
done < <(find "$AGENTS_DIR" -name "*.md" | sort)

# ── Phase 1: Auto-fix broken path references in agents ───────────────────────
FIXED_MSGS=()

for agent_file in "${AGENT_FILES[@]}"; do
    broken_refs=()
    while IFS= read -r ref; do
        [ -z "$ref" ] && continue
        [ ! -f "$REPO_ROOT/$ref" ] && broken_refs+=("$ref")
    done < <(grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md' "$agent_file" 2>/dev/null || true)

    for ref in "${broken_refs[@]:-}"; do
        [ -z "$ref" ] && continue
        # shellcheck disable=SC2016
        escaped_ref=$(printf '%s\n' "$ref" | sed 's/[[\.*^$()+?{|]/\\&/g; s/\//\\\//g')
        if sed -i.bak "/$escaped_ref/d" "$agent_file" 2>/dev/null; then
            rm -f "${agent_file}.bak"
            rel_agent="${agent_file#"$REPO_ROOT"/}"
            FIXED_MSGS+=("  · $rel_agent: removed broken ref → $ref")
        fi
    done
done

# ── Phase 2: Detect orphaned skills ──────────────────────────────────────────
ORPHAN_MSGS=()
DUPLICATE_MSGS=()

while IFS= read -r skill_file; do
    rel_path="${skill_file#"$REPO_ROOT"/}"          # skills/category/name/SKILL.md
    skill_dir="$(dirname "$skill_file")"
    skill_name="$(basename "$skill_dir")"           # name (last dir before SKILL.md)

    # Skip entries inside references/ subdirectories
    [[ "$rel_path" == *"/references/"* ]] && continue

    # Skip user-invocable skills
    is_user_invocable "$skill_name" && continue

    referenced=false
    for agent_file in "${AGENT_FILES[@]}"; do
        # Full path reference: skills/category/name/SKILL.md
        if grep -q "$rel_path" "$agent_file" 2>/dev/null; then
            referenced=true
            break
        fi
        # Name reference: `skill-name` or "skill-name skill" or "skill `skill-name`"
        if grep -qE "\`${skill_name}\`|[^a-zA-Z0-9_-]${skill_name}[[:space:]]+(skill|Skill)|[Ss]kill[[:space:]]+\`?${skill_name}\`?" \
               "$agent_file" 2>/dev/null; then
            referenced=true
            break
        fi
    done

    if [ "$referenced" = false ]; then
        category="$(echo "$rel_path" | cut -d'/' -f2)"
        case "$category" in
            shared)       suggested="all coding agents" ;;
            architecture) suggested="software-architect, backend-developer, or frontend-developer" ;;
            testing)      suggested="backend-test-specialist or frontend-test-specialist" ;;
            security)     suggested="security-specialist or qa-specialist" ;;
            design)       suggested="ui-ux-designer or frontend-developer" ;;
            devops)       suggested="devops-specialist" ;;
            integrations) suggested="backend-developer or devops-specialist (inspect skill content to decide)" ;;
            ui-libraries) suggested="frontend-developer or ui-ux-designer" ;;
            *)            suggested="(inspect skill content to determine the right agent)" ;;
        esac
        ORPHAN_MSGS+=("  · $rel_path\n    → Suggested agent(s): $suggested\n    → Add a load reference matching the agent's existing skill-loading pattern")
    fi
done < <(find "$SKILLS_DIR" -name "SKILL.md" | sort)

# ── Phase 3: Detect duplicate skill loads in same agent ──────────────────────
# Only scans non-table lines (lines not starting with |) so detection tables
# that map multiple signals to the same skill don't produce false positives.
for agent_file in "${AGENT_FILES[@]}"; do
    rel_agent="${agent_file#"$REPO_ROOT"/}"
    while IFS= read -r dup_path; do
        [ -z "$dup_path" ] && continue
        DUPLICATE_MSGS+=("  · $rel_agent loads $dup_path more than once")
    done < <(
        grep -v '^\s*|' "$agent_file" 2>/dev/null \
          | grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md' \
          | sort | uniq -d || true
    )
done

# ── Output ────────────────────────────────────────────────────────────────────
if [ ${#FIXED_MSGS[@]} -eq 0 ] && [ ${#ORPHAN_MSGS[@]} -eq 0 ] && [ ${#DUPLICATE_MSGS[@]} -eq 0 ]; then
    [ "${1:-}" != "--quiet" ] && echo "orphan-skill-scan: clean ✓"
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

if [ ${#DUPLICATE_MSGS[@]} -gt 0 ]; then
    echo ""
    echo " WARN — Skills loaded more than once in the same agent:"
    for msg in "${DUPLICATE_MSGS[@]}"; do
        echo "$msg"
    done
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
