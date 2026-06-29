# Health Check Categories and Commands

## Category 1 — Symlinks

```bash
ls -la .claude/agents/dev-team 2>/dev/null || echo "MISSING"
ls -la .claude/commands/devteam 2>/dev/null || echo "MISSING"
ls .claude/skills/ 2>/dev/null | head -5 || echo "MISSING"
```

| Check | Expected | Auto-fix |
|-------|----------|----------|
| `.claude/agents/dev-team` symlink exists | → `../dev-team-agents/agents` | `ln -s ../dev-team-agents/agents .claude/agents/dev-team` |
| `.claude/commands/devteam` symlink exists | → `../dev-team-agents/commands` | `ln -s ../dev-team-agents/commands .claude/commands/devteam` |
| `.claude/skills/` has at least one symlink | Any skill dir linked | Re-run skill linking loop from `install.sh` |

## Category 2 — Scripts & Executability

```bash
for f in \
  .claude/dev-team-agents/scripts/hooks/pre-tool-use.sh \
  .claude/dev-team-agents/scripts/hooks/stop.sh \
  .claude/dev-team-agents/scripts/hooks/session-start.sh \
  .claude/dev-team-agents/scripts/hooks/pre-tool-use/01-check-updates.sh \
  .claude/dev-team-agents/scripts/hooks/stop/01-session-summary.sh \
  .claude/dev-team-agents/scripts/hooks/stop/04-notifier.sh \
  .claude/dev-team-agents/scripts/update.sh; do
  [ -f "$f" ] && [ -x "$f" ] && echo "OK: $f" || echo "FAIL: $f"
done
```

| Check | Auto-fix |
|-------|----------|
| All dispatcher and sub-scripts exist | Re-run `chmod +x` |
| All scripts are executable | `chmod +x <script>` |

## Category 3 — User Data

```bash
ls -la .claude/user-data/ 2>/dev/null || echo "MISSING"
cat .claude/user-data/.installed-version 2>/dev/null || echo "MISSING"
```

| Check | Auto-fix |
|-------|----------|
| `.claude/user-data/` directory exists | `mkdir -p .claude/user-data/` |
| `.installed-version` exists | WARN only — re-run installer to populate |

## Category 4 — settings.json

```bash
cat .claude/settings.json 2>/dev/null || echo "MISSING"
```

Verify the following and flag any deviation as FIX (show diff, ask confirmation before applying):

| Check | Expected value | Fix action |
|-------|---------------|------------|
| `hooks.PreToolUse` has exactly one dev-team entry | command = `…/scripts/hooks/pre-tool-use.sh`, matcher `.*` | Replace old entries (e.g. `update.sh --check`, inline graphify command) with dispatcher |
| `hooks.Stop` has exactly one dev-team entry | command = `…/scripts/hooks/stop.sh` | Replace old entries (e.g. `session-summary-hook.sh`, `graphify-refresh.sh`) with dispatcher |
| No stale direct hook paths remain | No `update.sh --check`, `session-summary-hook.sh`, or `graphify-refresh.sh` as direct hook commands | Consolidate into dispatchers |
| `includeCoAuthoredBy` is `false` | `"includeCoAuthoredBy": false` | Auto-fix: inject via python3 (see fix-patterns.md) |

## Category 5 — Graphify (skip if not enabled)

Detect: `[ -f .claude/user-data/graphify.json ] && echo ENABLED || echo DISABLED`

If ENABLED:

```bash
ls .claude/dev-team-agents/scripts/hooks/stop/99-graphify-refresh.sh 2>/dev/null || echo "MISSING"
ls .claude/dev-team-agents/scripts/hooks/pre-tool-use/02-graphify-hint.sh 2>/dev/null || echo "MISSING"
ls graphify-out/ 2>/dev/null | head -3 || echo "MISSING"
grep -qxF '.claude/user-data/.graphify-last-run' .gitignore 2>/dev/null && echo "OK" || echo "MISSING"
# Also check for legacy sub-script that causes stop-hook loops
ls .claude/dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh 2>/dev/null && echo "LEGACY_FOUND"
```

| Check | Auto-fix |
|-------|----------|
| `stop/99-graphify-refresh.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6) |
| `stop/02-graphify-refresh.sh` exists (legacy) | `rm .claude/dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh` |
| `pre-tool-use/02-graphify-hint.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6b) |
| `graphify-out/` directory exists | WARN — run: `bash .claude/dev-team-agents/scripts/graphify-refresh.sh` |
| `.claude/user-data/.graphify-last-run` in `.gitignore` | `echo '.claude/user-data/.graphify-last-run' >> .gitignore` |

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

```bash
# Check for new directory-pattern entries
grep -qF ".claude/user-data/" .gitignore 2>/dev/null && echo "OK: user-data dir" || echo "MISSING: .claude/user-data/"
grep -qF "!.claude/user-data/graphify.json" .gitignore 2>/dev/null && echo "OK: graphify exception" || echo "MISSING: !.claude/user-data/graphify.json"
grep -qF ".claude/.worktree-session" .gitignore 2>/dev/null && echo "OK: worktree-session" || echo "MISSING: .claude/.worktree-session"

# Detect legacy individual entries (outdated pattern from versions < current)
for _LEGACY in \
  ".claude/user-data/session-summary.md" \
  ".claude/user-data/.last-update-check" \
  ".claude/user-data/.installed-version" \
  ".claude/user-data/.auto-update"; do
  grep -qF "$_LEGACY" .gitignore 2>/dev/null && echo "LEGACY: $_LEGACY"
done
```

| Check | Status | Auto-fix |
|-------|--------|----------|
| `.claude/user-data/` in `.gitignore` | Required | Append automatically |
| `!.claude/user-data/graphify.json` in `.gitignore` | Required | Append automatically |
| `.claude/.worktree-session` in `.gitignore` | Required | Append automatically |
| Legacy individual entries present | Outdated | **Offer migration**: remove individual entries and add directory pattern |

## Category 8 — User Preferences

```bash
cat .claude/user-data/preferences.json 2>/dev/null || echo "MISSING"
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
    with open(".claude/user-data/preferences.json") as f:
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
[ -f .claude/user-data/.auto-update ] && echo "LEGACY_FLAG_PRESENT" || echo "OK"
```

| Result | Action |
|--------|--------|
| `LEGACY_FLAG_PRESENT` | Auto-fix: set `auto_update: true` in `preferences.json`, then `rm .claude/user-data/.auto-update` |

## Category 9 — Notifier

```bash
[ -f .claude/dev-team-agents/scripts/hooks/stop/04-notifier.sh ] && \
[ -x .claude/dev-team-agents/scripts/hooks/stop/04-notifier.sh ] && \
echo "OK" || echo "FAIL"

[ -f .claude/user-data/.session-id ] && echo "session-id: OK" || echo "session-id: MISSING (will be created on next session start)"
[ -f .claude/user-data/.notifier-state ] && echo "notifier-state: OK" || echo "notifier-state: MISSING (will be created on first stop hook)"
```

| Check | Auto-fix |
|-------|----------|
| `stop/04-notifier.sh` exists and is executable | `chmod +x .claude/dev-team-agents/scripts/hooks/stop/04-notifier.sh` |
| `.session-id` missing | OK — created automatically by `session-start.sh` on next session |
| `.notifier-state` missing | OK — created automatically by `stop/04-notifier.sh` on first turn |
