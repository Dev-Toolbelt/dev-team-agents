#!/usr/bin/env bash
# Shared touched-path detection for Stop sub-scripts.
# Source this file, then call: devteam_touched_matches '<extended-regex>'
#
# The Stop dispatcher (stop.sh) computes the set ONCE per Stop and exports it as
# DEVTEAM_TOUCHED_PATHS (newline-separated, repo-relative) plus the marker
# DEVTEAM_TOUCHED_COMPUTED=1. Sub-scripts consume it instead of re-forking git.
# When a sub-script is invoked standalone (no dispatcher, marker absent) the set
# is computed here on first use — so no sub-script depends on the dispatcher
# having run.
#
# Not a hook. Sourced by stop.sh and by stop/02-, 02b-, 03-, 03b- sub-scripts.

# Every repo-relative path touched in this session:
#   - working tree: staged, unstaged and untracked
#   - commits made today
# Prints one path per line; prints nothing outside a git work tree.
devteam_compute_touched_paths() {
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
    local today
    today=$(date +%Y-%m-%d)
    {
        # cut -c4- drops the "XY " status prefix; the sed drops the "old -> " half
        # of a rename so only the destination path is reported.
        git status --porcelain 2>/dev/null | cut -c4- | sed 's/^.* -> //' || true
        git log --since="${today} 00:00:00" --name-only --pretty=format: 2>/dev/null || true
    } | sed '/^[[:space:]]*$/d' | sort -u
}

# Returns 0 when at least one touched path matches the extended regex.
devteam_touched_matches() {
    local pattern="$1"
    if [ "${DEVTEAM_TOUCHED_COMPUTED:-0}" != "1" ]; then
        DEVTEAM_TOUCHED_PATHS="$(devteam_compute_touched_paths || true)"
        DEVTEAM_TOUCHED_COMPUTED=1
        export DEVTEAM_TOUCHED_PATHS DEVTEAM_TOUCHED_COMPUTED
    fi
    [ -n "${DEVTEAM_TOUCHED_PATHS:-}" ] || return 1
    printf '%s\n' "$DEVTEAM_TOUCHED_PATHS" | grep -qE "$pattern"
}
