#!/usr/bin/env bash
# 20-attendance.sh — Per-provider rendered file counts must equal source counts.
# Counts are DERIVED from the canonical source (not hardcoded), so removido or
# adding agents/commands updates the expectation automatically.
#
# Usage: bash 20-attendance.sh <provider> <repo-root> <staging-dir>
set -euo pipefail

PROVIDER="$1"
SOURCE="$2"
STAGING="$3"

expected_agents=$(find "$SOURCE/agents" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
expected_commands=$(python3 -c "import json; print(len(json.load(open('$SOURCE/scripts/lib/commands.json'))['commands']))")

case "$PROVIDER" in
  claude)
    actual_agents=$(find "$STAGING/.claude/agents/dev-team" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    actual_commands=$(find "$STAGING/.claude/commands/devteam" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    ;;
  opencode)
    actual_agents=$(find "$STAGING/.opencode/agents" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    actual_commands=$(python3 - <<PY
import json
text = open("$STAGING/.opencode/commands.snippet.jsonc").read()
clean = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
print(len(json.loads(clean)))
PY
)
    ;;
  codex)
    actual_agents=$(find "$STAGING/.codex/agents" -maxdepth 1 -name '*.toml' -type f | wc -l | tr -d ' ')
    actual_commands=$(find "$STAGING/.codex/skills" -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' | wc -l | tr -d ' ')
    ;;
  *)
    echo "20-attendance: unknown provider '$PROVIDER'" >&2; exit 2 ;;
esac

echo "agents:   $actual_agents  (expected $expected_agents)"
echo "commands: $actual_commands  (expected $expected_commands)"

if [ "$actual_agents" -eq "$expected_agents" ] && [ "$actual_commands" -eq "$expected_commands" ]; then
  echo "attendance OK ✓  ($PROVIDER)"
else
  echo "attendance FAIL — $PROVIDER did not produce expected file counts" >&2
  exit 1
fi
