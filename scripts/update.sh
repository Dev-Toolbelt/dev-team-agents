#!/usr/bin/env bash
# update.sh — Unified update manager for dev-team-agents.
#
# Modes:
#   --check          On-demand update check; see scripts/check-updates.sh
#   --enable-auto    Enable automatic updates (creates .auto-update flag)
#   --disable-auto   Disable automatic updates (removes .auto-update flag)
#   [latest|vX.Y.Z]  Download the latest install.sh from GitHub and run it

set -euo pipefail

# `python3` resolves to a working Python 3.9+ on Windows Git Bash too (see the file).
_dta_py="$(dirname "${BASH_SOURCE[0]}")/lib/python.sh"
[ -f "$_dta_py" ] && . "$_dta_py"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
USER_DATA_DIR="$INSTALL_DIR/user-data"
AUTO_UPDATE_FLAG="$USER_DATA_DIR/.auto-update"

# shellcheck source=scripts/lib/state.sh
source "$SCRIPTS_DIR/lib/state.sh"
STATE_FILE="$USER_DATA_DIR/state.json"

# ── Check mode — delegates to the on-demand check ────────────────────────────

if [[ "${1:-}" == "--check" ]]; then
    exec bash "$SCRIPTS_DIR/check-updates.sh"
fi

# ── A v3-bound project is updated by the CLI, never by this script ────────────
# shellcheck source=scripts/lib/bound-project-guard.sh
source "$SCRIPTS_DIR/lib/bound-project-guard.sh"
refuse_if_bound "$INSTALL_DIR" "devteam update   (auto-update: devteam prefs set auto_update true|false)"

# ── Enable / Disable auto-update ──────────────────────────────────────────────

if [[ "${1:-}" == "--enable-auto" ]]; then
    mkdir -p "$USER_DATA_DIR"
    touch "$AUTO_UPDATE_FLAG"
    echo "✓ Auto-update enabled. dev-team-agents will update automatically when a new version is detected."
    exit 0
fi

if [[ "${1:-}" == "--disable-auto" ]]; then
    rm -f "$AUTO_UPDATE_FLAG"
    echo "✓ Auto-update disabled. You will be notified but updates won't be applied automatically."
    exit 0
fi

# ── Shared installer-fetch logic ───────────────────────────────────────────────
# HTTP tool detection, GitHub coordinates, ref pinning and payload verification
# live in scripts/lib/installer-fetch.sh, shared with rollback.sh.

INSTALLER_LIB="$SCRIPTS_DIR/lib/installer-fetch.sh"
if [ ! -f "$INSTALLER_LIB" ]; then
    echo "✗ Missing $INSTALLER_LIB — the installation is incomplete." >&2
    echo "  Reinstall with:" >&2
    echo "    curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash" >&2
    exit 1
fi
# shellcheck source=scripts/lib/installer-fetch.sh
source "$INSTALLER_LIB"
# shellcheck source=scripts/lib/provider-ownership.sh
source "$SCRIPTS_DIR/lib/provider-ownership.sh"

if ! dta_have_http_tool; then
    echo "✗ Neither curl nor wget found. Cannot download update." >&2
    exit 1
fi

# ── Manual update mode ─────────────────────────────────────────────────────────

VERSION_ARG="${1:-latest}"

# Record the current version as the rollback target before the installer swaps it.
_CURRENT_VERSION="$(state_get installed_version "$STATE_FILE")"
if [ -n "$_CURRENT_VERSION" ]; then
    state_set installed_version_prev "$_CURRENT_VERSION" "$STATE_FILE"
fi

TMP_INSTALLER=$(mktemp)
trap 'rm -f "$TMP_INSTALLER"' EXIT

# Pin the installer to the ref being installed. "latest" is resolved to the
# newest release tag first, so the installer and the release payload it fetches
# come from the same immutable tag instead of a moving `main`. Resolution falls
# back to `main` when the GitHub API is unreachable, preserving the old path.
INSTALL_REF=$(dta_resolve_ref "$VERSION_ARG")

if [ "$INSTALL_REF" = "main" ]; then
    INSTALL_TARGET="$VERSION_ARG"
    echo "→ Downloading installer from GitHub (ref: main — could not resolve a release tag)..."
else
    INSTALL_TARGET="$INSTALL_REF"
    echo "→ Downloading installer from GitHub (ref: $INSTALL_REF)..."
fi

# Fails closed: the installer is only executed after it downloads cleanly and
# passes verification (see the integrity model in scripts/lib/installer-fetch.sh).
if ! dta_fetch_installer "$TMP_INSTALLER" "$INSTALL_REF"; then
    echo "✗ Update aborted — the installer could not be downloaded or verified." >&2
    echo "  Nothing was changed. Your current installation is untouched." >&2
    exit 1
fi

bash "$TMP_INSTALLER" "$INSTALL_TARGET"

# Re-render the opencode / Codex trees. A failing provider is a warning and the rest still
# run; the failure is carried to the script's final exit status.
_PROVIDER_FAILED=0
po_rerender_providers || _PROVIDER_FAILED=1

# Invalidate context cache after version change
rm -f ".dev-team-agents/user-data/.context-cache.json" 2>/dev/null || true

# Send update telemetry event (silent — never blocks the update flow)
_PREV_VER="$(state_get installed_version_prev "$STATE_FILE")"
[ -n "$_PREV_VER" ] || _PREV_VER="unknown"
_NEW_VER="$(state_get installed_version "$STATE_FILE")"
[ -n "$_NEW_VER" ] || _NEW_VER="unknown"
_TELEMETRY_SEND="$INSTALL_DIR/scripts/helpers/telemetry-send.sh"
if [ -f "$_TELEMETRY_SEND" ]; then
    bash "$_TELEMETRY_SEND" --queue "update" \
        "{\"from_version\": \"$_PREV_VER\", \"to_version\": \"$_NEW_VER\", \"mode\": \"manual\"}" \
        2>/dev/null || true
    bash "$_TELEMETRY_SEND" --flush 2>/dev/null || true
fi

echo ""
echo "---"
echo "Installation complete. Run a health check to verify that all"
echo "project configuration is up to date with this version:"
echo "  /devteam:health-check"
echo "  (or say: \"Run a health check on this project\")"
echo ""
echo "If this project's docs/ have conventions never cataloged as reuse rules,"
echo "scan and catalog them with:"
echo "  /devteam:sync-rules"
echo "---"
echo ""

if [ "$_PROVIDER_FAILED" -ne 0 ]; then
    echo "✗ Update finished, but at least one provider re-render failed (see warnings above)." >&2
    exit 1
fi
