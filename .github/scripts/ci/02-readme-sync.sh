#!/usr/bin/env bash
# 02-readme-sync.sh — Structural parity gate for EN ↔ pt-BR documentation pairs.
#
# WHAT THIS GATE CAN AND CANNOT DO
# --------------------------------
# Bash cannot compare meaning across two languages. What it *can* compare is the
# structural skeleton that a faithful translation is expected to preserve:
# the ordered sequence of headings, and per-section counts of lines, code
# fences, table rows and links. A translator who rewrites an EN section must
# almost always change one of those numbers on the pt-BR side too; a stale
# mirror keeps the old numbers and is caught here.
#
# Pairs are DISCOVERED, not hardcoded: every `*.pt-BR.md` in the tree must have
# an EN counterpart (same path with `.pt-BR.md` → `.md`), or this script fails.
#
# Escapes this gate (documented honestly, not a TODO): prose rewritten in place
# with the same line/fence/table/link shape, wrong-but-faithfully-translated
# facts (the `docs/agents.md` Model-column incident), and swapped cell values
# inside a table whose row count is unchanged. Those need a human or a
# translation-memory tool.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

# ── Per-section line-count tolerance ────────────────────────────────────────
# Measured on the current tree, every in-sync section is line-for-line identical
# (0% delta) — the translations are maintained as strict parallel mirrors. The
# tolerance below is therefore deliberately tight; it exists only to absorb the
# occasional reflow, not to make the check optional. Tolerance is the greater of
# 10% of the EN section and 3 lines (the floor keeps short sections usable).
# Raising these numbers weakens the gate — do not do it to silence a real drift;
# fix the translation or add a reviewed KNOWN_DRIFT entry instead.
SECTION_PCT=10
SECTION_FLOOR=3

# ── Known-drift baseline ────────────────────────────────────────────────────
# Entries here are REAL, already-known divergences that predate this gate. They
# are reported as warnings instead of failures so the gate can be turned on
# without a red CI, and each one MUST be deleted from this list the moment the
# translation catches up. Format: "<ptbr-path>:<check>" where <check> is one of
# headings | lines | fences | tables | links.
# Adding a new entry requires a reviewer — see .github/CODEOWNERS.
KNOWN_DRIFT=(
  # Empty. The gate passes on the real tree with no exemptions.
  # If you are about to add an entry: translating the section is almost always
  # cheaper than the review this list requires.
)

is_known_drift() {
  local key="$1" entry
  for entry in "${KNOWN_DRIFT[@]}"; do
    [ "$entry" = "$key" ] && return 0
  done
  return 1
}

