# Health Check Categories and Commands

## Category 1 — Symlinks

Do NOT trust `ls -la` alone: on Windows (git-bash/MSYS) it prints `lrwxrwxrwx`
for links that are really plain text files. Test with `-L` (true symlink) to
tell the three states apart:

```bash
# For each link path, classify: OK (symlink) / MATERIALIZED (file) / MISSING
for p in .claude/agents/dev-team .claude/commands/devteam; do
  if [ -L "$p" ]; then echo "OK: $p"
  elif [ -e "$p" ]; then echo "MATERIALIZED: $p"   # file/dir where a symlink belongs
  else echo "MISSING: $p"; fi
done
# skills: count any entry that exists but is neither a symlink nor a directory
find .claude/skills -maxdepth 1 -mindepth 1 ! -type l ! -type d 2>/dev/null | wc -l
```

| Check | Expected | Auto-fix |
|-------|----------|----------|
| `.claude/agents/dev-team` is a symlink | `-L` true → `../../.dev-team-agents/agents` | If MISSING: `ln -s ../../.dev-team-agents/agents .claude/agents/dev-team` |
| `.claude/commands/devteam` is a symlink | `-L` true → `../../.dev-team-agents/commands` | If MISSING: `ln -s ../../.dev-team-agents/commands .claude/commands/devteam` |
| `.claude/skills/` entries are symlinks | Each skill dir linked | If MISSING: re-run skill linking loop from `install.sh` |
| No link is **MATERIALIZED** (a plain file) | `find … ! -type l ! -type d` returns 0 | If any MATERIALIZED: **do not** `ln -s` (path exists). Run `bash .dev-team-agents/scripts/fix-symlinks.sh` — see fix-patterns.md |

> **MATERIALIZED = the Windows condition.** git/MSYS wrote the link target
> into a ~62-byte text file because native symlinks were unavailable
> (Developer Mode off, process not elevated, `core.symlinks=false`). The
> dev-team is invisible to the CLI even though git-bash "sees" the links.
> This is a `🔧 FIX` that cannot be auto-`ln -s`'d — route it through
> `fix-symlinks.sh`, which repairs when possible and otherwise surfaces the
> 3 remediation options for the user.

## Category 2 — Scripts & Executability

```bash
for f in \
  .dev-team-agents/scripts/hooks/pre-tool-use.sh \
  .dev-team-agents/scripts/hooks/stop.sh \
  .dev-team-agents/scripts/hooks/session-start.sh \
  .dev-team-agents/scripts/hooks/pre-tool-use/01-check-updates.sh \
  .dev-team-agents/scripts/hooks/stop/01-session-summary.sh \
  .dev-team-agents/scripts/hooks/stop/04-notifier.sh \
  .dev-team-agents/scripts/update.sh; do
  [ -f "$f" ] && [ -x "$f" ] && echo "OK: $f" || echo "FAIL: $f"
done
```

| Check | Auto-fix |
|-------|----------|
| All dispatcher and sub-scripts exist | Re-run `chmod +x` |
| All scripts are executable | `chmod +x <script>` |

## Category 3 — User Data & Legacy Paths

⚠️ **CRITICAL — do NOT create or write to `.claude/user-data/` or `.claude/dev-team-agents/`.** Those paths are legacy. All operations must use `.dev-team-agents/user-data/`.

```bash
# Check new paths
ls -la .dev-team-agents/user-data/ 2>/dev/null || echo "MISSING"
cat .dev-team-agents/user-data/.installed-version 2>/dev/null || echo "MISSING"

# Check for legacy paths that should have been migrated
for _legacy in .claude/user-data .claude/docs .claude/context .claude/tasks .claude/dev-team-agents; do
  [ -e "$_legacy" ] && echo "LEGACY_DIR: $_legacy"
done
```

