#!/usr/bin/env bash
# PreToolUse sub-script: injects graphify context hint when Claude searches the codebase.
# Only fires when graph.json exists and the current tool is Glob or Grep.
set -euo pipefail

GRAPH="graphify-out/graph.json"
[ -f "$GRAPH" ] || exit 0

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | grep -o '"tool_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')

case "$TOOL_NAME" in
    Glob|Grep) ;;
    *) exit 0 ;;
esac

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. First consult graphify-out/GRAPH_REPORT.md and graphify-out/graph.json to understand structure and relationships. Only search raw files if those two layers are insufficient."}}\n'
