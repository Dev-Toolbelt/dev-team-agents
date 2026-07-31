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
# NOTE: agent-lint carries one internal ADVISORY sub-check — the 95-char skill
# `description` budget, gated by `SKILL_DESC_STRICT` in helpers/agent-lint.sh.
# PROMOTE WHEN: all skill descriptions are within the 95-char budget
# (20 are over today). Flip `SKILL_DESC_STRICT=false` → `true` in that helper.
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
# PROMOTE WHEN: every agent, skill and command is under its declared cap
# (i.e. `bash helpers/size-limits.sh` exits 0 on a clean tree).
advisory "size-limits" bash helpers/size-limits.sh

# Shell correctness across shipped scripts. Blocking: the tree is clean and a
# shellcheck finding in an installer or hook is a real runtime hazard.
blocking "shellcheck scripts + helpers" \
  find scripts helpers -name '*.sh' -exec shellcheck -x {} +

# ── Summary ─────────────────────────────────────────────────────────────────
if [ ${#ADVISORY_HITS[@]} -gt 0 ]; then
  echo ""
  echo "lint OK ✓ (with advisory findings: ${ADVISORY_HITS[*]})"
else
  echo ""
  echo "lint OK ✓"
fi