| Check | Auto-fix |
|-------|----------|
| `.dev-team-agents/user-data/` directory exists | `mkdir -p .dev-team-agents/user-data/` (never `.claude/user-data/`) |
| `.installed-version` exists | WARN only — re-run installer to populate |
| Legacy `.claude/` dirs exist (user-data, docs, context, tasks, dev-team-agents) | **Migrate immediately**: move contents to new locations (see fix-patterns.md Legacy directory migration). Do NOT skip this step. Leftovers are `rmdir`'d only when empty, and quarantined otherwise — never `rm -rf` |
| Memory artifacts present (`session-summary.md`, `docs/wiki/`, `docs/development/adrs/`, `docs/project.md`) | Adapt in place only — see Category 11. Never regenerate over an existing file |

## Category 4 — settings.json / Provider Config

```bash
cat .claude/settings.json 2>/dev/null || echo "MISSING_CLAUDE"
cat .opencode/opencode.json 2>/dev/null || echo "MISSING_OPENCODE"
```

### For Claude provider

| Check | Expected value | Fix action |
|-------|---------------|------------|
| `hooks.PreToolUse` has exactly one dev-team entry | command = `…/scripts/hooks/pre-tool-use.sh`, matcher `.*` | Replace old entries (e.g. `update.sh --check`, inline graphify command) with dispatcher |
| `hooks.Stop` has exactly one dev-team entry | command = `…/scripts/hooks/stop.sh` | Replace old entries (e.g. `session-summary-hook.sh`, `graphify-refresh.sh`) with dispatcher |
| No stale direct hook paths remain | No `update.sh --check`, `session-summary-hook.sh`, or `graphify-refresh.sh` as direct hook commands | Consolidate into dispatchers |
| `includeCoAuthoredBy` is `false` | `"includeCoAuthoredBy": false` | Auto-fix: inject via python3 (see fix-patterns.md) |

### For opencode provider

```bash
# Check that every agent file has model + variant in frontmatter
for f in .opencode/agents/*.md; do
  [ -f "$f" ] || continue
  has_model=$(grep -c '^model: ' "$f" || true)
  has_variant=$(grep -c '^variant: ' "$f" || true)
  name=$(basename "$f" .md)
  if [ "$has_model" -eq 0 ] || [ "$has_variant" -eq 0 ]; then
    echo "MISSING_CONFIG: $name"
  fi
done
```

| Check | Expected | Fix action |
|-------|----------|------------|
| `.opencode/agents/*.md` have `model:` and `variant:` in frontmatter | Every agent file has both fields | Re-run `bash .dev-team-agents/scripts/install-opencode.sh` |
| `.opencode/opencode.json` `command` entries have `model:` | Each `devteam:*` command entry has `model` key | Re-run `bash .dev-team-agents/scripts/install-opencode.sh` |
| Plugin exists | `.opencode/plugins/dev-team-agents.ts` | Re-run `bash .dev-team-agents/scripts/install-opencode.sh` |

### For Codex provider

