#!/usr/bin/env bash
# Effective graphify config, shared by scripts/refresh.sh and hooks/stop.sh.
# Sourced, never executed.
#
# Source order (ADR-0019): DEVTEAM_PLUGIN_CONFIG (JSON, set by `devteam plugin run`
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
# Set DEVTEAM_GRAPHIFY_NO_PYTHON=1 to force the pure-shell fallback (used by tests).
_graphify_realpath() {
    local p="$1"
    if [ -z "${DEVTEAM_GRAPHIFY_NO_PYTHON:-}" ] && command -v python3 >/dev/null 2>&1; then
        python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$p" 2>/dev/null && return 0
    fi
    _graphify_realpath_sh "$p"
}

# Shell fallback: follow a final symlink, then resolve the deepest existing ancestor
# physically (cd -P) and append the components that do not exist yet, so /var vs
# /private/var never makes an in-project path look foreign.
_graphify_realpath_sh() {
    local p="$1" target rest="" n=0 base
    while [ -L "$p" ] && [ "$n" -lt 40 ]; do
        target="$(readlink "$p")" || break
        case "$target" in /*) p="$target" ;; *) p="$(dirname "$p")/$target" ;; esac
        n=$((n + 1))
    done
    while [ ! -e "$p" ] && [ "$p" != "/" ] && [ "$p" != "." ]; do
        rest="$(basename "$p")${rest:+/$rest}"
        p="$(dirname "$p")"
    done
    if [ -d "$p" ]; then
        base="$(cd -P "$p" 2>/dev/null && pwd)" || base="$p"
    else
        base="$(cd -P "$(dirname "$p")" 2>/dev/null && pwd)/$(basename "$p")" || base="$p"
    fi
    if [ -n "$rest" ]; then
        [ "$base" = "/" ] && base=""
        printf '%s/%s\n' "$base" "$rest"
    else
        printf '%s\n' "$base"
    fi
}

# Names a source path may never start with (compared case-insensitively: on a case-
# insensitive filesystem `.GIT` is the git dir): repository internals, framework state,
# and the plugin's own build directories.
_graphify_reserved() {
    case "$1" in
        .git|.dev-team-agents|.worktrees|graphify-out|graphify-src) return 0 ;;
    esac
    return 1
}

# graphify_path_problem <project_root> <entry>: prints why an entry is refused (exit 0),
# or prints nothing and exits 1 when the entry is acceptable.
graphify_path_problem() {
    local root="$1" entry="$2" real_root real rel first git_dir norm="" c
    local -a parts
    case "$entry" in
        "") echo "empty"; return 0 ;;
        /*) echo "absolute paths are not allowed"; return 0 ;;
        -*) echo "must not start with '-'"; return 0 ;;
        ..|../*|*/..|*/../*) echo "'..' components are not allowed"; return 0 ;;
    esac
    IFS=/ read -r -a parts <<< "$entry"
    for c in ${parts[@]+"${parts[@]}"}; do
        case "$c" in ""|.) continue ;; esac
        norm="${norm:+$norm/}$c"
    done
    if [ -z "$norm" ]; then
        echo "the project root itself is not allowed; list its directories instead"
        return 0
    fi
    first="$(printf '%s' "${norm%%/*}" | tr '[:upper:]' '[:lower:]')"
    if _graphify_reserved "$first"; then
        echo "'$first' is reserved and cannot be a source path"
        return 0
    fi
    real_root="$(_graphify_realpath "$root")"
    real="$(_graphify_realpath "$root/$entry")"
    if [ "$real" != "$real_root" ] && [[ "$real" != "$real_root"/* ]]; then
        echo "resolves outside the project root"
        return 0
    fi
    # A symlink can land on a reserved name or inside the checkout's git dir.
    rel="${real#"$real_root"}"
    rel="${rel#/}"
    first="$(printf '%s' "${rel%%/*}" | tr '[:upper:]' '[:lower:]')"
    if [ -n "$first" ] && _graphify_reserved "$first"; then
        echo "resolves into '$first', which is reserved"
        return 0
    fi
    git_dir="$(git -C "$root" rev-parse --absolute-git-dir 2>/dev/null || true)"
    if [ -n "$git_dir" ]; then
        git_dir="$(_graphify_realpath "$git_dir")"
        if [ "$real" = "$git_dir" ] || [[ "$real" == "$git_dir"/* ]]; then
            echo "resolves inside the git directory"
            return 0
        fi
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
