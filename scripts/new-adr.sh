#!/usr/bin/env bash
# Creates a numbered ADR file with MADR template in docs/development/adrs/
# Usage: bash .dev-team-agents/scripts/new-adr.sh "title of the decision"
set -euo pipefail

TITLE="${1:-}"

if [ -z "$TITLE" ]; then
    echo "Usage: $0 \"title of the decision\""
    echo "Example: $0 \"Use PostgreSQL as primary database\""
    exit 1
fi

ADR_DIR="docs/development/adrs"
mkdir -p "$ADR_DIR"

# Find the next sequential number
LAST=$(for f in "$ADR_DIR"/adr-[0-9]*.md; do
    [ -f "$f" ] || continue
    basename "$f"
done 2>/dev/null | grep -oE 'adr-[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1)
NEXT=$(printf "%03d" $(( ${LAST:-0} + 1 )))

# Build a URL-safe slug from the title
SLUG=$(echo "$TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9' '-' \
    | sed 's/^-//;s/-$//')

FILENAME="$ADR_DIR/adr-${NEXT}-${SLUG}.md"
TODAY=$(date +%Y-%m-%d)

# Locate the template relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/../templates/adr-template.md"

if [ ! -f "$TEMPLATE" ]; then
    echo "Error: ADR template not found at $TEMPLATE" >&2
    exit 1
fi

sed \
    -e "s/\[NUMBER\]/$NEXT/g" \
    -e "s|\[Title\]|$TITLE|g" \
    -e "s/\[YYYY-MM-DD\]/$TODAY/g" \
    "$TEMPLATE" > "$FILENAME"

echo "Created: $FILENAME"
