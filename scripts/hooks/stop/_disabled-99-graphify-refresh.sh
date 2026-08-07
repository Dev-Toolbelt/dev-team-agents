#!/usr/bin/env bash
# DISABLED (2026-08-06) — Graphify refresh is now on-demand only, not automatic
# on every Stop. Run manually: bash .dev-team-agents/scripts/graphify-refresh.sh
# See CLAUDE-md/hooks.md § Disabled Hooks.
# Stop sub-script: rebuild the Graphify knowledge graph after each session.
# Uses 99- prefix (cleanup tier) per the Stop hook convention.
# graphify-refresh.sh exits 0 silently when graphify is not installed or not configured.
set -euo pipefail

# Fast-path: skip immediately when dispatcher reports no session changes —
# same gate every other stop/02-*/03-* script uses, so a no-op session doesn't
# pay for a full graph rebuild.
[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/scripts/graphify-refresh.sh"
