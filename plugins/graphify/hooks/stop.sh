#!/usr/bin/env bash
# Graphify plugin, Stop: rebuild the graph when a source path changed structurally.
# Opt-in per project through the `auto_refresh` config key (default false).
set -euo pipefail

QUIET=""
for arg in "$@"; do
  [ "$arg" = "--quiet" ] && QUIET="--quiet"
done

[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

SELF_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(dirname "$SELF_DIR")"
# shellcheck source=plugins/graphify/lib/config.sh
. "$PLUGIN_DIR/lib/config.sh"

ROOT="${DEVTEAM_PROJECT_ROOT:-$PWD}"
CONFIG_JSON="$(graphify_config_json "$ROOT")" || exit 0
[ "$(graphify_cfg_bool "$CONFIG_JSON" auto_refresh)" = "true" ] || exit 0
command -v graphify >/dev/null 2>&1 || exit 0

exec bash "$PLUGIN_DIR/scripts/refresh.sh" --if-changed ${QUIET:+"$QUIET"}
