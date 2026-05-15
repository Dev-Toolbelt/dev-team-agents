#!/usr/bin/env bash
# orphan-template-scan.sh — Detect template files in templates/ that have no
# reference in agents/, skills/, commands/, or workflows/.
# Exit 0 always (informational only); use --quiet to suppress clean output.
set -euo pipefail

QUIET=false
[[ "${1:-}" == "--quiet" ]] && QUIET=true

TEMPLATES_DIR="templates"
CONSUMERS="agents skills commands workflows scripts"
FOUND_ORPHANS=false

for template_file in "$TEMPLATES_DIR"/*.md; do
    [ -f "$template_file" ] || continue
    template_name=$(basename "$template_file")
    refs=0
    for dir in $CONSUMERS; do
        [ -d "$dir" ] || continue
        if grep -rl "$template_name" "$dir/" >/dev/null 2>&1; then
            refs=$((refs + 1))
        fi
    done
    if [ "$refs" -eq 0 ]; then
        if [ "$FOUND_ORPHANS" = false ]; then
            echo ""
            echo " ACTION REQUIRED — Orphan templates (no agent/skill/command references):"
        fi
        echo "  · $template_file"
        FOUND_ORPHANS=true
    fi
done

if [ "$FOUND_ORPHANS" = false ]; then
    $QUIET || echo "✓ All templates are referenced."
fi
