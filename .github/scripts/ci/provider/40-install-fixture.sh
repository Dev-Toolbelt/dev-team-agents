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
  opencode) OWN=".opencode/agents/project-own.md"; CLASH=".opencode/agents/backend-developer.md" ;;
  codex)    OWN=".codex/agents/project-own.toml";  CLASH=".codex/agents/backend-developer.toml" ;;
  *)
    echo "40-install-fixture: unknown provider '$PROVIDER'" >&2; exit 2 ;;
esac
INSTALLER="$SOURCE/scripts/install-${PROVIDER}.sh"

# Ownership: a file the project authored next to the framework's must survive.
mkdir -p "$(dirname "$OWN")"
echo "project-own" > "$OWN"
bash "$INSTALLER" --source "$SOURCE" >/dev/null
bash "$INSTALLER" --source "$SOURCE" >/dev/null   # idempotent: the ledger claims its own files
[[ "$(cat "$OWN")" == "project-own" ]] || { echo "40-install-fixture: $OWN was modified" >&2; exit 1; }

# A project file at a name the framework writes: refused with exit 4, untouched.
CLASH_FIXTURE="$(mktemp -d)"
mkdir -p "$CLASH_FIXTURE/$(dirname "$CLASH")"
echo "project-own" > "$CLASH_FIXTURE/$CLASH"
set +e
( cd "$CLASH_FIXTURE" && bash "$INSTALLER" --source "$SOURCE" >/dev/null 2>&1 )
status=$?
set -e
[[ $status -eq 4 ]] || { echo "40-install-fixture: expected exit 4 on a collision, got $status" >&2; exit 1; }
[[ "$(cat "$CLASH_FIXTURE/$CLASH")" == "project-own" ]] || { echo "40-install-fixture: $CLASH was overwritten" >&2; exit 1; }
rm -rf "$CLASH_FIXTURE"
rm -f "$OWN"

echo "fixture install OK ✓  ($PROVIDER)"