#!/usr/bin/env bash
# verify-mac-notarised.sh — prove the macOS release artifact is what the cask claims.
#
# Mounts the dmg a USER would download and checks the app inside it the way Gatekeeper
# does, not the intermediate bundle electron-builder left in release/mac-universal:
#   1. codesign --verify --deep --strict          the signature is intact
#   2. codesign -dvv  -> "Developer ID Application" a real identity, not ad-hoc
#   3. xcrun stapler validate                     a notarisation ticket is attached
#   4. spctl -a -vvv -t exec                      Gatekeeper accepts it ("source=Notarized Developer ID")
#
# Exit 0 only when all four pass. Any other outcome — including "cannot mount" — is a
# failure: this script exists so that nothing downstream calls an artifact notarised
# because credentials were present.
#
# Usage: verify-mac-notarised.sh <path/to/file.dmg>
set -euo pipefail

DMG="${1:-}"
[ -f "$DMG" ] || { echo "verify-mac-notarised: no such dmg: ${DMG:-<none>}" >&2; exit 2; }

MOUNT="$(mktemp -d /tmp/devteam-dmg.XXXXXX)"
cleanup() {
  hdiutil detach "$MOUNT" -quiet -force >/dev/null 2>&1 || true
  rmdir "$MOUNT" >/dev/null 2>&1 || true
}
trap cleanup EXIT

hdiutil attach "$DMG" -nobrowse -readonly -noverify -mountpoint "$MOUNT" -quiet
APP="$(find "$MOUNT" -maxdepth 1 -name '*.app' -print -quit)"
[ -n "$APP" ] || { echo "verify-mac-notarised: no .app inside $DMG" >&2; exit 1; }
echo "app: $APP"

fail=0
step() {
  local label="$1"; shift
  if "$@"; then echo "PASS  $label"; else echo "FAIL  $label"; fail=1; fi
}

has_developer_id() { codesign -dvv "$APP" 2>&1 | tee /dev/stderr | grep -q 'Authority=Developer ID Application'; }

step "codesign --verify --deep --strict" codesign --verify --deep --strict --verbose=2 "$APP"
step "signed with a Developer ID Application identity (not ad-hoc)" has_developer_id
step "xcrun stapler validate" xcrun stapler validate "$APP"
step "spctl -a -vvv -t exec (Gatekeeper assessment)" spctl -a -vvv -t exec "$APP"

if [ "$fail" -ne 0 ]; then
  echo "verify-mac-notarised: $APP is NOT signed and notarised." >&2
  exit 1
fi
echo "verify-mac-notarised: signed and notarised."
