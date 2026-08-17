#!/usr/bin/env bash
# PreToolUse sub-script: injects graphify context hint when Claude searches the codebase.
# Only fires when graph.json exists and the current tool is Glob or Grep — and
# only ONCE per session. Without the marker below this used to re-inject the
# same additionalContext block on every single Glob/Grep call, which compounds
# in the retained transcript over a long exploration-heavy session and was a
# confirmed contributor to "Prompt is too long" failures. The marker lives
# under user-data/ (mirroring session-start.sh's resolution so a linked
# worktree shares it with the main checkout) and is cleared by
# session-start.sh so the hint fires again at the start of the next session.
set -euo pipefail

GRAPH="graphify-out/graph.json"
[ -f "$GRAPH" ] || exit 0

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || PROJECT_ROOT="$(pwd)"
MAIN_REPO_ROOT="$(cd "$(git rev-parse --git-common-dir 2>/dev/null)/.." 2>/dev/null && pwd)"
[ -n "$MAIN_REPO_ROOT" ] || MAIN_REPO_ROOT="$PROJECT_ROOT"
MARKER="${MAIN_REPO_ROOT}/.dev-team-agents/user-data/.graphify-hint-shown"
[ -f "$MARKER" ] && exit 0

INPUT=$(cat)

# Pure-bash substring match instead of grep|sed: skips 2 forked subprocesses
# on every tool call that isn't Glob/Grep — the common case whenever a
# knowledge graph is present.
case "$INPUT" in
    *'"tool_name":"Glob"'*|*'"tool_name": "Glob"'*) ;;
    *'"tool_name":"Grep"'*|*'"tool_name": "Grep"'*) ;;
    *) exit 0 ;;
esac

mkdir -p "$(dirname "$MARKER")" 2>/dev/null && : > "$MARKER" 2>/dev/null || true
printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"graphify: Knowledge graph exists. First consult graphify-out/GRAPH_REPORT.md and graphify-out/graph.json to understand structure and relationships. Only search raw files if those two layers are insufficient."}}\n'
