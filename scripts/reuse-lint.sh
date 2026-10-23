#!/usr/bin/env bash
# Enforces <docs>/development/reuse-guidelines.md against the working diff — <docs> is
# the docs write root, context_paths[0] (lib/docs-root.sh; `docs` by default).
# No-op (exit 0) when the registry does not exist — absence means no rule
# registered, not a failure. See skills/shared/reuse-guidelines/SKILL.md.
#
# Only `code-pattern` and `path-convention` rows are mechanically checked.
# `design-rule` and `review-rule` rows are parsed and skipped on purpose — they
# have no regex, by design, and are enforced only by the review gate.
#
# Columns: name | type | rule | detection | canonical_ref | scope | severity | added
# The last three are optional, so a five-column registry stays valid.
#
# What is checked: the branch's commits against its base, plus staged, unstaged
# and untracked changes. The Stop hook runs before anything is committed, so a
# committed-only diff would never see the change it exists to catch.
#
# Usage: reuse-lint.sh [--quiet] [--validate]
#   --quiet     no output, exit code only
#   --validate  check the registry itself (regex compiles, canonical_ref exists,
#               known type/severity) instead of the diff
# Exit: 0 clean (advisory findings do not fail), 1 blocking finding or invalid row.
set -euo pipefail

QUIET=0
VALIDATE=0
for arg in "$@"; do
  case "$arg" in
    --quiet) QUIET=1 ;;
    --validate) VALIDATE=1 ;;
  esac
done

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
DOCS_ROOT="docs"
# shellcheck source=scripts/lib/docs-root.sh
DOCS_ROOT_SH="$(dirname "${BASH_SOURCE[0]}")/lib/docs-root.sh"
if [ -f "$DOCS_ROOT_SH" ] && . "$DOCS_ROOT_SH"; then
    DOCS_ROOT="$(devteam_docs_root "$REPO_ROOT")"
fi
REGISTRY="$REPO_ROOT/$DOCS_ROOT/development/reuse-guidelines.md"
[ -f "$REGISTRY" ] || exit 0
cd "$REPO_ROOT"

_say() { [ "$QUIET" = "1" ] || printf '%s\n' "$*"; }

# Repo-controlled text reaches the agent's prompt through the Stop hook: cap it.
_cap() { local s="$1"; [ "${#s}" -gt 120 ] && s="${s:0:120}…"; printf '%s' "$s"; }

# Strip surrounding backticks/whitespace a Markdown table cell may carry.
_clean() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  s="${s#\`}"
  s="${s%\`}"
  printf '%s' "$s"
}

# grep exits 2 on an invalid pattern; 0/1 both mean it compiled. Back-references
# are refused: the registry is repo-controlled, and `\1` makes BSD grep exponential,
# which would hang every Stop.
_regex_ok() {
  local rc=0
  # shellcheck disable=SC1003 # a literal backslash in the pattern, not an escaped quote
  case "$1" in *'\'[1-9]*) return 1 ;; esac
  grep -E -e "$1" </dev/null >/dev/null 2>&1 || rc=$?
  [ "$rc" -ne 2 ]
}

# A scope is a comma-separated list of globs matched against the repo-relative
# path; `*` crosses directory separators, so `src/api/*` covers nested files.
# Empty or `*` means the whole repository.
_in_scope() {
  local path="$1" scope="$2" glob globs
  [ -z "$scope" ] && return 0
  # read -a splits without pathname expansion; an unquoted `for in $scope` would
  # expand `src/*` against the working tree.
  IFS=',' read -r -a globs <<<"$scope"
  for glob in "${globs[@]}"; do
    glob="$(_clean "$glob")"
    [ -z "$glob" ] && continue
    # shellcheck disable=SC2053 # intentional glob match against the registry's scope
    [[ "$path" == $glob ]] && return 0
  done
  return 1
}

NAMES=() TYPES=() DETECTS=() REFS=() SCOPES=() SEVS=() ADDEDS=() CELLS=()

# `\|` is how a Markdown table cell carries a literal pipe (a regex alternation).
# Swap it for a unit separator before splitting on `|`, then restore it unescaped.
SEP=$'\x1f'
while IFS= read -r raw; do
  row="${raw//\\|/$SEP}"
  pipes="${row//[^|]/}"
  IFS='|' read -r _ f_name f_type _ f_detect f_ref f_scope f_sev f_added _ <<<"$row"
  name="$(_clean "$f_name")"
  [ -z "$name" ] && continue
  [ "$name" = "name" ] && continue
  case "$name" in *---*) continue ;; esac
  NAMES+=("$(_cap "$name")")
  TYPES+=("$(_clean "$f_type")")
  detect="$(_clean "$f_detect")"
  DETECTS+=("${detect//$SEP/|}")
  REFS+=("$(_cap "$(_clean "$f_ref")")")
  scope="$(_clean "${f_scope:-}")"
  [ "$scope" = "*" ] && scope=""
  SCOPES+=("${scope//$SEP/|}")
  SEVS+=("$(_clean "${f_sev:-}")")
  ADDEDS+=("$(_clean "${f_added:-}")")
  CELLS+=("$((${#pipes} - 1))")
