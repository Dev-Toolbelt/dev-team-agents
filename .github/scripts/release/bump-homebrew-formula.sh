#!/usr/bin/env bash
# bump-homebrew-formula.sh — rewrite the `url` and `sha256` lines of the devteam
# Homebrew formula to a released tag and the digest of that tag's real tarball.
#
# WHY THIS IS A SCRIPT AND NOT A WORKFLOW STEP
# ============================================
# This logic used to live inline in two `run:` blocks of
# .github/workflows/release.yml ("Update packaging/homebrew/devteam.rb" and
# "Verify the edit landed correctly"). Inline in YAML it could only ever be
# exercised by pushing a real version tag, so it had never executed once — and
# the case it was actually written for (a formula that already carries a real
# tag and digest from a previous release, being rewritten to a new one) was the
# least likely of all to be right. Extracted here it has an interface, and
# tests/test_release_bump.py drives it against a copy of the real formula.
#
# The sed anchors came from those inline blocks, and so did the comments
# explaining why they are shaped that way. Having an interface made them
# reviewable, and review found defects the extraction had carried over intact.
# Each fix is explained at its site: the write is staged and renamed into place
# so a failed run cannot leave a half-rewritten formula; the repository name is
# escaped before it is interpolated into the ERE; the url verification is
# repo-qualified; a formula where more than one line would be rewritten is
# refused instead of rewritten on a guess; and the writability check tests the
# directory both real operations need rather than the file neither does.
#
# USAGE
# =====
#   bump-homebrew-formula.sh --tag <vX.Y.Z> --sha256 <64-hex> \
#                            --formula <path> [--repo <owner/repo>]
#
# --repo defaults to $GITHUB_REPOSITORY (which Actions always sets). It is part
# of the `url` match anchor and of the url verification, so it is required
# rather than guessed.
#
# What protects the file against a WRONG --repo is that verification being
# repo-qualified. An earlier comment here claimed a wrong owner/repo "makes the
# rewrite match nothing, and the failure would then surface as a confusing
# verification error" — it did not. The rewrite indeed matched nothing, but the
# verification grepped for `archive/refs/tags/<tag>.tar.gz` and
# `sha256 "<digest>"`, and neither of those carries the repository. So bumping a
# formula whose url ALREADY pointed at the requested tag left that url untouched,
# rewrote the digest under it (the sha256 anchor is repo-independent), found both
# strings present and exited 0 — publishing one repository's digest against
# another repository's tarball. The url check below matches the whole
# `url "https://github.com/<repo>/archive/refs/tags/<tag>.tar.gz"` line instead.
#
# Idempotent by construction: the anchors match a placeholder, a previous real
# tag/digest, or the values being written, so a second run with the same inputs
# leaves the file byte-identical and still exits 0.
set -euo pipefail

SELF="$(basename "$0")"

die() {
  printf '%s: error: %s\n' "$SELF" "$*" >&2
  exit 1
}

usage() {
  cat <<EOF
usage: $SELF --tag <vX.Y.Z> --sha256 <64-hex> --formula <path> [--repo <owner/repo>]

  --tag      the released git tag, exactly vMAJOR.MINOR.PATCH
  --sha256   64 lowercase hex characters — the digest of the tag tarball that
             was actually downloaded, never a hand-written value
  --formula  path to the Homebrew formula to rewrite (packaging/homebrew/devteam.rb)
  --repo     owner/repo the url line points at; defaults to \$GITHUB_REPOSITORY
EOF
}

TAG=""
SHA256=""
FORMULA=""
REPO="${GITHUB_REPOSITORY:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --tag)
      [ "$#" -ge 2 ] || die "--tag requires a value"
      TAG="$2"
      shift 2
      ;;
    --sha256)
      [ "$#" -ge 2 ] || die "--sha256 requires a value"
      SHA256="$2"
      shift 2
      ;;
    --formula)
      [ "$#" -ge 2 ] || die "--formula requires a value"
      FORMULA="$2"
      shift 2
      ;;
    --repo)
      [ "$#" -ge 2 ] || die "--repo requires a value"
      REPO="$2"
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      die "unknown argument: $1"
      ;;
  esac
