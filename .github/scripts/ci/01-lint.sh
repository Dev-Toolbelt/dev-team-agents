#!/usr/bin/env bash
# 01-lint.sh — repository hygiene gate (frontmatter, orphan scan, fingerprint
# uniqueness, size limits, shellcheck).
#
# ENFORCEMENT POLICY
# ==================
# Every check below runs through exactly one of two wrappers. There is no third
# tier and no bare invocation — if you add a check, you must pick a wrapper.
#
#   blocking <label> <cmd…>
#     Findings fail the build. Use when the check is (a) deterministic, (b) has
#     zero known violations in the tree today, and (c) a violation is either a
#     correctness bug or something a contributor can fix in the same PR that
#     introduced it. Nothing merges past a blocking finding.
#
#   advisory <label> <cmd…>
#     Findings are printed and the build stays green. Use ONLY as a staging area
#     for a check that is destined to become blocking but currently has a known
#     backlog of pre-existing violations. An advisory check is a debt marker,
#     not a permanent state: each one below carries a `PROMOTE WHEN:` note
#     stating the exact condition that must hold before it flips.
#
#   Promotion is a ONE-LINE change: swap the word `advisory` for `blocking` on
#   the invocation line. Do not add flags, env vars or extra tiers to express
#   "sort of blocking" — that ambiguity is what this policy replaced.
#
#   Exit-code nuance: `advisory` softens *findings* (exit 1) only. An exit code
#   of 2 or higher means the check itself broke (syntax error, bad usage,
#   missing dependency) and always fails the build — a check that cannot run is
#   not a check that passed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

ADVISORY_HITS=()

blocking() {
  local label="$1"; shift
  echo "─ ${label} [BLOCKING] ──────────────────────────────────────"
  "$@"
}

advisory() {
  local label="$1"; shift
  echo "─ ${label} [ADVISORY] ──────────────────────────────────────"
  local rc=0
  "$@" || rc=$?
  if [ "$rc" -ge 2 ]; then
    echo "  ${label} failed to run (exit ${rc}) — that is always blocking."
    return "$rc"
  fi
  if [ "$rc" -ne 0 ]; then
    echo "  ADVISORY — findings above do NOT fail the build. See PROMOTE WHEN in this script."
    ADVISORY_HITS+=("$label")
  fi
  return 0
}

# ── Checks ──────────────────────────────────────────────────────────────────

# Frontmatter/schema validation. Blocking: the tree is clean and a malformed
# agent or skill header breaks loading at runtime.
# agent-lint is fully blocking as of 2026-07-31 — the 95-char skill `description`
# budget was its last advisory sub-check, and every violator has been trimmed
# (`SKILL_DESC_STRICT=true` in helpers/agent-lint.sh).
blocking "agent-lint" bash helpers/agent-lint.sh

# Plugin manifests (plugins/*/plugin.json) against the ADR-0017 schema rules.
blocking "plugin-lint" bash helpers/plugin-lint.sh

# A skill with no agent referencing it is dead weight, not a broken build, and
# the scan is heuristic (it matches path and backtick-name references, so it can
# miss an indirect load).
# PROMOTE WHEN: the scan reports zero orphans on a clean tree AND its matching
# is proven non-heuristic enough to not produce false positives.
advisory "orphan-skill-scan" bash helpers/orphan-skill-scan.sh

# Duplicate fingerprints silently break install/update identity resolution.
# Blocking: zero known violations, and a collision is a correctness bug.
blocking "check-fingerprint-uniqueness" bash helpers/check-fingerprint-uniqueness.sh

# Agent/skill/command line caps. NOT blocking today: 11 of 17 agents exceed the
# 200-line agent cap. Enforcing now would fail every PR regardless of content.
# The helper's own `--warn-only` flag is deliberately NOT passed — the wrapper
# owns the blocking decision, so promotion stays a one-line change here.
# PROMOTED 2026-07-31: every agent, skill and command is now under its declared
# cap (17/17 agents, 25/25 commands, 138/138 skills). The condition below held,
# so this is blocking. Do not demote it to buy room for one oversized file —
# extract to a skill, which is what the cap exists to force.
blocking "size-limits" bash helpers/size-limits.sh