```bash
# Hooks.json present and parseable
[ -f .codex/hooks.json ] && python3 - <<'PY'
import json
from pathlib import Path
p = Path(".codex/hooks.json")
try:
    data = json.loads(p.read_text())
except Exception:
    print("HOOKS_JSON_INVALID")
    raise SystemExit(0)

hooks = data.get("hooks", {})
managed = {
    "SessionStart": ".dev-team-agents/scripts/hooks/session-start.sh",
    "PreToolUse": ".dev-team-agents/scripts/hooks/pre-tool-use.sh",
    "PreCompact": ".dev-team-agents/scripts/hooks/pre-compact.sh",
    "Stop": ".dev-team-agents/scripts/hooks/stop.sh",
}
for event, suffix in managed.items():
    groups = hooks.get(event, [])
    found = False
    for grp in groups if isinstance(groups, list) else []:
        for hook in (grp.get("hooks", []) if isinstance(grp, dict) else []):
            if isinstance(hook, dict) and hook.get("type") == "command" and suffix in (hook.get("command") or ""):
                found = True
                break
        if found:
            break
    print(f"{event}:{'OK' if found else 'MISSING'}")
PY

# Generated command skills
find .codex/skills -mindepth 1 -maxdepth 1 -type d -name 'devteam-*' 2>/dev/null | wc -l

# Generated skill payload files
find .codex/skills -path '*/devteam-*/SKILL.md' 2>/dev/null | wc -l

# Generated skill frontmatter names match their folder basenames
python3 - <<'PY'
import re
from pathlib import Path

skills_dir = Path(".codex/skills")
for skill_dir in sorted(skills_dir.glob("devteam-*")):
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"{skill_dir.name}:MISSING_SKILL_MD")
        continue
    text = skill_md.read_text()
    m_name = re.search(r'^name:\s*"([^"]+)"', text, re.M)
    got = m_name.group(1) if m_name else None
    state = "OK" if got == skill_dir.name else "MISMATCH"
    print(f"{skill_dir.name}:{state}:name={got}")
PY

# Legacy project-local prompts from the pre-skills-first Codex layout
find .codex/prompts -maxdepth 1 -type f -name 'devteam-*.md' 2>/dev/null | wc -l

# Render-generation marker for structured quiz support on Codex
python3 - <<'PY'
from pathlib import Path

skills = [
    Path(".codex/skills/devteam-update/SKILL.md"),
    Path(".codex/skills/devteam-commit/SKILL.md"),
    Path(".codex/skills/devteam-explain/SKILL.md"),
]

missing = []
for path in skills:
    if not path.exists():
        missing.append(f"{path.name}:MISSING")
        continue
    text = path.read_text()
    has_request = "`request_user_input`" in text
    has_plan_note = "/plan" in text
    has_plaintext_degrade = "ask the user directly and present the same options as plain text" in text
    if has_request and has_plan_note and not has_plaintext_degrade:
        print(f"{path.parent.name}:OK")
    else:
        parts = []
        if not has_request:
            parts.append("missing_request_user_input")
        if not has_plan_note:
            parts.append("missing_plan_mode_retry")
        if has_plaintext_degrade:
            parts.append("legacy_plain_text_degrade")
        print(f"{path.parent.name}:MISMATCH:{','.join(parts)}")

for item in missing:
    print(item)
PY

# Agent TOML model / effort mapping against tiers.json + agent_effort overrides
python3 - <<'PY'
import json, re
from pathlib import Path

tiers = json.loads(Path(".dev-team-agents/scripts/lib/tiers.json").read_text())
agent_dir = Path(".codex/agents")

def expected_for(agent_name, tier):
    model = tiers["tiers"][tier]["codex"].split("/", 1)[1]
    effort = None
    override = tiers.get("agent_effort", {}).get(agent_name)
    if isinstance(override, dict):
        effort = override.get("codex")
    if effort is None:
        effort = tiers.get("effort", {}).get(tier, {}).get("codex")
    return model, effort

for f in sorted(agent_dir.glob("*.toml")):
    text = f.read_text()
    m_model = re.search(r'^model = "([^"]+)"', text, re.M)
    m_effort = re.search(r'^model_reasoning_effort = "([^"]+)"', text, re.M)
    m_tier = re.search(r'^\| `[^`]+` \| `([^`]+)` \|', text, re.M)
    if not (m_model and m_tier):
        print(f"{f.stem}:INVALID")
        continue
    tier = m_tier.group(1)
    want_model, want_effort = expected_for(f.stem, tier)
    got_model = m_model.group(1)
    got_effort = m_effort.group(1) if m_effort else None
    state = "OK" if (got_model == want_model and got_effort == want_effort) else "MISMATCH"
    print(f"{f.stem}:{state}:model={got_model}:effort={got_effort}:expected_model={want_model}:expected_effort={want_effort}")
PY
```

| Check | Expected | Fix action |
|-------|----------|------------|
| `.codex/hooks.json` exists and parses | No `HOOKS_JSON_INVALID` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |
| Managed hook entries present | `SessionStart:OK`, `PreToolUse:OK`, `PreCompact:OK`, `Stop:OK` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |
| Generated command skills present | Counts of `.codex/skills/devteam-*` dirs and `SKILL.md` files equal `find commands -maxdepth 1 -name '*.md'` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |
| Generated command skill names match folder basenames | Every row ends in `:OK:name=devteam-*` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |
| Legacy project-local prompt aliases absent | Count of `.codex/prompts/devteam-*.md` is `0` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |
| Rendered Codex quiz guidance is on the new `request_user_input` generation | `devteam-update:OK`, `devteam-commit:OK`, `devteam-explain:OK` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |
| Agent TOML `model`/`model_reasoning_effort` matches `tiers.json` | Every row ends in `:OK:` | Re-run `bash .dev-team-agents/scripts/install-codex.sh` |

