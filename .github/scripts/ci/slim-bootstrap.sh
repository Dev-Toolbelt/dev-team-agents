#!/usr/bin/env bash
# slim-bootstrap.sh — End-to-end contract test for the slim Claude install +
# on-demand provider bootstrap. Verifies that:
#
#   1. A `git archive HEAD` tarball, after applying the strip rules in
#      scripts/lib/strip-tarball.sh (the SAME rules install.sh uses), has
#      the slim shape: cross-CLI plumbing absent, Claude runtime essential
#      scripts present.
#   2. install-provider.sh opencode --source <clone> populates .opencode/
#      correctly into a fixture project.
#   3. install-provider.sh codex --source <clone> populates .codex/ correctly.
#
# Usage: bash slim-bootstrap.sh <repo-root> <fixture-dir>
set -euo pipefail

SOURCE="$(cd "$1" && pwd)"
FIXTURE="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Files that MUST NOT appear in a slim Claude install's scripts/ directory.
# Mirrors the explicit rm -f list in scripts/lib/strip-tarball.sh (kept in sync
# by sourcing the same function below — this list is for documentation only;
# the authoritative source is strip-tarball.sh's apply_strip).
#
# Note: Cross-CLI plumbing (opencode/Codex render engine and installer scripts)
# is now INCLUDED in the slim Claude install so users can add Codex or opencode
# support without network access. These are no longer stripped.
SLIM_STRIP_LIST=()
SLIM_STRIP_DIRS=()

# Files that MUST still appear in slim scripts/ (Claude runtime essentials).
# install.sh itself is intentionally NOT in this list — it's stripped by
# apply_strip (curl-piped from GitHub, never bundled in the package).
# scripts/lib/strip-tarball.sh is NOT stripped because install.sh sources it.
SLIM_KEEP_LIST=(
  "scripts/install-provider.sh"
  "scripts/update.sh"
  "scripts/rollback.sh"
  "scripts/new-adr.sh"
  "scripts/validate-commit-msg.sh"
  "scripts/fix-symlinks.sh"
  "scripts/check-updates.sh"
  "scripts/graphify-refresh.sh"
  "scripts/hooks/stop.sh"
  "scripts/hooks/pre-tool-use.sh"
  "scripts/hooks/session-start.sh"
  "scripts/hooks/pre-compact.sh"
  "scripts/helpers/telemetry-send.sh"
  "scripts/lib/preferences-defaults.json"
  "scripts/lib/strip-tarball.sh"
)

# ── 1. Simulate tarball + strip ────────────────────────────────────────
# We use cp -r of the working tree (matching what CI sees after checkout,
# including uncommitted files) rather than `git archive HEAD` (which would
# exclude uncommitted files and break local rehearsal of this test).
STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

cp -r "$SOURCE/." "$STAGING/"
rm -rf "$STAGING/.git"

# Apply the SAME strip rules install.sh uses (single source of truth).
# shellcheck source=scripts/lib/strip-tarball.sh
source "$REPO_ROOT/scripts/lib/strip-tarball.sh"
apply_strip "$STAGING"

# ── 2. Assert slim-shape contract ──────────────────────────────────────
# Note: install.sh bundles everything into <project>/.dev-team-agents/
# so the paths are relative to STAGING which simulates that INSTALLED_DIR root.
fail=0
for path in "${SLIM_KEEP_LIST[@]}"; do
  if [ ! -e "$STAGING/$path" ]; then
    echo "slim: FAIL — expected $path not found after strip" >&2
    fail=1
  fi
done

for path in "${SLIM_STRIP_LIST[@]+"${SLIM_STRIP_LIST[@]}"}"; do
  [ -z "$path" ] && continue
  if [ -e "$STAGING/$path" ]; then
    echo "slim: FAIL — forbidden $path present after strip" >&2
    fail=1
  fi
done

for d in "${SLIM_STRIP_DIRS[@]+"${SLIM_STRIP_DIRS[@]}"}"; do
  [ -z "$d" ] && continue
  if [ -e "$STAGING/$d" ]; then
    echo "slim: FAIL — forbidden directory $d/ present after strip" >&2
    fail=1
  fi
done

[ "$fail" -eq 0 ] && echo "slim install shape OK ✓"

# ── 3. Bootstrap opencode via install-provider.sh --source ──────────────
rm -rf "$FIXTURE"
mkdir -p "$FIXTURE"
cd "$FIXTURE"
git init -q

