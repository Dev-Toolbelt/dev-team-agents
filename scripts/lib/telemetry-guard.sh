#!/usr/bin/env bash
# telemetry-guard.sh — Single definition of the telemetry consent gate.
#
# Sourced by (the only three places that may decide whether telemetry runs):
#   - scripts/helpers/telemetry-send.sh
#   - scripts/hooks/stop/05-telemetry.sh
#   - scripts/hooks/pre-tool-use/02b-telemetry.sh
#
# Sourcing contract:
#   Set PREFS_FILE to the preferences.json path before sourcing, or pass the
#   path as the first argument to _telemetry_enabled. Then:
#       _telemetry_enabled || exit 0
#
# FAILS CLOSED — deliberately. A missing preferences file, an unreadable one, a
# missing `telemetry` key, or no python3 to read it with all mean the same
# thing: consent was never recorded. The installer writes `"telemetry": true`
# only after the user was actually given the chance to decline, so absence of
# that explicit true is absence of consent. Never flip these defaults to true.
#
# A consumer that cannot source this file must also fail closed (skip telemetry).

_telemetry_enabled() {
    local prefs="${1:-${PREFS_FILE:-}}"
    [ -n "$prefs" ] || return 1
    [ -f "$prefs" ] || return 1
    command -v python3 >/dev/null 2>&1 || return 1
    local val
    val=$(python3 - "$prefs" <<'PYEOF' 2>/dev/null || echo "false"
import sys, json
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    print(str(d.get("telemetry", False)).lower())
except (json.JSONDecodeError, IOError, FileNotFoundError):
    print("false")
PYEOF
)
    [ "$val" = "true" ]
}
