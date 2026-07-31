#!/usr/bin/env bash
# orphan-template-scan.sh — Detect templates that no consumer references, and
# references that do not actually resolve at runtime.
#
# Matching a bare basename anywhere in a consumer only proves the name is
# mentioned — not that an agent following the reference can open the file.
# `templates/` ships to `.dev-team-agents/templates/` and is never symlinked into
# `.claude/` (unlike agents/, skills/ and commands/), so a bare relative path such
# as `templates/plan-template.md` resolves in this repo but not from the root of
# an installed project. Reporting those as healthy is worse than not scanning.
#
# Reference classes:
#   resolvable   `.dev-team-agents/templates/<file>`         — installed path
#                `$SCRIPT_DIR/../templates/<file>` and kin   — self-anchored path
#                bare `templates/<file>` in a repo-only consumer (see below)
#   unreachable  bare `templates/<file>` in a shipped consumer — no such path at a
#                                                               project root
#   ignored      the basename with no path at all — prose, not a path reference:
#                neither evidence of health nor a broken link
#
# Consumer contexts:
#   shipped   agents/ skills/ commands/ scripts/ — run with cwd = project root of
#             an *installed* project, so only installed/self-anchored paths work.
#   repo      CLAUDE.md CLAUDE-md/ helpers/ — this repository's own files, run with
#             cwd = repo root, where a bare `templates/…` path does resolve.
#
# Exit 0 always (informational only); use --quiet to suppress clean output.
set -euo pipefail

QUIET=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES_DIR="$REPO_ROOT/templates"

SHIPPED_CONSUMERS="agents skills commands scripts"
REPO_CONSUMERS="CLAUDE.md CLAUDE-md helpers"

ORPHAN_MSGS=()
UNRESOLVED_MSGS=()

# Suggested consumer for an orphan template, mirroring orphan-skill-scan.sh.
suggest_consumer() {
    case "$1" in
        adr-template.md)     echo "software-architect (or scripts/new-adr.sh, which already anchors its own path)" ;;
        plan-template.md)    echo "skills/shared/plan-mode/SKILL.md or any agent that presents a plan" ;;
        backlog-template.md) echo "product-analyst or skills/shared/backlog-template/SKILL.md" ;;
        runbook-template.md) echo "skills/shared/runbook/SKILL.md or devops-specialist" ;;
        *)                   echo "(inspect template content to determine the right agent or skill)" ;;
    esac
}

for template_file in "$TEMPLATES_DIR"/*.md; do
    [ -f "$template_file" ] || continue
    template_name="$(basename "$template_file")"
    rel_template="templates/$template_name"
    name_re="${template_name//./\\.}"

    resolvable_refs=0
    unresolved_refs=0

    for context in shipped repo; do
        if [ "$context" = "shipped" ]; then
            consumers="$SHIPPED_CONSUMERS"
        else
            consumers="$REPO_CONSUMERS"
        fi

        for consumer in $consumers; do
            target="$REPO_ROOT/$consumer"
            [ -e "$target" ] || continue

            while IFS= read -r hit; do
                [ -z "$hit" ] && continue
                # hit = <path>:<line-no>:<content>
                hit_path="${hit%%:*}"
                rest="${hit#*:}"
                hit_line="${rest%%:*}"
                content="${rest#*:}"
                rel_hit="${hit_path#"$REPO_ROOT"/}"

                if printf '%s' "$content" | grep -q "\.dev-team-agents/templates/$name_re"; then
                    resolvable_refs=$((resolvable_refs + 1))
                elif printf '%s' "$content" | grep -qE "(\\\$[A-Za-z_][A-Za-z0-9_]*|\.\.)/[^ \`\"']*templates/$name_re"; then
                    # Self-anchored path (e.g. "$SCRIPT_DIR/../templates/x.md") — resolves
                    # relative to the referencing script, wherever it is installed.
                    resolvable_refs=$((resolvable_refs + 1))
                elif printf '%s' "$content" | grep -qE "templates/$name_re"; then
                    if [ "$context" = "repo" ]; then
                        resolvable_refs=$((resolvable_refs + 1))
                    else
                        unresolved_refs=$((unresolved_refs + 1))
                        UNRESOLVED_MSGS+=("  · $rel_hit:$hit_line — bare \`templates/$template_name\`\n    → unreachable from a project root; use \`.dev-team-agents/templates/$template_name\`")
                    fi
                fi
                # A bare basename with no path (prose, or a label in this scanner
                # itself) is not a path reference: it is neither evidence of health
                # nor a broken link, so it is ignored entirely.
            done < <(grep -rn "$template_name" "$target" 2>/dev/null || true)
        done
    done

    if [ "$resolvable_refs" -eq 0 ] && [ "$unresolved_refs" -eq 0 ]; then
        ORPHAN_MSGS+=("  · $rel_template\n    → Suggested consumer: $(suggest_consumer "$template_name")\n    → Add a reference using the installed path form: \`.dev-team-agents/templates/$template_name\`")
    elif [ "$resolvable_refs" -eq 0 ]; then
        # Referenced, but no reference that an agent can actually follow.
        ORPHAN_MSGS+=("  · $rel_template — referenced, but no reference resolves at runtime\n    → Suggested consumer: $(suggest_consumer "$template_name")\n    → Fix the reference(s) listed below to \`.dev-team-agents/templates/$template_name\`")
    fi
done

if [ "${#ORPHAN_MSGS[@]}" -eq 0 ] && [ "${#UNRESOLVED_MSGS[@]}" -eq 0 ]; then
    $QUIET || echo "orphan-template-scan: clean ✓"
    exit 0
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ORPHAN TEMPLATE SCAN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "${#ORPHAN_MSGS[@]}" -gt 0 ]; then
    echo ""
    echo " ACTION REQUIRED — Templates with no usable consumer reference:"
    for msg in "${ORPHAN_MSGS[@]}"; do
        printf "%b\n" "$msg"
    done
fi

if [ "${#UNRESOLVED_MSGS[@]}" -gt 0 ]; then
    echo ""
    echo " ACTION REQUIRED — Template references that do not resolve at runtime:"
    for msg in "${UNRESOLVED_MSGS[@]}"; do
        printf "%b\n" "$msg"
    done
    echo ""
    echo " Why: templates install to .dev-team-agents/templates/ and are never"
    echo " symlinked into .claude/, so a bare \`templates/…\` path resolves only"
    echo " inside this repository — not from the root of an installed project."
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
