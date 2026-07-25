#!/usr/bin/env bash
# 50-validate-installed.sh — Verify the fixture project's provider-specific
# files parse and carry the expected artifacts after the installer ran.
#
# Usage: bash 50-validate-installed.sh <provider> <repo-root> <fixture-dir>
set -euo pipefail

PROVIDER="$1"
FIXTURE="$3"

case "$PROVIDER" in
  claude)
    echo "claude fixture validate: skipped (Claude installer downloads from network; validated via contract.sh against staging)"
    exit 0
    ;;
  opencode)
    # .opencode/opencode.json parses; commands >=22; plugin present; skills symlink exists
    python3 -c "
import json, os
d = json.load(open('$FIXTURE/.opencode/opencode.json'))
assert len(d.get('command', {})) >= 22, f'commands {len(d.get(\"command\", {}))} < 22'
for k, v in d['command'].items():
    assert k.startswith('devteam:'), f'bad command key: {k}'
    for req in ('description', 'agent', 'model', 'template'):
        assert v.get(req), f'{k} missing {req}'
print(f'opencode fixture: commands={len(d[\"command\"])}')
"
    [ -f "$FIXTURE/.opencode/plugins/dev-team-agents.ts" ] || { echo "FAIL: plugin missing" >&2; exit 1; }
    [ -L "$FIXTURE/.opencode/skills/dev-team-agents" ] || { echo "FAIL: skills symlink missing" >&2; exit 1; }
    n_agents=$(find "$FIXTURE/.opencode/agents" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
    echo "opencode fixture: agents=$n_agents"
    [ "$n_agents" -ge 17 ] || { echo "FAIL: <17 opencode agents" >&2; exit 1; }
    ;;
  codex)
    # .codex/hooks.json parses and has the 4 managed events
    python3 -c "
import json
d = json.load(open('$FIXTURE/.codex/hooks.json'))
events = {h['event'] for h in d.get('hooks', [])}
required = {'SessionStart', 'PreToolUse', 'PreCompact', 'Stop'}
missing = required - events
assert not missing, f'codex hooks.json missing events: {sorted(missing)}'
print(f'codex fixture: hook events={sorted(events)}')
"
    n_agents=$(find "$FIXTURE/.codex/agents" -maxdepth 1 -name '*.toml' -type f | wc -l | tr -d ' ')
    n_prompts=$(find "$FIXTURE/.codex/prompts" -maxdepth 1 -name 'devteam-*.md' -type f | wc -l | tr -d ' ')
    [ -L "$FIXTURE/.codex/skills/dev-team-agents" ] || { echo "FAIL: codex skills symlink missing" >&2; exit 1; }
    echo "codex fixture: agents=$n_agents prompts=$n_prompts"
    [ "$n_agents" -ge 17 ] || { echo "FAIL: <17 codex agents" >&2; exit 1; }
    [ "$n_prompts" -ge 22 ] || { echo "FAIL: <22 codex prompts" >&2; exit 1; }
    ;;
  *)
    echo "50-validate-installed: unknown provider '$PROVIDER'" >&2; exit 2 ;;
esac

echo "fixture validated ✓  ($PROVIDER)"