## Category 5 — Graphify (skip if not enabled)

Detect: `[ -f .dev-team-agents/user-data/graphify.json ] && echo ENABLED || echo DISABLED`

If DISABLED, skip the rest of this category and report `Graphify ... N/A (not configured)`.

If ENABLED, run 5a–5e in order.

### 5a — Dependencies

```bash
command -v graphify >/dev/null 2>&1 && echo "OK: graphify" || echo "MISSING: graphify binary"
command -v jq >/dev/null 2>&1 && echo "OK: jq" || echo "MISSING: jq"
```

### 5b — Config validity

```bash
CFG=.dev-team-agents/user-data/graphify.json
jq empty "$CFG" 2>/dev/null && echo "OK: valid JSON" || echo "INVALID: graphify.json is not valid JSON"
jq -e '.targetPaths | length > 0' "$CFG" >/dev/null 2>&1 && echo "OK: targetPaths present" || echo "MISSING: targetPaths empty or absent"

# Every targetPath must exist in the project
jq -r '.targetPaths[]? // empty' "$CFG" 2>/dev/null | while IFS= read -r p; do
  [ -e "$p" ] && echo "OK: targetPath $p" || echo "MISSING: targetPath '$p' does not exist"
done

# Every manifestPath, if declared, must exist
jq -r '.manifestPaths[]? // empty' "$CFG" 2>/dev/null | while IFS= read -r m; do
  [ -e "$m" ] && echo "OK: manifestPath $m" || echo "MISSING: manifestPath '$m' does not exist"
done
```

### 5c — Hook wiring

```bash
ls .dev-team-agents/scripts/hooks/stop/99-graphify-refresh.sh 2>/dev/null || echo "MISSING"
ls .dev-team-agents/scripts/hooks/pre-tool-use/02-graphify-hint.sh 2>/dev/null || echo "MISSING"
# Legacy sub-script that causes stop-hook loops
ls .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh 2>/dev/null && echo "LEGACY_FOUND"
```

### 5d — Output presence and integrity

```bash
ls graphify-out/ 2>/dev/null | head -3 || echo "MISSING: graphify-out/"
if [ -f graphify-out/graph.json ]; then
  jq empty graphify-out/graph.json 2>/dev/null && echo "OK: graph.json valid" || echo "INVALID: graphify-out/graph.json is not valid JSON"
else
  echo "MISSING: graphify-out/graph.json"
fi
[ -f graphify-out/GRAPH_REPORT.md ] && echo "OK: GRAPH_REPORT.md" || echo "MISSING: graphify-out/GRAPH_REPORT.md"

# Is the last recorded build behind the current commit?
LAST="$(tr -d '[:space:]' < .dev-team-agents/user-data/.graphify-last-run 2>/dev/null)"
HEAD_COMMIT="$(git rev-parse HEAD 2>/dev/null)"
[ -n "$LAST" ] && [ -n "$HEAD_COMMIT" ] && [ "$LAST" != "$HEAD_COMMIT" ] && echo "MARKER_BEHIND_HEAD: last=$LAST head=$HEAD_COMMIT"
```

### 5e — Generation actually works (not just "files exist")

Run the refresh script for real and confirm it does what it claims — file *presence* alone does not prove the pipeline works; `graphify-refresh.sh` has shipped versions where the change-detection gate silently no-op'd (SIGPIPE under `pipefail`) or the output swap silently aborted (macOS ACL on `graphify-out/cache` blocking `rm -rf`), both exiting `0` with no visible error:

