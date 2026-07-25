#!/usr/bin/env bash
# 40-install-fixture.sh — Install the rendered provider into a throwaway
# fixture project.
#
# For opencode and Codex: the installers take --source and run from the local
# checkout, so they exercise the PR's own code. For Claude: install.sh
# downloads a tarball from GitHub by design, which would test the main branch
# rather than the PR's changes and require network — Claude's coverage comes
# from contract.sh against the rendered staging tree alone (no install step).
#
# Usage: bash 40-install-fixture.sh <provider> <repo-root> <fixture-dir>
# Exits 0 with "skipped" message for claude.
set -euo pipefail

PROVIDER="$1"
FIXTURE="$3"

if [ "$PROVIDER" = "claude" ]; then
  echo "claude fixture install: skipped (Claude installer downloads from network; covered by contract.sh against staging)"
  exit 0
fi

SOURCE="$2"
mkdir -p "$FIXTURE"
cd "$FIXTURE"
git init -q 2>/dev/null || true

case "$PROVIDER" in
  opencode)
    bash "$SOURCE/scripts/install-opencode.sh" --source "$SOURCE" >/dev/null
    ;;
  codex)
    bash "$SOURCE/scripts/install-codex.sh" --source "$SOURCE" >/dev/null
    ;;
  *)
    echo "40-install-fixture: unknown provider '$PROVIDER'" >&2; exit 2 ;;
esac

echo "fixture install OK ✓  ($PROVIDER)"