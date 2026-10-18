#!/usr/bin/env bash
# Stop sub-script: runs the stop hook of every ENABLED plugin (ADR-0019).
# Names no plugin - the hook path comes from each plugin's manifest. A plugin hook that
# fails is reported on stderr but does not fail the Stop: nothing here needs the user
# to act before the session can end.
set -euo pipefail

# The Stop dispatcher passes no arguments to its sub-scripts, so quiet is this script's
# own default; DEVTEAM_HOOK_DEBUG turns the plugins' progress output back on.
QUIET="--quiet"
[ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && QUIET=""

[ "${DEVTEAM_NO_CHANGES:-0}" = "1" ] && exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
SETTINGS_DIR="$ROOT/.dev-team-agents/plugin-settings"
[ -d "$SETTINGS_DIR" ] || exit 0

HERE="${BASH_SOURCE[0]%/*}"
# shellcheck source=scripts/hooks/lib/plugins.sh
. "$HERE/../lib/plugins.sh"

PLUGINS_DIR="$(devteam_plugins_dir)" || exit 0
NAME_RE='^[a-z][a-z0-9-]{1,31}$'

shopt -s nullglob
for settings in "$SETTINGS_DIR"/*.json; do
    devteam_plugin_enabled "$settings" || continue
    name="$(basename "$settings" .json)"
    [[ "$name" =~ $NAME_RE ]] || continue
    plugin_dir="$PLUGINS_DIR/$name"
    hook="$(devteam_plugin_hook "$plugin_dir" stop)"
    [ -n "$hook" ] || continue
    rc=0
    (
        devteam_plugin_export_env "$ROOT" "$plugin_dir" "$settings"
        DEVTEAM_PLUGIN_CONFIG="$(devteam_plugin_effective_config "$plugin_dir" "$settings")"
        export DEVTEAM_PLUGIN_CONFIG
        bash "$plugin_dir/$hook" ${QUIET:+"$QUIET"}
    ) || rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "[devteam:plugin:$name] stop hook exited $rc" >&2
    fi
done

exit 0
