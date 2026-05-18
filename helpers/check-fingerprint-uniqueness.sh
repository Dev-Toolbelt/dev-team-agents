#!/usr/bin/env bash
# check-fingerprint-uniqueness.sh — Detect duplicate fingerprint slugs in docs/reports/_index.md.
# Exit 1 if duplicates found; exit 0 if all slugs are unique.
set -euo pipefail

INDEX_FILE="docs/reports/_index.md"

if [ ! -f "$INDEX_FILE" ]; then
    echo "→ $INDEX_FILE not found; skipping uniqueness check." >&2
    exit 0
fi

DUPLICATES=$(grep -E "^- \`[a-z][a-z0-9-]+" "$INDEX_FILE" 2>/dev/null \
    | sed "s/^- \`\([a-z][a-z0-9-]*\)\`.*/\1/" \
    | sort \
    | uniq -d)

if [ -n "$DUPLICATES" ]; then
    echo "✗ Duplicate fingerprint slugs found in $INDEX_FILE:" >&2
    echo "$DUPLICATES" | while read -r slug; do
        echo "  · $slug" >&2
    done
    exit 1
fi

echo "✓ All fingerprint slugs are unique."