```bash
BEFORE_MTIME=$(stat -f %m graphify-out/graph.json 2>/dev/null || stat -c %Y graphify-out/graph.json 2>/dev/null || echo 0)
bash .dev-team-agents/scripts/graphify-refresh.sh; REFRESH_EXIT=$?
AFTER_MTIME=$(stat -f %m graphify-out/graph.json 2>/dev/null || stat -c %Y graphify-out/graph.json 2>/dev/null || echo 0)
echo "EXIT:$REFRESH_EXIT"
[ "$REFRESH_EXIT" -ne 0 ] && echo "REFRESH_FAILED"
```

- If `MARKER_BEHIND_HEAD` was reported in 5d (or `graphify-out/` was `MISSING`) and `AFTER_MTIME` equals `BEFORE_MTIME`, the refresh **silently no-op'd** — the script ran, exited `0`, and did not rebuild. Report as FIX, not WARN.
- If `REFRESH_FAILED`, surface the script's stderr to the user rather than treating it as a WARN.

### 5f — .gitignore entries

```bash
grep -qxF ".dev-team-agents/user-data/.graphify-last-run" .gitignore 2>/dev/null && echo "OK" || echo "MISSING"
grep -qxF "graphify-out/cache" .gitignore 2>/dev/null && echo "OK" || echo "MISSING"
grep -qF "!.dev-team-agents/user-data/graphify.json" .gitignore 2>/dev/null && echo "OK" || echo "MISSING"
```

| Check | Auto-fix |
|-------|----------|
| `graphify` binary installed | WARN — cannot auto-install; report the install command for the detected OS (`graphify-setup/SKILL.md` Step 2) |
| `jq` installed | WARN — same (Step 3) |
| `graphify.json` is valid JSON | FIX blocked — report the parse error; never rewrite user config content automatically |
| `targetPaths` non-empty | Same — report and ask the user to correct `graphify.json` |
| Each `targetPaths` entry exists on disk | WARN — list the missing paths; do not remove them from the config (may be a rename in progress) |
| Each `manifestPaths` entry exists | WARN — same |
| `stop/99-graphify-refresh.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6) |
| `stop/02-graphify-refresh.sh` exists (legacy) | `rm .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh` |
| `pre-tool-use/02-graphify-hint.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6b) |
| `graphify-out/` directory exists | WARN — run: `bash .dev-team-agents/scripts/graphify-refresh.sh` |
| `graphify-out/graph.json` present and valid JSON | FIX — re-run the refresh script; if still missing/invalid after that, report the failure instead of fabricating a graph |
| `graphify-out/GRAPH_REPORT.md` present | WARN — re-run the refresh script |
| Refresh script silently no-op'd or failed (5e) | FIX — re-run `bash .dev-team-agents/scripts/graphify-refresh.sh` and surface its stderr; this signals a bug in the script itself, not stale output |
| `.dev-team-agents/user-data/.graphify-last-run` in `.gitignore` | `echo '.dev-team-agents/user-data/.graphify-last-run' >> .gitignore` |
| `graphify-out/cache` in `.gitignore` | `echo 'graphify-out/cache' >> .gitignore` |
| `!.dev-team-agents/user-data/graphify.json` in `.gitignore` | Append automatically (see Category 7) |

## Category 6 — CLAUDE.md

```bash
grep -l "dev-team-agents" CLAUDE.md 2>/dev/null || echo "MISSING SECTION"
grep -qF "<!-- dev-team-agents: pre-compact-auto-summary -->" CLAUDE.md 2>/dev/null && echo "OK: pre-compact-rule" || echo "MISSING: pre-compact-rule"
```

| Check | Auto-fix |
|-------|----------|
| `## dev-team-agents` section present in `CLAUDE.md` | WARN — re-run setup (Step 5) to append the section |
| `<!-- dev-team-agents: pre-compact-auto-summary -->` marker present | Auto-fix: append the pre-compact auto-summary rule block (see fix-patterns.md) |

## Category 7 — .gitignore

⚠️ **CRITICAL — only add `.dev-team-agents/` entries. Never add `.claude/user-data/`, `.claude/dev-team-agents/`, or `.claude/.worktree-session`.**

