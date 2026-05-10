## 2026-05-10 21:00:00 | Phases 5 & 6 — Agent refactoring and governance automation

**Done**:
- Phase 5 (Agent Refactoring): extracted 4 new skills to reduce oversized agents
  - `skills/database/db-comparison/SKILL.md` — from database-specialist (272 lines, was 309)
  - `skills/shared/setup-health-check/SKILL.md` — from setup-assistant (280 lines, was 436)
  - `skills/architecture/frontend-patterns/SKILL.md` — from frontend-developer (268 lines, was 334)
  - `skills/devops/ssh-remote-access/SKILL.md` — from devops-specialist (226 lines, was 330)
- Phase 6 (Governance): created CI workflow, agent-lint script, 2 new stop sub-scripts
  - `.github/workflows/ci.yml` — frontmatter validation, orphan scan, shellcheck, README sync check
  - `scripts/agent-lint.sh` — validates frontmatter on all agents/*.md (name, description, model, tools; model enum)
  - `scripts/hooks/stop/02-orphan-skill-scan.sh` — shim delegating to orphan-skill-scan.sh --quiet
  - `scripts/hooks/stop/03-agent-lint.sh` — shim delegating to agent-lint.sh --quiet
  - `.claude/settings.json` updated to use stop dispatcher (`scripts/hooks/stop.sh`) instead of direct orphan scan
  - `orphan-skill-scan.sh` Phase 3 added: duplicate skill detection (excludes table rows to avoid false positives)
  - Fixed 23 real duplicate skill references across 6 agents (devops redundant table, reviewer body text refs, database inline refs)
- README.md + README.pt-BR.md synced: new workflows (refactor, review) and stop hook description updated

**Decisions**:
- Phase 3 duplicate detection skips lines starting with `|` (table rows) — detection tables legitimately point multiple signals to same skill
- `devops-specialist.md` Skill Loading Reference table removed (redundant with Integration Awareness auto-detection table)
- setup-assistant secondary mentions of docs-sync/setup-scan changed to prose to avoid false-positive duplicate warnings

**Next**:
- All 6 phases from the audit improvement plan are now complete
- Consider a patch version bump (v → v+0.0.1) for this batch of improvements
- Optional: further trim agents still above 200 lines (setup-assistant 280, database-specialist 272, frontend-developer 268)

---

## 2026-05-10 18:19:38 | Plano de 13 melhorias ao dev-team-agents

**Done**:
- Created 5 new skills: `multipart-upload`, `single-action-controller`, `supply-chain`, `idor`, `iso27001-sgsi`
- Added full mobile design section to `ui-ux-designer` (breakpoints, navigation, typography, spacing, touch rules, mobile-first convention)
- Added SSH Remote Access Helper section to `devops-specialist` (auto-detect remote server context, generate key, configure ~/.ssh/config, document in project CLAUDE.md)
- Added Contradiction Guard to `project-context` skill (all agents now flag conflicts with CLAUDE.md, ADRs, architecture docs, sprint scope)
- Added Wiki section to `docs-sync` skill (.claude/docs/wiki/ with dynamic domain folders and README.md index)
- Updated `backlog-template`: one file per sprint + Agent Assignment table for auto-suggesting agents per task type
- Updated `install.sh`: replaced 4 individual gitignore entries with `.claude/user-data/` + `!.claude/user-data/graphify.json` + `.claude/.worktree-session`
- Updated `setup-assistant`: FIRST_RUN creates wiki/README.md; health check Category 7 detects legacy gitignore entries and offers migration
- Rewrote `commands/update.md`: strict anti-commentary instructions, clean terse output format, health check suggestion after update
- Updated `CLAUDE.md`, `README.md`, `README.pt-BR.md` to reflect all observable behavior changes
- Orphan skill scan: clean (all new skills referenced by agents)

**Decisions**:
- Wiki domains are project-driven (dynamic), not predefined — agents create folders based on actual domain context
- Single Action Controller is MANDATORY (not optional) for all backend controllers
- ISO 27001 + SGSI + CIA Triad grouped into one skill (they are intrinsically linked)
- Contradiction Guard sources: CLAUDE.md + ADRs + architecture.md + code-standards.md + sprint files
- GitIgnore migrates automatically (health check offers migration; install.sh removes legacy entries on next run)

**Next**: Version bump and release prep when ready (new agents/skills = minor version bump).

---

