#!/usr/bin/env bash
# 03-python.sh — python gate for the devteam CLI.
#
# Until v3 the repository had NO python check at all: 01-lint.sh runs shellcheck
# over `scripts` and `helpers`, and shellcheck does not read `*.py`. The most
# complex logic in the tree (store resolution, bind, migration) is now python, so
# a syntax error or a broken invariant would have reached users unseen.
#
# Blocking by policy: the tree is clean today, and both checks are deterministic.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT"

echo "─ python: byte-compile ─────────────────────────────────────"
python3 -m compileall -q scripts/lib/devteam scripts/lib/render_provider.py
python3 -m py_compile scripts/cli/devteam
echo "  compiled OK"

echo "─ python: unit tests ───────────────────────────────────────"
# Neither -v nor a `tail` window: with -v the per-test lines fill any window, and
# a truncated log drops exactly the traceback an operator needs. unittest's
# default output is already compact and puts every failure at the end.
python3 --version
python3 -m unittest discover -s tests -t tests

echo ""
echo "python OK ✓"
