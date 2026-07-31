#!/usr/bin/env bash
# Anonymous telemetry helper for dev-team-agents.
#
# Usage:
#   telemetry-send.sh --queue EVENT_NAME [JSON_PROPERTIES]
#   telemetry-send.sh --flush
#   telemetry-send.sh --dry-run   (prints queue contents, sends nothing)
#
# The queue file (telemetry-queue.json) stores the anonymous ID, last flush
# timestamp, and pending events. All operations are silent on failure.
#
# Privacy:
#   - No PII is collected. The anonymous ID is a SHA-256 hash of hostname +
#     home directory path and is not reversible.
#   - No file paths, project names, code, or user identifiers are sent.
#   - All data is sent over HTTPS to PostHog. Set telemetry: false in
#     preferences.json to opt out permanently.
#   - See PRIVACY.md for the full list of collected events and properties.

set -euo pipefail

# ── PostHog configuration ──────────────────────────────────────────────────────
# POSTHOG_API_KEY below is this project's PostHog *project* key (the `phc_`
# prefix marks a write-only capture key). Such keys are designed to be embedded
# in client-side code: they can submit events to the project and nothing else —
# they cannot read, query, export or modify any data. Shipping it in this file
# is intentional and is not a secret leak; it is what makes an installed copy
# able to report at all. Both values can be overridden via the environment
# (DEVTEAM_POSTHOG_KEY / DEVTEAM_POSTHOG_ENDPOINT) to point at a self-hosted
# PostHog instance or at a test project.
POSTHOG_API_KEY="${DEVTEAM_POSTHOG_KEY:-phc_wBFupbyPPEw8DWTJd8Z8UAjNMxwHJusBEPJsrURsQ93a}"
POSTHOG_ENDPOINT="${DEVTEAM_POSTHOG_ENDPOINT:-https://us.i.posthog.com}"

# ── Path resolution ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go up two levels: helpers/ -> scripts/ -> dev-team-agents/ (the install root)
INSTALL_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# DEVTEAM_USER_DATA_DIR can be set by tests or CI to override the default path
USER_DATA_DIR="${DEVTEAM_USER_DATA_DIR:-"$INSTALL_DIR/user-data"}"
PREFS_FILE="$USER_DATA_DIR/preferences.json"
QUEUE_FILE="$USER_DATA_DIR/telemetry-queue.json"
VERSION_FILE="$USER_DATA_DIR/.installed-version"

FLUSH_TTL_HOURS=24
QUEUE_MAX_EVENTS=100

# ── Guard: consent check ───────────────────────────────────────────────────────
# Fails closed. Telemetry runs only when preferences.json exists and explicitly
# records consent (`"telemetry": true`), which the installer writes only after
# the user was actually given the chance to decline. No preferences file, an
# unreadable one, a missing key, or no python3 to read it with all mean the
# same thing: consent was never recorded, so nothing is collected or sent.
_telemetry_enabled() {
    [ -f "$PREFS_FILE" ] || return 1
    command -v python3 >/dev/null 2>&1 || return 1
    local val
    val=$(python3 -c \
        "import json; d=json.load(open('$PREFS_FILE')); print(str(d.get('telemetry',False)).lower())" \
        2>/dev/null || echo "false")
    [ "$val" = "true" ]
}

