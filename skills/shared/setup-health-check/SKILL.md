---
name: setup-health-check
description: Health check categories, bash commands, expected values, auto-fix actions, and output format for the setup-assistant health check role.
---

### Category 1 — Symlinks

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

---

### Category 2 — Scripts & Executability

```bash
for f in \
  .claude/dev-team-agents/scripts/hooks/pre-tool-use.sh \
  .claude/dev-team-agents/scripts/hooks/stop.sh \
  .claude/dev-team-agents/scripts/hooks/pre-tool-use/01-check-updates.sh \
  .claude/dev-team-agents/scripts/hooks/stop/01-session-summary.sh \
  .claude/dev-team-agents/scripts/update.sh; do
  [ -f "$f" ] && [ -x "$f" ] && echo "OK: $f" || echo "FAIL: $f"
done
```

| Check | Auto-fix |
|-------|----------|
| All dispatcher and sub-scripts exist | Re-run `chmod +x` |
| All scripts are executable | `chmod +x <script>` |

---

### Category 3 — User Data

```bash
ls -la .claude/user-data/ 2>/dev/null || echo "MISSING"
cat .claude/user-data/.installed-version 2>/dev/null || echo "MISSING"
```

| Check | Auto-fix |
|-------|----------|
| `.claude/user-data/` directory exists | `mkdir -p .claude/user-data/` |
| `.installed-version` exists | WARN only — re-run installer to populate |

---

### Category 4 — settings.json

```bash
cat .claude/settings.json 2>/dev/null || echo "MISSING"
```

Verify the following and flag any deviation as FIX (show diff, ask confirmation before applying):

| Check | Expected value | Fix action |
|-------|---------------|------------|
| `hooks.PreToolUse` has exactly one dev-team entry | command = `…/scripts/hooks/pre-tool-use.sh`, matcher `.*` | Replace old entries (e.g. `update.sh --check`, inline graphify command) with dispatcher |
| `hooks.Stop` has exactly one dev-team entry | command = `…/scripts/hooks/stop.sh` | Replace old entries (e.g. `session-summary-hook.sh`, `graphify-refresh.sh`) with dispatcher |
| No stale direct hook paths remain | No `update.sh --check`, `session-summary-hook.sh`, or `graphify-refresh.sh` as direct hook commands | Consolidate into dispatchers |

---

### Category 5 — Graphify (skip if not enabled)

Detect: `[ -f .claude/user-data/graphify.json ] && echo ENABLED || echo DISABLED`

If ENABLED:

```bash
ls .claude/dev-team-agents/scripts/hooks/stop/02-graphify-refresh.sh 2>/dev/null || echo "MISSING"
ls .claude/dev-team-agents/scripts/hooks/pre-tool-use/02-graphify-hint.sh 2>/dev/null || echo "MISSING"
ls graphify-out/ 2>/dev/null | head -3 || echo "MISSING"
grep -qxF '.claude/user-data/.graphify-last-run' .gitignore 2>/dev/null && echo "OK" || echo "MISSING"
```

| Check | Auto-fix |
|-------|----------|
| `stop/02-graphify-refresh.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6) |
| `pre-tool-use/02-graphify-hint.sh` exists and is executable | Create it (content from `graphify-setup/SKILL.md` Step 6b) |
| `graphify-out/` directory exists | WARN — run: `bash .claude/dev-team-agents/scripts/graphify-refresh.sh` |
| `.claude/user-data/.graphify-last-run` in `.gitignore` | `echo '.claude/user-data/.graphify-last-run' >> .gitignore` |

---

### Category 6 — CLAUDE.md

```bash
grep -l "dev-team-agents" CLAUDE.md 2>/dev/null || echo "MISSING SECTION"
```

| Check | Auto-fix |
|-------|----------|
| `## dev-team-agents` section present in `CLAUDE.md` | WARN — re-run setup (Step 5) to append the section |

---

### Category 7 — .gitignore

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

**Migration offer** — if legacy entries are detected, present:

> ⚠️ Your `.gitignore` uses the old per-file pattern for `user-data/`. The current version uses a directory-level ignore (`.claude/user-data/`) with a `graphify.json` exception. Migrate automatically? (yes/no)

On confirmation: remove the 4 legacy lines, add the 3 new entries.

---

### Health Check Output Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HEALTH CHECK — dev-team-agents
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Symlinks ................ ✅ OK
 Scripts ................. 🔧 FIX  (hooks/stop.sh not executable)
 User Data ............... ✅ OK
 settings.json ........... 🔧 FIX  (stale direct hooks found — see diff below)
 Graphify ................ ✅ OK
 CLAUDE.md ............... ✅ OK
 .gitignore .............. ⚠️ WARN  (1 entry missing)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 2 items need attention. Proposed changes:
  🔧 chmod +x .claude/dev-team-agents/scripts/hooks/stop.sh
  🔧 settings.json — replace stale hooks with dispatcher [diff shown]
  ⚠️ .gitignore — add missing entry (auto-applying)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Show the diff for any `settings.json` changes, then ask: **"Apply fixes to settings.json? (yes/no)"**. Apply all other auto-fixes without asking.
