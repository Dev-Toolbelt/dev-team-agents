#!/usr/bin/env bash
# Creates a numbered ADR file with MADR template in .claude/docs/development/adrs/
# Usage: bash .claude/dev-team-agents/scripts/new-adr.sh "title of the decision"
set -euo pipefail

TITLE="${1:-}"

if [ -z "$TITLE" ]; then
    echo "Usage: $0 \"title of the decision\""
    echo "Example: $0 \"Use PostgreSQL as primary database\""
    exit 1
fi

ADR_DIR=".claude/docs/development/adrs"
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

cat > "$FILENAME" <<EOF
# $TITLE

**Status**: Proposed
**Date**: $TODAY
**Deciders**: [names or roles involved]

## Context

[Describe the issue motivating this decision and the forces at play:
technical constraints, team size, performance requirements, etc.]

## Decision

[State the decision in active voice: "We will use X because..."]

## Rationale

[Explain why this option was chosen over the alternatives.
Link to benchmarks, constraints, or prior art that drove the choice.]

## Alternatives Considered

### Option A — [Name]
- **Pros**: ...
- **Cons**: ...
- **Why rejected**: ...

### Option B — [Name]
- **Pros**: ...
- **Cons**: ...
- **Why rejected**: ...

## Consequences

**Positive**: [What becomes easier or possible]
**Negative**: [What becomes harder, what debt is accepted]
**Risks**: [What could go wrong, and how to mitigate]
EOF

echo "Created: $FILENAME"