done

# ── Validation ──────────────────────────────────────────────────────────────
# Every one of these refuses rather than falls back. This script writes the
# value users' machines will trust when Homebrew verifies the download, so a
# malformed input must never reach the file on disk in any form.

[ -n "$TAG" ] || { usage >&2; die "--tag is required"; }
[ -n "$SHA256" ] || { usage >&2; die "--sha256 is required"; }
[ -n "$FORMULA" ] || { usage >&2; die "--formula is required"; }

printf '%s' "$TAG" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' \
  || die "tag '$TAG' does not match ^v[0-9]+\\.[0-9]+\\.[0-9]+\$ — refusing to bump the formula."

# Lowercase hex only, exactly 64 characters. This is also what rejects the
# formula's own placeholder (REPLACE_WITH_SHA256_OF_RELEASE_TARBALL) and an
# uppercase digest: Homebrew's own format check is strict, and a digest that
# fails it only at `brew install` time fails on a user's machine, not here.
printf '%s' "$SHA256" | grep -Eq '^[0-9a-f]{64}$' \
  || die "sha256 '$SHA256' is not 64 lowercase hex characters — refusing to bump the formula."

[ -n "$REPO" ] \
  || die "no repository known: pass --repo <owner/repo> or run with GITHUB_REPOSITORY set."

printf '%s' "$REPO" | grep -Eq '^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$' \
  || die "repo '$REPO' does not look like owner/repo."

[ -f "$FORMULA" ] || die "formula not found: $FORMULA"

# Two writability checks, because two different things have to be writable, and
# `[ -w "$FORMULA" ]` stood here alone. On its own it was NOT sufficient: the
# `mktemp` and the `mv -f` below both act on the DIRECTORY, so a 0666 formula in
# a 0555 directory passed the check and then failed inside the rewrite.
#
# It is, however, necessary — which is worth writing down, because the file is
# never written in place and the check therefore looks like it is guarding
# nothing. What makes the target's own mode matter is `cp -p`: it hands that
# mode to the staging file (see its comment below), and the rewrite is then
# redirected into that copy. So a 0444 formula produces a 0444 staging file that
# `>` cannot open, and the run dies on a bare redirection error from the middle
# of the script instead of here. Checked up front instead.
#
# Both remain diagnostics rather than gates — `-w` sees neither an ACL, nor a
# read-only mount, nor an immutable flag — so `mktemp` keeps its own `die`. What
# they buy is a comprehensible message before anything has been created.
FORMULA_DIR="$(dirname "$FORMULA")"
[ -w "$FORMULA_DIR" ] \
  || die "cannot write in ${FORMULA_DIR}: the rewrite is staged there before being renamed over ${FORMULA}."
[ -w "$FORMULA" ] \
  || die "formula is not writable: ${FORMULA} — its mode is copied onto the staging file the rewrite is written into."

# ── The repo, as a regex-safe literal ───────────────────────────────────────
# `$REPO` is interpolated into the `sed -E` pattern below, where every ERE
# metacharacter in it would be honoured as one. The validated shape above
# admits `.`, `_` and `-`, so a real repository like `Dev.Toolbelt/tool` would
# make `.` match *any* character and rewrite the url of a formula pointing at
# `Dev-Toolbelt/tool` — the wrong repository, silently accepted.
#
# So escape first. The bracket expression covers the full ERE metacharacter
# set — `] [ ^ $ . * + ? ( ) { } |` and backslash itself — not merely the `.`
# the current validation can produce, so widening that validation later cannot
# quietly reopen this. `]` is first in the class because that is the only
# position where it is a literal. The `#` used as the `s###` delimiter below
# needs no escaping: the validation rejects it outright.
REPO_ERE="$(printf '%s' "$REPO" | sed 's/[][^$.*+?(){}|\\]/\\&/g')"