# ── Anonymous ID ───────────────────────────────────────────────────────────────
_get_or_create_id() {
    # Read from queue file if already generated
    if [ -f "$QUEUE_FILE" ] && command -v python3 >/dev/null 2>&1; then
        local existing
        existing=$(python3 -c \
            "import json; d=json.load(open('$QUEUE_FILE')); print(d.get('id',''))" \
            2>/dev/null || echo "")
        if [ -n "$existing" ]; then
            echo "$existing"
            return
        fi
    fi

    # Generate: SHA-256 of hostname + home dir (one-way, not reversible)
    local raw="${HOSTNAME:-$(hostname 2>/dev/null || echo unknown)}:${HOME:-/unknown}"
    local hashed
    if command -v sha256sum >/dev/null 2>&1; then
        hashed=$(printf '%s' "$raw" | sha256sum | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        hashed=$(printf '%s' "$raw" | shasum -a 256 | awk '{print $1}')
    else
        hashed="no-sha-$(date +%s)"
    fi
    echo "$hashed"
}

# ── Queue management ───────────────────────────────────────────────────────────
_queue_event() {
    local event_name="$1"
    local props="${2:-}"
    [ -n "$props" ] || props="{}"
    local anon_id
    anon_id=$(_get_or_create_id)
    local version
    version=$(cat "$VERSION_FILE" 2>/dev/null || echo "unknown")
    local os_name
    os_name=$(uname -s 2>/dev/null | tr '[:upper:]' '[:lower:]' || echo "unknown")
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

    command -v python3 >/dev/null 2>&1 || return 0

    python3 - "$QUEUE_FILE" "$anon_id" "$event_name" "$props" \
              "$version" "$os_name" "$timestamp" "$QUEUE_MAX_EVENTS" <<'PYEOF'
import sys, json, os

queue_file, anon_id, event_name, props_str = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
version, os_name, timestamp, max_events = sys.argv[5], sys.argv[6], sys.argv[7], int(sys.argv[8])

queue = {"id": anon_id, "last_flush": 0, "events": []}
if os.path.exists(queue_file):
    try:
        with open(queue_file, "r") as f:
            queue = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

# Ensure ID is set (idempotent)
if not queue.get("id"):
    queue["id"] = anon_id

# Parse extra properties
try:
    extra_props = json.loads(props_str)
except (json.JSONDecodeError, ValueError):
    extra_props = {}

event = {
    "event": event_name,
    "timestamp": timestamp,
    "properties": {
        "$lib": "dev-team-agents",
        "version": version,
        "os": os_name,
        **extra_props,
    },
}

queue.setdefault("events", []).append(event)

# Trim oldest events when over the cap (FIFO)
if len(queue["events"]) > max_events:
    queue["events"] = queue["events"][-max_events:]

with open(queue_file, "w") as f:
    json.dump(queue, f, indent=2)
    f.write("\n")
PYEOF
}

# ── Flush queue to PostHog ─────────────────────────────────────────────────────
_should_flush() {
    [ -f "$QUEUE_FILE" ] || return 1
    command -v python3 >/dev/null 2>&1 || return 1

    python3 - "$QUEUE_FILE" "$FLUSH_TTL_HOURS" "$QUEUE_MAX_EVENTS" <<'PYEOF'
import sys, json, os, time

queue_file, ttl_hours, max_cap = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ttl_secs = ttl_hours * 3600

try:
    with open(queue_file, "r") as f:
        queue = json.load(f)
except (json.JSONDecodeError, IOError):
    sys.exit(1)

events = queue.get("events", [])
if not events:
    sys.exit(1)

last_flush = queue.get("last_flush", 0)
age = time.time() - last_flush
if age >= ttl_secs or len(events) >= max_cap:
    sys.exit(0)   # should flush
sys.exit(1)       # not yet
PYEOF
}

_flush_queue() {
    [ -f "$QUEUE_FILE" ] || return 0
    command -v python3 >/dev/null 2>&1 || return 0

    local anon_id
    anon_id=$(_get_or_create_id)
    local dry_run="${1:-}"

    # Build PostHog batch payload
    local payload
    payload=$(python3 - "$QUEUE_FILE" "$anon_id" "$POSTHOG_API_KEY" <<'PYEOF'
import sys, json

queue_file, anon_id, api_key = sys.argv[1], sys.argv[2], sys.argv[3]

try:
    with open(queue_file, "r") as f:
        queue = json.load(f)
except (json.JSONDecodeError, IOError):
    sys.exit(0)

events = queue.get("events", [])
if not events:
    sys.exit(0)

batch = []
for ev in events:
    batch.append({
        "distinct_id": anon_id,
        "event": ev.get("event", "unknown"),
        "timestamp": ev.get("timestamp", ""),
        "properties": ev.get("properties", {}),
    })

print(json.dumps({"api_key": api_key, "batch": batch}))
PYEOF
    ) || return 0

    [ -n "$payload" ] || return 0

    if [ "$dry_run" = "--dry-run" ]; then
        echo "=== telemetry dry-run: would send ==="
        echo "$payload" | python3 -m json.tool 2>/dev/null || echo "$payload"
        echo "======================================"
        return 0
    fi

    # Send to PostHog (silent on network failure)
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL \
            --connect-timeout 5 \
            --max-time 10 \
            -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "${POSTHOG_ENDPOINT}/batch/" \
            >/dev/null 2>&1 || true
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- \
            --timeout=10 \
            --post-data="$payload" \
            --header="Content-Type: application/json" \
            "${POSTHOG_ENDPOINT}/batch/" \
            >/dev/null 2>&1 || true
    else
        return 0
    fi

    # Update last_flush timestamp and clear sent events
    python3 - "$QUEUE_FILE" <<'PYEOF'
import sys, json, time

queue_file = sys.argv[1]
try:
    with open(queue_file, "r") as f:
        queue = json.load(f)
except (json.JSONDecodeError, IOError):
    sys.exit(0)

queue["last_flush"] = time.time()
queue["events"] = []

with open(queue_file, "w") as f:
    json.dump(queue, f, indent=2)
    f.write("\n")
PYEOF
}

# ── Main dispatch ──────────────────────────────────────────────────────────────
MODE="${1:-}"

case "$MODE" in
    --queue)
        _telemetry_enabled || exit 0
        EVENT="${2:-}"
        PROPS="${3:-}"
        [ -n "$PROPS" ] || PROPS="{}"
        [ -n "$EVENT" ] || exit 0
        mkdir -p "$USER_DATA_DIR"
        _queue_event "$EVENT" "$PROPS"
        ;;
    --flush)
        _telemetry_enabled || exit 0
        _should_flush || exit 0
        _flush_queue
        ;;
    --dry-run)
        _flush_queue --dry-run
        ;;
    *)
        echo "Usage: telemetry-send.sh --queue EVENT [JSON_PROPS]" >&2
        echo "       telemetry-send.sh --flush" >&2
        echo "       telemetry-send.sh --dry-run" >&2
        exit 1
        ;;
esac

exit 0
