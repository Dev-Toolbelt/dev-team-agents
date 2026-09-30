#!/usr/bin/env bash
# PreToolUse sub-script: runs the pre_tool_use hook of every ENABLED plugin (ADR-0018).
# Names no plugin - the hook path comes from each plugin's manifest.
#
# Runs on every tool call: with no plugin-settings directory, or no enabled file in it,
# it returns before forking anything. Never blocks a tool call - a failing plugin hook
# is ignored and the script exits 0.
set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
SETTINGS_DIR="$ROOT/.dev-team-agents/plugin-settings"
[ -d "$SETTINGS_DIR" ] || exit 0

HERE="${BASH_SOURCE[0]%/*}"
# shellcheck source=scripts/hooks/lib/plugins.sh
. "$HERE/../lib/plugins.sh"

shopt -s nullglob
ENABLED=()
for settings in "$SETTINGS_DIR"/*.json; do
    devteam_plugin_enabled "$settings" && ENABLED+=("$settings")
done
[ "${#ENABLED[@]}" -gt 0 ] || exit 0

INPUT=$(cat)
PLUGINS_DIR="$(devteam_plugins_dir)" || exit 0
NAME_RE='^[a-z][a-z0-9-]{1,31}$'

for settings in "${ENABLED[@]}"; do
    name="$(basename "$settings" .json)"
    [[ "$name" =~ $NAME_RE ]] || continue
    plugin_dir="$PLUGINS_DIR/$name"
    hook="$(devteam_plugin_hook "$plugin_dir" pre_tool_use)"
    [ -n "$hook" ] || continue
    (
        devteam_plugin_export_env "$ROOT" "$plugin_dir" "$settings"
        bash "$plugin_dir/$hook" <<<"$INPUT"
    ) || true
done

exit 0
