#!/usr/bin/env bash
# DEPRECATED: the logic lives in plugins/graphify/scripts/refresh.sh (ADR-0018).
# This wrapper is removed in the next minor release after the plugin system lands.
set -euo pipefail

SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "graphify-refresh.sh is deprecated and will be removed in the next minor release; use 'devteam plugin run graphify rebuild'." >&2

exec bash "$SCRIPT_DIR/../plugins/graphify/scripts/refresh.sh" --if-changed "$@"
