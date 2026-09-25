#!/usr/bin/env bash
# rollback.sh — Reinstall a previous version of dev-team-agents.
#
# Usage:
#   bash rollback.sh              # roll back to last-known good version (installed_version_prev in state.json)
#   bash rollback.sh v1.2.3       # roll back to a specific version tag
#
# The script re-downloads the requested version via the same install path
# used by update.sh, so network access is required.
set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(cd "$SCRIPTS_DIR/.." && pwd)"
USER_DATA_DIR="$INSTALL_DIR/user-data"

# shellcheck source=scripts/lib/state.sh
source "$SCRIPTS_DIR/lib/state.sh"
STATE_FILE="$USER_DATA_DIR/state.json"

# ── Shared installer-fetch logic ───────────────────────────────────────────────
# HTTP tool detection, GitHub coordinates, ref pinning and payload verification
# live in scripts/lib/installer-fetch.sh, shared with update.sh.

INSTALLER_LIB="$SCRIPTS_DIR/lib/installer-fetch.sh"
if [ ! -f "$INSTALLER_LIB" ]; then
    echo "✗ Missing $INSTALLER_LIB — the installation is incomplete." >&2
    echo "  Reinstall with:" >&2
    echo "    curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash" >&2
    exit 1
fi
# shellcheck source=scripts/lib/installer-fetch.sh
source "$INSTALLER_LIB"

# ── Resolve target version ─────────────────────────────────────────────────────

if [ -n "${1:-}" ]; then
    TARGET="$1"
else
    TARGET="$(state_get installed_version_prev "$STATE_FILE")"
    if [ -z "$TARGET" ]; then
        echo "✗ No previous version recorded in $STATE_FILE" >&2
        echo "  Specify a version explicitly: bash rollback.sh v1.2.3" >&2
        exit 1
    fi
fi

CURRENT="$(state_get installed_version "$STATE_FILE")"

# ── Validate version format ──────────────────────────────────────────────────
if [[ ! "$TARGET" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "✗ Invalid version format: '$TARGET'" >&2
    echo "  Expected: vX.Y.Z (e.g., v1.2.3)" >&2
    echo "  See: https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases" >&2
    exit 1
fi

# ── No-op check ──────────────────────────────────────────────────────────────
if [ "$CURRENT" = "$TARGET" ]; then
    echo "→ Already at $TARGET; nothing to do."
    exit 0
fi

echo "→ Rolling back from ${CURRENT:-unknown} to $TARGET ..."

if ! dta_have_http_tool; then
    echo "✗ Neither curl nor wget found. Cannot download." >&2
    exit 1
fi

# ── Download and run the installer at the target version ──────────────────────

TMP_INSTALLER=$(mktemp)
trap 'rm -f "$TMP_INSTALLER"' EXIT

# ── Safety checkpoint ─────────────────────────────────────────────────────────
echo "→ Creating safety checkpoint tag..."
SAFETY_TAG="pre-rollback-${TARGET}-$(date +%Y%m%d%H%M%S)"
git tag "$SAFETY_TAG" 2>/dev/null || true
echo "  Tagged current state as: $SAFETY_TAG"
echo "  To undo: git checkout $SAFETY_TAG && git checkout -b recovery-from-rollback"

# The installer is fetched from the target tag itself, not from `main`: rolling
# back to v1.2.3 must run v1.2.3's installer, so the installer and the payload
# it unpacks always come from the same immutable ref.
echo "→ Downloading installer from GitHub (ref: $TARGET)..."
if ! dta_fetch_installer "$TMP_INSTALLER" "$TARGET"; then
    echo "✗ Rollback aborted — the installer for $TARGET could not be downloaded or verified." >&2
    echo "  Nothing was changed. Your current installation is untouched." >&2
    exit 1
fi

bash "$TMP_INSTALLER" "$TARGET"

# Invalidate context cache after version change
rm -f ".dev-team-agents/user-data/.context-cache.json" 2>/dev/null || true

echo ""
echo "✓ Rolled back to $TARGET."
echo "  If the issue persists, check the changelog: https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/releases"
