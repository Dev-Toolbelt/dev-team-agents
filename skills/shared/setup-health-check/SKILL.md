---
name: setup-health-check
description: Setup health check — categories, commands, auto-fix actions.
---

# Setup Health Check

Run a structured audit of the dev-team-agents installation in a project. Checks 9 categories in order, applies safe fixes automatically, and asks for confirmation before modifying `settings.json` or migrating `.gitignore`.

## When to Run

- On first install (after `install.sh`)
- When an agent or hook behaves unexpectedly
- After a manual update or migration
- When the user asks for a health check

## Flow

1. Load `references/checks-list.md` — run each category's detection commands
2. Collect results: ✅ OK / ⚠️ WARN / 🔧 FIX per category
3. Display the summary using the format in `references/audit-format.md`
4. Apply auto-fixes from `references/fix-patterns.md`:
   - WARN items: apply silently
   - FIX items that touch `settings.json`: show diff, ask confirmation
   - FIX items that touch `.gitignore` (legacy migration): ask confirmation
   - All other FIX items: apply without asking

## Categories (checked in order)

| # | Category | Key check |
|---|----------|-----------|
| 1 | Symlinks | `.claude/agents/dev-team`, `.claude/commands/devteam` |
| 2 | Scripts & Executability | All hook dispatchers and sub-scripts are executable |
| 3 | User Data | `.claude/user-data/` directory and `.installed-version` |
| 4 | settings.json | Hook dispatcher entries, `includeCoAuthoredBy: false` |
| 5 | Graphify | Skip if not enabled; check sub-scripts and output dir |
| 6 | CLAUDE.md | `## dev-team-agents` section present |
| 7 | .gitignore | Directory-pattern entries, legacy per-file migration |
| 8 | User Preferences | `preferences.json` exists, schema complete |
| 9 | Notifier | `04-notifier.sh` executable, state files present |

## Load on Demand

| When | Load |
|------|------|
| Running checks | `references/checks-list.md` |
| Applying auto-fixes | `references/fix-patterns.md` |
| Formatting output | `references/audit-format.md` |
