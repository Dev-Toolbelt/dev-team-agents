#!/usr/bin/env bash
# Graphify plugin status: one JSON object {"summary": str, "facts": [{"label","value","tone"?}]}.
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
  local tone=""
  [ -n "${3:-}" ] && tone=",\"tone\":\"$3\""
  FACTS="$FACTS{\"label\":\"$(json_escape "$1")\",\"value\":\"$(json_escape "$2")\"$tone}"
}

emit() {
  printf '{"summary":"%s","facts":[%s]}\n' "$(json_escape "$1")" "$FACTS"
  exit 0
}

ROOT="${DEVTEAM_PROJECT_ROOT:-$(pwd)}"

GRAPH="$ROOT/graphify-out/graph.json"
MARKER="$ROOT/graphify-out/.build-commit"
LAST_COMMIT=""
[ -f "$MARKER" ] && LAST_COMMIT="$(head -c 200 "$MARKER" 2>/dev/null | tr -d '[:space:]' || true)"
# The marker is committed with the graph, so untrusted: anything but a hex object name is absent.
if [ -n "$LAST_COMMIT" ] && ! [[ "$LAST_COMMIT" =~ ^[0-9a-f]{7,64}$ ]]; then LAST_COMMIT=""; fi
HEAD_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"

# Build time: the marker file's mtime (GNU stat, then BSD stat; GNU date, then BSD date).
build_time() {
  local epoch
  epoch="$(stat -c %Y "$MARKER" 2>/dev/null || stat -f %m "$MARKER" 2>/dev/null || true)"
  case "$epoch" in ''|*[!0-9]*) return 0 ;; esac
  date -d "@$epoch" '+%Y-%m-%d %H:%M' 2>/dev/null || date -r "$epoch" '+%Y-%m-%d %H:%M' 2>/dev/null || true
}
LAST_AT=""
[ -n "$LAST_COMMIT" ] && LAST_AT="$(build_time)"

if [ ! -f "$GRAPH" ]; then
  add_fact "graphify-out/graph.json" "missing" warning
  emit "No graph yet - run Rebuild graph"
fi

add_fact "graphify-out/graph.json" "present" positive

if [ -n "$LAST_COMMIT" ]; then
  if [ -n "$LAST_AT" ]; then add_fact "Last build" "$LAST_AT"; else add_fact "Last build" "not recorded" warning; fi
  if [ -n "$HEAD_COMMIT" ] && [ "$HEAD_COMMIT" != "$LAST_COMMIT" ]; then
    ahead="$(git -C "$ROOT" rev-list --count "$LAST_COMMIT..HEAD" 2>/dev/null || true)"
    if [ -n "$ahead" ]; then
      add_fact "Since build" "$ahead commit(s) ahead" warning
    else
      add_fact "Since build" "HEAD moved" warning
    fi
    emit "Graph built at ${LAST_COMMIT:0:7}, HEAD has moved"
  fi
  add_fact "Since build" "up to date" positive
  emit "Graph built at ${LAST_COMMIT:0:7}"
fi

add_fact "Last build" "not recorded" warning
emit "Graph present, last build not recorded"