bash "$SOURCE/scripts/install-provider.sh" opencode --source "$SOURCE" >/dev/null

python3 - <<PY
import json
d = json.load(open("$FIXTURE/.opencode/opencode.json"))
cmds = d.get("command", {})
assert len(cmds) >= 22, f"opencode bootstrap commands {len(cmds)} < 22"
for k, v in cmds.items():
    assert k.startswith("devteam:"), f"bad command key: {k}"
    for req in ("description", "agent", "model", "template"):
        assert v.get(req), f"{k} missing {req}"
print(f"opencode bootstrap OK ✓  ({len(cmds)} commands)")
PY

[ -f "$FIXTURE/.opencode/plugins/dev-team-agents.ts" ] || {
  echo "opencode bootstrap FAIL: plugin missing" >&2; exit 1
}
[ -L "$FIXTURE/.opencode/skills/dev-team-agents" ] || {
  echo "opencode bootstrap FAIL: skills symlink missing" >&2; exit 1
}
n_openc_agents=$(find "$FIXTURE/.opencode/agents" -maxdepth 1 -name '*.md' -type f | wc -l | tr -d ' ')
[ "$n_openc_agents" -ge 17 ] || {
  echo "opencode bootstrap FAIL: <17 agents ($n_openc_agents)" >&2; exit 1
}

# ── 4. Bootstrap codex via install-provider.sh --source ─────────────────
bash "$SOURCE/scripts/install-provider.sh" codex --source "$SOURCE" >/dev/null

python3 - <<PY
import json, os
d = json.load(open("$FIXTURE/.codex/hooks.json"))
hooks_obj = d.get("hooks")
assert isinstance(hooks_obj, dict), f"codex hooks.json 'hooks' must be object keyed by event (got {type(hooks_obj).__name__})"
required = {"SessionStart", "PreToolUse", "PreCompact", "Stop"}
present = set(hooks_obj.keys())
missing = required - present
assert not missing, f"codex hooks.json missing events: {sorted(missing)}"
# Each hook command must be a STRING and its referenced script must exist on disk.
missing_paths = []
for event, groups in hooks_obj.items():
    for grp in groups:
        for hh in grp.get("hooks", []):
            assert isinstance(hh.get("command"), str), f"{event}: command must be string"
            parts = hh["command"].split()
            assert len(parts) >= 2, f"{event}: malformed command"
            rel = parts[1]
            full = os.path.join("$FIXTURE", rel)
            if not os.path.exists(full):
                missing_paths.append(f"{event}: {rel}")
assert not missing_paths, f"codex hooks reference missing scripts: {missing_paths}"
print(f"codex bootstrap OK ✓  (hooks: {sorted(present)}, all 4 paths verified on disk)")
PY

n_codex_agents=$(find "$FIXTURE/.codex/agents" -maxdepth 1 -name '*.toml' -type f | wc -l | tr -d ' ')
n_codex_prompts=$(find "$FIXTURE/.codex/prompts" -maxdepth 1 -name 'devteam-*.md' -type f | wc -l | tr -d ' ')
[ "$n_codex_agents" -ge 17 ] || { echo "codex bootstrap FAIL: <17 agents" >&2; exit 1; }
[ "$n_codex_prompts" -ge 22 ] || { echo "codex bootstrap FAIL: <22 prompts" >&2; exit 1; }
[ -L "$FIXTURE/.codex/skills/dev-team-agents" ] || {
  echo "codex bootstrap FAIL: skills symlink missing" >&2; exit 1
}
# Codex hooks.json references bash scripts at .dev-team-agents/scripts/hooks/.
# Verify they actually exist post-bootstrap (catches broken ensure_claude_framework wiring).
for h in stop pre-tool-use session-start pre-compact; do
  [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/$h.sh" ] || {
    echo "codex bootstrap FAIL: hooks/$h.sh not materialized at .dev-team-agents/" >&2; exit 1; }
done
# Same check for the opencode plugin — verify its referenced hooks exist.
for h in stop pre-tool-use session-start pre-compact; do
  [ -f "$FIXTURE/.dev-team-agents/scripts/hooks/$h.sh" ] || {
    echo "opencode bootstrap FAIL: hooks/$h.sh not materialized at .dev-team-agents/" >&2; exit 1; }
done

echo "slim-bootstrap OK ✓  (slim Claude + opencode + codex)"