# ── What the rewrite matches, defined once ──────────────────────────────────
# Each of these two EREs is used twice: to COUNT the places the rewrite would
# land (the refusal below) and then to perform it (the `sed` further down).
# Sharing one definition is the whole point — a guard that counted a pattern
# even slightly different from the one that rewrites is a guard for a different
# script, and would go stale the first time either copy was touched.
#
# `url` is anchored tightly: the repository, the `archive/refs/tags/` path and
# the `.tar.gz` suffix are all part of the match, so a vendored `resource` url
# pointing anywhere else is provably out of reach. `sha256` cannot be anchored
# that way — a digest line carries nothing but the digest — so the most it can
# require is the string-literal shape `sha256 "…"`. That asymmetry is exactly
# why the count below is needed.
URL_ERE="(url \"https://github.com/${REPO_ERE}/archive/refs/tags/)[^\"]+(\\.tar\\.gz\")"
SHA256_ERE="(sha256 \")[^\"]+(\")"

# ── Refuse a formula the rewrite cannot land unambiguously ──────────────────
# `sed` rewrites EVERY match, and the verification afterwards only proves the
# wanted values are present *somewhere*. So a formula carrying two rewritable
# digests has both replaced by the release digest and still exits 0. Reproduced
# with a `resource` block holding a vendored digest: the stable digest and the
# vendored one both came out as the release digest.
#
# A comment here used to claim the rewrite was "anchored on the literal
# `url \"...\"` / `sha256 \"...\"` line shape this formula uses, so a change to
# unrelated lines is never touched". For `url` that is true. For `sha256` it was
# never true: the pattern is the line shape, not a position, and every line
# wearing that shape is rewritten. What it does correctly skip is a `bottle do`
# block, whose per-platform digests are spelled `sha256 <platform>: "…"` and
# carry no `sha256 "` for the anchor to find; a `resource` block's plain
# `sha256 "…"` is a different thing and is matched.
#
# This refuses rather than rewriting only the first match. Taking the first is a
# guess about which of two digests is the stable one: right for a formula written
# in the conventional order, silently wrong for any other, and wrong in the one
# direction that matters — a digest users' machines are told to trust. A refusal
# costs a maintainer a minute and cannot corrupt anything. Nothing has been
# staged or copied at this point either, so the formula is byte-identical on this
# path by construction rather than by a cleanup step.
occurrences() {
  { grep -oE "$1" "$FORMULA" || true; } | wc -l | tr -d '[:space:]'
}

# Occurrences, not matching lines: `sed` without `/g` rewrites the first match
# on a line, so two matches on one line would leave the second behind — which a
# line count would report as unambiguous.
URL_HITS="$(occurrences "$URL_ERE")"
SHA256_HITS="$(occurrences "$SHA256_ERE")"

# `-le 1`, not `-eq 1`: zero matches is a real and already-handled case (a
# placeholder-free formula, `sha256 :no_check`, a url pointing at another repo),
# and the post-rewrite verification below reports it with the message that says
# which of the two lines did not land. Only ambiguity is new here.
[ "$URL_HITS" -le 1 ] \
  || die "formula has ${URL_HITS} url matches for a ${REPO} tag archive — the rewrite would change every one. Refusing rather than guessing which is the stable url; leave exactly one."
[ "$SHA256_HITS" -le 1 ] \
  || die "formula has ${SHA256_HITS} rewritable 'sha256 \"…\"' matches — the rewrite would write the release digest over every one. Refusing rather than guessing which is the stable digest; leave exactly one plain 'sha256 \"…\"'. (A 'bottle do' block's 'sha256 <platform>: \"…\"' digests are a different shape and are never matched.)"

# ── Rewrite, staged ─────────────────────────────────────────────────────────
# WHY THE WRITE IS STAGED
# =======================
# The rewrite is verified only after the fact — and the verification can fail
# on a file whose two lines are independent: the url anchor carries owner/repo
# while the sha256 anchor does not, so a wrong `--repo` used to leave the
# formula on disk carrying a NEW digest against its OLD url. The workflow
# exited non-zero and never committed, so nothing bad was published, but a
# half-rewritten file is the wrong shape for a script this repository ships —
# and `CLAUDE.md` already holds the rule for the python store code that every
# mutation is written atomically. So: rewrite into a sibling temp file, verify
# *that*, and rename it over the target only once every check has passed. The
# formula is therefore either fully updated or byte-identical to before, and it
# never stops existing.
#
# `$FORMULA_DIR` is resolved up in the validation section, where it is also
# checked for writability.
STAGED=""

