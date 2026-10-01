#!/usr/bin/env bash
# 05-app.sh — JavaScript/TypeScript gate for the Electron desktop client in app/.
#
# WHY THIS FILE EXISTS
# ====================
# ADR-0015 puts an Electron client under `app/` and its own Risks table names the
# hole that opens: "An Electron dependency tree lands in a repository with no
# JavaScript gate." Before this file CI's jobs were tag-name, lint (shellcheck),
# python, provider-contracts, slim-bootstrap and packaging — nothing read a
# package.json, ran tsc, or executed a test written in TypeScript. ADR-0009 set
# the precedent when python became load-bearing ("CI had no python gate at all"):
# the gate lands in the same change as the language, not after it.
#
# ENFORCEMENT POLICY
# ==================
# Same wrappers, same meaning, as `.github/scripts/ci/01-lint.sh`. Read that
# file's ENFORCEMENT POLICY header — it is the canonical statement and this
# script deliberately does not restate it.
#
# Only `blocking` is defined here. `advisory` exists to stage a check that has a
# backlog of pre-existing violations, and `app/` is new, so there is no backlog
# to stage and an always-empty advisory summary would be decoration. If that ever
# changes, copy the wrapper from 01-lint.sh verbatim rather than inventing a
# third tier.
#
# The exit-code nuance carries over and is load-bearing below: exit 1 is a
# finding, exit 2 or higher means the check itself could not run, and a check
# that could not run has not passed.
#
# THE CONTRACT THIS GATE RUNS AGAINST
# ===================================
# app/package.json must declare three npm scripts that complete with no display:
#
#   typecheck · lint · test
#
# plus `build`, run after lint and asserted to emit the main, preload and renderer entries.
#
# CI calls exactly those three and nothing else. The scripts that open a window
# (`start`, `dev:app`, `dev:renderer`) or produce an installer (`dist:mac`, `dist:win`,
# `dist:all`) are
# never invoked here: a gate that needs a display cannot run on a headless
# runner, and one that builds an unsigned artifact is shipping, not checking.
#
# WHEN IT RUNS
# ============
# Called by the `app` job in `.github/workflows/ci.yml`, which inherits the
# workflow trigger and adds nothing to it: every pull request, plus pushes to
# `main` and to tags. It is NOT "on every push" — a branch with no open PR gets
# no CI at all, a trade-off stated in ci.yml's own trigger-policy header.
#
# There is deliberately NO path filter on `app/**`. The app is a client of the
# CLI's `--json` output, which ADR-0011 makes public API; filtering would mean a
# change to `scripts/lib/devteam/` never exercises the only thing in the
# repository that consumes that output, and a contract breaking on the consumer
# side is exactly the failure a filter hides. The cost is bounded: the job runs
# concurrently with the other jobs, and setup-node caches the dependency tree
# keyed on app/package-lock.json, so the minutes a filter saves buy nothing the
# wall clock notices.
#
# NODE VERSION
# ============
# `app/.nvmrc` is the single pin and the only place the number is written. The
# precedent is `.github/shellcheck.pin`: pin the tool the gate's verdict depends
# on, keep exactly one copy of the version, and have the gate prove the binary on
# PATH is the pinned one rather than assuming it. `.nvmrc` rather than a
# workflow-level literal because actions/setup-node reads it through
# `node-version-file:` while `nvm use`, fnm and asdf read the same file — CI and a
# contributor's shell then obey one number instead of two.
#
# This script adds no second version fact. app/package.json already declares a
# floor in `engines.node`; the checks below assert the pin satisfies that floor
# and that the running interpreter satisfies both.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

APP_DIR="app"
PKG="$APP_DIR/package.json"
LOCK="$APP_DIR/package-lock.json"
NVMRC="$APP_DIR/.nvmrc"

blocking() {
  local label="$1"; shift
  echo "─ ${label} [BLOCKING] ──────────────────────────────────────"
  "$@"
}

# Exit 2, never 1: the distinction the policy header draws is between "the
# subject has a problem" and "the gate could not form a verdict". Everything
# routed through here is the second kind.
cannot_run() {
  echo "  CANNOT RUN — $1" >&2
  echo "  A check that could not run has not passed (01-lint.sh, ENFORCEMENT POLICY)." >&2
  exit 2
}

