# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `SECURITY.md` — vulnerability disclosure policy for `curl | bash` installer
- `CHANGELOG.md` — this file; human-readable release history
- `CONTRIBUTING.md` — human-oriented contribution guide
- `.github/PULL_REQUEST_TEMPLATE.md` and `ISSUE_TEMPLATE/` — structured contribution templates
- `.github/CODEOWNERS` — path-based ownership declaration
- `workflows/fullstack.md` — full-stack workflow aligned with `/devteam:fullstack`
- `skills/architecture/event-driven/SKILL.md` — CQRS, saga, event sourcing, idempotency
- `skills/architecture/rate-limiting/SKILL.md` — token bucket, sliding window, headers, failure modes
- `skills/architecture/performance-budgets/SKILL.md` — Core Web Vitals, bundle size, Lighthouse CI
- `skills/architecture/api-versioning/SKILL.md` — URL/header/content-negotiation strategies, deprecation lifecycle
- `skills/shared/diataxis-framework/SKILL.md` — extracted from `technical-writer` agent
- `skills/database/postgres/SKILL.md`, `mysql/SKILL.md`, `mongodb/SKILL.md` — per-engine reference skills
- `SessionStart` hook — warns when `project.md` or `session-summary.md` is stale
- `scripts/hooks/stop/04-notifier.sh` — context-window warnings (⚠️/🚨) and a rotating tip-of-session using the DEV TEAM AGENTS notification format; suppression controlled via `preferences.json`

### Changed
- All 21 `/devteam:*` commands now load `skills/shared/current-context/SKILL.md` instead of inlining the git block (~150 lines removed)
- `commands/plan.md` delegates conditional spawn decisions to `skills/shared/spawn-classifier/SKILL.md`
- Reviewer agents (`code-reviewer`, `backend-reviewer`, `frontend-reviewer`) reference `reviewer-mindset` skill instead of duplicating the inline block
- `token-efficiency` apply line standardised to one canonical form across 10 agents
- Stop hooks `02-orphan-skill-scan.sh` and `03-agent-lint.sh` now gate by `agents/`/`skills/` changes
- `/devteam:commit` runs a pre-commit lint gate before committing
- All 7 workflows have a Recovery Paths section
- `/devteam:pr` detects and fills `.github/PULL_REQUEST_TEMPLATE.md` when present
- `01-check-updates.sh` uses `If-None-Match` / ETag to avoid redundant GitHub API calls
- CI shellcheck step uses pre-installed binary instead of `apt-get install`

---

## [1.4.0] — 2026-05-10

### Added
- MIT `LICENSE` file
- `.github/workflows/ci.yml` — frontmatter validation, orphan scan, shellcheck, README sync check
- `scripts/agent-lint.sh` — validates frontmatter on all `agents/*.md`
- Stop hook sub-scripts: `02-orphan-skill-scan.sh`, `03-agent-lint.sh`
- Orphan skill scan Phase 3: duplicate skill detection

### Changed
- `.claude/settings.json` uses the stop dispatcher (`scripts/hooks/stop.sh`) instead of direct orphan scan
- Fixed 23 real duplicate skill references across 6 agents

---

## [1.3.16] — 2026-05

### Added
- `/devteam:update` command for checking and applying updates
- 13 new skills across security, testing, database, devops, and integrations
- 7 new architecture skills; updated `api-design`
- 7 new shared skills; refactored `comments-policy` (417 → 76 lines)
- `workflows/refactor.md` and `workflows/review.md`
- Jira integration section in 7 agents; `skills/integrations/jira/SKILL.md`

### Changed
- Refactored 4 agents by extracting skills: `db-comparison`, `setup-health-check`, `frontend-patterns`, `ssh-remote-access`
- `/devteam:*` commands namespaced (were `/devteam-*`)
- `session-summary.md` moved to `user-data/` directory

---

## [1.3.0] — 2026-05

### Added
- Comprehensive `/devteam:*` slash commands (plan, backend, frontend, fullstack, fix, refactor, architect, review, qa, security, dba, devops, tester, docs, pr, design, commit, update)
- Graphify integration for visual codebase navigation
- Wiki knowledge base system (`.claude/docs/wiki/`)
- Contradiction Guard in `project-context` skill

### Changed
- Agents enforce human-only authorship in git artifacts (no Claude attribution)
- `setup-assistant` adds audit step, devops/tests doc dirs

---

## [1.2.0] — 2026-04

### Added
- `skills/shared/` modular skill system
- `agent-creator` and `skill-creator` skills
- Release preparation skill (`release-prep`)
- `session-summary.md` per-session notes (multi-agent append pattern)

### Changed
- Skills extracted from agents to reduce inline duplication
- Auto-routing skill for agent delegation

---

## [1.1.0] — 2026-04

### Added
- Core agent roster: `backend-developer`, `frontend-developer`, `database-specialist`, `devops-specialist`, `qa-specialist`, `security-specialist`, `software-architect`, `product-analyst`, `technical-writer`, `code-reviewer`, `setup-assistant`
- Worktree isolation pattern for coding agents
- `skills/shared/project-context/SKILL.md` — foundational context loader
- `skills/shared/conventional-commits/SKILL.md`
- Pre-tool-use update check hook (`01-check-updates.sh`)
- Stop hook for session summary (`01-session-summary.sh`)
- Orphan skill scan (`scripts/orphan-skill-scan.sh`)

---

## [1.0.0] — 2026-03

### Added
- Initial release: installer (`scripts/install.sh`), updater (`scripts/update.sh`)
- 5 core workflows: `new-project`, `bug-fix`, `maintenance`, `inherited-project`, `security-patch`
- `templates/plan-template.md`
- `CLAUDE.md` authoring standards

[Unreleased]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.16...v1.4.0
[1.3.16]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.0...v1.3.16
[1.3.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Dev-Toolbelt/dev-team-agents/releases/tag/v1.0.0
