#!/usr/bin/env bash
# Graphify plugin, PreToolUse: inject a graph hint when Claude searches the codebase.
# Fires on Glob/Grep only, and only ONCE per session (marker in the state dir, cleared
# by session-start.sh) - re-injecting on every search compounds in the retained
# transcript and contributed to "Prompt is too long" failures.
# Runs on every tool call: return before forking anything.
set -euo pipefail

ROOT="${DEVTEAM_PROJECT_ROOT:-$PWD}"
[ -f "$ROOT/graphify-out/graph.json" ] || exit 0

STATE_DIR="${DEVTEAM_STATE_DIR:-$ROOT/.dev-team-agents/user-data}"
MARKER="$STATE_DIR/.graphify-hint-shown"
[ -f "$MARKER" ] && exit 0

INPUT=$(cat)

case "$INPUT" in
    *'"tool_name":"Glob"'*|*'"tool_name": "Glob"'*) ;;
    *'"tool_name":"Grep"'*|*'"tool_name": "Grep"'*) ;;
    *) exit 0 ;;
esac

{ mkdir -p "$STATE_DIR" && : > "$MARKER"; } 2>/dev/null || true
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. First consult graphify-out/GRAPH_REPORT.md and graphify-out/graph.json to understand structure and relationships. Only search raw files if those two layers are insufficient."}}\n'
