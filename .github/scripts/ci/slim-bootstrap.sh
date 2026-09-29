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

# ── 2b. Root allowlist: what must NEVER reach a user project ────────────
# Everything above tests apply_strip. install.sh applies a SECOND mechanism that
# apply_strip knows nothing about: a KEEP_ROOT allowlist over the extracted
# tarball root, which deletes every root entry not named in it. Section 2 cannot
# see that mechanism at all, so until now a change to the allowlist was checked
# by nothing.
#
# ADR-0015's Electron client under app/ is the case that made the gap matter. Its
# Risks table leans on the allowlist by name — "KEEP_ROOT keeps app/ out of every
# installed project, so a dependency defect cannot reach a user through the
# framework's own channel" — and that mitigation was incidental: one word added to
# one line would have put node_modules (100 MB+, tens of thousands of files), a
# lockfile that every JS tool walking upward would then honour, and a packaged
# Chromium into every user's repository. This section makes the claim asserted.
#
# The allowlist is PARSED from install.sh, never restated. A second copy here
# would go green while the real allowlist shipped app/ — the only failure this
# section exists to catch.
#
# The tree it is applied to is SYNTHETIC on purpose. Asserting against the
# working tree alone passes vacuously on any checkout where app/ happens not to
# exist, which is a green that proves nothing; the synthetic root always contains
# the forbidden entries, so the assertion has something to remove on every run.
KEEP_ROOT_DECL="$(sed -n 's/^KEEP_ROOT=(\(.*\))[[:space:]]*$/\1/p' "$SOURCE/scripts/install.sh")"
if [ -z "$KEEP_ROOT_DECL" ]; then
  echo "allowlist: CANNOT RUN — no KEEP_ROOT=(...) line found in scripts/install.sh." >&2
  echo "  The declaration moved or changed shape. Re-point this parser; a check that" >&2
  echo "  cannot run has not passed (see 01-lint.sh, ENFORCEMENT POLICY)." >&2
  exit 2
fi
KEEP_ROOT_PARSED=()
read -r -a KEEP_ROOT_PARSED <<<"$KEEP_ROOT_DECL"
echo "allowlist parsed from install.sh: ${KEEP_ROOT_PARSED[*]}"