# ── Preflight ───────────────────────────────────────────────────────────────
# Runs with no node on PATH so the workflow can call it BEFORE actions/setup-node
# and fail with these messages instead of the action's "Unable to find .nvmrc".
#
# MISSING TREE POLICY — `app/` absent is a FAILURE, not a skip. A gate that
# passes when its subject is gone is indistinguishable from a gate that works,
# and this repository already refuses that trade: 01-lint.sh returns 2 for a
# missing shellcheck target, and 03-python.sh has no skip path at all. There is
# deliberately no env var or flag to bypass it. If the desktop client is ever
# removed, the commit that removes it deletes this script and its job — one
# visible edit in a reviewed diff, which is precisely what a skip switch hides
# and how a temporary skip becomes permanent.
preflight() {
  [ -d "$APP_DIR" ] \
    || cannot_run "no ${APP_DIR}/ directory. ADR-0015 puts the desktop client there; if it was removed, delete this script and the \`app\` job in ci.yml in the same commit."
  [ -f "$PKG" ] \
    || cannot_run "no ${PKG} — nothing declares the typecheck/lint/test scripts this gate calls."
  [ -f "$LOCK" ] \
    || cannot_run "no ${LOCK} — \`npm ci\` needs a committed lockfile, and a gate that resolves fresh versions on every run is not a gate."
  [ -f "$NVMRC" ] \
    || cannot_run "no ${NVMRC} — the node version must be pinned in one file that both actions/setup-node (node-version-file:) and \`nvm use\` read. Write a literal version there, e.g. 24.21.0."
  echo "  ${APP_DIR}/ present; ${LOCK##*/} and ${NVMRC##*/} in place"
}

case "${1:-}" in
  --preflight)
    blocking "app: preflight" preflight
    echo ""
    echo "app preflight OK ✓"
    exit 0
    ;;
  "") ;;
  *)
    echo "usage: ${0##*/} [--preflight]" >&2
    exit 2
    ;;
esac

# ── Helpers ─────────────────────────────────────────────────────────────────

# Component `$2` (1-based) of a dotted version, 0 when absent. `cut -d.` is wrong
# here: on the input "20" it returns "20" for every field index, so a major-only
# pin would compare as 20.20.20.
ver_part() {
  printf '%s' "$1" | awk -F. -v i="$2" '{ print ($i == "" ? 0 : $i) + 0 }'
}

# 0 when $1 >= $2, comparing three components numerically.
ver_ge() {
  local i a b
  for i in 1 2 3; do
    a="$(ver_part "$1" "$i")"
    b="$(ver_part "$2" "$i")"
    [ "$a" -gt "$b" ] && return 0
    [ "$a" -lt "$b" ] && return 1
  done
  return 0
}

# One field out of app/package.json, parsed by node rather than grepped. The
# main phase always has the pinned interpreter available, so there is no reason
# to read JSON with a regex.
pkg_get() {
  node -e '
    const fs = require("node:fs");
    const pkg = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
    const value = process.argv[2].split(".").reduce((o, k) => (o == null ? o : o[k]), pkg);
    process.stdout.write(value == null ? "" : String(value));
  ' "$PKG" "$1" || cannot_run "${PKG} could not be parsed as JSON (field '$1'). Every check below reads it, so none of them can form a verdict."
}

app_npm() { ( cd "$APP_DIR" && "$@" ); }

# The runner's output is captured so it can be searched for a test count, and
# printed either way — a truncated or swallowed log is how a real failure becomes
# unreadable. Created and cleaned up at this level so the trap is registered once.
TEST_LOG="$(mktemp)"
trap 'rm -f "$TEST_LOG"' EXIT

# ── Checks ──────────────────────────────────────────────────────────────────