done < <(grep '^|' "$REGISTRY" || true)

[ "${#NAMES[@]}" -gt 0 ] || exit 0

if [ "$VALIDATE" = "1" ]; then
  PROBLEMS=0
  _bad() { PROBLEMS=$((PROBLEMS + 1)); _say "[reuse-lint] INVALID — rule '$1': $2"; }
  for i in "${!NAMES[@]}"; do
    n="${NAMES[$i]}" t="${TYPES[$i]}" d="${DETECTS[$i]}" r="${REFS[$i]}"
    # An unescaped `|` inside a regex shifts every later column; it shows as extra cells.
    [ "${CELLS[$i]}" -gt 8 ] && _bad "$n" "row has ${CELLS[$i]} cells (max 8) — escape a literal | as \\|"
    case "$t" in
      code-pattern)
        if [ -z "$d" ]; then _bad "$n" "code-pattern has an empty detection"
        elif ! _regex_ok "$d"; then _bad "$n" "detection is not a valid extended regex (back-references are not allowed)"; fi ;;
      path-convention)
        case "$d" in path:?*=\>?*) : ;; *) _bad "$n" "detection must be path:<name-glob>=><required-dir>" ;; esac ;;
      design-rule|review-rule) : ;;
      *) _bad "$n" "unknown type '$t'" ;;
    esac
    ref_path="${r%%#*}"
    case "$ref_path" in
      /*|..|../*|*/../*|*/..) _bad "$n" "canonical_ref must be a repo-relative path without .."; ref_path="" ;;
    esac
    if [ -n "$ref_path" ] && [ ! -e "$ref_path" ]; then
      _bad "$n" "canonical_ref '$ref_path' does not exist"
    fi
    case "${SEVS[$i]}" in ""|blocking|advisory) : ;; *) _bad "$n" "severity must be blocking or advisory" ;; esac
    a="${ADDEDS[$i]}"
    if [ -n "$a" ] && ! [[ "$a" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
      _bad "$n" "added must be YYYY-MM-DD"
    fi
  done
  [ "$PROBLEMS" -gt 0 ] && exit 1
  exit 0
fi

# --- Collect added lines --------------------------------------------------------
TMP="$(mktemp -d 2>/dev/null || mktemp -d -t reuselint)"
trap 'rm -rf "$TMP"' EXIT
PATHS_F="$TMP/paths" LINES_F="$TMP/lines" FILES_F="$TMP/files"
: >"$PATHS_F"; : >"$LINES_F"; : >"$FILES_F"

# `.dev-team-agents/` is the installed framework — immutable, replaced on update, and
# materialized as untracked copies in some bind modes. It is never project code.
PATHSPEC=(-- . ':(exclude).dev-team-agents')
UNTRACKED_MAX_BYTES=1048576

# The user's diff settings (noprefix, mnemonicPrefix, external diff, textconv) are
# pinned off; and the file path never comes from a diff header — git C-quotes names
# with quotes, backslashes or control characters there. Files are listed with -z
# and diffed one by one, so the path is exactly the one git listed.
GIT_DIFF=(git -c core.quotepath=false diff --no-ext-diff --no-textconv --no-color --unified=0)

# Appends the added lines of one file's diff (stdin) to the path/line files. Values go
# through ENVIRON, not `awk -v`, which would interpret backslashes in a file name.
_record_hunks() {
  RL_F="$1" RL_PF="$PATHS_F" RL_LF="$LINES_F" awk '
    BEGIN { f = ENVIRON["RL_F"]; pf = ENVIRON["RL_PF"]; lf = ENVIRON["RL_LF"] }
    /^diff --git / { h = 0; next }
    /^@@/ { h = 1; next }
    h && /^\+/ { print f >> pf; print substr($0, 2) >> lf }
  '
}

# _record_range <rev-args...> — every non-deleted file the range changes.
_record_range() {
  local f
  while IFS= read -r -d '' f; do
    case "$f" in *$'\n'*) continue ;; esac
    printf '%s\n' "$f" >>"$FILES_F"
    "${GIT_DIFF[@]}" "$@" -- "$f" 2>/dev/null | _record_hunks "$f" || true
  done < <("${GIT_DIFF[@]}" --name-only -z --diff-filter=d "$@" "${PATHSPEC[@]}" 2>/dev/null || true)
}

DIFF_RANGE="${REUSE_LINT_DIFF_RANGE:-}"
if [ -z "$DIFF_RANGE" ]; then
  # A repository without origin/HEAD (one wired with `git remote add`) is common;
  # under `set -o pipefail` a bare symbolic-ref used to abort the whole lint.
  BASE="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if [ -z "$BASE" ]; then
    for cand in origin/main origin/master main master; do
      if git rev-parse --verify --quiet "$cand^{commit}" >/dev/null 2>&1; then BASE="$cand"; break; fi
    done
  fi
  [ -n "$BASE" ] && DIFF_RANGE="${BASE}...HEAD"
fi

case "$DIFF_RANGE" in -*) DIFF_RANGE="" ;; esac
[ -n "$DIFF_RANGE" ] && _record_range "$DIFF_RANGE"
if git rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
  _record_range HEAD