# Shell correctness across every shell script in the repository. Blocking: the
# tree is clean and any finding in an installer, a hook or a CI script is a real
# runtime hazard. (Do not start a comment line with the tool's own name followed
# by a space — shellcheck parses that as a directive and errors out, silently
# disabling checks in this file.)
#
# TARGET SET — the gate used to lint `scripts helpers` only, which left every
# script in this very directory, in .github/scripts/release/ and in packaging/
# unchecked: the gate did not cover the scripts that run the gate. Pinning a
# checker version to make a verdict trustworthy and then aiming it away from CI's
# own shell is a hole, so all four trees are in the set. Adding a tree is one
# entry in SHELLCHECK_TARGETS below — do not add a second shellcheck invocation.
# --source-path=SCRIPTDIR makes shellcheck resolve a `source=` directive relative
# to the sourcing script rather than to the invocation's working directory. Without
# it, every hook sub-script that sources ../lib/ raises SC1091 for a file that is
# right there on disk — and any finding, even info-level, exits non-zero. That was
# a red build caused by the checker's path resolution, not by the tree.
#
# The version is checked, not just used. This gate's verdict depends on it: the runner
# image shipped 0.9.0 while a contributor had 0.11.0, and 0.11.0 no longer emits an
# SC2317 false positive that 0.9.0 still does — a clean local run and a red CI on the
# same commit. CI now installs exactly the pinned version (see the workflow step that
# reads `.github/shellcheck.pin`); this check is what tells a contributor running the
# gate by hand that their result may not be the one CI will produce.
#
# A mismatch is advisory rather than blocking on purpose. CI is pinned, so this can only
# fire locally, and refusing to lint at all because someone's package manager is a minor
# version behind trades a real check for a version complaint. The warning names the
# direction that actually bites: a NEWER shellcheck finds fewer things, so it hands you a
# green that CI will not honour.
echo "─ shellcheck version ──────────────────────────────────────────"
SHELLCHECK_PIN_FILE="$REPO_ROOT/.github/shellcheck.pin"
SHELLCHECK_PINNED="$(sed -n 's/^version=//p' "$SHELLCHECK_PIN_FILE" 2>/dev/null)"
SHELLCHECK_ACTUAL="$(shellcheck --version 2>/dev/null | sed -n 's/^version: //p')"
echo "  shellcheck ${SHELLCHECK_ACTUAL:-unknown} (pinned: ${SHELLCHECK_PINNED:-unknown})"
if [ -z "$SHELLCHECK_PINNED" ]; then
  echo "  cannot read the pinned version from ${SHELLCHECK_PIN_FILE} — findings below may not match CI."
  ADVISORY_HITS+=("shellcheck-pin-unreadable")
elif [ "$SHELLCHECK_ACTUAL" != "$SHELLCHECK_PINNED" ]; then
  echo "  MISMATCH — CI runs ${SHELLCHECK_PINNED}. A newer shellcheck reports fewer findings,"
  echo "  so a green here can still fail CI. Install ${SHELLCHECK_PINNED} to reproduce the gate."
  ADVISORY_HITS+=("shellcheck-version-mismatch")
fi
# Quoted array expansion, never a bare glob list: the entries are literal paths
# and must reach `find` as-is. An unquoted list here would be re-globbed against
# the working tree, which this repository has been bitten by before.
SHELLCHECK_TARGETS=(scripts helpers .github/scripts packaging)

# Preconditions are part of the check, not a third tier. A missing target
# directory and an empty target set both mean the gate did not lint what its
# label claims, so both return 2 — "the check itself broke" per the exit-code
# nuance in the policy header, because a check that cannot run has not passed.
# Only shellcheck's own findings return 1, which is what `blocking` is judging.
shellcheck_targets() {
  local dir missing=0 count
  for dir in "${SHELLCHECK_TARGETS[@]}"; do
    [ -d "$dir" ] && continue
    echo "  MISSING target directory: ${dir}"
    missing=1
  done
  if [ "$missing" -ne 0 ]; then
    echo "  A target tree was renamed or removed without updating SHELLCHECK_TARGETS."
    return 2
  fi
  # Counted by NUL bytes from -print0, so the number is right even for a
  # filename containing spaces or newlines.
  count="$(find "${SHELLCHECK_TARGETS[@]}" -name '*.sh' -print0 \
    | tr -dc '\000' | wc -c | tr -d '[:space:]')" || return 2
  if [ "${count:-0}" -eq 0 ]; then
    echo "  no *.sh found under: ${SHELLCHECK_TARGETS[*]} — linting nothing is not passing."
    return 2
  fi
  echo "  ${count} shell script(s) under: ${SHELLCHECK_TARGETS[*]}"
  # -exec … + passes filenames as argv, so no path is ever word-split.
  find "${SHELLCHECK_TARGETS[@]}" -name '*.sh' \
    -exec shellcheck -x --source-path=SCRIPTDIR {} +
}
blocking "shellcheck ${SHELLCHECK_TARGETS[*]}" shellcheck_targets

# ── Summary ─────────────────────────────────────────────────────────────────
if [ ${#ADVISORY_HITS[@]} -gt 0 ]; then
  echo ""
  echo "lint OK ✓ (with advisory findings: ${ADVISORY_HITS[*]})"
else
  echo ""
  echo "lint OK ✓"
fi
