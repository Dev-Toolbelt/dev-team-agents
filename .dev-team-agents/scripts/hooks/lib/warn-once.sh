#!/usr/bin/env bash
# Shared "warn once per signature" gate for Stop sub-scripts. Sourced, not dispatched.
#
# A Stop sub-script reaches the agent by exiting 2, and Claude Code and Codex answer
# that by continuing the turn. A warning nothing in the turn can clear would then fire
# after every reply, so each warning is keyed by a signature of what triggered it and
# stays quiet until that signature changes.
#
#   devteam_warn_once <marker-basename> <signature>
#     returns 0 → warn now (the signature has been recorded)
#     returns 1 → this exact signature was already warned about
#
# The marker lives in the machine-local state dir of the main checkout. Without a
# usable marker (no state dir, a symlinked marker) the function returns 0: the hook
# warns rather than going silent.

# shellcheck source=scripts/hooks/lib/data-dirs.sh
. "$(dirname "${BASH_SOURCE[0]}")/data-dirs.sh"

# The marker path for <marker-basename>, or nothing when no usable state dir exists.
_devteam_warn_once_marker() {
    local repo_root main_root state_dir
    repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || return 0
    main_root="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)" || main_root="$repo_root"
    state_dir="$(devteam_state_dir "${main_root:-$repo_root}" 2>/dev/null || true)"
    [ -n "$state_dir" ] && printf '%s/%s' "$state_dir" "$1"
    return 0
}

#   devteam_warn_once_reset <marker-basename>
#     forget the last signature, so the same findings warn again if they come back
#     after the condition was cleared.
devteam_warn_once_reset() {
    local marker
    marker="$(_devteam_warn_once_marker "$1")"
    [ -n "$marker" ] && [ ! -L "$marker" ] && rm -f "$marker" 2>/dev/null
    return 0
}

devteam_warn_once() {
    local name="$1" signature="$2" marker state_dir tmp
    [ -n "$signature" ] || return 0
    marker="$(_devteam_warn_once_marker "$name")"
    [ -n "$marker" ] || return 0
    state_dir="$(dirname "$marker")"
    # A symlinked marker is never read or written: a cloned repository could commit one
    # pointing at a file of the user's.
    [ -L "$marker" ] && return 0
    [ -d "$marker" ] && return 0
    if [ -f "$marker" ] && [ "$(cat "$marker" 2>/dev/null)" = "$signature" ]; then
        return 1
    fi
    if mkdir -p "$state_dir" 2>/dev/null; then
        # Written beside the marker and renamed over it, after refusing a symlinked or
        # directory marker above; `mv` onto a directory would move the file into it.
        tmp="$(mktemp "$marker.XXXXXX" 2>/dev/null || true)"
        if [ -n "$tmp" ]; then
            if printf '%s\n' "$signature" 2>/dev/null >"$tmp"; then
                mv -f "$tmp" "$marker" 2>/dev/null || rm -f "$tmp"
            else
                rm -f "$tmp"
            fi
        fi
    fi
    return 0
}
