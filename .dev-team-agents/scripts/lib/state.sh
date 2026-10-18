#!/usr/bin/env bash
# scripts/lib/state.sh — shared read/write/migrate helpers for
# .dev-team-agents/user-data/state.json, the consolidated home for the
# small scalar markers that used to live as individual dotfiles
# (.installed-version, .last-health-check, .last-update-check,
# .update-check-interval, .graphify-last-run, .session-id, .session-head,
# .installed-version.prev). Source this file; do not execute it.
#
# Usage:
#   state_get <key> [state_file]              # prints value, or "" if absent
#   state_set <key> <value> [state_file]      # writes/updates one key
#   state_migrate_legacy <user_data_dir>      # one-shot, idempotent import of
#                                              # legacy dotfiles into state.json
set -uo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/python.sh"
# shellcheck source=python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

# Resolution order: an explicit STATE_FILE, then USER_DATA_DIR, then the project's
# recorded state directory, then the v2 in-project location.
#
# `.dev-team-agents/state-dir` is a pointer the v3 bind writes with the absolute
# path of this project's state directory, which is the data store once the project
# has been upgraded. It is read as a single file read on purpose: asking the CLI
# would mean a python subprocess on every `state_get`, and these run inside hooks.
#
# state_read_pointer <root> <pointer_name>
# Generic one-file-read for either of the two ADR-0013 pointers a v3 bind
# writes under <root>/.dev-team-agents/ — "state-dir" (machine-local) or its
# sibling "memory-dir" (portable). Prints the resolved absolute path; returns 1
# when the pointer is absent or empty so the caller can fall through to its own
# default. Shared with scripts/hooks/lib/data-dirs.sh, which resolves
# "memory-dir" the same way for the hooks that need the portable directory —
# do not re-derive this one-file-read anywhere else.
state_read_pointer() {
    local root="$1" name="$2"
    local pointer="$root/.dev-team-agents/$name"
    [ -f "$pointer" ] || return 1
    local resolved
    resolved="$(tr -d '\r\n' < "$pointer")"
    [ -n "$resolved" ] || return 1
    echo "$resolved"
}

_state_dir_pointer() {
    state_read_pointer "${DEVTEAM_PROJECT_ROOT:-.}" "state-dir"
}

_state_default_file() {
    if [ -n "${STATE_FILE:-}" ]; then
        echo "$STATE_FILE"
        return 0
    fi
    if [ -n "${USER_DATA_DIR:-}" ]; then
        echo "$USER_DATA_DIR/state.json"
        return 0
    fi
    local from_pointer
    if from_pointer="$(_state_dir_pointer)"; then
        echo "$from_pointer/state.json"
        return 0
    fi
    echo "./state.json"
}

state_get() {
    local key="$1"
    local file="${2:-$(_state_default_file)}"
    [ -f "$file" ] || { echo ""; return 0; }

    if command -v python3 >/dev/null 2>&1; then
        python3 - "$file" "$key" <<'PYEOF'
import sys, json
file_path, key = sys.argv[1], sys.argv[2]
try:
    with open(file_path) as f:
        data = json.load(f)
    val = data.get(key, "")
    print("" if val is None else val)
except (json.JSONDecodeError, IOError, FileNotFoundError):
    print("")
PYEOF
    else
        # No-python3 fallback: values in state.json are always flat scalars
        # (string or number), so a line-oriented grep is sufficient here —
        # this is not a general JSON parser.
        local str_match
        str_match="$(grep -o "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" "$file" 2>/dev/null)"
        if [ -n "$str_match" ]; then
            echo "$str_match" | sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/' | head -n1
        else
            grep -o "\"$key\"[[:space:]]*:[[:space:]]*[0-9][0-9]*" "$file" 2>/dev/null \
                | sed -E 's/.*:[[:space:]]*([0-9]+)/\1/' | head -n1
        fi
    fi
}

