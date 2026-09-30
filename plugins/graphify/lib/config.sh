#!/usr/bin/env bash
# Effective graphify config, shared by scripts/refresh.sh and hooks/stop.sh.
# Sourced, never executed.
#
# Source order (ADR-0018): DEVTEAM_PLUGIN_CONFIG (JSON, set by `devteam plugin run`
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

# ── path confinement ──────────────────────────────────────────────────────────
# targetPaths / manifestPaths come from a committed, shared settings file, so an entry
# is untrusted input. The rules live here so every script that reads them agrees.

# _graphify_realpath <path>: physical path, symlinks resolved; the path need not exist.
_graphify_realpath() {
    local p="$1" dir base target n=0
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$p" 2>/dev/null && return 0
    fi
    while [ -L "$p" ] && [ "$n" -lt 40 ]; do
        target="$(readlink "$p")" || break
        case "$target" in /*) p="$target" ;; *) p="$(dirname "$p")/$target" ;; esac
        n=$((n + 1))
    done
    if [ -d "$p" ]; then
        (cd -P "$p" 2>/dev/null && pwd)
        return
    fi
    dir="$(dirname "$p")"
    base="$(basename "$p")"
    if [ -d "$dir" ]; then
        printf '%s/%s\n' "$(cd -P "$dir" 2>/dev/null && pwd)" "$base"
    else
        printf '%s\n' "$p"
    fi
}

# graphify_path_problem <project_root> <entry>: prints why an entry is refused (exit 0),
# or prints nothing and exits 1 when the entry is acceptable.
graphify_path_problem() {
    local root="$1" entry="$2" real_root real
    case "$entry" in
        "") echo "empty"; return 0 ;;
        /*) echo "absolute paths are not allowed"; return 0 ;;
        -*) echo "must not start with '-'"; return 0 ;;
        ..|../*|*/..|*/../*) echo "'..' components are not allowed"; return 0 ;;
    esac
    real_root="$(_graphify_realpath "$root")"
    real="$(_graphify_realpath "$root/$entry")"
    if [ "$real" != "$real_root" ] && [[ "$real" != "$real_root"/* ]]; then
        echo "resolves outside the project root"
        return 0
    fi
    return 1
}

# graphify_safe_paths <project_root> <json> <key>: the valid entries of a list key, one
# per line; refused entries are reported on stderr and skipped.
graphify_safe_paths() {
    local root="$1" json="$2" key="$3" entry problem
    while IFS= read -r entry; do
        [ -n "$entry" ] || continue
        if problem="$(graphify_path_problem "$root" "$entry")"; then
            echo "graphify: ignoring $key entry '$entry': $problem." >&2
            continue
        fi
        printf '%s\n' "$entry"
    done < <(graphify_cfg_list "$json" "$key")
}
