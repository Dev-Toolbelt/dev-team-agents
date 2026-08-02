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
    # The plugin references ${directory}/.dev-team-agents/scripts/hooks/<n>.sh
    # Verify those paths actually exist on disk after the installer ran (catches
    # the case where ensure-claude-framework.sh was not invoked).
    for h in stop pre-tool-use session-start pre-compact; do
      [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/$h.sh" ] || {
        echo "FAIL: .dev-team-agents/scripts/hooks/$h.sh not materialized — the opencode plugin will fail to fire $h hooks" >&2; exit 1; }
    done
    ;;
  codex)
    # .codex/hooks.json parses, has 4 managed events, each hook command path resolves
    python3 - <<PY
import json, os
fpath = "$FIXTURE/.codex/hooks.json"
d = json.load(open(fpath))
hooks_obj = d.get("hooks")
assert isinstance(hooks_obj, dict), f"codex hooks.json 'hooks' must be an object keyed by event (got {type(hooks_obj).__name__})"
required = {"SessionStart", "PreToolUse", "PreCompact", "Stop"}
missing = required - set(hooks_obj.keys())
assert not missing, f"codex hooks.json missing events: {sorted(missing)}"
missing_paths = []
for event, groups in hooks_obj.items():
    for grp in groups:
        for hh in grp.get("hooks", []):
            assert isinstance(hh.get("command"), str), f"{event}: command must be a string"
            # commands look like 'bash .dev-team-agents/scripts/hooks/<n>.sh'
            parts = hh["command"].split()
            if len(parts) < 2:
                missing_paths.append(f"{event}: malformed command '{hh['command']}'")
                continue
            rel = parts[1]
            full = os.path.join("$FIXTURE", rel)
            if not os.path.exists(full):
                missing_paths.append(f"{event}: hook script '{rel}' not on disk at '{full}'")
assert not missing_paths, f"codex hooks.json references missing scripts: {missing_paths}"
print(f"codex fixture: hook events={sorted(hooks_obj.keys())} (all 4 paths verified on disk)")
PY
    n_agents=$(find "$FIXTURE/.codex/agents" -maxdepth 1 -name '*.toml' -type f | wc -l | tr -d ' ')
    n_skills=$(find "$FIXTURE/.codex/skills" -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' | wc -l | tr -d ' ')
    [ -L "$FIXTURE/.codex/skills/dev-team-agents" ] || { echo "FAIL: codex skills symlink missing" >&2; exit 1; }
    # Also assert the Claude framework runtime subset is materialized
    [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/stop.sh" ] || { echo "FAIL: .dev-team-agents/scripts/hooks/stop.sh not materialized (codex hooks would dangle)" >&2; exit 1; }
    [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/pre-tool-use.sh" ] || { echo "FAIL: .dev-team-agents/scripts/hooks/pre-tool-use.sh not materialized" >&2; exit 1; }
    [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/session-start.sh" ] || { echo "FAIL: .dev-team-agents/scripts/hooks/session-start.sh not materialized" >&2; exit 1; }
    [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/pre-compact.sh" ] || { echo "FAIL: .dev-team-agents/scripts/hooks/pre-compact.sh not materialized" >&2; exit 1; }
    if [ -d "$FIXTURE/.codex/prompts" ]; then
      n_prompts=$(find "$FIXTURE/.codex/prompts" -maxdepth 1 -name 'devteam-*.md' -type f | wc -l | tr -d ' ')
      [ "$n_prompts" -eq 0 ] || { echo "FAIL: legacy project-local codex prompts still present ($n_prompts)" >&2; exit 1; }
    fi
    echo "codex fixture: agents=$n_agents skills=$n_skills"
    [ "$n_agents" -ge 17 ] || { echo "FAIL: <17 codex agents" >&2; exit 1; }
    [ "$n_skills" -ge 22 ] || { echo "FAIL: <22 codex command skills" >&2; exit 1; }
    ;;
  *)
    echo "50-validate-installed: unknown provider '$PROVIDER'" >&2; exit 2 ;;
esac

echo "fixture validated ✓  ($PROVIDER)"
