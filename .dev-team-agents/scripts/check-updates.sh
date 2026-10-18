#!/usr/bin/env bash
# check-updates.sh — on-demand update check for a v2 install (/devteam:update Step 3,
# `update.sh --check`). A v3-bound project uses `devteam update --check` instead.
#
# Prints exactly one line on stdout, and always exits 0:
#   Update available: <current> → <latest>    a strictly newer release exists
#   (nothing)                                 up to date, or ahead of the release
#   Could not check for updates: <reason>     no network, or no installed version
#
# Read-only: no notification, no auto-update, no TTL. It always asks GitHub afresh,
# with throwaway ETag and version-cache files, so a cached 304 cannot mask a release.
# The session-start hook is the scheduled check; this is the one a user asks for.
set -euo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/lib/python.sh"
# shellcheck source=lib/python.sh
[ -f "$_dta_py" ] && . "$_dta_py"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
STATE_FILE="$INSTALL_DIR/user-data/state.json"
GITHUB_API="https://api.github.com/repos/Dev-Toolbelt/dev-team-agents"

cannot() {
    printf 'Could not check for updates: %s\n' "$1"
    exit 0
}

[ -f "$SCRIPTS_DIR/lib/state.sh" ] && [ -f "$SCRIPTS_DIR/hooks/lib/update-check.sh" ] \
    || cannot "the installation is incomplete (run /devteam:health-check)"
# shellcheck source=scripts/lib/state.sh
. "$SCRIPTS_DIR/lib/state.sh"
# shellcheck source=scripts/hooks/lib/update-check.sh
. "$SCRIPTS_DIR/hooks/lib/update-check.sh"

CURRENT="$(state_get installed_version "$STATE_FILE" 2>/dev/null || true)"
[ -n "$CURRENT" ] || cannot "the installed version is unknown (run /devteam:health-check)"

uc_setup_http || cannot "neither curl nor wget is installed"

SCRATCH="$(mktemp -d 2>/dev/null)" || cannot "no temporary directory"
trap 'rm -rf "$SCRATCH"' EXIT
LATEST="$(uc_fetch_latest "$GITHUB_API" "$SCRATCH/etag" "$SCRATCH/version" || true)"
[ -n "$LATEST" ] || cannot "GitHub did not answer"

if uc_is_newer "$CURRENT" "$LATEST"; then
    printf 'Update available: %s → %s\n' "${CURRENT#v}" "${LATEST#v}"
fi
exit 0
