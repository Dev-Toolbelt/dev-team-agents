#!/usr/bin/env bash
# Shared resolver for the project's two v3 data directories (ADR-0013), plus
# the preference cascade's resolved projection (ADR-0008 / M2):
#
#   state-dir  -> machine-local: state.json and the dot-markers
#                 (.last-releases-etag, .last-releases-version, .auto-update,
#                 .graphify-hint-shown, .last-archive-index, .agent-usage-cache,
#                 telemetry-queue.json)
#   memory-dir -> portable: session-summary.md
#   prefs file -> .dev-team-agents/resolved/preferences.json — "the one file
#                 agents read" (CLAUDE-md/cli.md), written by `bind`/`sync` on
#                 every layout from prefs.materialize() in
#                 scripts/lib/devteam/prefs.py
#
# Under layout 1 (a project that has never run `devteam upgrade`) both
# state-dir/memory-dir pointers resolve to the same .dev-team-agents/user-data/
# directory, so every hook that sources this file runs one code path on both
# layouts.
#
# Not a hook. Source this file, then call:
#   devteam_state_dir <project_root>
#   devteam_memory_dir <project_root>
#   devteam_memory_still_in_project <project_root>
#   devteam_prefs_file <project_root>
#   devteam_prefs_is_legacy <project_root>
#
# <project_root> must be the MAIN checkout root (the parent of
# `git rev-parse --git-common-dir`), never a linked worktree's own root — the
# pointer files, like user-data/ before them, live only there.

# state_read_pointer is defined in scripts/lib/state.sh; source it defensively
# so this file works whether or not the caller already sourced state.sh.
if ! command -v state_read_pointer >/dev/null 2>&1; then
    # shellcheck source=scripts/lib/state.sh
    . "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/state.sh"
fi

# devteam_state_dir <project_root>
# Resolution order: an explicit $STATE_FILE (its directory) or $USER_DATA_DIR
# — honoured first only because some callers already set one of those as an
# override — then the `state-dir` pointer, then the layout-1 fallback.
devteam_state_dir() {
    local root="$1"
    if [ -n "${STATE_FILE:-}" ]; then
        dirname "$STATE_FILE"
        return 0
    fi
    if [ -n "${USER_DATA_DIR:-}" ]; then
        printf '%s\n' "$USER_DATA_DIR"
        return 0
    fi
    state_read_pointer "$root" "state-dir" && return 0
    printf '%s\n' "$root/.dev-team-agents/user-data"
}

# devteam_memory_dir <project_root>
# Resolution order: the `memory-dir` pointer, then the layout-1 fallback. No
# hook sources this with a pre-resolved memory directory today, so there is no
# env override to honour first (unlike devteam_state_dir's $STATE_FILE).
devteam_memory_dir() {
    local root="$1"
    state_read_pointer "$root" "memory-dir" && return 0
    printf '%s\n' "$root/.dev-team-agents/user-data"
}

# devteam_memory_still_in_project <project_root>
# True (exit 0) only when this project genuinely still keeps its memory inside
# .dev-team-agents/user-data/ — the condition the "run `devteam upgrade`" nag
# must gate on:
#   1. bound: .dev-team-agents/project.json exists
#   2. user-data/ exists and holds at least one file OTHER than graphify.json
#      — that file is a project-owned, git-shared record (see
#      scripts/lib/devteam/paths.py PROJECT_OWNED_RECORDS) that legitimately
#      stays in the project after an upgrade, so its presence alone must not
#      read as "memory still in project"
#   3. no `state-dir` pointer resolves outside the project — once it does, the
#      project has already moved to the store and a leftover user-data/ is
#      stale debris from a previous layout, not a pending upgrade
devteam_memory_still_in_project() {
    local root="$1"
    [ -f "$root/.dev-team-agents/project.json" ] || return 1
    local legacy_dir="$root/.dev-team-agents/user-data"
    [ -d "$legacy_dir" ] || return 1

    local other_files=""
    other_files="$(find "$legacy_dir" -type f ! -name 'graphify.json' -print 2>/dev/null | head -n1 || true)"
    [ -n "$other_files" ] || return 1

    local pointer="$root/.dev-team-agents/state-dir"
    if [ -f "$pointer" ]; then
        local resolved=""
        resolved="$(tr -d '\r\n' < "$pointer" 2>/dev/null || true)"
        case "$resolved" in
            "$root"/*|"$root") ;;
            *) return 1 ;;
        esac
    fi
    return 0
}

# devteam_prefs_file <project_root>
# Resolution order for READING a preference in a hook:
#   1. .dev-team-agents/resolved/preferences.json — the cascade's resolved
#      projection (shipped defaults -> global -> project, resolved on write),
#      present on every layout once the project has run `devteam bind`/`sync`.
#      This is "the one file agents read" (CLAUDE-md/cli.md); it also bakes
#      the CONSENT_KEYS ("telemetry", "auto_update") down to an explicit
#      `false` ("consent-withheld") whenever no layer set them, so reading it
#      is what makes a hook honour that.
#   2. .dev-team-agents/user-data/preferences.json — the v2 / never-bound
#      fallback, for a project that predates `devteam bind`.
# NEVER write to path 1 from a hook: it is generated (prefs.materialize()
# stamps `_generated_by`) and the next `devteam sync` silently discards a hand
# edit — persist a change with `devteam prefs set` instead.
devteam_prefs_file() {
    local root="$1"
    local resolved="$root/.dev-team-agents/resolved/preferences.json"
    if [ -f "$resolved" ]; then
        printf '%s\n' "$resolved"
        return 0
    fi
    printf '%s\n' "$root/.dev-team-agents/user-data/preferences.json"
}

# devteam_prefs_is_legacy <project_root>
# True (exit 0) only when devteam_prefs_file would fall through to the
# in-project fallback — i.e. this project has never run `devteam bind`/`sync`
# and has no resolved projection yet. session-start.sh's preferences.json
# backfill (a v2 mechanism: writing missing default keys into the file) must
# only run in this case — once a projection exists, `devteam prefs set` owns
# writes, and backfilling into user-data/preferences.json there would write a
# file nothing reads and could resurrect a directory ADR-0013 retired.
devteam_prefs_is_legacy() {
    local root="$1"
    [ -f "$root/.dev-team-agents/resolved/preferences.json" ] && return 1
    return 0
}
