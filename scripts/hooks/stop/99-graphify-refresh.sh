#!/usr/bin/env bash
# Stop sub-script: rebuild the Graphify knowledge graph after each session.
# Uses 99- prefix (cleanup tier) per the Stop hook convention.
# graphify-refresh.sh exits 0 silently when graphify is not installed or not configured.
set -euo pipefail
bash "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)/scripts/graphify-refresh.sh"
