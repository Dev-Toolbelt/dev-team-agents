# Health Check Output Format

## Output Template

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
 User Preferences ........ 🔧 FIX  (2 fields missing from preferences.json)
 Notifier ................ ✅ OK

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 2 items need attention. Proposed changes:
  🔧 chmod +x .dev-team-agents/scripts/hooks/stop.sh
  🔧 settings.json — replace stale hooks with dispatcher [diff shown]
  ⚠️ .gitignore — add missing entry (auto-applying)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Status Icons

| Icon | Meaning |
|------|---------|
| ✅ OK | Check passed — no action needed |
| ⚠️ WARN | Non-critical issue — auto-applying fix |
| 🔧 FIX | Action required — show diff and confirm before applying |

## Confirmation Protocol

- Show the diff for any `settings.json` changes, then ask: **"Apply fixes to settings.json? (yes/no)"**
- Apply all other auto-fixes without asking
- For `.gitignore` migration (legacy per-file entries), offer migration and wait for confirmation