cleanup() {
  [ -z "$STAGED" ] || rm -f "$STAGED"
}
trap cleanup EXIT

# In the target's own directory, so the move below is a rename on one
# filesystem rather than a cross-device copy — which is what makes it atomic.
#
# What keeps this file out of the release commit is NOT the dot prefix. That was
# claimed here and is false: git has no notion of hidden files, `git status
# --short` lists `?? packaging/homebrew/.devteam-bump.AbC123` and `git add -A`
# stages it. Two real things protect the release job, and both live outside this
# line: `.github/workflows/release.yml` stages one explicit path
# (`git add packaging/homebrew/devteam.rb`, and its skip check is the equally
# path-scoped `git diff --quiet -- packaging/homebrew/devteam.rb`), and this
# name carries no `.rb`, so the `ruby -c` step and any future `*.rb` glob cannot
# reach it either. The `trap` above is what actually removes it.
#
# The dot prefix is kept anyway: it costs nothing and keeps a stray file out of
# a plain `ls` if one ever survives, which is the only thing it does.
STAGED="$(mktemp "${FORMULA_DIR}/.devteam-bump.XXXXXX")" \
  || die "could not create a staging file in ${FORMULA_DIR}."

# `cp -p` is how the target's permission bits reach the staging file (mktemp
# creates it 0600), so the rename cannot change the formula's mode. The `>`
# redirection that follows truncates that copy and leaves the bits alone.
cp -p "$FORMULA" "$STAGED" \
  || die "could not stage a copy of ${FORMULA}."

# Replace the url line's tag placeholder (or a previous real tag) and the
# sha256 line's placeholder (or a previous real digest), using the same two EREs
# the ambiguity guard above counted with — so what is rewritten here is by
# construction what was counted there.
#
# The original of this command used `sed -i.bak` — the suffixed spelling being
# the only in-place form both the macOS system sed and the runner's GNU sed
# accept. That portability note is not lost by accident: `-i` is simply gone,
# because reading the target and redirecting into the staging file needs no
# in-place edit at all. One less stray `.bak` file to remove, and no sed
# variant to be portable across.
sed -E \
  -e "s#${URL_ERE}#\\1${TAG}\\2#" \
  -e "s#${SHA256_ERE}#\\1${SHA256}\\2#" \
  "$FORMULA" > "$STAGED"

# ── Show, then verify ───────────────────────────────────────────────────────
# Printed before the assertions so a failing run still shows what the two lines
# actually look like — that is the whole diagnostic. `[[:space:]]` rather than
# `\s`: the latter is a GNU extension that the macOS system grep matches as a
# literal `s`, which would quietly print nothing on a developer's machine.
#
# Read from the staged file, headed with the target's path: what is shown is the
# content about to land, under the name it will land as.
echo "── ${FORMULA} ──"
grep -nE '^[[:space:]]*(url|sha256) ' "$STAGED" || true

# Repo-qualified, and that is the point: the fixed string is the whole url line,
# not the tag fragment. Matching `archive/refs/tags/${TAG}.tar.gz` alone passed
# for a formula whose url already carried that tag under a DIFFERENT repository
# — the rewrite matched nothing, this check matched the url that was already
# there, the repo-independent sha256 check matched the digest just written, and
# the run exited 0 having claimed one repository's digest for another's tarball.
# `-F` keeps $REPO and $TAG literal, so neither is read as a pattern.
grep -qF "url \"https://github.com/${REPO}/archive/refs/tags/${TAG}.tar.gz\"" "$STAGED" \
  || die "url line was not updated to ${REPO} at tag ${TAG}."
grep -qF "sha256 \"${SHA256}\"" "$STAGED" \
  || die "sha256 line was not updated to the computed digest."

# Every check passed — this is the only line that touches the target.
mv -f "$STAGED" "$FORMULA" || die "could not move the staged formula into place."
STAGED=""