state_set() {
    local key="$1"
    local value="$2"
    local file="${3:-$(_state_default_file)}"
    mkdir -p "$(dirname "$file")"

    if command -v python3 >/dev/null 2>&1; then
        python3 - "$file" "$key" "$value" <<'PYEOF'
import sys, json, os
file_path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
data = {}
if os.path.exists(file_path):
    try:
        with open(file_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        data = {}
# Numeric-looking values are stored as numbers (timestamps, intervals);
# everything else stays a string (versions, git SHAs).
if value.isdigit():
    data[key] = int(value)
else:
    data[key] = value
with open(file_path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
PYEOF
    else
        # No-python3 fallback: rewrite the file from parallel shell arrays.
        # Sufficient for the flat scalar schema state.json holds; not a
        # general JSON merge.
        local tmp
        tmp="$(mktemp)"
        # bash 3.2 has no associative arrays: parallel indexed arrays, keyed by linear scan.
        local -a kv_keys=() kv_vals=()
        local _i _hit

        if [ -f "$file" ]; then
            while IFS=': ' read -r k v; do
                k="${k//\"/}"
                v="${v%,}"
                v="${v//\"/}"
                if [ -n "$k" ]; then
                    _hit=-1
                    for ((_i = 0; _i < ${#kv_keys[@]}; _i++)); do
                        [ "${kv_keys[$_i]}" = "$k" ] && { _hit=$_i; break; }
                    done
                    if [ "$_hit" -ge 0 ]; then kv_vals[_hit]="$v"; else kv_keys+=("$k"); kv_vals+=("$v"); fi
                fi
            done < <(grep -o '"[^"]*"[[:space:]]*:[[:space:]]*[^,}]*' "$file" 2>/dev/null)
        fi
        _hit=-1
        for ((_i = 0; _i < ${#kv_keys[@]}; _i++)); do
            [ "${kv_keys[$_i]}" = "$key" ] && { _hit=$_i; break; }
        done
        if [ "$_hit" -ge 0 ]; then kv_vals[_hit]="$value"; else kv_keys+=("$key"); kv_vals+=("$value"); fi
        {
            echo "{"
            local first=true
            for ((_i = 0; _i < ${#kv_keys[@]}; _i++)); do
                local k="${kv_keys[$_i]}" v="${kv_vals[$_i]}"
                $first || echo ","
                first=false
                if [[ "$v" =~ ^[0-9]+$ ]]; then
                    printf '  "%s": %s' "$k" "$v"
                else
                    printf '  "%s": "%s"' "$k" "$v"
                fi
            done
            echo ""
            echo "}"
        } > "$tmp"
        mv "$tmp" "$file"
    fi
}

state_migrate_legacy() {
    local user_data_dir="$1"
    local state_file="$user_data_dir/state.json"

    # Map: dotfile basename -> state.json key. .installed-version.prev must be
    # listed before .installed-version so the longer filename is matched first.
    local -a legacy_files=(
        ".installed-version.prev:installed_version_prev"
        ".installed-version:installed_version"
        ".last-health-check:last_health_check"
        ".last-update-check:last_update_check"
        ".update-check-interval:update_check_interval"
        ".graphify-last-run:graphify_last_run"
        ".session-id:session_id"
        ".session-head:session_head"
    )

    local found_any=false
    for entry in "${legacy_files[@]}"; do
        local fname="${entry%%:*}"
        local key="${entry##*:}"
        local legacy_path="$user_data_dir/$fname"
        if [ -f "$legacy_path" ]; then
            found_any=true
            local val
            val="$(tr -d '[:space:]' < "$legacy_path" 2>/dev/null)"
            [ -n "$val" ] && state_set "$key" "$val" "$state_file"
            mv "$legacy_path" "$legacy_path.pre-migration.bak"
        fi
    done

    if [ "$found_any" = true ]; then
        echo "→ Migrated legacy user-data markers into state.json" >&2
    fi
}
