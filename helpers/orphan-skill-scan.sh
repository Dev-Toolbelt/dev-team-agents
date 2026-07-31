#!/usr/bin/env bash
# Scans for orphaned skills and broken skill references across agents/, commands/.
#
# Orphaned  — skill exists in skills/ but no consumer file loads it (by path or name).
# Broken    — a consumer file references a skills/.../SKILL.md path that does not exist.
#
# Broken references are repaired in place when the skill can be located by its
# directory basename (the moved-skill case); anything else is reported, never
# deleted. This script runs unattended from the Stop hook.
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

# ── Phase 1: Repair broken path references in consumer files ─────────────────
# This phase runs UNATTENDED from the Stop hook, so it must never destroy
# content. A broken reference is repaired only when the skill can be located
# unambiguously by its directory basename (the moved-skill case). Anything else
# is reported for a human to resolve.
#
# It previously ran `sed "/$ref/d"`, deleting the whole line. On a routing-table
# row that took the detection signals with it — silently, on every Stop. Do not
# reintroduce a delete here.
FIXED_MSGS=()
UNRESOLVED_MSGS=()

for consumer_file in "${CONSUMER_FILES[@]}"; do
    broken_refs=()
    while IFS= read -r ref; do
        [ -z "$ref" ] && continue
        [ ! -f "$REPO_ROOT/$ref" ] && broken_refs+=("$ref")
    done < <(grep -oE 'skills/[a-zA-Z0-9/_-]+/SKILL\.md' "$consumer_file" 2>/dev/null || true)

    for ref in "${broken_refs[@]:-}"; do
        [ -z "$ref" ] && continue
        rel_consumer="${consumer_file#"$REPO_ROOT"/}"

        # Locate the skill by directory basename: skills/<cat>/<name>/SKILL.md
        skill_name=$(basename "$(dirname "$ref")")
        matches=()
        while IFS= read -r m; do
            [ -n "$m" ] && matches+=("${m#"$REPO_ROOT"/}")
        done < <(find "$SKILLS_DIR" -type d -name "$skill_name" \
                 -exec test -f '{}/SKILL.md' \; -print 2>/dev/null | sort)

        if [ "${#matches[@]}" -eq 1 ]; then
            new_ref="${matches[0]}/SKILL.md"
            # Single quotes are required: these are sed programs, not strings to
            # expand — `&` and the bracket class must reach sed verbatim.
            # shellcheck disable=SC2016
            old_e=$(printf '%s\n' "$ref"     | sed 's/[[\.*^$()+?{|/]/\\&/g')
            # shellcheck disable=SC2016
            new_e=$(printf '%s\n' "$new_ref" | sed 's/[[\.*^$&/]/\\&/g')
            if sed -i.bak "s/$old_e/$new_e/g" "$consumer_file" 2>/dev/null; then
                rm -f "${consumer_file}.bak"
                FIXED_MSGS+=("  · $rel_consumer: repaired path → $new_ref")
            fi
        else
            UNRESOLVED_MSGS+=("  · $rel_consumer: broken ref → $ref")
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
# A bare path regex cannot tell a load directive from a narrative mention, so it
# reports prose ("… via the model-identity skill") as a second load. The awk
# program below extracts only paths that appear as an actual load directive:
#
#   counted   Load `path` · Apply `path` · Follow `path` · When X, load `path`
#             - `path` — description   (top-level skill-load bullet list)
#   ignored   | trigger | `path` |     (conditional load tables — one row per
#                                       trigger is legitimate, not a duplicate)
#             nested/indented list items (branches of one decision cascade, and
#                                       instruction blocks aimed at sub-agents)
#             "… load `path` …"        (quoted prompts passed to another agent)
#             prose connectors: "defined in `path`", "table in `path`",
#                               "the `x` skill (`path`)", "format from `path`"
# Single-quoted on purpose: this is an awk program, not a shell string.
# shellcheck disable=SC2016
LOAD_DIRECTIVE_AWK='
{
  line = $0
  if (line ~ /^[[:space:]]*\|/) next            # table row
  if (line ~ /^[[:space:]][[:space:]]+/) next   # nested list item / continuation
  gsub(/"[^"]*"/, " ", line)                    # drop quoted sub-agent instructions
  while (match(line, /skills\/[a-zA-Z0-9\/_-]+\/SKILL\.md/)) {
    before = substr(line, 1, RSTART - 1)
    path   = substr(line, RSTART, RLENGTH)
    if (before !~ /(defined in|described in|documented in|table in|format from|listed in|see|skill) *\(?`?$/)
      print path
    line = substr(line, RSTART + RLENGTH)
  }
}'

for consumer_file in "${CONSUMER_FILES[@]}"; do
    rel_consumer="${consumer_file#"$REPO_ROOT"/}"
    while IFS= read -r dup_path; do
        [ -z "$dup_path" ] && continue
        DUPLICATE_MSGS+=("  · $rel_consumer loads $dup_path more than once")
    done < <(
        awk "$LOAD_DIRECTIVE_AWK" "$consumer_file" 2>/dev/null \
          | sort | uniq -d || true
    )
done

# ── Output ────────────────────────────────────────────────────────────────────
EFFECTIVE_DUPLICATE_COUNT=0
[ "$ERRORS_ONLY" = false ] && EFFECTIVE_DUPLICATE_COUNT=${#DUPLICATE_MSGS[@]}

if [ ${#FIXED_MSGS[@]} -eq 0 ] && [ ${#ORPHAN_MSGS[@]} -eq 0 ] && [ ${#UNRESOLVED_MSGS[@]} -eq 0 ] && [ "$EFFECTIVE_DUPLICATE_COUNT" -eq 0 ]; then
    [[ "${1:-}" != "--quiet" && "${1:-}" != "--errors-only" ]] && echo "orphan-skill-scan: clean ✓"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ORPHAN SKILL SCAN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ${#FIXED_MSGS[@]} -gt 0 ]; then
    echo ""
    echo " AUTO-FIXED — Broken references repointed to the skill's new location:"
    for msg in "${FIXED_MSGS[@]}"; do
        echo "$msg"
    done
    echo "   → Verify the surrounding text still reads correctly after the move."
fi

if [ ${#UNRESOLVED_MSGS[@]} -gt 0 ]; then
    echo ""
    echo " ACTION REQUIRED — Broken references that could not be resolved:"
    for msg in "${UNRESOLVED_MSGS[@]}"; do
        echo "$msg"
    done
    echo "   → The skill was deleted, or its basename is ambiguous across categories."
    echo "   → Repoint the reference by hand, or remove it if the skill is gone."
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
