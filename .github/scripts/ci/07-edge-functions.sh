#!/usr/bin/env bash
# 07-edge-functions.sh — deno tests for the Supabase Edge Functions (ADR-0029).
#
# The entitlement and account-delete functions mint and verify the signed tokens the CLI
# trusts, so their tests are a release gate. They need no network and no secrets.
# `infra/supabase/config.toml` is checked by tests/test_supabase_config.py, which the python
# gate (03-python.sh) already discovers.
#
# deno is installed by the workflow. Locally a missing deno is a skip with a note; under CI
# (CI=true) it is a failure, so a broken setup step cannot turn this gate into a no-op.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO_ROOT/infra/supabase"

if ! command -v deno >/dev/null 2>&1; then
    if [ "${CI:-}" = "true" ]; then
        echo "deno is not installed; the workflow's setup-deno step should have provided it." >&2
        exit 1
    fi
    echo "edge functions: skipped (deno not installed; https://deno.com)"
    exit 0
fi

echo "─ edge functions: deno test ────────────────────────────────"
deno --version | head -1
deno test --no-lock -q functions/

echo ""
echo "edge functions OK ✓"
