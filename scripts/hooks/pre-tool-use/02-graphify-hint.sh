#!/usr/bin/env bash
# PreToolUse sub-script: injects graphify context hint when Claude searches the codebase.
# Only fires when graph.json exists and the current tool is Glob or Grep.
set -euo pipefail

GRAPH="graphify-out/graph.json"
[ -f "$GRAPH" ] || exit 0

INPUT=$(cat)

# Pure-bash substring match instead of grep|sed: skips 2 forked subprocesses
# on every tool call that isn't Glob/Grep — the common case whenever a
# knowledge graph is present.
case "$INPUT" in
    *'"tool_name":"Glob"'*|*'"tool_name": "Glob"'*) ;;
    *'"tool_name":"Grep"'*|*'"tool_name": "Grep"'*) ;;
    *) exit 0 ;;
esac

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. First consult graphify-out/GRAPH_REPORT.md and graphify-out/graph.json to understand structure and relationships. Only search raw files if those two layers are insufficient."}}\n'