else
  _record_range --cached
fi

SKIPPED_LARGE=0 SKIPPED_NAMES=""
while IFS= read -r -d '' f; do
  # A symlink is never followed: an untracked link could point outside the repository.
  [ -L "$f" ] && continue
  [ -f "$f" ] || continue
  case "$f" in *$'\n'*) continue ;; esac
  printf '%s\n' "$f" >>"$FILES_F"
  grep -Iq . "$f" 2>/dev/null || continue
  if [ "$(wc -c <"$f" | tr -d ' ')" -gt "$UNTRACKED_MAX_BYTES" ]; then
    SKIPPED_LARGE=$((SKIPPED_LARGE + 1))
    [ "$SKIPPED_LARGE" -le 5 ] && SKIPPED_NAMES="$SKIPPED_NAMES $f"
    continue
  fi
  RL_F="$f" RL_PF="$PATHS_F" RL_LF="$LINES_F" awk '
    BEGIN { f = ENVIRON["RL_F"]; pf = ENVIRON["RL_PF"]; lf = ENVIRON["RL_LF"] }
    { print f >> pf; print >> lf }' "$f"
done < <(git ls-files -z --others --exclude-standard "${PATHSPEC[@]}" 2>/dev/null || true)
if [ "$SKIPPED_LARGE" -gt 0 ]; then
  _say "[reuse-lint] SKIPPED — $SKIPPED_LARGE untracked text file(s) over ${UNTRACKED_MAX_BYTES} bytes not scanned:$SKIPPED_NAMES"
fi

# --- Check ----------------------------------------------------------------------
BLOCKING=0
REPORTED="$TMP/reported"
: >"$REPORTED"

_report() {
  local sev="$1" msg="$2"
  grep -Fxq -- "$msg" "$REPORTED" 2>/dev/null && return 0
  printf '%s\n' "$msg" >>"$REPORTED"
  if [ "$sev" = "advisory" ]; then
    _say "[reuse-lint] ADVISORY — $msg"
  else
    BLOCKING=$((BLOCKING + 1))
    _say "[reuse-lint] BLOCKED — $msg"
  fi
}

for i in "${!NAMES[@]}"; do
  n="${NAMES[$i]}" t="${TYPES[$i]}" d="${DETECTS[$i]}" r="${REFS[$i]}" s="${SCOPES[$i]}" sev="${SEVS[$i]}"
  case "$t" in
    code-pattern)
      [ -n "$d" ] || continue
      if ! _regex_ok "$d"; then
        _report blocking "rule '$n' has an invalid detection regex — fix the registry row (run reuse-lint.sh --validate)"
        continue
      fi
      [ -s "$LINES_F" ] || continue
      # Matching line numbers → their paths in one awk pass, deduplicated.
      while IFS= read -r p; do
        [ -n "$p" ] || continue
        _in_scope "$p" "$s" || continue
        _report "$sev" "$p: matches '$n' rule, use $r instead"
      done < <(grep -anE -e "$d" "$LINES_F" 2>/dev/null | cut -d: -f1 | awk 'NR == FNR { want[$1] = 1; next } FNR in want' - "$PATHS_F" | sort -u || true)
      ;;
    path-convention)
      name_glob="${d#path:}"
      name_glob="${name_glob%%=>*}"
      required_dir="${d#*=>}"
      [ -n "$name_glob" ] && [ -n "$required_dir" ] || continue
      while IFS= read -r p; do
        [ -n "$p" ] || continue
        _in_scope "$p" "$s" || continue
        base="$(basename "$p")"
        # shellcheck disable=SC2053 # intentional glob match against the registry's name-glob/dir-prefix
        if [[ "$base" == $name_glob ]] && [[ "$p" != $required_dir* ]]; then
          _report "$sev" "$p: violates '$n' path-convention, must live under $required_dir"
        fi
      done < <(sort -u "$FILES_F")
      ;;
  esac
done

[ "$BLOCKING" -gt 0 ] && exit 1
exit 0
