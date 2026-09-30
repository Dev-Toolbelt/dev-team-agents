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

ROOT="${DEVTEAM_PROJECT_ROOT:-$(pwd)}"

GRAPH="$ROOT/graphify-out/graph.json"
MARKER="$ROOT/graphify-out/.build-commit"
LAST_COMMIT=""
[ -f "$MARKER" ] && LAST_COMMIT="$(tr -d '[:space:]' < "$MARKER" 2>/dev/null || true)"
HEAD_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"

# Build time: the marker file's mtime (GNU stat, then BSD stat; GNU date, then BSD date).
build_time() {
  local epoch
  epoch="$(stat -c %Y "$MARKER" 2>/dev/null || stat -f %m "$MARKER" 2>/dev/null || true)"
  case "$epoch" in ''|*[!0-9]*) return 0 ;; esac
  date -u -d "@$epoch" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$epoch" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true
}
LAST_AT=""
[ -n "$LAST_COMMIT" ] && LAST_AT="$(build_time)"

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
