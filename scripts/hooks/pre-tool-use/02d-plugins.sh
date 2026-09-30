#!/usr/bin/env bash
# PreToolUse sub-script: runs the pre_tool_use hook of every ENABLED plugin (ADR-0019).
# Names no plugin - the hook path comes from each plugin's manifest.
#
# Runs on every tool call: with no plugin-settings directory, no enabled file in it, or
# no enabled plugin that declares a pre_tool_use hook, it returns before forking anything.
# Never blocks a tool call - a failing plugin hook is ignored and the script exits 0.
#
# Only ONE hook output can be honoured per tool call (the provider reads a single
# hookSpecificOutput), so hooks run in name order and the dispatcher stops at the first
# one that prints something; later hooks are not run, so any once-per-session marker they
# keep stays unspent and they get their turn on a later call. DEVTEAM_HOOK_DEBUG names
# the hooks that were skipped this way.
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

PLUGINS_DIR="$(devteam_plugins_dir)" || exit 0
NAME_RE='^[a-z][a-z0-9-]{1,31}$'

# Resolve which enabled plugins have a hook before any fork-heavy work.
HOOK_PLUGINS=()
HOOK_PATHS=()
HOOK_SETTINGS=()
for settings in "${ENABLED[@]}"; do
    name="$(basename "$settings" .json)"
    [[ "$name" =~ $NAME_RE ]] || continue
    hook="$(devteam_plugin_hook "$PLUGINS_DIR/$name" pre_tool_use)"
    [ -n "$hook" ] || continue
    HOOK_PLUGINS+=("$name")
    HOOK_PATHS+=("$PLUGINS_DIR/$name/$hook")
    HOOK_SETTINGS+=("$settings")
done
[ "${#HOOK_PLUGINS[@]}" -gt 0 ] || exit 0

INPUT=$(cat)
devteam_plugin_resolve_state_dir "$ROOT" || true

for i in "${!HOOK_PLUGINS[@]}"; do
    name="${HOOK_PLUGINS[$i]}"
    output="$(
        devteam_plugin_export_env "$ROOT" "$PLUGINS_DIR/$name" "${HOOK_SETTINGS[$i]}"
        bash "${HOOK_PATHS[$i]}" <<<"$INPUT" || true
    )" || output=""
    if [ -n "$output" ]; then
        printf '%s\n' "$output"
        if [ -n "${DEVTEAM_HOOK_DEBUG:-}" ]; then
            for skipped in "${HOOK_PLUGINS[@]:$((i + 1))}"; do
                echo "[devteam:plugin:$skipped] pre_tool_use hook skipped: '$name' already produced output" >&2
            done
        fi
        break
    fi
done

exit 0