# The loop from scripts/install.sh, iterating `/*` so dotfiles are untouched
# exactly as they are there, and removing every root entry not in the allowlist.
#
# One deliberate difference: the removal is an `if`, not install.sh's
# `[ "$keep" = false ] && rm -rf "$item"`. That form makes a kept entry the last
# command's failure, so a function (or a loop) that ends on one returns 1 and
# aborts the caller under `set -e`. install.sh survives it only because the
# alphabetically last root entry happens to be one it removes.
apply_root_allowlist() {
  local root="$1" item name k keep
  for item in "$root"/*; do
    [ -e "$item" ] || continue
    name="$(basename "$item")"
    keep=false
    for k in "${KEEP_ROOT_PARSED[@]}"; do
      if [ "$name" = "$k" ]; then keep=true; break; fi
    done
    if [ "$keep" = false ]; then rm -rf "$item"; fi
  done
}

# Names and extensions that must not survive anywhere in an installed project.
# Chosen for what a user would have to live with, not just for app/:
#   node_modules                — the size and the file count, and the only
#                                 directory here a user is certain to notice
#   package.json / lockfiles    — an installed tree that reads as a node package
#                                 to every JS tool walking upward, and to a
#                                 dependency bot that would then open pull
#                                 requests against a file the user never wrote
#   *.asar / *.dmg / *.AppImage — a packaged Electron build, i.e. shipping the
#                                 desktop app itself through the framework's
#                                 install channel
#
# Checked by NAME anywhere in the tree, not only under app/, because a
# node_modules or a lockfile nested inside an ALLOWLISTED tree (scripts/,
# skills/) survives both mechanisms and neither of them would say so. That is
# true today and is the case this assertion will still be here for.
#
# node_modules is reported once and pruned: without the prune the failure output
# is one line per nested package.json, which on a real dependency tree was 600+
# lines of log for a single finding.
assert_no_js_payload() {
  local root="$1" label="$2" hits total
  hits="$(cd "$root" && find . -name node_modules -print -prune -o \
      \( -name package.json \
         -o -name package-lock.json \
         -o -name npm-shrinkwrap.json \
         -o -name yarn.lock \
         -o -name pnpm-lock.yaml \
         -o -name '*.asar' \
         -o -name '*.dmg' \
         -o -name '*.AppImage' \) -print 2>/dev/null || true)"
  [ -n "$hits" ] || return 0
  total="$(printf '%s\n' "$hits" | wc -l | tr -d '[:space:]')"
  echo "allowlist: FAIL — ${label} still carries JavaScript payload after strip + allowlist (${total} path(s)):" >&2
  printf '%s\n' "$hits" | head -20 | sed 's/^/    /' >&2
  [ "$total" -gt 20 ] && echo "    … and $((total - 20)) more" >&2
  return 1
}

# (A) Synthetic root — the real allowlist applied to a tree that definitely
#     contains the Electron client, whatever the working tree looks like today.
ALLOW_STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING" "$ALLOW_STAGING"' EXIT
while IFS= read -r root_entry; do
  if [ -n "$root_entry" ]; then mkdir -p "$ALLOW_STAGING/$root_entry"; fi
done <<EOF
$(cd "$SOURCE" && ls -1)
EOF
mkdir -p "$ALLOW_STAGING/app/node_modules/electron/dist" \
         "$ALLOW_STAGING/app/src/cli" \
         "$ALLOW_STAGING/app/release"
touch "$ALLOW_STAGING/app/package.json" \
      "$ALLOW_STAGING/app/package-lock.json" \
      "$ALLOW_STAGING/app/node_modules/electron/package.json" \
      "$ALLOW_STAGING/app/release/dev-team-agents.dmg" \
      "$ALLOW_STAGING/app/release/app.asar"
apply_root_allowlist "$ALLOW_STAGING"
apply_strip "$ALLOW_STAGING"

if [ -e "$ALLOW_STAGING/app" ]; then
  echo "allowlist: FAIL — app/ survived the KEEP_ROOT allowlist in scripts/install.sh." >&2
  echo "  The Electron desktop client (ADR-0015) would be installed into every user project." >&2
  echo "  KEEP_ROOT is an allowlist: adding 'app' to it ships app/, and ADR-0015's risk" >&2
  echo "  mitigation depends on it not being there." >&2
  fail=1
fi
assert_no_js_payload "$ALLOW_STAGING" "the synthetic root" || fail=1

# The other direction: an allowlist that stops keeping what the runtime needs is
# just as broken as one that keeps too much, and nothing else asserts the five
# top-level trees survive it.
#
# This list is hardcoded ON PURPOSE, unlike the allowlist itself. It states what
# an installed project REQUIRES, so it has to be independent of the declaration
# it is checking — parsing KEEP_ROOT here would make the assertion agree with
# whatever the allowlist says and therefore assert nothing. Do not "deduplicate"
# it against the parser above.
for keep_dir in agents scripts skills templates commands; do
  if [ ! -d "$ALLOW_STAGING/$keep_dir" ]; then
    echo "allowlist: FAIL — ${keep_dir}/ did not survive the allowlist; an installed project needs it." >&2
    fail=1
  fi
done

# (B) The real tree, which today genuinely carries app/ with an installed
#     node_modules — so this proves the mechanism removes the actual payload and
#     not merely a fixture. STAGING is consumed here: section 2's assertions are
#     complete and nothing below reads it again.
apply_root_allowlist "$STAGING"
assert_no_js_payload "$STAGING" "the stripped working tree" || fail=1

[ "$fail" -eq 0 ] || exit 1
echo "root allowlist OK ✓  (app/, node_modules, lockfiles and packaged builds cannot reach a user project)"

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
n_codex_skills=$(find "$FIXTURE/.codex/skills" -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' | wc -l | tr -d ' ')
[ "$n_codex_agents" -ge 17 ] || { echo "codex bootstrap FAIL: <17 agents" >&2; exit 1; }
[ "$n_codex_skills" -ge 22 ] || { echo "codex bootstrap FAIL: <22 command skills" >&2; exit 1; }
[ -L "$FIXTURE/.codex/skills/dev-team-agents" ] || {
  echo "codex bootstrap FAIL: skills symlink missing" >&2; exit 1
}
# Project-local prompts were removed in the skills-first Codex layout.
if [ -d "$FIXTURE/.codex/prompts" ]; then
  n_codex_prompts=$(find "$FIXTURE/.codex/prompts" -maxdepth 1 -name 'devteam-*.md' -type f | wc -l | tr -d ' ')
  [ "$n_codex_prompts" -eq 0 ] || {
    echo "codex bootstrap FAIL: legacy project-local prompts still present ($n_codex_prompts)" >&2; exit 1; }
fi
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
