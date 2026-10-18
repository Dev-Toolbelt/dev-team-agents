#!/usr/bin/env bash
# self-heal.sh <dispatcher> — run by a provider's hook wrapper, from the STORE, when the project's
# `.dev-team-agents/scripts/hooks` is gone but its `core-dir` pointer is not.
#
# The link is a bind artifact git treats as expendable: a rebase onto a commit that still vendored
# `.dev-team-agents/scripts` deletes it, and every hook then failed as a "non-blocking error" nobody
# reads — the task board, the session summary and the notifier stopped in silence. This re-binds the
# project with the store's own CLI (absolute path, so `devteam` need not be on PATH) and hands the
# payload to the project's dispatcher again. If the re-bind does not bring it back, the dispatcher
# runs from the store instead, so the hooks keep working, and one line on stderr says what to do.
#
# Runs in the project root (the wrapper `cd`s there). stdin is the hook payload: the re-bind reads
# /dev/null, so the dispatcher still receives it whole. Never exits 2 — healing never blocks a call.
unset BASH_ENV ENV
set -uo pipefail

DISPATCHER="${1:-}"
case "$DISPATCHER" in
    ''|*/*|*..*) exit 0 ;;
esac

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STORE_HOOKS="$(dirname "$HERE")"
SCRIPTS="$(dirname "$STORE_HOOKS")"
PROJECT_HOOKS=".dev-team-agents/scripts/hooks"

# shellcheck source=../../lib/python.sh
[ -f "$SCRIPTS/lib/python.sh" ] && . "$SCRIPTS/lib/python.sh"

if [ ! -d "$PROJECT_HOOKS" ] && [ -f "$SCRIPTS/cli/devteam" ]; then
    python3 "$SCRIPTS/cli/devteam" sync "$PWD" </dev/null >/dev/null 2>&1 || true
fi

if [ -f "$PROJECT_HOOKS/$DISPATCHER" ]; then
    exec bash "$PROJECT_HOOKS/$DISPATCHER"
fi

echo "dev-team-agents: $PWD/$PROJECT_HOOKS is missing and \`devteam sync\` did not restore it; running the hooks from the store. Run \`devteam doctor\` in this project." >&2
[ -f "$STORE_HOOKS/$DISPATCHER" ] || exit 0
exec bash "$STORE_HOOKS/$DISPATCHER"
