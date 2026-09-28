#!/usr/bin/env bash
#
# verify-formula-locally.sh — exercise packaging/homebrew/devteam.rb through a real
# Homebrew, end to end: install block, test block, installed-binary smoke check,
# style and audit. This is the check packaging/README.md's "What is unverified"
# table used to describe as impossible.
#
# ── Two modes, one interface ─────────────────────────────────────────────────
#   Local mode (no --url/--sha256): builds a tarball from the current HEAD whose
#   top-level directory matches GitHub's tag-archive shape
#   (dev-team-agents-<version>/), hashes it, and points a TEMPORARY copy of the
#   formula at that file:// URL. The tracked formula is never written to; the
#   script asserts that at exit.
#
#   Release mode (--tag + --url + --sha256): verifies the formula against a real
#   released artifact. This is the mode .github/workflows/release.yml calls once a
#   tag has landed and the digest is known.
#
# ── Why this script creates a throwaway Homebrew tap ─────────────────────────
#   Homebrew used to accept `brew install ./some-formula.rb`. It does not any
#   more: as of Homebrew 7.x, Formulary rejects any formula file that is not
#   inside a tap ("Homebrew requires formulae to be in a tap, rejecting: ..."),
#   and `brew audit <path>` is disabled outright in favour of `brew audit <name>`.
#   Homebrew's own error message tells you to run `brew tap-new`. So this script
#   creates a uniquely-named, git-less, throwaway tap, drops the temporary
#   formula into it, and removes the tap again on exit. It never touches a tap
#   the machine already had, and it verifies its own teardown.
#
# ── Side effects, and how they are undone ────────────────────────────────────
#   * Homebrew 7 also refuses to LOAD a formula from an untrusted tap, so the tap
#     has to be trusted. Trust records live in $XDG_CONFIG_HOME/homebrew/trust.json
#     (else ~/.homebrew/trust.json), so this script runs every `brew` invocation
#     — and only `brew` — with XDG_CONFIG_HOME pointed at its own temp dir: the
#     trust entry is written there and disappears with the temp dir. The
#     machine's real ~/.homebrew/trust.json is copied in read-only, never
#     written, and the script asserts it is byte-identical at exit. The
#     redirection is deliberately NOT a global `export`: git also reads
#     $XDG_CONFIG_HOME/git/{config,ignore,attributes}, and the artifact stage
#     runs `git describe` and `git archive`, which must see the user's real one.
#   * the throwaway tap                      — untapped and deleted on exit
#   * the `devteam` formula                  — uninstalled on exit
#   * the formula's declared python dependency, if Homebrew has to install it to
#     satisfy `depends_on` — announced loudly BEFORE the install, and uninstalled
#     on exit only if this script is what installed it
#   * PERMANENT, AND NOT UNDONE: `brew style` and `brew audit` are Homebrew *dev*
#     commands. Both call Utils::GemSetup.install_bundler_gems! (see
#     Library/Homebrew/dev-cmd/style.rb and dev-cmd/audit.rb), which bootstraps
#     rubocop and the audit gems into
#     $(brew --repository)/Library/Homebrew/vendor/bundle — ~100 MB on a prefix
#     that has never run a dev command before. This script CANNOT undo that:
#     deleting that tree would damage Homebrew's own state, and Homebrew reuses
#     it for every later dev command. It is announced as loudly as the python
#     install below, before the stage that triggers it, and then left in place.
#   * $DEVTEAM_HOME is pointed at a temp directory for every devteam invocation,
#     so the machine's real store is never read or written
#   Pass --keep to skip the TEARDOWN (for debugging a failure). It does not skip
#   the two read-only assertions — real trust.json byte-identity and tracked
#   formula immutability — which run on every exit path, keep or no keep.
#
# It never runs `brew update`, `brew upgrade`, or touches a pre-existing tap.
#
# ── Requirements ─────────────────────────────────────────────────────────────
#   Homebrew >= 7. `brew trust` and the tap-only Formulary rules this script is
#   built around are 7.x semantics; the preflight stage fails with that reason
#   rather than letting the run die mid-way at the `brew trust` call.
#
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TRACKED_FORMULA="$REPO_ROOT/packaging/homebrew/devteam.rb"
FORMULA_NAME="devteam"

TAP_USER="devteam-verify-local"
TAP_REPO="verify$$"
TAP_FULL="$TAP_USER/$TAP_REPO"

# ── options ─────────────────────────────────────────────────────────────────
OPT_TAG=""
OPT_URL=""
OPT_SHA=""
OPT_KEEP="no"

usage() {
    cat <<'EOF'
Usage: verify-formula-locally.sh [--tag <vX.Y.Z>] [--url <tarball-url>] [--sha256 <64-hex>] [--keep]

  --tag     Version tag the artifact represents. Local mode: names the tarball's
            top-level directory (defaults to the most recent git tag, else
            v0.0.0-local). Release mode: required.
  --url     Release mode only. URL of the real released tarball.
  --sha256  Release mode only. 64-hex digest of that tarball.
  --keep    Do not tear down (leaves the formula installed and the temp tap in
            place). Use only when debugging a failure. It skips the TEARDOWN
            only: the real-trust.json and tracked-formula-immutability
            assertions are read-only and still run.

Requires Homebrew >= 7 (brew trust, tap-only formula loading).

With neither --url nor --sha256 the script runs in local mode and builds the
artifact from the current HEAD. Both must be given together.
EOF
}

