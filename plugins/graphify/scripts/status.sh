#!/usr/bin/env bash
# Graphify plugin status: one JSON object {"summary": str, "facts": [{"label","value"}]}.
# Cheap by contract (runs on every `plugin list`), and always exits 0 with valid JSON.
set -uo pipefail

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/ }"
  s="${s//$'\t'/ }"
  printf '%s' "$s"
}

FACTS=""
add_fact() {
  [ -n "$FACTS" ] && FACTS="$FACTS,"
  FACTS="$FACTS{\"label\":\"$(json_escape "$1")\",\"value\":\"$(json_escape "$2")\"}"
}

emit() {
  printf '{"summary":"%s","facts":[%s]}\n' "$(json_escape "$1")" "$FACTS"
  exit 0
}

SELF_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || emit "Status unavailable"
CORE_DIR="$(cd -P "$SELF_DIR/../../.." 2>/dev/null && pwd)" || emit "Status unavailable"
# shellcheck source=scripts/lib/state.sh
. "$CORE_DIR/scripts/lib/state.sh" 2>/dev/null || emit "Status unavailable"

ROOT="${DEVTEAM_PROJECT_ROOT:-$(pwd)}"
STATE_DIR="${DEVTEAM_STATE_DIR:-$ROOT/.dev-team-agents/user-data}"
STATE_FILE="$STATE_DIR/state.json"

GRAPH="$ROOT/graphify-out/graph.json"
LAST_COMMIT="$(state_get graphify_last_run "$STATE_FILE" 2>/dev/null || true)"
LAST_AT="$(state_get graphify_last_run_at "$STATE_FILE" 2>/dev/null || true)"
HEAD_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"

if [ ! -f "$GRAPH" ]; then
  add_fact "Graph" "not built"
  emit "No graph yet - run Rebuild graph"
fi

add_fact "Graph" "graphify-out/graph.json present"

if [ -n "$LAST_COMMIT" ]; then
  when=""
  [ -n "$LAST_AT" ] && when=" at $LAST_AT"
  add_fact "Last build" "${LAST_COMMIT:0:7}$when"
  if [ -n "$HEAD_COMMIT" ] && [ "$HEAD_COMMIT" != "$LAST_COMMIT" ]; then
    ahead="$(git -C "$ROOT" rev-list --count "$LAST_COMMIT..HEAD" 2>/dev/null || true)"
    if [ -n "$ahead" ]; then
      add_fact "Since build" "$ahead commit(s) ahead"
    else
      add_fact "Since build" "HEAD moved"
    fi
    emit "Graph built at ${LAST_COMMIT:0:7}, HEAD has moved"
  fi
  add_fact "Since build" "up to date"
  emit "Graph built at ${LAST_COMMIT:0:7}"
fi

add_fact "Last build" "unknown"
emit "Graph present, last build not recorded"
