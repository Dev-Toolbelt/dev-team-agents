#!/usr/bin/env bash
# Creates a numbered ADR file with MADR template in docs/development/adrs/
# Usage: bash .dev-team-agents/scripts/new-adr.sh "title of the decision"
#        bash .dev-team-agents/scripts/new-adr.sh --list
set -euo pipefail

TITLE="${1:-}"

ADR_DIR="docs/development/adrs"

# The two naming schemes are defined in exactly ONE place here: the historical
# `adr-NNN-slug.md` this script used to emit, and the prefix-less `NNNN-slug.md`
# form the repository actually carries. They used to be spelled out twice in this
# file and a third time in skills/shared/adr/SKILL.md — and that third copy was
# stale, so the mandated duplicate-ADR check matched nothing and returned an empty
# list for every ADR that exists. One definition, every reader routed through it.
#
# Tolerates a missing directory on purpose: the guard below skips a glob that did
# not expand, so `--list` answers a question without creating anything.
adr_files() {
    local f
    for f in "$ADR_DIR"/adr-[0-9]*.md "$ADR_DIR"/[0-9]*.md; do
        [ -f "$f" ] || continue
        printf '%s\n' "$f"
    done
}

adr_titles() {
    local f
    adr_files | while IFS= read -r f; do
        grep -h '^# ' "$f" 2>/dev/null || true
    done
}

# `--list` is the listing `skills/shared/adr/SKILL.md` § Check Before Creating
# calls: it must be possible to read the registry *before* deciding whether a new
# ADR is warranted, and the check is worthless if reading it creates a file.
if [ "$TITLE" = "--list" ] || [ "$TITLE" = "-l" ]; then
    EXISTING=$(adr_titles)
    if [ -n "$EXISTING" ]; then
        echo "$EXISTING"
    else
        echo "No ADRs yet in $ADR_DIR."
    fi
    exit 0
fi

if [ -z "$TITLE" ]; then
    echo "Usage: $0 \"title of the decision\""
    echo "       $0 --list    # print existing ADR titles, create nothing"
    echo "Example: $0 \"Use PostgreSQL as primary database\""
    exit 1
fi

mkdir -p "$ADR_DIR"

# Surface existing ADR titles first — the caller is responsible for checking
# this list isn't already covering the same decision before a new file is
# created (see skills/shared/adr/SKILL.md § Check Before Creating).
EXISTING=$(adr_titles)
if [ -n "$EXISTING" ]; then
    echo "Existing ADRs — confirm this decision isn't already covered:"
    echo "$EXISTING"
    echo
fi

# Find the next sequential number. The pipeline legitimately produces no
# output on a fresh project with no existing ADRs — `grep` then exits 1,
# which under `set -o pipefail` would abort the whole script before the
# first ADR is ever written. `|| true` tolerates that empty case; LAST
# falls back to 0 via the ${LAST:-0} default below.
LAST=$( (adr_files | while IFS= read -r f; do
    basename "$f"
done | grep -oE '^(adr-)?[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1) || true)
# 10# forces base-10 interpretation — without it, a zero-padded value like
# "008" is parsed as octal by bash arithmetic and 8/9 are invalid octal
# digits, aborting the script from ADR-008 onward.
NEXT=$(printf "%04d" $(( 10#${LAST:-0} + 1 )))

# Build a URL-safe slug from the title
SLUG=$(echo "$TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9' '-' \
    | sed 's/^-//;s/-$//')

FILENAME="$ADR_DIR/${NEXT}-${SLUG}.md"
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
