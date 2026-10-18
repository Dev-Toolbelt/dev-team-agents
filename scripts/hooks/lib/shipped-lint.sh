#!/usr/bin/env bash
# Where a Stop sub-script finds the lint it runs. Sourced, not dispatched.
#
#   devteam_shipped_lint <script-name>
#     prints the path of <script-name> in the scripts/ tree this hook ships in,
#     or nothing when that tree has no such regular file.
#
# Only that tree. Every layout runs the hooks from `.dev-team-agents/scripts/hooks/`
# (link, copy and vendored binds) or from this repository's own `scripts/hooks/`,
# so the lint beside the hook is the only copy that is ever the framework's. The
# project-relative fallbacks this replaced either named the same file again or
# named one the project provides — `scripts/design-token-lint.sh`,
# `scripts/reuse-lint.sh` — which would run repository code on every Stop. When the
# lint is absent the caller exits 0: a version without it simply has no gate.

# Resolved once, at source time, to an absolute path: a relative BASH_SOURCE would
# point elsewhere if the caller changed directory before calling.
# Logical cd on purpose (no -P): the result is the tree stop.sh itself came from.
_DEVTEAM_SHIPPED_TREE="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)" || _DEVTEAM_SHIPPED_TREE=""

devteam_shipped_lint() {
    [ -n "$_DEVTEAM_SHIPPED_TREE" ] || return 0
    [ -f "$_DEVTEAM_SHIPPED_TREE/$1" ] && printf '%s\n' "$_DEVTEAM_SHIPPED_TREE/$1"
    return 0
}
