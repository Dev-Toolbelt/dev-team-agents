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

_state_default_file() {
    echo "${STATE_FILE:-${USER_DATA_DIR:-.}/state.json}"
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
        # No-python3 fallback: rewrite the file from a shell assoc array.
        # Sufficient for the flat scalar schema state.json holds; not a
        # general JSON merge.
        local tmp
        tmp="$(mktemp)"
        declare -A kv
        if [ -f "$file" ]; then
            while IFS=': ' read -r k v; do
                k="${k//\"/}"
                v="${v%,}"
                v="${v//\"/}"
                [ -n "$k" ] && kv["$k"]="$v"
            done < <(grep -o '"[^"]*"[[:space:]]*:[[:space:]]*[^,}]*' "$file" 2>/dev/null)
        fi
        kv["$key"]="$value"
        {
            echo "{"
            local first=true
            for k in "${!kv[@]}"; do
                local v="${kv[$k]}"
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