# ── Structural extractor ────────────────────────────────────────────────────
# Emits one record per level-1/2 section:
#   <idx>|<heading-level-path>|<lines>|<fences>|<table-rows>|<links>
# Heading text is NOT compared (it is translated); only the ordered sequence of
# heading *levels* is, which is what a faithful translation must preserve.
# Fenced code blocks are tracked so that `# comment` lines inside a shell or
# gitignore block are never mistaken for headings.
extract() {
  awk '
    function flush(i) {
      printf "%d|%s|%d|%d|%d|%d\n", i, (hdr[i] == "" ? "-" : hdr[i]), \
             lines[i]+0, fences[i]+0, tables[i]+0, links[i]+0
    }
    BEGIN { fence = 0; sec = 0; maxsec = 0 }
    {
      line = $0
      if (line ~ /^[[:space:]]*(```|~~~)/) {
        fence = 1 - fence; fences[sec]++; lines[sec]++; next
      }
      if (fence == 0 && line ~ /^#+[[:space:]]/) {
        match(line, /^#+/); lvl = RLENGTH
        if (lvl <= 2) { sec++; if (sec > maxsec) maxsec = sec }
        hdr[sec] = hdr[sec] lvl ","
        lines[sec]++
        next
      }
      lines[sec]++
      if (fence == 0) {
        if (line ~ /^[[:space:]]*\|/) tables[sec]++
        tmp = line
        links[sec] += gsub(/\]\(/, "", tmp)
      }
    }
    END { for (i = 0; i <= maxsec; i++) flush(i) }
  ' "$1"
}

field() { echo "$1" | cut -d'|' -f"$2"; }

# Compare one numeric metric for one section; exact match required.
compare_exact() {
  local label="$1" en_v="$2" pt_v="$3" idx="$4"
  [ "$en_v" = "$pt_v" ] && return 0
  echo "    section $idx: $label differ (EN=$en_v, pt-BR=$pt_v)"
  return 1
}

check_pair() {
  local en="$1" ptbr="$2"
  local fail_headings=0 fail_lines=0 fail_fences=0 fail_tables=0 fail_links=0
  local en_rec pt_rec idx

  local en_data pt_data
  en_data="$(extract "$en")"
  pt_data="$(extract "$ptbr")"

  # 1. Heading skeleton — the ordered sequence of heading levels across the
  #    whole file. Catches added, removed, reordered or re-levelled sections.
  local en_skel pt_skel
  en_skel="$(echo "$en_data" | cut -d'|' -f2 | tr -d '\n')"
  pt_skel="$(echo "$pt_data" | cut -d'|' -f2 | tr -d '\n')"
  if [ "$en_skel" != "$pt_skel" ]; then
    echo "    heading skeleton differs"
    echo "      EN    : $en_skel"
    echo "      pt-BR : $pt_skel"
    fail_headings=1
  fi

  # 2. Per-section metrics. Only meaningful when the section count matches;
  #    when it does not, the skeleton failure above already says so.
  local en_secs pt_secs
  en_secs="$(echo "$en_data" | wc -l)"
  pt_secs="$(echo "$pt_data" | wc -l)"
  if [ "$en_secs" = "$pt_secs" ]; then
    while IFS= read -r en_rec; do
      idx="$(field "$en_rec" 1)"
      pt_rec="$(echo "$pt_data" | awk -F'|' -v i="$idx" '$1 == i')"
      [ -n "$pt_rec" ] || continue

      compare_exact "code fences" "$(field "$en_rec" 4)" "$(field "$pt_rec" 4)" "$idx" || fail_fences=1
      compare_exact "table rows"  "$(field "$en_rec" 5)" "$(field "$pt_rec" 5)" "$idx" || fail_tables=1
      compare_exact "links"       "$(field "$en_rec" 6)" "$(field "$pt_rec" 6)" "$idx" || fail_links=1

      local en_l pt_l delta tol
      en_l="$(field "$en_rec" 3)"
      pt_l="$(field "$pt_rec" 3)"
      delta=$(( en_l - pt_l )); delta=${delta#-}
      tol=$(( en_l * SECTION_PCT / 100 ))
      [ "$tol" -lt "$SECTION_FLOOR" ] && tol="$SECTION_FLOOR"
      if [ "$delta" -gt "$tol" ]; then
        echo "    section $idx: line counts differ by $delta (EN=$en_l, pt-BR=$pt_l, tolerance=$tol)"
        fail_lines=1
      fi
    done <<< "$en_data"
  fi

  # 3. Resolve failures against the known-drift baseline.
  local rc=0 warned=0 check
  for check in headings lines fences tables links; do
    local var="fail_$check"
    [ "${!var}" -eq 0 ] && continue
    if is_known_drift "$ptbr:$check"; then
      echo "  WARN  $ptbr: '$check' drift is in the known-drift baseline — fix the translation and drop the entry"
      warned=1
    else
      echo "  FAIL  $ptbr: '$check' parity broken"
      rc=1
    fi
  done

  if [ "$rc" -eq 0 ]; then
    if [ "$warned" -eq 1 ]; then
      echo "  OK*   $en ↔ $ptbr (passing only via the known-drift baseline)"
    else
      echo "  OK    $en ↔ $ptbr"
    fi
  fi
  return $rc
}

# ── Pair discovery ──────────────────────────────────────────────────────────
FAIL=0
FOUND=0
while IFS= read -r ptbr; do
  ptbr="${ptbr#./}"
  en="${ptbr%.pt-BR.md}.md"
  FOUND=$(( FOUND + 1 ))
  if [ ! -f "$en" ]; then
    echo "  FAIL  $ptbr has no EN counterpart (expected $en)"
    FAIL=1
    continue
  fi
  echo "─ $en ↔ $ptbr ─"
  check_pair "$en" "$ptbr" || FAIL=1
done < <(find . -name '*.pt-BR.md' -not -path './.git/*' -not -path './node_modules/*' | sort)

if [ "$FOUND" -eq 0 ]; then
  echo "No *.pt-BR.md files found — nothing to check."
fi

[ "$FAIL" -eq 0 ] && echo "readme-sync OK ✓"
exit $FAIL
