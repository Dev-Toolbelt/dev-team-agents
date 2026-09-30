#!/usr/bin/env bash
# Effective graphify config, shared by scripts/refresh.sh and hooks/stop.sh.
# Sourced, never executed.
#
# Source order (ADR-0017): DEVTEAM_PLUGIN_CONFIG (JSON, set by `devteam plugin run`
# and by the Stop dispatcher) -> .config of plugin-settings/graphify.json ->
# the legacy .dev-team-agents/user-data/graphify.json.
#
#   graphify_config_json <project_root>     prints the config object; exit 1 when no source exists
#   graphify_cfg_bool <json> <key>          prints true|false
#   graphify_cfg_list <json> <key>          prints one item per line

graphify_config_json() {
    local root="$1" settings legacy
    if [ -n "${DEVTEAM_PLUGIN_CONFIG:-}" ]; then
        printf '%s\n' "$DEVTEAM_PLUGIN_CONFIG"
        return 0
    fi
    settings="${DEVTEAM_PLUGIN_SETTINGS:-$root/.dev-team-agents/plugin-settings/graphify.json}"
    legacy="$root/.dev-team-agents/user-data/graphify.json"
    if [ -f "$settings" ]; then
        _graphify_json_extract "$settings" config
        return 0
    fi
    if [ -f "$legacy" ]; then
        _graphify_json_extract "$legacy" ""
        return 0
    fi
    return 1
}

# _graphify_json_extract <file> <key-or-empty>: compact JSON of .<key> (or the whole file).
_graphify_json_extract() {
    local file="$1" key="$2"
    if command -v jq >/dev/null 2>&1; then
        if [ -n "$key" ]; then jq -c --arg k "$key" '.[$k] // {}' "$file" 2>/dev/null || echo '{}'
        else jq -c '.' "$file" 2>/dev/null || echo '{}'; fi
    elif command -v python3 >/dev/null 2>&1; then
        python3 - "$file" "$key" <<'PY' 2>/dev/null || echo '{}'
import json, sys
data = json.load(open(sys.argv[1]))
if sys.argv[2]:
    data = data.get(sys.argv[2]) or {}
print(json.dumps(data))
PY
    else
        echo '{}'
    fi
}

graphify_cfg_bool() {
    local json="$1" key="$2"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$json" | jq -r --arg k "$key" 'if .[$k] == true then "true" else "false" end' 2>/dev/null || echo false
    elif command -v python3 >/dev/null 2>&1; then
        printf '%s' "$json" | python3 -c 'import json,sys
try: print("true" if json.load(sys.stdin).get(sys.argv[1]) is True else "false")
except Exception: print("false")' "$key"
    else
        case "$json" in *"\"$key\": true"*|*"\"$key\":true"*) echo true ;; *) echo false ;; esac
    fi
}

graphify_cfg_list() {
    local json="$1" key="$2"
    if command -v jq >/dev/null 2>&1; then
        printf '%s' "$json" | jq -r --arg k "$key" '.[$k][]? // empty' 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        printf '%s' "$json" | python3 -c 'import json,sys
try:
    for v in json.load(sys.stdin).get(sys.argv[1]) or []: print(v)
except Exception: pass' "$key"
    fi
}
