#!/usr/bin/env bash
# 30-contract.sh — Per-provider contract validation (schema, keys, cross-refs).
# Runs shared contracts (tiers.json completeness, commands.json cross-ref) plus
# the provider-specific contract from _contract.py.
#
# Usage: bash 30-contract.sh <provider> <repo-root> <staging-dir>
set -euo pipefail

PROVIDER="$1"
SOURCE="$2"
STAGING="$3"

python3 "$(dirname "${BASH_SOURCE[0]}")/_contract.py" \
  --provider "$PROVIDER" \
  --staging "$STAGING" \
  --source "$SOURCE"