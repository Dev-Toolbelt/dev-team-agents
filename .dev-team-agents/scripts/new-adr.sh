#!/usr/bin/env bash
# Creates a numbered ADR file with MADR template in the project's ADR directory
# and appends its row to the ADR index (<adr-dir>/README.md).
# Usage: bash .dev-team-agents/scripts/new-adr.sh "title of the decision"
#        bash .dev-team-agents/scripts/new-adr.sh --list
#        bash .dev-team-agents/scripts/new-adr.sh --dir
set -euo pipefail

# Newlines and control characters would break the sed below after the redirect
# had already created the file, leaving an empty ADR with no index row.
TITLE="$(printf '%s' "${1:-}" | tr -d '\000-\037')"

# The ADR directory is resolved here and nowhere else — skills/shared/adr/SKILL.md
# § File Location points every reader at `--dir`. It lives under the project's docs
# write root, the first `context_paths` entry (lib/docs_root.py; `docs` when there is
# no project.json, no Python or no helper beside this script). <root>/development/adrs/
# is the default; a project that already keeps its ADRs in <root>/adr/ is followed
# rather than forked into a second series, which is how numbers collided before.
# In the gated docs layout (project.json `docs_layout`, the `adr` key of
# lib/doc-layouts.json) a project with no ADRs yet starts <root>/adr/ instead, and
# names its files ADR-NNNN-slug.md.
# A symlinked directory is never followed: a cloned repository could otherwise
# send the new ADR and its index row anywhere on disk. index_lint.py:adr_dir()
# applies the same rule, so the writer and the checker agree on the directory.
DOCS_ROOT="docs"
DOCS_ROOT_SH="$(dirname "${BASH_SOURCE[0]}")/lib/docs-root.sh"
# shellcheck source=scripts/lib/docs-root.sh
if [ -f "$DOCS_ROOT_SH" ] && . "$DOCS_ROOT_SH"; then
    DOCS_ROOT="$(devteam_docs_root "$PWD")"
fi
real_dir() { [ -d "$1" ] && [ ! -L "$1" ]; }
NEW_SERIES_PREFIX=""
SYMLINK_CHECK=""
IFS='/' read -r -a DOCS_PARTS <<<"$DOCS_ROOT"
for part in "${DOCS_PARTS[@]}"; do
    [ -n "$part" ] || continue
    SYMLINK_CHECK="${SYMLINK_CHECK:+$SYMLINK_CHECK/}$part"
    if [ -L "$SYMLINK_CHECK" ]; then
        echo "Error: $SYMLINK_CHECK is a symlink — refusing to read or write ADRs through it." >&2
        exit 1
    fi
done
for d in "$DOCS_ROOT/development" "$DOCS_ROOT/development/adrs" "$DOCS_ROOT/adr"; do
    if [ -L "$d" ]; then
        echo "Error: $d is a symlink — refusing to read or write ADRs through it." >&2
        exit 1
    fi
