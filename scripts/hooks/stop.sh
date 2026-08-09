#!/usr/bin/env bash
# Dispatcher for all Stop hooks.
# Captures the Claude Code hook payload from stdin and makes it available to
# sub-scripts via the DEVTEAM_HOOK_PAYLOAD env var (path to a temp JSON file).
# Runs each sub-script in alphabetical order; a non-zero exit from any
# sub-script is propagated.

# Prevent WSL from loading /etc/bash.bashrc (and its start-systemd-namespace
# call) for every bash sub-process spawned by this dispatcher.
unset BASH_ENV ENV

set -euo pipefail

# Capture hook payload from stdin before dispatching to sub-scripts.
HOOK_TMP=$(mktemp /tmp/devteam-stop-payload.XXXXXX)
cat > "$HOOK_TMP" || true
export DEVTEAM_HOOK_PAYLOAD="$HOOK_TMP"
trap 'rm -f "$HOOK_TMP"' EXIT

# Fast-path: compute git state once here so sub-scripts 01–05 can skip
# expensive checks when nothing relevant changed in this session.
# DEVTEAM_NO_CHANGES=1 means: no staged/unstaged changes AND no commits today.
DEVTEAM_NO_CHANGES=0
if git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    if git diff --quiet 2>/dev/null && git diff --cached --quiet 2>/dev/null; then
        TODAY=$(date +%Y-%m-%d)
        if ! git log --oneline --since="${TODAY} 00:00:00" --format="%h" 2>/dev/null | grep -q .; then
            DEVTEAM_NO_CHANGES=1
        fi
    fi
fi
export DEVTEAM_NO_CHANGES

# Touched-path set, computed once here so sub-scripts 02/02b/03/03b do not each
# re-fork `git status` + `git log`. Only worth computing when something changed —
# with DEVTEAM_NO_CHANGES=1 every consumer exits at its own fast path anyway.
# Sub-scripts fall back to computing it themselves when run standalone.
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/lib" 2>/dev/null && pwd)" || LIB_DIR=""
DEVTEAM_TOUCHED_PATHS=""
DEVTEAM_TOUCHED_COMPUTED=0
if [ "$DEVTEAM_NO_CHANGES" = "0" ] && [ -f "$LIB_DIR/touched-paths.sh" ]; then
    # shellcheck source=scripts/hooks/lib/touched-paths.sh
    . "$LIB_DIR/touched-paths.sh"
    DEVTEAM_TOUCHED_PATHS="$(devteam_compute_touched_paths || true)"
    DEVTEAM_TOUCHED_COMPUTED=1
fi
export DEVTEAM_TOUCHED_PATHS DEVTEAM_TOUCHED_COMPUTED

HOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/stop" && pwd)"
EXIT_CODE=0

# Only files matching the documented sub-script convention are executed:
# NN-name.sh or NNx-name.sh (see CLAUDE.md, "Stop Hook Sub-script Convention").
# Drafts, backups (02-foo.sh.bak), notes.sh and half-finished files are ignored
# instead of being auto-run — a non-zero exit from a stray file would otherwise
# surface to the user on every Stop.
SUBSCRIPT_RE='^[0-9]{2}[a-z]?-[a-z0-9]([a-z0-9-]*[a-z0-9])?\.sh$'

for script in "$HOOKS_DIR"/*.sh; do
    [ -f "$script" ] || continue
    if [[ ! "$(basename "$script")" =~ $SUBSCRIPT_RE ]]; then
        [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && \
            echo "[devteam:stop] skipped (name does not match ${SUBSCRIPT_RE}): $(basename "$script")" >&2
        continue
    fi
    SCRIPT_EXIT=0
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:stop] running: $(basename "$script")" >&2
    env -u BASH_ENV -u ENV bash "$script" || SCRIPT_EXIT=$?
    [ -n "${DEVTEAM_HOOK_DEBUG:-}" ] && echo "[devteam:stop] exit ${SCRIPT_EXIT}: $(basename "$script")" >&2
    if [ "$SCRIPT_EXIT" -ne 0 ] && [ "$EXIT_CODE" -eq 0 ]; then
        EXIT_CODE=$SCRIPT_EXIT
    fi
done

exit $EXIT_CODE
