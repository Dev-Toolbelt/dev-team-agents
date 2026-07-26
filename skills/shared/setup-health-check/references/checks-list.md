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
> dev-team is invisible to Claude Code even though git-bash "sees" the links.
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
| Legacy `.claude/` dirs exist (user-data, docs, context, tasks, dev-team-agents) | **Migrate immediately**: move contents to new locations (see fix-patterns.md Legacy directory migration), then remove old dirs. Do NOT skip this step. |

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

Check `.codex/hooks.json` — the 4 managed hook entries (SessionStart, PreToolUse, Stop, PreCompact) are present and point to valid script paths; check `prompts/` dir for `devteam-*.md` files.

## Category 5 — Graphify (skip if not enabled)

Detect: `[ -f .dev-team-agents/user-data/graphify.json ] && echo ENABLED || echo DISABLED`

If ENABLED:

```bash
ls .dev-team-agents/scripts/hooks/stop/99-graphify-refresh.sh 2>/dev/null || echo "MISSING"
ls .dev-team-agents/scripts/hooks/pre-tool-use/02-graphify-hint.sh 2>/dev/null || echo "MISSING"
ls graphify-out/ 2>/dev/null | head -3 || echo "MISSING"
grep -qxF '.dev-team-agents/user-data/.graphify-last-run' .gitignore 2>/dev/null && echo "OK" || echo "MISSING"
# Also check for legacy sub-script that causes stop-hook loops
ls .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh 2>/dev/null && echo "LEGACY_FOUND"
```

| Check | Auto-fix |
|-------|----------|
| `stop/99-graphify-refresh.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6) |
| `stop/02-graphify-refresh.sh` exists (legacy) | `rm .dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh` |
| `pre-tool-use/02-graphify-hint.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6b) |
| `graphify-out/` directory exists | WARN — run: `bash .dev-team-agents/scripts/graphify-refresh.sh` |
| `.dev-team-agents/user-data/.graphify-last-run` in `.gitignore` | `echo '.dev-team-agents/user-data/.graphify-last-run' >> .gitignore` |

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
| Legacy individual entries present | Outdated | **Offer migration**: remove individual entries and add directory pattern |
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

```bash
python3 - <<'EOF'
import json, sys
required = {
    "language": "en",
    "context_window_percent_warning": 55,
    "context_window_percent_limit": 60,
    "suppress_notifications": False,
    "session_summary_max_days": 30,
    "session_summary_max_entries": 30,
    "docs_stale_after_days": 30,
    "auto_update": False,
    "update_check_interval_hours": 24,
}
try:
    with open(".dev-team-agents/user-data/preferences.json") as f:
        data = json.load(f)
    missing = {k: v for k, v in required.items() if k not in data}
    if missing:
        print("MISSING_FIELDS: " + ", ".join(missing.keys()))
    else:
        print("OK")
except Exception as e:
    print(f"ERROR: {e}")
EOF
```

| Result | Action |
|--------|--------|
| `OK` | No action needed |
| `MISSING_FIELDS: …` | Auto-fix: inject missing fields with defaults (do not overwrite existing values) |
| `ERROR: …` | Ask user to re-run setup-assistant; file may be malformed |

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
[ -f .dev-team-agents/user-data/.notifier-state ] && echo "notifier-state: OK" || echo "notifier-state: MISSING (will be created on first stop hook)"
```

| Check | Auto-fix |
|-------|----------|
| `stop/04-notifier.sh` exists and is executable | `chmod +x .dev-team-agents/scripts/hooks/stop/04-notifier.sh` |
| `.session-id` missing | OK — created automatically by `session-start.sh` on next session |
| `.notifier-state` missing | OK — created automatically by `stop/04-notifier.sh` on first turn |

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

# Check gitignore entry
grep -qF ".dev-team-agents/user-data/credentials.local.json" .gitignore 2>/dev/null && echo "GITIGNORE: OK" || echo "GITIGNORE: MISSING"
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| `credentials.local.json` exists | Required | Create with default template if missing |
| Top-level keys (`devops`, `app`) present | Required | Add missing keys with defaults (never remove existing data) |
| `.gitignore` entry present | Required | Append `.dev-team-agents/user-data/credentials.local.json` with a strong comment |
