#!/usr/bin/env bash
# archive-index.sh — Move fingerprint entries older than 90 days from _index.md to quarterly archive files.
# Usage: bash scripts/archive-index.sh [--dry-run]
# Exit 0 always (archival is non-destructive; dry-run prints what would move).
set -euo pipefail

INDEX_FILE="docs/reports/_index.md"
DRY_RUN=false

for arg in "$@"; do
    [ "$arg" = "--dry-run" ] && DRY_RUN=true
done

if [ ! -f "$INDEX_FILE" ]; then
    echo "→ $INDEX_FILE not found; nothing to archive." >&2
    exit 0
fi

# Compute cutoff date (90 days ago) in YYYY-MM-DD format.
CUTOFF=$(date -v-90d +%Y-%m-%d 2>/dev/null || date -d "90 days ago" +%Y-%m-%d 2>/dev/null || true)
if [ -z "$CUTOFF" ]; then
    echo "→ Could not compute cutoff date; skipping archive." >&2
    exit 0
fi

# Collect date headers older than cutoff.
OLD_DATES=()
while IFS= read -r line; do
    if [[ "$line" =~ ^###\ ([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        ENTRY_DATE="${BASH_REMATCH[1]}"
        if [[ "$ENTRY_DATE" < "$CUTOFF" ]]; then
            OLD_DATES+=("$ENTRY_DATE")
        fi
    fi
done < "$INDEX_FILE"

if [ "${#OLD_DATES[@]}" -eq 0 ]; then
    echo "✓ No entries older than 90 days in $INDEX_FILE."
    exit 0
fi

echo "→ Found ${#OLD_DATES[@]} date sections older than $CUTOFF:"
for d in "${OLD_DATES[@]}"; do echo "    $d"; done

if $DRY_RUN; then
    echo "→ Dry-run mode: no files modified."
    exit 0
fi

# For each old date, extract the section and append to the quarterly archive file.
for ENTRY_DATE in "${OLD_DATES[@]}"; do
    YEAR="${ENTRY_DATE:0:4}"
    MONTH="${ENTRY_DATE:5:2}"
    QUARTER=$(( (10#$MONTH - 1) / 3 + 1 ))
    ARCHIVE_FILE="docs/reports/_index-archive-${YEAR}-Q${QUARTER}.md"

    if [ ! -f "$ARCHIVE_FILE" ]; then
        echo "# Fingerprint Archive — ${YEAR} Q${QUARTER}" > "$ARCHIVE_FILE"
        echo "" >> "$ARCHIVE_FILE"
    fi

    # Extract section: from the ### header line until the next ### header (exclusive).
    awk -v date="$ENTRY_DATE" '
        /^### / && found { exit }
        /^### / && $0 ~ date { found=1 }
        found { print }
    ' "$INDEX_FILE" >> "$ARCHIVE_FILE"
    echo "" >> "$ARCHIVE_FILE"

    # Remove section from index (in-place with temp file).
    TMP=$(mktemp)
    awk -v date="$ENTRY_DATE" '
        /^### / && $0 ~ date { skip=1 }
        /^### / && $0 !~ date { skip=0 }
        !skip { print }
    ' "$INDEX_FILE" > "$TMP"
    mv "$TMP" "$INDEX_FILE"

    echo "→ Archived $ENTRY_DATE → $ARCHIVE_FILE"
done

echo "✓ Archive complete. $(wc -l < "$INDEX_FILE") lines remain in $INDEX_FILE."
