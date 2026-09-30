#!/usr/bin/env bash
# Shared helpers for the plugin hook dispatchers (ADR-0018 section 4).
#
# Not a hook. Source this file, then call:
#   devteam_plugins_dir                              core plugins/ tree, physical path
#   devteam_plugin_settings_dir <project_root>       .dev-team-agents/plugin-settings
#   devteam_plugin_enabled <settings_file>           exit 0 when the file says enabled
#   devteam_plugin_hook <plugin_dir> <event>         prints the hook path (relative) or nothing
#   devteam_plugin_resolve_state_dir <root>          sets _DEVTEAM_PLUGIN_STATE_DIR once (forks git)
#   devteam_plugin_export_env <root> <plugin_dir> <settings_file>
#   devteam_plugin_effective_config <plugin_dir> <settings_file>   (python3; Stop path only)
#
# PreToolUse runs on every tool call, so the enabled/hook lookups below are builtin-only
# (no fork, no JSON parser). The CLI writes settings with json.dumps(indent=2,
# sort_keys=True), so a top-level key sits on its own line at two spaces of indent; that
# canonical line decides when present. A minified or re-indented file has no such line,
# and is matched by a whitespace-tolerant `"enabled": true` pattern instead.

# devteam_plugins_dir: <core>/plugins, resolved physically. In a bound project
# .dev-team-agents/scripts is a symlink into the core, and so is .dev-team-agents/plugins.
devteam_plugins_dir() {
    (cd -P "$(dirname "${BASH_SOURCE[0]}")/../../../plugins" 2>/dev/null && pwd)
}

devteam_plugin_settings_dir() {
    printf '%s\n' "$1/.dev-team-agents/plugin-settings"
}

devteam_plugin_enabled() {
    local file="$1" content
    [ -f "$file" ] || return 1
    content="$(<"$file")" 2>/dev/null || return 1
    # Canonical form first: a nested config key that is itself called "enabled" must not
    # be mistaken for the top-level one.
    [[ "$content" == *$'\n  "enabled": true'* ]] && return 0
    [[ "$content" == *$'\n  "enabled": '* ]] && return 1
    [[ "$content" =~ \"enabled\"[[:space:]]*:[[:space:]]*true ]]
}

devteam_plugin_hook() {
    local plugin_dir="$1" event="$2" content rel
    [ -f "$plugin_dir/plugin.json" ] || return 0
    content="$(<"$plugin_dir/plugin.json")" 2>/dev/null || return 0
    [[ "$content" =~ \"$event\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]] || return 0
    rel="${BASH_REMATCH[1]}"
    case "$rel" in
        /*|..|../*|*/..|*/../*) return 0 ;;
    esac
    [ -f "$plugin_dir/$rel" ] || return 0
    printf '%s\n' "$rel"
}

# Exports DEVTEAM_PROJECT_ROOT, DEVTEAM_PLUGIN_DIR, DEVTEAM_PLUGIN_SETTINGS and
# DEVTEAM_STATE_DIR (an already-set DEVTEAM_STATE_DIR wins). DEVTEAM_PLUGIN_CONFIG is deliberately NOT set here: computing it
# needs python3, which the PreToolUse hot path cannot afford. Hooks that need config
# read the settings file themselves, or the Stop dispatcher adds it.
devteam_plugin_resolve_state_dir() {
    local root="$1" common main
    if [ -n "${_DEVTEAM_PLUGIN_STATE_DIR:-}" ]; then
        return 0
    fi
    if [ -n "${DEVTEAM_STATE_DIR:-}" ]; then
        _DEVTEAM_PLUGIN_STATE_DIR="$DEVTEAM_STATE_DIR"
        return 0
    fi
    common="$(cd "$root" && git rev-parse --git-common-dir 2>/dev/null)" || common=""
    if [ -n "$common" ]; then
        main="$(cd "$root" && cd "$common/.." && pwd)" || main="$root"
    else
        main="$root"
    fi
    # shellcheck source=scripts/hooks/lib/data-dirs.sh
    . "$(dirname "${BASH_SOURCE[0]}")/data-dirs.sh"
    _DEVTEAM_PLUGIN_STATE_DIR="$(STATE_FILE='' USER_DATA_DIR='' devteam_state_dir "$main")"
}

devteam_plugin_export_env() {
    local root="$1" plugin_dir="$2" settings="$3"
    devteam_plugin_resolve_state_dir "$root"
    export DEVTEAM_PROJECT_ROOT="$root"
    export DEVTEAM_PLUGIN_DIR="$plugin_dir"
    export DEVTEAM_PLUGIN_SETTINGS="$settings"
    export DEVTEAM_STATE_DIR="$_DEVTEAM_PLUGIN_STATE_DIR"
}

# Manifest defaults merged with the settings file's config, as compact JSON.
# Prints nothing (and returns 0) when python3 or the files are unavailable.
devteam_plugin_effective_config() {
    command -v python3 >/dev/null 2>&1 || return 0
    python3 - "$1/plugin.json" "$2" <<'PY' 2>/dev/null || true
import json, sys
manifest = json.load(open(sys.argv[1]))
settings = json.load(open(sys.argv[2]))
config = {f["key"]: f.get("default") for f in manifest.get("config", []) if "key" in f}
config.update(settings.get("config") or {})
print(json.dumps(config, sort_keys=True))
PY
}