```bash
# Check for new directory-pattern entries
grep -qF ".dev-team-agents/user-data/" .gitignore 2>/dev/null && echo "OK: user-data dir" || echo "MISSING: .dev-team-agents/user-data/"
grep -qF "!.dev-team-agents/user-data/graphify.json" .gitignore 2>/dev/null && echo "OK: graphify exception" || echo "MISSING: !.dev-team-agents/user-data/graphify.json"
grep -qF ".dev-team-agents/.worktree-session" .gitignore 2>/dev/null && echo "OK: worktree-session" || echo "MISSING: .dev-team-agents/.worktree-session"

# Detect legacy individual entries (outdated pattern from versions < current)
for _LEGACY in \
  ".dev-team-agents/user-data/session-summary.md" \
  ".dev-team-agents/user-data/.last-update-check" \
  ".dev-team-agents/user-data/.installed-version" \
  ".dev-team-agents/user-data/.auto-update"; do
  grep -qF "$_LEGACY" .gitignore 2>/dev/null && echo "LEGACY: $_LEGACY"
done

# Detect malformed single-line entries (missing newline separator)
for _MALFORMED in \
  "user-data/*!.claude" \
  "user-data/*!."; do
  grep -qF "$_MALFORMED" .gitignore 2>/dev/null && echo "MALFORMED: $_MALFORMED"
done

# Detect legacy .claude/ gitignore entries
for _LEGACY_CLAUDE in \
  ".claude/user-data" \
  ".claude/docs" \
  ".claude/context" \
  ".claude/tasks" \
  ".claude/dev-team-agents"; do
  grep -qF "$_LEGACY_CLAUDE" .gitignore 2>/dev/null && echo "LEGACY_CLAUDE: $_LEGACY_CLAUDE"
done
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| `.dev-team-agents/user-data/` in `.gitignore` | Required | Append automatically (never `.claude/user-data/`) |
| `!.dev-team-agents/user-data/graphify.json` in `.gitignore` | Required | Append automatically |
| `.dev-team-agents/.worktree-session` in `.gitignore` | Required | Append automatically |
| Legacy individual entries present | Outdated | **Offer migration**: replace the individual entries with the directory pattern in one rewrite (fix-patterns.md) — not a delete followed by an append |
| `.claude/user-data/` or `.claude/dev-team-agents/` in `.gitignore` | **WRONG** — replace with `.dev-team-agents/` entries immediately | `sed -i '' 's|\.claude/user-data|.dev-team-agents/user-data|g' .gitignore` |

## Category 8 — User Preferences

```bash
cat .dev-team-agents/user-data/preferences.json 2>/dev/null || echo "MISSING"
```

**Step 1 — File existence:**

| Check | Auto-fix |
|-------|----------|
| `preferences.json` exists | WARN only — re-run installer or setup-assistant to create |

**Step 2 — Schema validation (if file exists):**

Read the required key set from the canonical schema — never hardcode it here. The
hardcoded list this check used to carry went stale and missed eight fields.

```bash
python3 - <<'EOF'
import json
DEFAULTS = ".dev-team-agents/scripts/lib/preferences-defaults.json"
PREFS    = ".dev-team-agents/user-data/preferences.json"
# Opt-in fields. This preferences.json already exists, so its owner never saw
# the installer prompt for a field added later — backfill them as false.
CONSENT_KEYS = ("telemetry", "auto_update")
try:
    with open(DEFAULTS) as f:
        required = json.load(f)
    with open(PREFS) as f:
        data = json.load(f)
    missing = [k for k in required if k not in data]
    if missing:
        print("MISSING_FIELDS: " + ", ".join(sorted(missing)))
        print("CONSENT_FIELDS: " + ", ".join(k for k in CONSENT_KEYS if k in missing))
    else:
        print("OK")
except Exception as e:
    print(f"ERROR: {e}")
