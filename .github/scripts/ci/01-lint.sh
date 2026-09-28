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

# Shell correctness across shipped scripts. Blocking: the tree is clean and any
# finding in an installer or hook is a real runtime hazard. (Do not start a
# comment line with the tool's own name followed by a space — shellcheck parses
# that as a directive and errors out, silently disabling checks in this file.)
# --source-path=SCRIPTDIR makes shellcheck resolve a `source=` directive relative
# to the sourcing script rather than to the invocation's working directory. Without
# it, every hook sub-script that sources ../lib/ raises SC1091 for a file that is
# right there on disk — and any finding, even info-level, exits non-zero. That was
# a red build caused by the checker's path resolution, not by the tree.
#
# The version is printed because this gate's verdict depends on it and nothing pins it:
# CI uses whatever shellcheck the runner image ships, a contributor uses whatever their
# machine has, and the two disagree. That is not hypothetical — a clean local run and a
# red CI on the same commit were traced to 0.11.0 no longer emitting an SC2317 false
# positive that the runner's older build still does. Until the version is pinned, the
# log is what makes the next divergence diagnosable in one look instead of one bisect.
echo "─ shellcheck version ──────────────────────────────────────────"
shellcheck --version | sed -n 's/^version: /  shellcheck /p'
blocking "shellcheck scripts + helpers" \
  find scripts helpers -name '*.sh' -exec shellcheck -x --source-path=SCRIPTDIR {} +

# ── Summary ─────────────────────────────────────────────────────────────────
if [ ${#ADVISORY_HITS[@]} -gt 0 ]; then
  echo ""
  echo "lint OK ✓ (with advisory findings: ${ADVISORY_HITS[*]})"
else
  echo ""
  echo "lint OK ✓"
fi