# `--tag` with no value used to exit 1 silently: `shift 2` fails under `set -e`
# before anything is printed. Every value-taking flag says so instead.
need_value() {
    if [ -z "${2:-}" ]; then
        printf 'verify-formula-locally: %s requires a value\n\n' "$1" >&2
        usage >&2
        exit 2
    fi
}

while [ $# -gt 0 ]; do
    case "$1" in
        --tag)    need_value "$1" "${2:-}"; OPT_TAG="$2"; shift 2 ;;
        --url)    need_value "$1" "${2:-}"; OPT_URL="$2"; shift 2 ;;
        --sha256) need_value "$1" "${2:-}"; OPT_SHA="$2"; shift 2 ;;
        --keep)   OPT_KEEP="yes"; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'verify-formula-locally: unknown argument: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -n "$OPT_URL" ] && [ -z "$OPT_SHA" ]; then
    printf 'verify-formula-locally: --url given without --sha256\n' >&2
    exit 2
fi
if [ -n "$OPT_SHA" ] && [ -z "$OPT_URL" ]; then
    printf 'verify-formula-locally: --sha256 given without --url\n' >&2
    exit 2
fi

MODE="local"
if [ -n "$OPT_URL" ]; then
    MODE="release"
    if [ -z "$OPT_TAG" ]; then
        printf 'verify-formula-locally: release mode requires --tag\n' >&2
        exit 2
    fi
    case "$OPT_SHA" in
        *[!0-9a-f]* | "") printf 'verify-formula-locally: --sha256 must be 64 lowercase hex chars\n' >&2; exit 2 ;;
    esac
    if [ ${#OPT_SHA} -ne 64 ]; then
        printf 'verify-formula-locally: --sha256 must be 64 lowercase hex chars (got %s)\n' "${#OPT_SHA}" >&2
        exit 2
    fi
fi

# ── reporting ───────────────────────────────────────────────────────────────
STAGE=""
RESULTS=""

say()   { printf '\n==> %s\n' "$*"; }
note()  { printf '    %s\n' "$*"; }
record() { RESULTS="${RESULTS}${1}|${2}|${3}
"; }

stage() {
    STAGE="$1"
    say "stage: $1"
}

die() {
    printf '\nverify-formula-locally: FAILED at stage "%s": %s\n' "$STAGE" "$1" >&2
    exit 1
}

# ── environment ─────────────────────────────────────────────────────────────
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ENV_HINTS=1
export HOMEBREW_NO_ANALYTICS=1
export HOMEBREW_NO_INSTALL_CLEANUP=1

# The trust-store sandbox applies to Homebrew and to nothing else. A global
# `export XDG_CONFIG_HOME` would also reroute git — which reads
# $XDG_CONFIG_HOME/git/{config,ignore,attributes} — and the artifact stage runs
# `git describe` and `git archive`. So `brew` is wrapped instead: the sandbox
# path is set for the duration of each brew process and never enters this
# shell's own environment. Empty until the preflight stage creates the sandbox,
# so the read-only preflight brew calls see the machine's real trust picture.
BREW_XDG=""
brew() {
    if [ -n "$BREW_XDG" ]; then
        XDG_CONFIG_HOME="$BREW_XDG" command brew "$@"
    else
        command brew "$@"
    fi
}

TMP_ROOT=""
TAP_DIR=""
FORMULA_SNAPSHOT=""
INSTALLED_FORMULA="no"
INSTALLED_PY_DEP=""
CREATED_TAP="no"
GEM_BUNDLE_DIR=""
GEM_BUNDLE_PRESENT="unknown"
EXIT_RC=0
CLEANUP_OK="yes"

# A teardown step went wrong. Record it and keep going — never return non-zero
# out of a step in a way that could end the teardown early.
# shellcheck disable=SC2329
problem() {
    note "PROBLEM: $1"
    CLEANUP_OK="no"
}

# Remove a formula and report on PRESENCE, not on brew's exit code. `brew
# uninstall` can remove the keg and still exit non-zero (an untrusted-tap warning
# elsewhere on the machine is enough), which made an earlier version of this
# script report a clean teardown as a failure.
#
# It reports a FAILED `brew list` as a problem rather than as absence: a listing
# this script could not read is not evidence that the formula is gone.
# shellcheck disable=SC2329
remove_formula() {
    local name="$1"
    local why="$2"
    local log="${TMP_ROOT:-/tmp}/uninstall-$name.log"
    local listing=""

    if listing=$(brew list --formula 2>/dev/null); then
        if ! printf '%s\n' "$listing" | grep -qx "$name"; then
            note "$name is not installed; nothing to remove ($why)"
            return 0
        fi
    fi

    note "brew uninstall $name ($why)"
    brew uninstall --formula "$name" > "$log" 2>&1

    if ! listing=$(brew list --formula 2>/dev/null); then
        problem "cannot confirm $name was removed: 'brew list --formula' failed"
        note "    check it yourself:  brew list --formula | grep -x $name"
        return 0
    fi
    if printf '%s\n' "$listing" | grep -qx "$name"; then
        problem "$name is STILL installed. brew said:"
        [ -f "$log" ] && sed 's/^/        /' "$log"
        note "    remove it yourself:  brew uninstall $name"
        return 0
    fi
    note "    removed"
    return 0
}

# The mutating half of the teardown. Every step is independent: no step's exit
# status can prevent a later one from running, because `cleanup` has already
# turned `errexit` and `pipefail` off before calling this.
# shellcheck disable=SC2329
teardown() {
    say "stage: teardown"

    if [ "$INSTALLED_FORMULA" = "yes" ]; then
        remove_formula "$FORMULA_NAME" "this run may have installed it"
    fi

    if [ -n "$INSTALLED_PY_DEP" ]; then
        remove_formula "$INSTALLED_PY_DEP" "declared dependency, this run may have installed it"
    fi

    if [ "$CREATED_TAP" = "yes" ]; then
        note "brew untap $TAP_FULL"
        brew untap --force "$TAP_FULL" >/dev/null 2>&1
        # --no-git taps are sometimes left on disk by untap; the path is one this
        # script constructed and named uniquely, so removing it is bounded.
        case "$TAP_DIR" in
            */Library/Taps/"$TAP_USER"/homebrew-"$TAP_REPO")
                if [ -d "$TAP_DIR" ]; then
                    rm -rf "$TAP_DIR"
                fi
                ;;
        esac
        if [ -d "$TAP_DIR" ]; then
            problem "temp tap still on disk: $TAP_DIR"
        fi
    fi

    # One listing, read once, used by all three checks below. A `brew list` that
    # FAILS is reported as such — the old code let a non-zero `brew list` abort
    # the whole teardown at this point, skipping every check after it.
    local post_list=""
    local post_list_ok="yes"
    if ! post_list=$(brew list --formula 2>/dev/null); then
        post_list_ok="no"
        problem "'brew list --formula' failed; cannot verify what is installed now"
    fi

    # Any formula that exists now but did not before is a leftover this script
    # did not put there directly — Homebrew pulled it in as a transitive
    # dependency. Report it precisely rather than guessing whether it is safe to
    # remove (something else may now depend on it).
    if [ "$post_list_ok" = "yes" ] && [ -n "$FORMULA_SNAPSHOT" ] && [ -f "$FORMULA_SNAPSHOT" ]; then
        local leftovers
        leftovers=$(printf '%s\n' "$post_list" | sort | comm -13 "$FORMULA_SNAPSHOT" - | tr '\n' ' ')
        if [ -n "$(printf '%s' "$leftovers" | tr -d ' ')" ]; then
            problem "LEFTOVER formulae Homebrew pulled in transitively and this script did not remove:"
            note "    $leftovers"
            note "    remove them yourself if you want the machine exactly as it was:"
            note "    brew uninstall $leftovers"
        else
            note "verified: no transitively-installed formulae left behind"
        fi
    fi

    # Evidence, not assertion.
    if [ "$post_list_ok" = "yes" ]; then
        if printf '%s\n' "$post_list" | grep -qx "$FORMULA_NAME"; then
            problem "$FORMULA_NAME is STILL installed"
        else
            note "verified: no '$FORMULA_NAME' formula installed"
        fi
    fi

    local post_taps=""
    if post_taps=$(brew tap 2>/dev/null); then
        if printf '%s\n' "$post_taps" | grep -qx "$TAP_FULL"; then
            problem "temp tap $TAP_FULL is STILL tapped"
        else
            note "verified: temp tap $TAP_FULL is gone"
        fi
        note "taps now: $(printf '%s\n' "$post_taps" | tr '\n' ' ')"
    else
        problem "'brew tap' failed; cannot verify the temp tap is untapped"
    fi

    # Last, so that a failure above still leaves the logs behind to read. Note
    # that BREW_XDG lives inside TMP_ROOT, so no brew call may follow this.
    if [ -n "$TMP_ROOT" ] && [ -d "$TMP_ROOT" ]; then
        rm -rf "$TMP_ROOT"
        if [ -d "$TMP_ROOT" ]; then
            problem "temp dir could not be removed: $TMP_ROOT"
        else
            note "removed temp dir $TMP_ROOT"
        fi
    fi

    if [ "$CLEANUP_OK" = "yes" ]; then
        record teardown PASS "formula uninstalled, temp tap removed, temp files deleted"
    else
        record teardown FAIL "see PROBLEM lines above"
        [ "$EXIT_RC" -eq 0 ] && EXIT_RC=1
    fi
    return 0
}

# The read-only half. Both assertions are pure comparisons of two digests — they
# have nothing to do with whether the install was kept, so `--keep` does NOT
# skip them. The header states both unconditionally, and it is the only thing
# standing between "this script must never write to the tracked formula" and a
# run that wrote to it and exited 0.
# shellcheck disable=SC2329
verify_invariants() {
    local trust_after="absent"
    if [ -f "$REAL_TRUST_FILE" ]; then
        trust_after=$(shasum -a 256 "$REAL_TRUST_FILE" 2>/dev/null | awk '{print $1}')
        [ -n "$trust_after" ] || trust_after="UNREADABLE"
    fi
    if [ "$trust_after" = "$REAL_TRUST_SHA_BEFORE" ]; then
        note "verified: real trust.json unmodified ($REAL_TRUST_FILE)"
        record trust PASS "$REAL_TRUST_FILE byte-identical before and after"
    else
        note "ERROR: real trust.json CHANGED — the XDG sandbox did not hold"
        record trust FAIL "$REAL_TRUST_FILE was modified"
        EXIT_RC=1
    fi

    # The tracked formula must be byte-identical to what we started with.
    local after=""
    after=$(shasum -a 256 "$TRACKED_FORMULA" 2>/dev/null | awk '{print $1}')
    if [ -z "$after" ]; then
        note "ERROR: cannot read $TRACKED_FORMULA to verify it is unmodified"
        record immutability FAIL "packaging/homebrew/devteam.rb could not be read"
        EXIT_RC=1
    elif [ "$after" = "$TRACKED_SHA_BEFORE" ]; then
        note "verified: tracked formula unmodified ($TRACKED_FORMULA)"
        record immutability PASS "packaging/homebrew/devteam.rb byte-identical before and after"
    else
        note "ERROR: tracked formula CHANGED — this script must never write to it"
        record immutability FAIL "packaging/homebrew/devteam.rb was modified"
        EXIT_RC=1
    fi
    return 0
}

# Invoked by the EXIT trap, not directly.
# shellcheck disable=SC2329
cleanup() {
    EXIT_RC=$?

    # THE defect this structure exists to prevent: a teardown aborted halfway
    # leaves the machine changed AND skips the checks that would have said so.
    # One non-zero `brew list` used to do exactly that. From here on nothing in
    # the trap path can end the function early — `errexit` and `pipefail` are
    # off, the EXIT trap is disarmed against re-entry, and every step reports
    # its own failure into CLEANUP_OK/EXIT_RC instead of propagating it.
    set +e
    set +o pipefail
    trap - EXIT

    if [ "$OPT_KEEP" = "yes" ]; then
        say "stage: teardown — SKIPPED (--keep)"
        note "formula installed: $INSTALLED_FORMULA"
        note "temp tap:          ${TAP_DIR:-none}"
        note "temp dir:          ${TMP_ROOT:-none}"
        note "remove them yourself:  brew uninstall $FORMULA_NAME; brew untap --force $TAP_FULL; rm -rf ${TMP_ROOT:-}"
        record teardown SKIPPED "--keep was passed; nothing torn down"
    else
        teardown
    fi

    verify_invariants

    summary
    exit "$EXIT_RC"
}

# Invoked from cleanup(), which the EXIT trap runs.
# shellcheck disable=SC2329
summary() {
    printf '\n'
    printf '========================= VERDICT PER STAGE =========================\n'
    printf '%-14s %-8s %s\n' "STAGE" "RESULT" "DETAIL"
    printf '%s' "$RESULTS" | while IFS='|' read -r s r d; do
        [ -n "$s" ] || continue
        printf '%-14s %-8s %s\n' "$s" "$r" "$d"
    done
    printf '=====================================================================\n'
}

# ── stage: preflight ────────────────────────────────────────────────────────
stage preflight

# `type -P`, not `command -v`: `brew` is a shell function in this script, and
# `command -v brew` would report that function as success even with no Homebrew
# installed at all.
[ -n "$(type -P brew)" ] || { printf 'verify-formula-locally: brew not on PATH\n' >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { printf 'verify-formula-locally: python3 not on PATH (needed to validate --json output)\n' >&2; exit 1; }
[ -f "$TRACKED_FORMULA" ] || { printf 'verify-formula-locally: formula not found: %s\n' "$TRACKED_FORMULA" >&2; exit 1; }

# Homebrew version floor. This script depends on 7.x semantics — `brew trust`,
# and Formulary refusing a formula outside a tap. On an older Homebrew the run
# used to die at the `brew trust` call with a message that reads like a problem
# with the formula. Fail here, with the real reason.
BREW_MIN_MAJOR=7
BREW_VERSION_LINE=$(brew --version 2>/dev/null | head -1)
BREW_MAJOR=$(printf '%s\n' "$BREW_VERSION_LINE" | sed -n 's/^[^0-9]*\([0-9][0-9]*\).*/\1/p')
if [ -z "$BREW_MAJOR" ]; then
    printf 'verify-formula-locally: cannot parse a Homebrew version out of "%s";\n' "$BREW_VERSION_LINE" >&2
    printf '  this script requires Homebrew >= %s (brew trust, tap-only formula loading).\n' "$BREW_MIN_MAJOR" >&2
    printf '  Continuing, but a failure at the "brew trust" step is most likely this.\n' >&2
elif [ "$BREW_MAJOR" -lt "$BREW_MIN_MAJOR" ]; then
    printf 'verify-formula-locally: Homebrew %s is too old (found "%s").\n' "$BREW_MAJOR" "$BREW_VERSION_LINE" >&2
    printf '  This script requires Homebrew >= %s. It relies on two 7.x behaviours:\n' "$BREW_MIN_MAJOR" >&2
    printf "    * 'brew trust --tap', which older Homebrew does not have at all; and\n" >&2
    printf '    * Formulary refusing a formula file outside a tap, which is why the\n' >&2
    printf '      script builds a throwaway tap instead of installing a path.\n' >&2
    printf '  Upgrade Homebrew (brew update) and run this again.\n' >&2
    exit 1
fi

TRACKED_SHA_BEFORE=$(shasum -a 256 "$TRACKED_FORMULA" | awk '{print $1}')

REAL_TRUST_FILE="${XDG_CONFIG_HOME:+$XDG_CONFIG_HOME/homebrew}"
REAL_TRUST_FILE="${REAL_TRUST_FILE:-$HOME/.homebrew}/trust.json"
REAL_TRUST_SHA_BEFORE="absent"
if [ -f "$REAL_TRUST_FILE" ]; then
    REAL_TRUST_SHA_BEFORE=$(shasum -a 256 "$REAL_TRUST_FILE" | awk '{print $1}')
fi

trap cleanup EXIT

note "mode:              $MODE"
note "homebrew:          $(brew --version | head -1)"
note "brew prefix:       $(brew --prefix)"
note "tracked formula:   $TRACKED_FORMULA"
note "tracked sha256:    $TRACKED_SHA_BEFORE"
note "pre-existing taps: $(brew tap 2>/dev/null | tr '\n' ' ')"
note "real trust.json:   $REAL_TRUST_FILE ($REAL_TRUST_SHA_BEFORE)"

if brew list --formula 2>/dev/null | grep -qx "$FORMULA_NAME"; then
    die "a '$FORMULA_NAME' formula is already installed on this machine; refusing to touch it"
fi

# The python formula the formula declares. Read it out of the formula rather than
# hardcoding it here, so this script cannot drift from devteam.rb.
PY_DEP=$(awk '/^[[:space:]]*depends_on[[:space:]]*"python@/ {
    match($0, /"[^"]+"/); print substr($0, RSTART + 1, RLENGTH - 2); exit
}' "$TRACKED_FORMULA")
[ -n "$PY_DEP" ] || die "could not read the declared python dependency out of the formula"
note "declared python:   $PY_DEP"

PY_DEP_PRESENT="no"
if brew list --formula 2>/dev/null | grep -qx "$PY_DEP"; then
    PY_DEP_PRESENT="yes"
fi
note "$PY_DEP installed: $PY_DEP_PRESENT"

# `brew style` and `brew audit` are Homebrew DEV commands, and both call
# Utils::GemSetup.install_bundler_gems! (Library/Homebrew/dev-cmd/style.rb:53 and
# dev-cmd/audit.rb:124). That bootstraps rubocop plus the audit/ast gem groups
# into the Homebrew prefix. It is a permanent change this script cannot undo, so
# it is reported here — before the stage that triggers it — rather than being the
# one side effect the header list left out.
GEM_BUNDLE_DIR="$(brew --repository)/Library/Homebrew/vendor/bundle"
GEM_BUNDLE_PRESENT="no"
if [ -d "$GEM_BUNDLE_DIR/ruby" ]; then
    GEM_BUNDLE_PRESENT="yes"
fi
note "brew dev gems:     $GEM_BUNDLE_PRESENT ($GEM_BUNDLE_DIR)"

CURRENT_PY3=$(brew info --json=v2 python3 2>/dev/null \
    | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
    print(d["formulae"][0]["name"])
except Exception:
    print("unknown")' 2>/dev/null || printf 'unknown')
note "brew python3 is:   $CURRENT_PY3"
if [ "$CURRENT_PY3" != "unknown" ] && [ "$CURRENT_PY3" != "$PY_DEP" ]; then
    note "NOTE: the formula depends on '$PY_DEP' but homebrew-core's current python3 is"
    note "      '$CURRENT_PY3'. This run is the drift report — packaging/README.md records"
    note "      that this script is what surfaces it, so it is not a remembered step."
fi

if [ "$PY_DEP_PRESENT" = "no" ]; then
    printf '\n'
    printf '  !! %s is NOT installed on this machine.\n' "$PY_DEP"
    printf '  !! The formula declares it with depends_on, so brew install WILL download\n'
    printf '  !! and install it (a bottle, plus any of its own deps that are missing).\n'
    printf '  !! That is a real change to this machine, announced here rather than made\n'
    printf '  !! silently. This script uninstalls it again during cleanup, because it was\n'
    printf '  !! this run that installed it.\n'
    printf '  !! To avoid it entirely, install it yourself first (then it is yours, and\n'
    printf '  !! cleanup leaves it alone):  brew install %s\n' "$PY_DEP"
    printf '\n'
fi

if [ "$GEM_BUNDLE_PRESENT" = "no" ]; then
    printf '\n'
    printf '  !! Homebrew has NEVER run a dev command on this prefix: there is no\n'
    printf '  !! %s\n' "$GEM_BUNDLE_DIR/ruby"
    printf "  !! The style and audit stages below run 'brew style' and 'brew audit',\n"
    printf '  !! which are dev commands. Both call install_bundler_gems!, so Homebrew\n'
    printf '  !! WILL download and install rubocop and the audit gems into that\n'
    printf '  !! directory — roughly 100 MB inside your Homebrew prefix.\n'
    printf '  !! THIS SCRIPT DOES NOT UNDO IT. Deleting that tree would damage\n'
    printf '  !! Homebrew'"'"'s own state, and Homebrew reuses it for every later dev\n'
    printf '  !! command, so it is left in place deliberately. It is announced here\n'
    printf '  !! because it is the one change this run makes that outlives it.\n'
    printf '  !! To avoid it entirely, do not run this script; or accept it once and\n'
    printf "  !! every later 'brew style'/'brew audit' on this machine reuses it.\n"
    printf '\n'
else
    note "brew dev gems already bootstrapped; the style/audit stages add nothing new"
fi

TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/devteam-verify.XXXXXX")
note "temp dir:          $TMP_ROOT"

# Sandbox Homebrew's trust store into the temp dir. The existing entries are
# copied in so the run sees the same trust picture the machine has; the entry
# this script adds for its throwaway tap is written HERE and nowhere else.
#
# This is NOT an `export`: it is picked up by the `brew` wrapper defined above and
# by nothing else, so `git describe` and `git archive` in the next stage keep the
# user's real $XDG_CONFIG_HOME/git/{config,ignore,attributes}.
mkdir -p "$TMP_ROOT/xdg/homebrew"
if [ -f "$REAL_TRUST_FILE" ]; then
    cp "$REAL_TRUST_FILE" "$TMP_ROOT/xdg/homebrew/trust.json"
fi
BREW_XDG="$TMP_ROOT/xdg"
note "trust sandbox:     $BREW_XDG/homebrew/trust.json (brew only; git unaffected)"
record preflight PASS "brew $BREW_MAJOR, declared dep $PY_DEP (present=$PY_DEP_PRESENT), dev gems present=$GEM_BUNDLE_PRESENT"

# ── stage: artifact ─────────────────────────────────────────────────────────
stage artifact

if [ -z "$OPT_TAG" ]; then
    OPT_TAG=$(git -C "$REPO_ROOT" describe --tags --abbrev=0 2>/dev/null || printf 'v0.0.0-local')
fi
VERSION="${OPT_TAG#v}"

if [ "$MODE" = "local" ]; then
    # GitHub's tag archive unpacks into <repo>-<version>/. scripts/cli/devteam
    # resolves its package as parent.parent/"lib", so the relative layout inside
    # the tarball is what the formula's install block depends on.
    ARCHIVE="$TMP_ROOT/dev-team-agents-$VERSION.tar.gz"
    note "git archive HEAD --prefix=dev-team-agents-$VERSION/"
    git -C "$REPO_ROOT" archive --format=tar.gz \
        --prefix="dev-team-agents-$VERSION/" -o "$ARCHIVE" HEAD \
        || die "git archive failed"

    ARTIFACT_URL="file://$ARCHIVE"
    ARTIFACT_SHA=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')

    # Cheap sanity check that the two paths the install block reaches for are
    # actually inside the artifact — a missing file here is a formula bug, not a
    # Homebrew one, and it is much easier to read at this stage than mid-install.
    tar -tzf "$ARCHIVE" > "$TMP_ROOT/listing.txt" || die "cannot list $ARCHIVE"
    grep -qx "dev-team-agents-$VERSION/scripts/cli/devteam" "$TMP_ROOT/listing.txt" \
        || die "artifact has no scripts/cli/devteam"
    grep -q "^dev-team-agents-$VERSION/scripts/lib/devteam/.*\.py\$" "$TMP_ROOT/listing.txt" \
        || die "artifact has no scripts/lib/devteam/*.py"
    note "artifact:          $ARCHIVE ($(wc -c < "$ARCHIVE" | tr -d ' ') bytes)"
    note "contains:          scripts/cli/devteam + $(grep -c "^dev-team-agents-$VERSION/scripts/lib/devteam/.*\.py\$" "$TMP_ROOT/listing.txt") lib/devteam/*.py files"
else
    ARTIFACT_URL="$OPT_URL"
    ARTIFACT_SHA="$OPT_SHA"
    note "artifact:          $ARTIFACT_URL (digest supplied, Homebrew will verify it)"
fi

note "sha256:            $ARTIFACT_SHA"
record artifact PASS "$MODE mode, tag $OPT_TAG, real 64-hex digest computed"

# ── stage: tap + temp formula ───────────────────────────────────────────────
stage tapsetup

# Both of these are set BEFORE `tap-new` runs, not after it succeeds. The EXIT
# trap fires on SIGINT and SIGTERM too, so a Ctrl-C landing inside `tap-new` used
# to leave the tap tapped with CREATED_TAP=no and a teardown that skipped the
# untap. `brew --repository <tap>` is pure path arithmetic and answers correctly
# for a tap that does not exist yet, so the teardown can know where to look
# before there is anything to look for.
TAP_DIR=$(brew --repository "$TAP_FULL")
CREATED_TAP="yes"
note "tap dir:           $TAP_DIR"
note "brew tap-new $TAP_FULL --no-git"
brew tap-new "$TAP_FULL" --no-git >/dev/null 2>&1 || die "brew tap-new failed"

TEMP_FORMULA="$TAP_DIR/Formula/$FORMULA_NAME.rb"
mkdir -p "$TAP_DIR/Formula"

awk -v u="$ARTIFACT_URL" -v s="$ARTIFACT_SHA" '
    !udone && $1 == "url"    { print "  url \"" u "\"";    udone = 1; next }
    !sdone && $1 == "sha256" { print "  sha256 \"" s "\""; sdone = 1; next }
    { print }
    END {
        if (!udone) { print "AWK_NO_URL" > "/dev/stderr"; exit 1 }
        if (!sdone) { print "AWK_NO_SHA" > "/dev/stderr"; exit 1 }
    }
' "$TRACKED_FORMULA" > "$TEMP_FORMULA" || die "could not rewrite url/sha256 in the temp formula"

# Only the sha256 DIRECTIVE matters; devteam.rb's header comment names the
# placeholder string on purpose, so a whole-file grep would always match.
REWRITTEN_SHA=$(awk '$1 == "sha256" { match($0, /"[^"]*"/); print substr($0, RSTART + 1, RLENGTH - 2); exit }' "$TEMP_FORMULA")
if [ "$REWRITTEN_SHA" != "$ARTIFACT_SHA" ]; then
    die "temp formula sha256 is '$REWRITTEN_SHA', expected '$ARTIFACT_SHA'"
fi
REWRITTEN_URL=$(awk '$1 == "url" { match($0, /"[^"]*"/); print substr($0, RSTART + 1, RLENGTH - 2); exit }' "$TEMP_FORMULA")
if [ "$REWRITTEN_URL" != "$ARTIFACT_URL" ]; then
    die "temp formula url is '$REWRITTEN_URL', expected '$ARTIFACT_URL'"
fi
note "temp formula:      $TEMP_FORMULA"

# Homebrew 7 will not LOAD a formula from an untrusted tap. This write goes to
# the sandboxed trust.json inside TMP_ROOT, not to the machine's real one.
note "brew trust --tap $TAP_FULL  (into the sandboxed trust.json)"
brew trust --tap "$TAP_FULL" 2>&1 | sed 's/^/      /' || die "brew trust failed"

note "diff vs tracked (url/sha256 only expected):"
diff "$TRACKED_FORMULA" "$TEMP_FORMULA" | sed 's/^/      /' || true
record tapsetup PASS "throwaway tap $TAP_FULL, formula rewritten to the real url+digest"

# ── stage: style ────────────────────────────────────────────────────────────
# `brew style` accepts a path, so it works on the temp formula directly.
stage style
if [ "$GEM_BUNDLE_PRESENT" = "no" ]; then
    note "!! this is the stage that bootstraps ~100 MB of gems into $GEM_BUNDLE_DIR"
    note "!! (announced in preflight; permanent, and this script does not undo it)"
else
    note "dev gems already present in $GEM_BUNDLE_DIR — nothing installed by this stage"
fi
STYLE_LOG="$TMP_ROOT/style.log"
STYLE_RC=0
brew style "$TEMP_FORMULA" > "$STYLE_LOG" 2>&1 || STYLE_RC=$?
sed 's/^/    /' "$STYLE_LOG"
if [ "$STYLE_RC" -eq 0 ]; then
    record style PASS "brew style clean"
else
    record style FINDINGS "brew style exited $STYLE_RC — see log above (does NOT fail this run)"
fi

# ── stage: audit ────────────────────────────────────────────────────────────
# `brew audit <path>` is disabled in Homebrew 7.x; the name form needs the tap,
# which we have. Findings are reported but never gate the run: homebrew-core's
# house rules and a private tap's requirements are not the same set.
stage audit
AUDIT_LOG="$TMP_ROOT/audit.log"
AUDIT_RC=0
brew audit --formula "$TAP_FULL/$FORMULA_NAME" > "$AUDIT_LOG" 2>&1 || AUDIT_RC=$?
sed 's/^/    /' "$AUDIT_LOG"
if [ "$AUDIT_RC" -eq 0 ]; then
    record audit PASS "brew audit --formula clean"
else
    record audit FINDINGS "brew audit --formula exited $AUDIT_RC — see log above"
fi

# ── why there is no `brew audit --new` stage ─────────────────────────────────
# There used to be one, recorded as INFO, on the theory that it reported
# homebrew-core submission rules. It reports nothing of the kind on a formula in
# a private tap, and a stage whose "clean" means "the checks did not run" is
# worse than no stage — it reads as an endorsement nobody earned.
#
# Every `--new`-only check in Library/Homebrew/formula_auditor.rb is gated on the
# core tap: audit_homepage_domain_age, audit_duplicate_formula, audit_bottle_spec
# and audit_specs each open with `return unless @core_tap`, and the four
# git-forge notability checks (audit_github_repository and its gitlab/bitbucket/
# forgejo siblings) reach it through get_repo_data, whose first line is
# `return unless @core_tap` (formula_auditor.rb:858 in Homebrew 7.0.6).
#
# Measured, not reasoned: against this formula in a throwaway tap,
# `brew audit --new` and `brew audit --strict --online` produce byte-identical
# output. `--new` implies exactly those two flags (dev-cmd/audit.rb:116-117) and
# adds nothing else here. Meanwhile SharedAudits.github("Dev-Toolbelt",
# "dev-team-agents") called directly DOES return "GitHub repository not notable
# enough (<30 forks, <30 watchers and <75 stars)" — so the check is not passing,
# it is unreachable.
#
# So run the two flags `--new` degrades to, under their own name. Unlike `--new`
# they mean something here: `--online` actually fetches the url, which is real
# coverage in release mode where the url is a live GitHub artifact.
AUDIT_STRICT_LOG="$TMP_ROOT/audit-strict.log"
AUDIT_STRICT_RC=0
say "stage: audit --strict --online (NOT homebrew-core eligibility — see comment above)"
brew audit --strict --online --formula "$TAP_FULL/$FORMULA_NAME" > "$AUDIT_STRICT_LOG" 2>&1 || AUDIT_STRICT_RC=$?
sed 's/^/    /' "$AUDIT_STRICT_LOG"
if [ "$AUDIT_STRICT_RC" -eq 0 ]; then
    record audit-strict PASS "brew audit --strict --online clean"
else
    record audit-strict FINDINGS "exited $AUDIT_STRICT_RC — see log above (does NOT fail this run)"
fi

# ── stage: install ──────────────────────────────────────────────────────────
stage install
FORMULA_SNAPSHOT="$TMP_ROOT/formulae-before.txt"
brew list --formula 2>/dev/null | sort > "$FORMULA_SNAPSHOT"
note "formulae installed before: $(wc -l < "$FORMULA_SNAPSHOT" | tr -d ' ')"

# Both flags are set BEFORE the install, so the teardown assumes the install MAY
# have happened. An install interrupted part-way through — the EXIT trap fires on
# SIGINT and SIGTERM — can already have poured a keg and pulled in the python
# dependency; flags set only after a SUCCESSFUL install would have reported that
# python as an untouchable transitive leftover instead of uninstalling it, which
# is the opposite of what this script's header promises. `remove_formula` reports
# on presence, so naming something that was never installed costs a note.
INSTALLED_FORMULA="yes"
if [ "$PY_DEP_PRESENT" = "no" ]; then
    INSTALLED_PY_DEP="$PY_DEP"
    note "$PY_DEP was absent before this run; teardown will remove it if the install pulled it in"
fi

note "brew install --build-from-source $TEMP_FORMULA"
if ! brew install --build-from-source "$TEMP_FORMULA" 2>&1 | sed 's/^/    /'; then
    die "brew install --build-from-source failed"
fi

BREW_PREFIX=$(brew --prefix)
DEVTEAM_BIN="$BREW_PREFIX/bin/devteam"
[ -x "$DEVTEAM_BIN" ] || die "formula installed but $DEVTEAM_BIN is not executable"
note "installed binary:  $DEVTEAM_BIN -> $(readlink "$DEVTEAM_BIN" 2>/dev/null || printf 'not a symlink')"

# bin.install_symlink writes a RELATIVE symlink, and the Cellar target is itself a
# symlink into libexec, so resolve the whole chain before reading the shebang.
REAL_BIN=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$DEVTEAM_BIN")
note "resolves to:       $REAL_BIN"
[ -f "$REAL_BIN" ] || die "the bin symlink does not resolve to a real file"
SHEBANG=$(head -1 "$REAL_BIN")
note "shebang:           $SHEBANG"

# The install block rewrites `#!/usr/bin/env python3` to the dependency's
# interpreter with `inreplace`. If that silently no-ops, the CLI would run on
# whatever python3 happens to be first on PATH — exactly what the dependency
# exists to prevent — so assert the rewrite actually happened.
PY_OPT_BIN="$(brew --prefix)/opt/$PY_DEP/bin"
case "$SHEBANG" in
    "#!$PY_OPT_BIN/"python*) note "verified: shebang was rewritten to the declared dependency's interpreter" ;;
    "#!/usr/bin/env python3") die "inreplace did not rewrite the shebang; it is still #!/usr/bin/env python3" ;;
    *) die "shebang is '$SHEBANG', expected an interpreter under $PY_OPT_BIN" ;;
esac

# The CLI resolves its package as parent.parent/"lib", so cli/ and lib/devteam
# must be siblings under libexec/scripts. Check the layout, not just the entry point.
LIBEXEC_DIR=$(dirname "$(dirname "$REAL_BIN")")
note "libexec layout:    $LIBEXEC_DIR"
[ -d "$LIBEXEC_DIR/lib/devteam" ] || die "libexec layout is wrong: $LIBEXEC_DIR/lib/devteam does not exist"
LIB_MODULES=$(find "$LIBEXEC_DIR/lib/devteam" -name '*.py' -type f | wc -l | tr -d ' ')
note "verified: lib/devteam is a sibling of cli/ ($LIB_MODULES modules)"

record install PASS "install block ran; shebang rewritten to $PY_DEP; cli/ and lib/devteam siblings under libexec"

# ── stage: brew test ────────────────────────────────────────────────────────
stage brewtest
note "brew test $FORMULA_NAME  (runs the formula's own test do block)"
TEST_RC=0
brew test --verbose "$FORMULA_NAME" 2>&1 | sed 's/^/    /' || TEST_RC=$?
if [ "$TEST_RC" -eq 0 ]; then
    record brewtest PASS "the formula's test do block passed"
else
    record brewtest FAIL "brew test exited $TEST_RC"
    die "brew test failed"
fi

# ── stage: smoke ────────────────────────────────────────────────────────────
# Independent of brew test: drive the INSTALLED binary directly, with
# DEVTEAM_HOME pointed at a throwaway dir. scripts/lib/devteam/paths.py documents
# DEVTEAM_HOME as the override seam for exactly this ("no test touches a real
# user directory"), so the machine's real store is neither read nor written.
stage smoke
SMOKE_HOME="$TMP_ROOT/devteam-home"
mkdir -p "$SMOKE_HOME"

check_json() {
    local label="$1"
    shift
    local out
    note "DEVTEAM_HOME=<temp> devteam $*"
    if ! out=$(DEVTEAM_HOME="$SMOKE_HOME" "$DEVTEAM_BIN" "$@" 2>&1); then
        printf '%s\n' "$out" | sed 's/^/      /'
        die "devteam $* exited non-zero"
    fi
    printf '%s\n' "$out" | sed 's/^/      /'
    printf '%s' "$out" | python3 -c '
import json, sys
label = sys.argv[1]
raw = sys.stdin.read()
try:
    data = json.loads(raw)          # loads(), not load-many: asserts ONE document
except Exception as exc:
    sys.stderr.write("%s: not a single valid JSON document: %s\n" % (label, exc))
    raise SystemExit(1)
if not isinstance(data, dict):
    sys.stderr.write("%s: top level is %s, expected object\n" % (label, type(data).__name__))
    raise SystemExit(1)
if data.get("ok") is not True:
    sys.stderr.write("%s: ok is %r, expected True\n" % (label, data.get("ok")))
    raise SystemExit(1)
sys.stderr.write("%s: single JSON object, ok=true\n" % label)
' "$label" || die "$label did not return a single JSON document with ok=true"
}

check_json "devteam path --json" path --json
check_json "devteam version --json" version --json

if [ -e "$SMOKE_HOME/core" ] || [ -e "$SMOKE_HOME/data" ]; then
    die "read-only commands created a store under DEVTEAM_HOME"
fi
note "verified: no core/ or data/ created under the temp DEVTEAM_HOME"
record smoke PASS "path --json and version --json each returned one JSON object with ok=true; no store created"

say "all stages complete — tearing down"
exit 0