EOF
```

| Result | Action |
|--------|--------|
| `OK` | No action needed |
| `MISSING_FIELDS: …` | Auto-fix: inject missing fields with their value from `preferences-defaults.json`. Never overwrite an existing value. Any field also listed on `CONSENT_FIELDS` is injected as `false`, not as its schema default |
| `ERROR: …` | Ask user to re-run setup-assistant; file may be malformed |

**Never regenerate `preferences.json` wholesale.** A malformed file is reported to the user, not replaced — the fix is additive or nothing. The same applies to `credentials.local.json` (Category 10): it is created only when absent.

**Step 3 — Legacy migration:**

```bash
[ -f .dev-team-agents/user-data/.auto-update ] && echo "LEGACY_FLAG_PRESENT" || echo "OK"
```

| Result | Action |
|--------|--------|
| `LEGACY_FLAG_PRESENT` | Auto-fix: set `auto_update: true` in `preferences.json`, then `rm .dev-team-agents/user-data/.auto-update` |

## Category 9 — Notifier

```bash
[ -f .dev-team-agents/scripts/hooks/stop/04-notifier.sh ] && \
[ -x .dev-team-agents/scripts/hooks/stop/04-notifier.sh ] && \
echo "OK" || echo "FAIL"

[ -f .dev-team-agents/user-data/.session-id ] && echo "session-id: OK" || echo "session-id: MISSING (will be created on next session start)"
[ -f .dev-team-agents/user-data/.session-head ] && echo "session-head: OK" || echo "session-head: MISSING (will be created on next session start)"
[ -f .dev-team-agents/user-data/.notifier-state ] && echo "notifier-state: OK" || echo "notifier-state: MISSING (will be created on first stop hook)"
[ -f .dev-team-agents/user-data/.last-health-check ] && echo "last-health-check: OK" || echo "last-health-check: MISSING (this run will create it — see Step 4 of /devteam:health-check)"
```

| Check | Auto-fix |
|-------|----------|
| `stop/04-notifier.sh` exists and is executable | `chmod +x .dev-team-agents/scripts/hooks/stop/04-notifier.sh` |
| `.session-id` missing | OK — created automatically by `session-start.sh` on next session |
| `.session-head` missing | OK — created automatically by `session-start.sh` on next session; until then the uncommitted-progress warning stays silent (no baseline HEAD to compare against) |
| `.notifier-state` missing | OK — created automatically by `stop/04-notifier.sh` on first turn |
| `.last-health-check` missing | OK — this very health check run writes it (Step 4 of `commands/health-check.md`); nothing to fix here |

## Category 10 — Credentials

⚠️ **CRITICAL — this file contains remote environment credentials. It must NEVER be committed or shared.**

```bash
# Check file exists
[ -f .dev-team-agents/user-data/credentials.local.json ] && echo "OK" || echo "MISSING"

# Check required top-level keys exist
if [ -f .dev-team-agents/user-data/credentials.local.json ]; then
    python3 -c "
import json
with open('.dev-team-agents/user-data/credentials.local.json') as f:
    d = json.load(f)
missing = [k for k in ['devops', 'app'] if k not in d]
if missing:
    print('MISSING_KEYS: ' + ', '.join(missing))
else:
    print('KEYS_OK')
"
fi

# Check for legacy root-level file
[ -f credentials.local.json ] && echo "LEGACY_ROOT: credentials.local.json found at project root" || echo "ROOT_OK"

# Check gitignore entry
grep -qF ".dev-team-agents/user-data/credentials.local.json" .gitignore 2>/dev/null && echo "GITIGNORE: OK" || echo "GITIGNORE: MISSING"
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| `credentials.local.json` exists | Required | Create with default template if missing |
| Top-level keys (`devops`, `app`) present | Required | Add missing keys with defaults (never remove existing data) |
| No root-level `credentials.local.json` | Required (migrate) | Move to `.dev-team-agents/user-data/credentials.local.json` (see fix-patterns.md) |
| `.gitignore` entry present | Required | Append `.dev-team-agents/user-data/credentials.local.json` with a strong comment |

## Category 11 — Memory Artifacts

These files accumulate knowledge that exists nowhere else (`skills/shared/project-context/SKILL.md` § Memory Layers). Every fix here is an in-place adaptation. **Nothing in this category may create, overwrite, or delete an entry** — the check reports and patches structure, never content.