# The pin is proven, not assumed. 01-lint.sh's shellcheck step exists because an
# unpinned checker produced a green local run and a red CI on one commit; the
# same reasoning applies to a typechecker, a linter and a test runner whose
# behaviour all move with the interpreter under them.
check_node_pin() {
  local pinned engines floor actual npm_actual i

  # Comments and blank lines are legal in .nvmrc; an alias (`lts/iron`, `node`)
  # is not accepted here, because an alias re-points under you and then the pin
  # names a moving target — which is the thing a pin exists to stop.
  # `|| true` because no match is a verdict this function reports itself; without
  # it the failing grep would abort under `set -e` with an exit code and no
  # explanation of what CI actually objected to.
  pinned="$(sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^v//' "$NVMRC" \
    | grep -E '^[0-9]+(\.[0-9]+)*$' | head -1 || true)"
  [ -n "$pinned" ] \
    || cannot_run "${NVMRC} does not contain a literal version. An alias such as lts/* re-points without a commit, so it cannot serve as the pin."

  engines="$(pkg_get engines.node)"
  [ -n "$engines" ] \
    || cannot_run "${PKG} declares no engines.node floor, so there is nothing for the pin to be checked against."

  # Only the `>=X.Y.Z` shape is understood. A wider range would need a semver
  # implementation, and guessing at one silently is worse than saying so.
  case "$engines" in
    '>='[0-9]*) floor="${engines#>=}" ;;
    *) cannot_run "engines.node is '${engines}'; this gate only understands a '>=X.Y.Z' floor. Widen the parser deliberately or narrow the declaration." ;;
  esac
  for i in $(printf '%s' "$floor" | tr '.' ' '); do
    case "$i" in
      ''|*[!0-9]*) cannot_run "engines.node floor '${floor}' is not a plain dotted version." ;;
    esac
  done

  actual="$(node -p 'process.versions.node')"
  npm_actual="$(npm --version)"
  echo "  node ${actual} (pinned ${pinned}, engines floor ${floor}) · npm ${npm_actual}"

  # Component-wise against the pin: a `20` pin constrains the major only, a
  # `20.19.0` pin constrains all three. Whatever precision the pin declares is
  # the precision enforced.
  for i in 1 2 3; do
    [ "$(ver_part "$pinned" "$i")" -eq 0 ] && continue
    if [ "$(ver_part "$actual" "$i")" -ne "$(ver_part "$pinned" "$i")" ]; then
      echo "  FAIL — node on PATH is ${actual}, but ${NVMRC} pins ${pinned}."
      echo "  The job must select the interpreter from ${NVMRC} (node-version-file:), not from the runner image."
      return 1
    fi
  done

  if ! ver_ge "$pinned" "$floor"; then
    echo "  FAIL — the pin ${pinned} is below the ${floor} floor in ${PKG} (engines.node)."
    echo "  Two version facts disagree; raise the pin or lower the floor, in one commit."
    return 1
  fi
  if ! ver_ge "$actual" "$floor"; then
    echo "  FAIL — node ${actual} is below the ${floor} floor in ${PKG} (engines.node)."
    return 1
  fi
}

# The three scripts are the contract. Asserting they exist before calling them
# turns "npm ERR! Missing script" into a message that says which contract broke.
check_script_contract() {
  local name value rc=0
  for name in typecheck lint test; do
    value="$(pkg_get "scripts.${name}")"
    if [ -z "$value" ]; then
      echo "  FAIL — ${PKG} declares no \`${name}\` script. CI calls typecheck, lint and test, and nothing else."
      rc=1
      continue
    fi
    echo "  ${name}: ${value}"
  done
  return "$rc"
}

# Reproducible install from the committed lockfile. `npm ci` rather than
# `npm install`: the latter is allowed to resolve newer versions and to rewrite
# the lockfile, so it would verify a dependency tree that no commit describes.
# --no-audit/--no-fund only quieten output; neither changes what is installed.
#
# --ignore-scripts is the one flag here that changes what runs. Three locked
# packages declare install scripts (electron-winstaller, esbuild, fsevents), and
# `npm ci` executes the ones `allowScripts` in package.json approves — a list a fork
# PR can edit along with the lockfile, on a runner it can reach. Measured before adding it: with the scripts skipped
# and no Electron binary downloaded at all, `typecheck` and `lint` are clean and
# every test that does not depend on the repository layout passes. This gate never
# launches Electron, so the binary those scripts fetch is not needed.
#
# REVERSE THIS if a test ever needs the real Electron runtime — an actual launch or
# a screen smoke test, which the v4 spec currently records as its unasserted gap.
# The symptom would be a module-not-found or a missing-binary error, and the fix is
# to drop the flag rather than to stub the runtime.
#
# ONE LOCAL COST, because `npm ci` reinstalls the tree: running this gate on a
# developer's machine removes the Electron binary. Electron 40+ downloads it again
# on the next `npm start`; to fetch it ahead of time:
#     node app/node_modules/electron/install.js
npm_ci() {
  app_npm npm ci --no-audit --no-fund --ignore-scripts
}

