#!/usr/bin/env bash
# check-fingerprint-uniqueness.sh — Detect duplicate fingerprint slugs across the whole bank.
#
# The bank is not a single file: the documented rotation policy (helpers/archive-index.sh)
# moves aged entries out of _index.md into _index-archive-YYYY-Q.md. Scanning only _index.md
# would silently downgrade the guarantee from global to per-file the moment rotation runs,
# letting an archived slug be re-registered undetected. So this gate scans _index.md plus
# every _index-archive-*.md that exists, and reports the source file of each occurrence.
#
# Exit 1 if duplicates found; exit 0 if all slugs are unique.
set -euo pipefail

# Anchored to the repo, not the caller's cwd: a blocking gate must never pass by
# silently failing to find the bank it is supposed to check.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$REPO_ROOT/docs/reports"
INDEX_FILE="$REPORTS_DIR/_index.md"

# Build the list of bank files: the live index first, then any quarterly archives.
BANK_FILES=()
[ -f "$INDEX_FILE" ] && BANK_FILES+=("$INDEX_FILE")
while IFS= read -r archive; do
    [ -n "$archive" ] && BANK_FILES+=("$archive")
done < <(find "$REPORTS_DIR" -maxdepth 1 -name '_index-archive-*.md' 2>/dev/null | sort)

if [ "${#BANK_FILES[@]}" -eq 0 ]; then
    echo "→ No fingerprint index found in $REPORTS_DIR; skipping uniqueness check." >&2
    exit 0
fi

# Emit "<slug>\t<file>" for every registered fingerprint across all bank files.
PAIRS=$(
    for bank_file in "${BANK_FILES[@]}"; do
        rel_bank="${bank_file#"$REPO_ROOT"/}"
        grep -E "^- \`[a-z][a-z0-9-]+" "$bank_file" 2>/dev/null \
            | sed "s/^- \`\([a-z][a-z0-9-]*\)\`.*/\1/" \
            | sed "s|\$|\t$rel_bank|"
    done
)

DUPLICATES=$(printf '%s\n' "$PAIRS" | cut -f1 | sort | uniq -d)

if [ -n "$DUPLICATES" ]; then
    echo "✗ Duplicate fingerprint slugs found across the fingerprint bank:" >&2
    printf '%s\n' "$DUPLICATES" | while read -r slug; do
        [ -z "$slug" ] && continue
        echo "  · $slug" >&2
        printf '%s\n' "$PAIRS" | awk -F'\t' -v s="$slug" '$1 == s { print $2 }' \
            | sort | uniq -c \
            | while read -r count file; do
                  echo "      ↳ $file (×$count)" >&2
              done
    done
    exit 1
fi

SLUG_COUNT=$(printf '%s\n' "$PAIRS" | grep -c . || true)
echo "✓ All $SLUG_COUNT fingerprint slugs are unique across ${#BANK_FILES[@]} bank file(s)."
