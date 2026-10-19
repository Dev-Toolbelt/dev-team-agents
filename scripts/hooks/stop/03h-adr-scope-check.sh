#!/usr/bin/env bash
# Stop sub-script: reminds the agent (non-blocking) when the session touched a path
# that an Accepted ADR declares it governs, through its `**Applies to:**` line — see
# skills/shared/adr/SKILL.md § Applies To.
#
# 03e-adr-gap-check.sh catches a decision with no ADR; this one catches the opposite
# gap: code changing under an existing decision nobody re-read. An ADR whose own file
# was touched this session is skipped — whoever edited it has it in view.
#
# Patterns are globs (`*`, `?`) converted to anchored regular expressions and matched
# against repo-relative paths by grep; `*` also crosses `/`. They are never evaluated,
# expanded against the disk, or handed to bash's own glob matcher.
#
# Exit 2 reaches the agent in the same session, once per distinct set of matches
# (`lib/warn-once.sh`, marker `.adr-scope-warned`). Claude Code and Codex surface the
# stderr; the opencode plugin only logs it — the same accepted gap as 03e.
set -euo pipefail

[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0

LIB_DIR="$(dirname "${BASH_SOURCE[0]}")/../lib"
if [ "${DEVTEAM_TOUCHED_COMPUTED:-0}" != "1" ]; then
    # shellcheck source=scripts/hooks/lib/touched-paths.sh
    . "$LIB_DIR/touched-paths.sh"
    DEVTEAM_TOUCHED_PATHS="$(devteam_compute_touched_paths || true)"
fi
[ -n "${DEVTEAM_TOUCHED_PATHS:-}" ] || exit 0

# new-adr.sh owns the ADR directory and its naming schemes; ask it rather than
# re-deriving them. It refuses a symlinked directory, and so does this check.
NEW_ADR="$(dirname "${BASH_SOURCE[0]}")/../../new-adr.sh"
[ -f "$NEW_ADR" ] || exit 0
ADR_DIR="$(cd "$REPO_ROOT" && bash "$NEW_ADR" --dir 2>/dev/null)" || exit 0
[ -n "$ADR_DIR" ] && [ -d "$REPO_ROOT/$ADR_DIR" ] && [ ! -L "$REPO_ROOT/$ADR_DIR" ] || exit 0

MAX_PATTERNS=50
MAX_PATTERN_LEN=200
MAX_LINE_LEN=2000
# A literal backtick: the patterns are the code spans of the Markdown line.
TICK=$'\x60'
MATCHES=""

# Repository text reaches the agent's context: drop C0 controls (newline kept as the line
# separator) and DEL, then the C1 controls and bidi overrides as UTF-8 byte sequences, and
# cap each line's length.
sanitize() {
    LC_ALL=C tr -d '\000-\011\013-\037\177' |
        LC_ALL=C sed $'s/\xc2[\x80-\x9f]//g; s/\xe2\x80[\xaa-\xae]//g; s/\xe2\x81[\xa6-\xa9]//g' |
        cut -c1-200
}

# A glob becomes an anchored ERE: every regex metacharacter is escaped, `*` becomes `.*`
# and `?` becomes `.`. Matching then runs in grep's regex engine, never in bash's glob
# matcher, which backtracks exponentially on patterns like `*a*a*a*a*b` (bash 3.2) or
# nested `+(…)` groups (bash 4.1+ inside `[[`) and would stall every Stop.
glob_to_ere() {
    printf '^%s$' "$(printf '%s' "$1" | LC_ALL=C sed -e 's/[].[^$\\+(){}|]/\\&/g' -e 's/\*/.*/g' -e 's/?/./g')"
}

for adr in "$REPO_ROOT/$ADR_DIR"/*.md; do
    [ -f "$adr" ] && [ ! -L "$adr" ] || continue
    name="$(basename "$adr")"
    # The filename is printed to the agent: only printable ASCII is accepted, which rules
    # out newlines, escapes and bidi overrides alike. `|` is the record separator below.
    # The trailing `x` keeps command substitution from stripping a leftover newline.
    [ "$(printf '%s' "$name" | LC_ALL=C tr -d ' -~'; printf x)" = x ] || continue
    case "$name" in *'|'*) continue ;; esac
    printf '%s\n' "$name" | grep -qE '^((adr|ADR)-)?[0-9]+-' || continue
    rel="$ADR_DIR/$name"
    printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qxF "$rel" && continue
    grep -qE '^\*\*Status(:\*\*|\*\*:)[[:space:]]*Accepted' "$adr" 2>/dev/null || continue
    line="$(grep -m1 -E '^\*\*Applies to(:\*\*|\*\*:)' "$adr" 2>/dev/null || true)"
    [ -n "$line" ] || continue
    line="${line:0:$MAX_LINE_LEN}"

    exprs=()
    while IFS= read -r p; do
        [ -n "$p" ] && [ "${#p}" -le "$MAX_PATTERN_LEN" ] || continue
        exprs+=(-e "$(glob_to_ere "$p")")
        [ "${#exprs[@]}" -ge $((MAX_PATTERNS * 2)) ] && break
    done < <(printf '%s\n' "$line" | grep -oE "${TICK}[^${TICK}]+${TICK}" | tr -d "$TICK" | tr -d '\000-\011\013-\037')
    [ "${#exprs[@]}" -gt 0 ] || continue

    hits="$(printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -E "${exprs[@]}" 2>/dev/null | head -n 10 || true)"
    [ -n "$hits" ] || continue

    title="$(grep -m1 '^# ' "$adr" 2>/dev/null | sed 's/^# //' | sanitize | tr -d '|' || true)"
    MATCHES="${MATCHES}${rel}|${title:-$name}"$'\n'
    while IFS= read -r h; do
        [ -n "$h" ] && MATCHES="${MATCHES}  - ${h}"$'\n'
    done < <(printf '%s\n' "$hits" | sanitize)
done

[ -n "$MATCHES" ] || exit 0

SIGNATURE="$(printf '%s' "$MATCHES" | git hash-object --stdin 2>/dev/null || true)"
# shellcheck source=scripts/hooks/lib/warn-once.sh
. "$LIB_DIR/warn-once.sh"
devteam_warn_once .adr-scope-warned "$SIGNATURE" || exit 0

{
    printf '\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
    printf ' CODE GOVERNED BY AN ADR CHANGED\n'
    printf '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
    printf ' This session touched paths an Accepted ADR declares it\n'
    printf ' governs. Re-read each ADR and confirm the change still\n'
    printf ' follows it — or amend or supersede the ADR.\n\n'
    printf '%s' "$MATCHES" | while IFS= read -r m; do
        case "$m" in
            "  - "*) printf '%s\n' "$m" ;;
            *) printf ' %s — %s\n' "${m%%|*}" "${m#*|}" ;;
        esac
    done
    printf '\n See skills/shared/adr/SKILL.md § Applies To.\n'
    printf '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n'
} >&2
exit 2