# Compiles with tsc + vite, neither of which needs the Electron binary that
# --ignore-scripts skips (esbuild resolves its binary from an optional dependency).
# Typecheck alone emits nothing, so this proves the shipped entry points exist.
run_build() {
  local f
  app_npm npm run build || return 1
  for f in dist/node/main/index.js dist/preload/index.js dist/renderer/index.html; do
    if [ ! -f "$APP_DIR/$f" ]; then
      echo "  FAIL — build succeeded but $APP_DIR/$f was not produced."
      return 1
    fi
  done
  echo "  build outputs present"
}

# Non-vacuity is the point of this check, not a bonus. A runner whose glob
# matches nothing is the failure mode worth catching: `vitest run` and `jest`
# both turn into an unconditional green the moment `--passWithNoTests` appears,
# and a moved test directory produces the same silence with no flag at all.
#
# Three independent assertions, because each catches a different way of ending
# up with zero executed tests:
#   1. at least one test file exists on disk;
#   2. the `test` script does not carry a pass-with-no-tests escape;
#   3. the runner reported a positive count of passing tests.
#
# WHICH modules must be covered is deliberately not asserted here. A hardcoded
# path (today the CLI invocation layer lives in app/src/cli/) breaks on the first
# rename, and a broken assertion gets deleted rather than fixed; coverage
# thresholds belong to app/'s own test config, where a rename moves with them.
run_tests() {
  local disk_count test_script log plain count esc rc=0

  disk_count="$(find "$APP_DIR" \
      \( -name node_modules -o -name build -o -name dist -o -name release \) -prune -o \
      -type f \( -name '*.test.*' -o -name '*.spec.*' \) -print 2>/dev/null \
    | wc -l | tr -d '[:space:]')"
  echo "  ${disk_count} test file(s) on disk under ${APP_DIR}/"
  if [ "${disk_count:-0}" -eq 0 ]; then
    echo "  FAIL — no *.test.* or *.spec.* file exists. A suite with nothing to match cannot fail,"
    echo "  which makes this gate's green meaningless for the code it is supposed to cover."
    return 1
  fi

  test_script="$(pkg_get scripts.test)"
  case "$test_script" in
    *passWithNoTests*)
      echo "  FAIL — the \`test\` script carries --passWithNoTests: '${test_script}'."
      echo "  That flag converts an empty run into a pass, which is the exact failure this check exists to catch."
      return 1
      ;;
  esac

  log="$TEST_LOG"

  # CI/NO_COLOR keep the summary free of escape sequences; the strip below is the
  # backstop for a runner that colours anyway.
  app_npm env CI=true NO_COLOR=1 FORCE_COLOR=0 npm test >"$log" 2>&1 || rc=$?
  esc="$(printf '\033')"
  plain="$(sed "s/${esc}\\[[0-9;]*[a-zA-Z]//g" "$log")"
  printf '%s\n' "$plain"
  [ "$rc" -eq 0 ] || return "$rc"

  if printf '%s\n' "$plain" | grep -qiE 'no test (files )?found'; then
    echo "  FAIL — the runner reported that it found no test files, and still exited 0."
    return 1
  fi

  # vitest: "Tests  12 passed (12)" · jest: "Tests:  12 passed, 12 total"
  count="$(printf '%s\n' "$plain" \
    | sed -n 's/.*[Tt]ests[:[:space:]][^0-9]*\([0-9][0-9]*\)[[:space:]]*passed.*/\1/p' | tail -1)"
  if [ -z "$count" ]; then
    # node:test's TAP-ish summary.
    count="$(printf '%s\n' "$plain" | sed -n 's/^# pass \([0-9][0-9]*\)$/\1/p' | tail -1)"
  fi
  [ -n "$count" ] \
    || cannot_run "no test count found in the runner's output. The runner or its reporter changed shape, so this gate can no longer tell a real pass from an empty one — teach the parser the new format rather than dropping the assertion."

  if [ "$count" -lt 1 ]; then
    echo "  FAIL — the suite exited 0 with ${count} passing tests."
    return 1
  fi
  echo "  ${count} test(s) executed and passed"
}

blocking "app: preflight" preflight
blocking "app: node pin" check_node_pin
blocking "app: npm script contract" check_script_contract
blocking "app: npm ci (from ${LOCK##*/})" npm_ci
blocking "app: typecheck" app_npm npm run typecheck
blocking "app: lint" app_npm npm run lint
blocking "app: build (entry points emitted)" run_build
blocking "app: unit tests (non-vacuous)" run_tests

echo ""
echo "app OK ✓"