done
# The directory that already holds ADRs wins; an empty one does not, or an empty
# <root>/development/adrs/ would fork a populated <root>/adr/ into a second series.
has_adrs() {
    local f
    real_dir "$1" || return 1
    for f in "$1"/*.md; do
        case "$(basename "$f")" in [0-9]*-*.md|adr-[0-9]*-*.md|ADR-[0-9]*-*.md) return 0 ;; esac
    done
    return 1
}
# Asked only when neither directory holds ADRs (the elif below), and Python only when
# project.json mentions "gated" at all — the same pre-filter as the read-only docs guard.
is_gated_layout() {
    local text=""
    [ -f "$PWD/.dev-team-agents/project.json" ] || return 1
    IFS= read -r -d '' text < "$PWD/.dev-team-agents/project.json" || true
    case "$text" in *gated*) ;; *) return 1 ;; esac
    command -v devteam_docs_layout >/dev/null 2>&1 || return 1
    [ "$(devteam_docs_layout "$PWD")" = "gated" ]
}
if has_adrs "$DOCS_ROOT/development/adrs"; then
    ADR_DIR="$DOCS_ROOT/development/adrs"
elif has_adrs "$DOCS_ROOT/adr"; then
    ADR_DIR="$DOCS_ROOT/adr"
elif is_gated_layout; then
    ADR_DIR="$DOCS_ROOT/adr"
    NEW_SERIES_PREFIX="ADR-"
elif real_dir "$DOCS_ROOT/development/adrs" || ! real_dir "$DOCS_ROOT/adr"; then
    ADR_DIR="$DOCS_ROOT/development/adrs"
else
    ADR_DIR="$DOCS_ROOT/adr"
fi
INDEX="$ADR_DIR/README.md"

# Three naming schemes are recognised in exactly ONE place: the historical
# `adr-NNN-slug.md`, the default `NNNN-slug.md`, and `ADR-NNNN-slug.md` used by
# projects that predate the default. One glob filtered by basename, not one glob
# per scheme: on a case-insensitive filesystem `adr-*` also matches `ADR-*` and
# every file would be listed twice.
#
# Tolerates a missing directory on purpose: the guard below skips a glob that did
# not expand, so `--list` answers a question without creating anything.
adr_files() {
    local f
    for f in "$ADR_DIR"/*.md; do
        [ -f "$f" ] && [ ! -L "$f" ] || continue
        basename "$f" | grep -qE '^((adr|ADR)-)?[0-9]+-' || continue
        printf '%s\n' "$f"
    done
}

if [ "$TITLE" = "--dir" ]; then
    echo "$ADR_DIR"
    exit 0
fi

adr_titles() {
    local f
    adr_files | while IFS= read -r f; do
        # Repository text reaches the agent's context — strip control characters.
        grep -h '^# ' "$f" 2>/dev/null | tr -d '\000-\011\013-\037' || true
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
done | grep -oE '^((adr|ADR)-)?[0-9]+' | grep -oE '[0-9]+' | sort -n | tail -1) || true)
# 10# forces base-10 interpretation — without it, a zero-padded value like
# "008" is parsed as octal by bash arithmetic and 8/9 are invalid octal
# digits, aborting the script from ADR-008 onward.
NEXT=$(printf "%04d" $(( 10#${LAST:-0} + 1 )))

# Build a URL-safe slug from the title
SLUG=$(echo "$TITLE" \
    | tr '[:upper:]' '[:lower:]' \
    | tr -cs 'a-z0-9' '-' \
    | sed 's/^-//;s/-$//')
if [ -z "$SLUG" ]; then
    echo "Error: the title must contain at least one ASCII letter or digit." >&2
    exit 1
fi

# Continue the scheme the directory already uses; a new series gets the layout's
# default (`ADR-` in the gated layout, none in the development layout).
# A loop, not `| grep -q`: under pipefail an early-exiting grep can SIGPIPE the
# producer and report "no match" for a directory that has one.
PREFIX="$NEW_SERIES_PREFIX"
while IFS= read -r f; do
    case "$(basename "$f")" in ADR-*) PREFIX="ADR-" ;; esac
done < <(adr_files)
FILENAME="$ADR_DIR/${PREFIX}${NEXT}-${SLUG}.md"
if [ -e "$FILENAME" ] || [ -L "$FILENAME" ]; then
    echo "Error: $FILENAME already exists." >&2
    exit 1
fi
TODAY=$(date +%Y-%m-%d)

# Locate the template relative to this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/../templates/adr-template.md"

if [ ! -f "$TEMPLATE" ]; then
    echo "Error: ADR template not found at $TEMPLATE" >&2
    exit 1
fi

# Escape the characters special in a sed replacement (\, &) and our delimiter (|).
TITLE_ESCAPED=$(printf '%s' "$TITLE" | sed -e 's/[\&|]/\\&/g')

sed \
    -e "s/\[NUMBER\]/$NEXT/g" \
    -e "s|\[Title\]|$TITLE_ESCAPED|g" \
    -e "s/\[YYYY-MM-DD\]/$TODAY/g" \
    "$TEMPLATE" > "$FILENAME"

echo "Created: $FILENAME"

# The index row is part of creating the ADR — an ADR with no row is one the
# keyword lookup in skills/shared/project-context/SKILL.md never finds.
# - No index yet: create it with a placeholder row for every ADR that already
#   exists, then the new one — a one-row index would hide the whole series,
#   because readers fall back to listing files only when there is no index.
# - Index with a `## Index` table: the row goes after the table's last row,
#   wherever the table sits in the file. Never regenerated.
# - Any other README.md (prose, a symlink): left untouched, with a notice.
# shellcheck disable=SC2016 # the backticks are literal Markdown, not command substitution
ROW=$(printf '| `%s` | Proposed | [keywords] | [read it when] |' "$(basename "$FILENAME")")
if [ -L "$INDEX" ]; then
    echo "Not indexed: $INDEX is a symlink — add this row by hand: $ROW" >&2
    exit 0
fi
if [ ! -f "$INDEX" ]; then
    {
        printf '# Architecture Decision Records\n\n## Index\n\n'
        printf '| ADR | Status | Keywords | Read it when |\n|-----|--------|----------|--------------|\n'
        adr_files | while IFS= read -r f; do
            [ "$f" = "$FILENAME" ] && continue
            # shellcheck disable=SC2016 # the backticks are literal Markdown, not command substitution
            printf '| `%s` | [status] | [keywords] | [read it when] |\n' "$(basename "$f")"
        done
        printf '%s\n' "$ROW"
    } > "$INDEX"
    echo "Indexed: $INDEX created — fill in the [status], [keywords] and [read it when] cells"
    exit 0
fi
if ! grep -qE '^## Index[[:space:]]*$' "$INDEX"; then
    echo "Not indexed: $INDEX has no '## Index' table — add this row by hand: $ROW" >&2
    exit 0
fi
TMP_INDEX="$(mktemp "$INDEX.XXXXXX")"
trap 'rm -f "$TMP_INDEX"' EXIT
awk -v row="$ROW" '
    { lines[NR] = $0 }
    /^## Index[[:space:]]*$/ && !heading { heading = NR }
    heading && NR > heading && !done {
        if ($0 ~ /^#+[[:space:]]/) { done = 1 }
        else if ($0 ~ /^\|/) { last = NR; intable = 1 }
        else if (intable) { done = 1 }
    }
    END {
        for (i = 1; i <= NR; i++) {
            print lines[i]
            if (i == heading && !last) {
                print ""
                print "| ADR | Status | Keywords | Read it when |"
                print "|-----|--------|----------|--------------|"
                print row
            }
            if (i == last) print row
        }
    }
' "$INDEX" > "$TMP_INDEX"
# Copy back rather than mv: mktemp creates the file 0600, and the index keeps
# its own mode and inode.
cat "$TMP_INDEX" > "$INDEX"
rm -f "$TMP_INDEX"
trap - EXIT
echo "Indexed: $INDEX — fill in the [keywords] and [read it when] cells"
