#!/usr/bin/env bash
# archive-index.sh — Move fingerprint sections older than 90 days out of
# docs/reports/_index.md into quarterly archives (_index-archive-YYYY-Q.md).
#
# What moves:  whole dated sections — a `## YYYY-MM-DD — <title>` (or `### …`)
#              header, its intro prose, its `### <Category>` sub-headings and
#              every `- \`slug\` — **SEVERITY** — … — [report](path)` entry under
#              them. A section ends at the next header of the same or higher
#              level, so nested category sub-headings travel with their section.
# What stays:  the whole preamble — title, How It Works, Fingerprint Convention,
#              Statistics, the `## Registered Fingerprints` heading and its
#              format comment — plus every section newer than the cutoff.
#
# Archives keep the `- \`slug\`` line format verbatim, so
# helpers/check-fingerprint-uniqueness.sh still sees archived slugs and the bank's
# uniqueness guarantee stays global after rotation.
#
# Usage:
#   bash helpers/archive-index.sh --dry-run   # print the plan, touch nothing
#   bash helpers/archive-index.sh             # perform the rotation
#
# Idempotent: a date already present in its quarterly archive is never appended
# twice, and a moved section is gone from _index.md, so re-runs are no-ops.
# Safe when nothing is older than 90 days (the common case) — the index is not
# rewritten at all.
#
# Exit 0 always (archival is non-destructive; failures degrade to a skip).
set -euo pipefail

# Anchored to the repo, not the caller's cwd: a hook or CI job invoking this from
# elsewhere must not silently degrade into a "nothing found, exit 0" no-op.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$REPO_ROOT/docs/reports"
INDEX_FILE="$REPORTS_DIR/_index.md"
DRY_RUN=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        *) echo "→ Unknown argument: $arg (supported: --dry-run)" >&2; exit 0 ;;
    esac
done

if [ ! -f "$INDEX_FILE" ]; then
    echo "→ ${INDEX_FILE#"$REPO_ROOT"/} not found; nothing to archive." >&2
    exit 0
fi

# Cutoff = 90 days ago, YYYY-MM-DD. GNU and BSD date both handled.
CUTOFF=$(date -d "90 days ago" +%Y-%m-%d 2>/dev/null || date -v-90d +%Y-%m-%d 2>/dev/null || true)
if [ -z "$CUTOFF" ]; then
    echo "→ Could not compute cutoff date; skipping archive." >&2
    exit 0
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Split the index into the part that stays ($WORK/keep) and one file per dated
# section older than the cutoff ($WORK/section-<date>). ISO dates compare
# correctly as strings, so a plain `<` is a valid date comparison.
awk -v cutoff="$CUTOFF" -v work="$WORK" '
function header_level(line,   n) {
    n = 0
    while (substr(line, n + 1, 1) == "#") n++
    return n
}
BEGIN { archiving = 0; cur_level = 0 }
{
    if ($0 ~ /^#+ /) {
        lvl = header_level($0)
        title = substr($0, lvl + 2)
        # A section ends at the next header of the same or higher level.
        if (archiving && lvl <= cur_level) archiving = 0
        if (!archiving && title ~ /^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]/) {
            d = substr(title, 1, 10)
            if (d < cutoff) {
                archiving  = 1
                cur_level  = lvl
                cur_date   = d
                out        = work "/section-" d
                print d >> (work "/dates")
            }
        }
    }
    if (archiving) print > out; else print > (work "/keep")
}
' "$INDEX_FILE"

OLD_DATES=()
if [ -f "$WORK/dates" ]; then
    while IFS= read -r d; do
        [ -n "$d" ] && OLD_DATES+=("$d")
    done < <(sort -u "$WORK/dates")
fi

if [ "${#OLD_DATES[@]}" -eq 0 ]; then
    echo "✓ No entries older than 90 days (cutoff $CUTOFF) in ${INDEX_FILE#"$REPO_ROOT"/}."
    exit 0
fi

archive_file_for() {
    local entry_date="$1"
    local year="${entry_date:0:4}"
    local month="${entry_date:5:2}"
    local quarter=$(( (10#$month - 1) / 3 + 1 ))
    echo "$REPORTS_DIR/_index-archive-${year}-Q${quarter}.md"
}

echo "→ ${#OLD_DATES[@]} dated section(s) older than $CUTOFF:"
for entry_date in "${OLD_DATES[@]}"; do
    archive_file=$(archive_file_for "$entry_date")
    entries=$(grep -cE "^- \`[a-z][a-z0-9-]+" "$WORK/section-$entry_date" 2>/dev/null || true)
    echo "    $entry_date — ${entries:-0} fingerprint entr(ies) → ${archive_file#"$REPO_ROOT"/}"
done

if $DRY_RUN; then
    KEEP_LINES=$(wc -l < "$WORK/keep" | tr -d ' ')
    CUR_LINES=$(wc -l < "$INDEX_FILE" | tr -d ' ')
    echo "→ Dry-run: no files modified. ${INDEX_FILE#"$REPO_ROOT"/} would go from $CUR_LINES to $KEEP_LINES lines."
    exit 0
fi

for entry_date in "${OLD_DATES[@]}"; do
    archive_file=$(archive_file_for "$entry_date")
    year="${entry_date:0:4}"
    month="${entry_date:5:2}"
    quarter=$(( (10#$month - 1) / 3 + 1 ))

    if [ ! -f "$archive_file" ]; then
        {
            echo "# Fingerprint Archive — ${year} Q${quarter}"
            echo ""
            echo "Fingerprint sections rotated out of \`_index.md\` by \`helpers/archive-index.sh\`."
            echo "Entries here remain part of the bank: they are still checked for uniqueness and"
            echo "must not be re-proposed."
            echo ""
        } > "$archive_file"
    fi

    # Idempotency guard: never append a date that is already archived.
    if grep -qE "^#+ ${entry_date}( |$)" "$archive_file" 2>/dev/null; then
        echo "→ $entry_date already present in ${archive_file#"$REPO_ROOT"/}; skipping append (section still removed from index)."
    else
        cat "$WORK/section-$entry_date" >> "$archive_file"
        echo "" >> "$archive_file"
        echo "→ Archived $entry_date → ${archive_file#"$REPO_ROOT"/}"
    fi
done

# Drop the trailing blank lines a removed tail section leaves behind (interior
# blank lines are preserved — only the tail is trimmed).
awk '
    { lines[NR] = $0 }
    END {
        last = 0
        for (i = 1; i <= NR; i++) if (lines[i] ~ /[^[:space:]]/) last = i
        for (i = 1; i <= last; i++) print lines[i]
    }
' "$WORK/keep" > "$WORK/keep.trimmed"

mv "$WORK/keep.trimmed" "$INDEX_FILE"

echo "✓ Archive complete. $(wc -l < "$INDEX_FILE" | tr -d ' ') lines remain in ${INDEX_FILE#"$REPO_ROOT"/}."
