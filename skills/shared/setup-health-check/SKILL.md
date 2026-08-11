---
name: setup-health-check
description: Setup health check — categories, commands, auto-fix actions.
---

# Setup Health Check

Run a structured audit of the dev-team-agents installation in a project. Checks 13 categories in order, applies safe fixes automatically, and asks for confirmation before modifying `settings.json` or migrating `.gitignore`. It never deletes — see the No-Destruction Rule below.

## When to Run

- On first install (after `install.sh`)
- When an agent or hook behaves unexpectedly
- After a manual update or migration
- When the user asks for a health check

## Flow

1. Load `references/checks-list.md` — run each category's detection commands
2. Collect results: ✅ OK / ⚠️ WARN / 🔧 FIX per category
3. Display the summary using the format in `references/audit-format.md`
4. Apply auto-fixes from `references/fix-patterns.md`, under the No-Destruction Rule below:
   - WARN items: apply silently
   - FIX items that touch `settings.json`: show diff, ask confirmation
   - FIX items that touch `.gitignore` (legacy migration): ask confirmation
   - All other FIX items: apply without asking
5. Write today's date (`YYYY-MM-DD`) to `.dev-team-agents/user-data/.last-health-check`, creating the file if absent. `session-start.sh` reads this marker to warn when a project has gone `docs_stale_after_days` (default `30`) without a health check — see `CLAUDE-md/notifications.md`. This step runs even when all categories pass.

## No-Destruction Rule

**This is the canonical statement. `references/checks-list.md` and `references/fix-patterns.md` delegate to it; neither restates it.**

> A health check never deletes. Every fix creates, moves, or adapts in place.

The health check runs unattended, on an installation it has just decided is broken — which is exactly the state in which its assumptions about what a file contains are least reliable. A wrong fix that moved something is recoverable; a wrong fix that deleted it is not.

| Situation | Permitted action | Never |
|-----------|-----------------|-------|
| Path moved between versions | `mv` to the new path (merge if the target exists) | `rm` the source "after" migrating |
| File in a superseded format | Adapt in place — add the new structure, keep existing content | Regenerate the file over the old one |
| Config line replaced | Rewrite the line to its current form | Delete and re-add as two steps |
| Content is unrecognized, orphaned, or ambiguous | `mv` to quarantine (below) | Delete as cleanup |
| Directory left over and **empty** | `rmdir` without `-r` | `rm -rf` |
| `<name>.pre-migration.bak` from `state_migrate_legacy`, confirmed | `rm` — only after Category 3 confirms the mapped key already holds a value in `state.json` | Delete before confirming, or on a mere assumption the migration ran |

`rmdir` without `-r` and the confirmed-`.bak` `rm` are the only two removals in the skill. `rmdir` is permitted because it fails by construction on a non-empty directory. The `.bak` deletion is permitted because the value it would destroy was already durably copied into `state.json` by the same operation that created it — verified again, independently, by Category 3 before any `rm` runs. Everything else stays a move, never a delete, because the check cannot make that same guarantee about content it did not itself just write.

### Quarantine

Anything that would otherwise be removed goes to a dated directory instead:

```bash
QUARANTINE=".dev-team-agents/user-data/legacy/$(date +%Y-%m-%d)"
mkdir -p "$QUARANTINE"
mv <path> "$QUARANTINE/"
```

Report every quarantined path in the audit output. Nothing empties this directory — not the health check, not the updater. It is gitignored with the rest of `user-data/`, and the cost of it accumulating is orders of magnitude below the cost of one wrongly deleted `user-data/`.

### Memory artifacts — adapt, never regenerate

`session-summary.md`, `docs/wiki/`, `docs/development/adrs/` and `docs/project.md` accumulate knowledge that exists nowhere else (see `skills/shared/project-context/SKILL.md` § Memory Layers). For these, "outdated format" is never grounds for a rewrite: patch the file to the current format and keep every line of content that is already there.

## Categories (checked in order)

| # | Category | Key check |
|---|----------|-----------|
| 1 | Symlinks | `.claude/agents/dev-team`, `.claude/commands/devteam` — test with `-L`, not `ls`; catch Windows materialized-file state |
| 2 | Scripts & Executability | All hook dispatchers and sub-scripts are executable |
| 3 | User Data | `.dev-team-agents/user-data/` directory and `.installed-version` |
| 4 | settings.json | Hook dispatcher entries, `includeCoAuthoredBy: false` |
| 5 | Graphify | Skip if not enabled; validate config/paths, hook wiring, output integrity, and that a real refresh run actually rebuilds the output (not just that files exist) |
| 6 | CLAUDE.md | `## dev-team-agents` section present |
| 7 | .gitignore | Directory-pattern entries, legacy per-file migration |
| 8 | User Preferences | `preferences.json` exists, schema complete |
| 9 | Notifier | Disabled by design (`_disabled-04-notifier.sh`) — do not report as missing; check state files only |
| 10 | Credentials | `credentials.local.json` at correct path, no legacy root file, required top-level keys, gitignored |
| 11 | Memory Artifacts | `session-summary.md`, `docs/wiki/` index format and coverage, ADRs — adapted in place, never regenerated; detection-only check for undocumented conventions, pointing to `/devteam:sync-rules` |
| 12 | Python Prerequisite | `python3` on PATH — WARN only, with OS-specific install hint; not auto-installable |
| 13 | Productivity & Token-Efficiency Tools | `rg`, `fd`, `jq`, `ast-grep`, `tokei`, `delta` on PATH — WARN only, with OS-specific install hint per tool; not auto-installable |

## Load on Demand

| When | Load |
|------|------|
| Running checks | `references/checks-list.md` |
| Applying auto-fixes | `references/fix-patterns.md` |
| Formatting output | `references/audit-format.md` |
