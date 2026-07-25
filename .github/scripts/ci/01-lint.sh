#!/usr/bin/env bash
# 01-lint.sh — Frontmatter, orphan scan, fingerprint uniqueness, size limits,
# and shellcheck. Exits non-zero on any hard failure.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "─ agent-lint ──────────────────────────────────────────────"
bash helpers/agent-lint.sh

echo "─ orphan-skill-scan (non-blocking) ───────────────────────"
bash helpers/orphan-skill-scan.sh || true

echo "─ check-fingerprint-uniqueness ────────────────────────────"
bash helpers/check-fingerprint-uniqueness.sh

echo "─ size-limits (--warn-only) ──────────────────────────────"
bash helpers/size-limits.sh --warn-only

echo "─ shellcheck scripts + helpers ───────────────────────────"
find scripts helpers -name '*.sh' -exec shellcheck {} +

echo "lint OK ✓"