```bash
# Presence
[ -f .dev-team-agents/user-data/session-summary.md ] && echo "SESSION: OK" || echo "SESSION: MISSING"
[ -d docs/wiki ] && echo "WIKI: OK" || echo "WIKI: MISSING"
[ -d docs/development/adrs ] && echo "ADRS: OK" || echo "ADRS: MISSING"

# Wiki index format: does README.md carry a retrieval index, or only the legacy domain-count table?
if [ -f docs/wiki/README.md ]; then
  grep -q "^## Index" docs/wiki/README.md && echo "WIKI_INDEX: OK" || echo "WIKI_INDEX: LEGACY_FORMAT"
  # entries on disk vs rows in the index
  echo "WIKI_FILES: $(find docs/wiki -name '*.md' ! -name 'README.md' 2>/dev/null | wc -l | tr -d ' ')"
  echo "WIKI_ROWS: $(grep -c '^| `' docs/wiki/README.md 2>/dev/null || echo 0)"
fi
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| `session-summary.md` missing | WARN | Create empty — never regenerate one that exists |
| `docs/wiki/` missing | WARN | `mkdir -p docs/wiki` + index-format `README.md` (see `skills/shared/docs-sync/references/wiki-format.md`) |
| `WIKI_INDEX: LEGACY_FORMAT` | Outdated | **Adapt in place**: insert the `## Index` section above the existing `## Domains` table. Keep every domain row — the `Covers` text is authored content. Never rewrite the file |
| `WIKI_ROWS` < `WIKI_FILES` | Outdated | Entries exist that the index cannot retrieve. Append one row per unindexed file, reading its `Tags` and callout. Report the count fixed |
| `WIKI_ROWS` > `WIKI_FILES` | WARN only | A row points at a file that is gone. **Report the row; do not remove it** — a missing entry is a restore candidate, and the row is the only surviving record of what it held |
| ADR numbering has gaps | WARN only | Report. Never renumber: ADR ids are referenced from commits, wiki entries, and other ADRs |

### Reuse Guidelines Backfill

Existing docs often already state a mandatory-reuse rule in prose — written before `docs/development/reuse-guidelines.md` (`skills/shared/reuse-guidelines/SKILL.md`) existed, or added later by someone who didn't know the registry was the right place. Scan for candidates and offer to promote them; never populate the registry silently.

```bash
# Candidate phrases (PT + EN) — mandatory-reuse language, not just any convention
grep -niE 'sempre us[ea]|componente (canônico|padrão|central)|padrão obrigatório|always use|canonical component|mandatory component|must (always )?use' \
  docs/development/code-standards.md docs/design/design-system.md 2>/dev/null
grep -rniE 'sempre us[ea]|componente (canônico|padrão|central)|padrão obrigatório|always use|canonical component|mandatory component|must (always )?use' \
  docs/wiki/ 2>/dev/null
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| Candidate sentence found, no matching row in `reuse-guidelines.md` | Report | Propose a row (`name`/`type`/`rule`/`detection`/`canonical_ref`, per the skill's classify step) to the user before writing anything |
| User confirms the proposed row | Fix | **Adapt the source document in place**: replace the rule's sentence/paragraph with a one-line reference (`See docs/development/reuse-guidelines.md § <name>`), keeping the same heading/anchor — never delete the heading or the surrounding section. Then append the confirmed row to `reuse-guidelines.md` (create the file from `.dev-team-agents/templates/reuse-guidelines-template.md`'s header if it doesn't exist yet) |
| User declines or the match is ambiguous | WARN only | Report and leave the source document untouched |

This is the same No-Destruction discipline as the rest of this category: content moves or gets referenced, it never disappears.

## Category 12 — Python Prerequisite

```bash
command -v python3 >/dev/null 2>&1 && echo "PYTHON3: OK" || echo "PYTHON3: MISSING"
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| `python3` not found | WARN only | None — this is a host-level prerequisite, not something the health check can install. Report it and print the OS-specific install hint (see install.sh's Prerequisites check: `brew install python3` on macOS, `apt`/`dnf install python3` on Linux, python.org or `winget install Python.Python.3` on Windows) |

Only warn when `python3` is actually missing — do not repeat this hint on every run once it is present.
