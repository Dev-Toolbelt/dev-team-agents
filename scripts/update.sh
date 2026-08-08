#!/usr/bin/env bash
# update.sh — Unified update manager for dev-team-agents.
#
# Modes:
#   --check          Silent TTL-based update check (used by PreToolUse hook)
#   --enable-auto    Enable automatic updates (creates .auto-update flag)
#   --disable-auto   Disable automatic updates (removes .auto-update flag)
#   [latest|vX.Y.Z]  Download the latest install.sh from GitHub and run it

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
USER_DATA_DIR="$INSTALL_DIR/user-data"
AUTO_UPDATE_FLAG="$USER_DATA_DIR/.auto-update"

# ── Silent check mode — delegates to hook sub-script ─────────────────────────

if [[ "${1:-}" == "--check" ]]; then
    exec bash "$(dirname "${BASH_SOURCE[0]}")/hooks/pre-tool-use/01-check-updates.sh"
fi

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

if ! dta_have_http_tool; then
    echo "✗ Neither curl nor wget found. Cannot download update." >&2
    exit 1
fi

# ── Manual update mode ─────────────────────────────────────────────────────────

VERSION_ARG="${1:-latest}"

# Record the current version as the rollback target before the installer swaps it.
CURRENT_VERSION_FILE="$USER_DATA_DIR/.installed-version"
PREV_VERSION_FILE="$USER_DATA_DIR/.installed-version.prev"
if [ -f "$CURRENT_VERSION_FILE" ]; then
    cp "$CURRENT_VERSION_FILE" "$PREV_VERSION_FILE"
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

# For opencode projects, re-render agents and merge command snippets
if [ -f ".opencode/opencode.json" ] || [ -d ".opencode" ]; then
    echo "→ opencode config detected, re-running install-opencode.sh..."
    bash .dev-team-agents/scripts/install-opencode.sh
fi

# For Codex projects, re-render agents, migrate legacy prompt layouts, and
# refresh project-local command skills.
if [ -f ".codex/hooks.json" ] || [ -d ".codex" ]; then
    echo "→ Codex config detected, re-running install-codex.sh..."
    bash .dev-team-agents/scripts/install-codex.sh
fi

# Invalidate context cache after version change
rm -f ".dev-team-agents/user-data/.context-cache.json" 2>/dev/null || true

# Send update telemetry event (silent — never blocks the update flow)
_PREV_VER=$(cat "$PREV_VERSION_FILE" 2>/dev/null || echo "unknown")
_NEW_VER=$(cat "$CURRENT_VERSION_FILE" 2>/dev/null || echo "unknown")
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
