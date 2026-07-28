# dev-team-agents — v1 → v2 Migration Notes

Runbook + gotchas catalogued while migrating this repo from dev-team-agents **v1.8.2 → v2.15.0** (2026-07-28). Read this before running `/devteam:update` on any other repo still on v1.

## What changed (layout v1 → v2)

| Item | v1 (old) | v2 (current) |
|---|---|---|
| Source tree | `.claude/dev-team-agents/` | `.dev-team-agents/` (project root) |
| Project docs | `.claude/docs/` | `docs/` |
| User data | `.claude/user-data/` | `.dev-team-agents/user-data/` |
| Agents | `.claude/agents/dev-team → ../dev-team-agents/agents` | symlink → `../../.dev-team-agents/agents` |
| Commands | `.claude/commands/devteam → ../dev-team-agents/commands` | symlink → `../../.dev-team-agents/commands` |
| Skills | `.claude/skills/* → ../dev-team-agents/...` | symlink → `../../.dev-team-agents/...` |
| Hooks (`settings.json`) | `.claude/dev-team-agents/scripts/hooks/*.sh` | `.dev-team-agents/scripts/hooks/*.sh` |
| Commands invocation | keyword auto-routing | explicit `/devteam:<name>` |

After migration, `.claude/` holds only: `agents/dev-team`, `commands/devteam`, `skills/*` symlinks, `settings.json`, `settings.local.json`.

## Gotchas detected (relevant instructions)

1. **Installer bug — missing `mkdir -p`.** The v2 installer writes `.dev-team-agents/user-data/credentials.local.json` without creating `user-data/` first, so it aborts on a fresh v2 dir. **Fix:** pre-create `.dev-team-agents/user-data/` (migrating the old `.claude/user-data/` into it), then re-run the installer.

2. **Split-brain after update.** The installer drops v2 files but logs *"already linked / already present (skipped)"* and does **not** repoint existing v1 symlinks or hooks. Result: the project keeps running v1 while an unused v2 tree sits beside it. A real migration must **manually repoint ~130 symlinks + the 4 hook paths**.

3. **`credentials.local.json` collision — do NOT delete the root file.** The installer warns the root `credentials.local.json` "will be ignored" and suggests `rm`-ing it. That file is **this project's secrets** (see `CLAUDE.md`) and is unrelated to the dev-team-agents devops template at `.dev-team-agents/user-data/credentials.local.json`. **Never delete the root file.**

4. **Cross-repo doc refs must be preserved.** When moving `.claude/docs/ → docs/`, do **not** rewrite references to `../home-insurance/.claude/docs/` — the `home-insurance` repo is still on v1.

5. **Stale cross-references.** Moving docs breaks internal links in `CLAUDE.md`, `README.md`, several `docs/**` files, `.claude/commands/qa-test-jira-task.md`, and a couple of source-code comments. Sweep `.claude/docs/ → docs/` and `.claude/dev-team-agents/ → .dev-team-agents/` across tracked files (skip `node_modules`, `session-summary.md`, and the home-insurance ref above).

6. **Legacy project-owned hooks become dead code.** `.claude/hooks/{pre-tool-use,stop}/*.sh` (marked *"project-owned so updates cannot delete it"*) were a v1 workaround for when graphify hooks weren't shipped. v2 ships native equivalents (`02-graphify-hint.sh`, `99-graphify-refresh.sh`), the v2 dispatcher never invokes `.claude/hooks/`, and their path pointed at the now-deleted v1 tree. Safe to `git rm`.

7. **`.gitignore` carries stale v1 entries.** Remove `.claude/worktrees`, `.claude/user-data/*`, `!.claude/user-data/graphify.json`, `.claude/user-data/.graphify-last-run`, `.claude/.worktree-session` (the installer already adds the `.dev-team-agents/…` equivalents). Keep the root `credentials.local.json` ignore line.

8. **`settings.local.json` is personal/untracked.** It may keep stale v1 paths in the Bash `permissions.allow` list — harmless dead pre-approvals, not shared with the team. Leave it.

## Official tooling (shipped in v2)

`.dev-team-agents/scripts/` includes helpers that automate most of the above (this repo was migrated manually, but prefer these next time):

- `migrate-to-root.sh` — moves v1 `.claude/dev-team-agents/` layout to the v2 root layout.
- `fix-symlinks.sh` — repoints/repairs the agent/command/skill symlinks.
- `rollback.sh` — reverts to the previous install.

Commands `/devteam:health-check`, `/devteam:symlinks`, and `/devteam:update` are also available.

## Post-migration verification checklist

```bash
cat .dev-team-agents/user-data/.installed-version           # v2.x.y
python3 -c "import json;json.load(open('.claude/settings.json'))"   # valid JSON
grep -o '\.dev-team-agents/scripts/hooks/[a-z-]*\.sh' .claude/settings.json | sort -u   # 4 hooks → v2
# symlinks resolve (0 broken):
for l in .claude/agents/dev-team .claude/commands/devteam .claude/skills/*; do [ -L "$l" ] && [ ! -e "$l" ] && echo "BROKEN $l"; done
# hooks run clean:
echo '{}' | bash .dev-team-agents/scripts/hooks/session-start.sh; echo "exit $?"
```

> After migrating, **start a new Claude Code session** to load the v2 agents/skills. The diff (tree move + docs move) lands on every teammate's checkout on merge.
