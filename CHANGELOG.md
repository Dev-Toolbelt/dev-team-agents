# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed — slim Claude install + on-demand provider bootstrapping
- **Slim Claude installer** — `scripts/install.sh` no longer bundles the cross-CLI plumbing into the client's `.claude/dev-team-agents/`. The following files are stripped from the extracted tarball before install: `scripts/install-opencode.sh`, `scripts/install-codex.sh`, `scripts/render-provider.sh`, `scripts/lib/render_provider.py`, `scripts/lib/{tiers,tool-map,command-map,commands}.json`, and the `opencode/` directory. The default Claude-only client footprint drops by the size of those ~7 files. Users who want opencode or Codex CLI support bootstrap it on demand (see below)
- **New `scripts/lib/strip-tarball.sh`** — single source of truth for the slim strip rules. Sourced by `install.sh` (during tarball install) and by `.github/scripts/ci/slim-bootstrap.sh` (CI contract test), eliminating duplication. Add or remove a strip entry in one place; CI catches the regression automatically

### Added — multi-provider CI contract net
- **Per-provider contract tests** — new job `provider-contracts` in `.github/workflows/ci.yml` runs across `claude | opencode | codex` with five sequential checks per provider: render → attendance (counts derived from canonical source, never hardcoded) → schema/cross-ref contract → fixture install → fixture validation. The contract checker (`.github/scripts/ci/provider/_contract.py`) enforces: every tier has a column for every provider; every command in `commands.json` has a valid `agent` ref pointing at an existing source agent; opencode agents have frontmatter matching the schema (`mode ∈ {subagent, primary, all}`, `model` carries a provider prefix, `permission` keys are from the allowed set); opencode command snippet entries have all four required keys (`description`, `agent`, `model`, `template`); codex agent TOML parses and carries `name/description/model/developer_instructions` without provider prefix on model and valid `model_reasoning_effort` if present; codex prompts carry a `<!-- description: ... -->` header and follow the `devteam-<name>.md` naming. Violations exit non-zero with a one-line diagnostic
- **`slim-bootstrap` CI job** — new dedicated job verifies (1) a `git archive HEAD | tar -x` extraction + `apply_strip` produces the slim Claude shape (cross-CLI plumbing absent, Claude runtime essentials present — both lists asserted), (2) `install-provider.sh opencode --source` bootstraps `.opencode/` correctly into a slim-claude fixture (22 commands merged into `opencode.json`, plugin copied, skills symlinked, 17 agents), (3) `install-provider.sh codex --source` does the same for `.codex/` (17 agents + 22 prompts + 4 managed hooks + skills)
- **CI scripts externalized** — `.github/workflows/ci.yml` now invokes helper scripts under `.github/scripts/ci/` instead of inlining logic. New layout: `.github/scripts/ci/01-lint.sh`, `02-readme-sync.sh`, `slim-bootstrap.sh`, and `provider/{10-render,20-attendance,30-contract,40-install-fixture,50-validate-installed}.sh` + `_contract.py`. Pipeline is 3 jobs (`lint`, `provider-contracts` ×3, `slim-bootstrap`) with each step a single `bash .github/scripts/ci/...` invocation
- **Negative-test rehearsal** — the contract checker has been locally verified to catch: missing tier column for a provider, dangling `agent` ref in `commands.json`, malformed rendered opencode frontmatter (unknown `permission` key, missing `mode`, etc.). Each prints one diagnostic line and fails the build
- **New `scripts/install-provider.sh`** — curl-pipeable bootstrap that downloads a tarball of the requested version (`main` by default, or `--version vX.Y.Z`) and runs `install-opencode.sh` / `install-codex.sh` from a temp source dir with `--source`. It accepts `--source <path>` for working from a local clone without network. Usage: `bash <(curl -sSL .../install-provider.sh) opencode` or `... codex`
- **install-opencode.sh / install-codex.sh** — added a defensive check that exits with a clear error and bootstrap guidance when invoked from a source dir that lacks the render engine (`scripts/render-provider.sh` or `lib/{render_provider.py,tiers.json,…}` not present). This case happens when a slim Claude install is mistakenly used as the source; the message points the user at the `install-provider.sh` curl-pipe
- **README.md and README.pt-BR.md** — new "How It Works — Single Source, Multi-CLI" section right after "What This Is" with a textual architecture diagram showing the canonical source → render engine → per-provider output flow, and the slim Claude install alongside it. The "Other providers" section is rewritten to use the new `install-provider.sh` curl-pipe as the entry point (instead of pointing at `install-opencode.sh` / `install-codex.sh` inside the framework install, which no longer ships by default)
- **docs/providers.md** — added a note at the end of the "Adding a new provider" section explaining why the install scripts are stripped from slim installs and how `install-provider.sh` bootstraps them on demand

### Removed
- **`workflows/` directory and concept** — the 5 scope-specific workflow files (`design.md`, `fullstack.md`, `mobile.md`, `refactor.md`, `review.md`) and the 5 `/devteam:workflow-*` loader commands are gone. Each scope is now reached directly through its `/devteam:<scope>` command (`/devteam:design`, `/devteam:fullstack`, `/devteam:mobile`, `/devteam:refactor`, `/devteam:review`), which already delegated to the right agent. The `skills/shared/workflow-detection/SKILL.md` skill was removed. `agents/software-architect.md` and `commands/architect.md` no longer reference a separate workflow file. `helpers/orphan-skill-scan.sh` and `helpers/orphan-template-scan.sh` no longer scan a `workflows/` directory. `scripts/install.sh` `KEEP_ROOT` no longer distributes a `workflows/` directory. The 5 `workflow-*` entries were removed from `scripts/lib/commands.json`. CLAUDE.md, both READMEs, `docs/providers.md`, `CONTRIBUTING.md`, and `.github` templates were updated to drop framework-workflow references (`.github/workflows/` and `skills/shared/git-workflow/` are unrelated and kept)

### Added — multi-provider port (single source of truth)
- **Provider-agnostic render engine** — `scripts/render-provider.sh` (+ python engine `scripts/lib/render_provider.py`) renders the canonical `agents/` + `commands/` into the frontmatter shape expected by Claude Code, opencode, or Codex CLI. Agent bodies stay unchanged; a short "Tool conventions" preamble per provider explains how Claude Code tool names map to that provider's native tools. Fails fast on any unknown tier or missing `tier:` key
- **Per-agent `tier:` frontmatter key** — every `agents/*.md` now declares one of `reasoning | backend-exec | frontend | repetitive`. `helpers/agent-lint.sh` validates this key
- **Canonical tier → provider model id map** — `scripts/lib/tiers.json` carries the full model id per tier per provider (`claude`, `opencode`, `codex`). Adding a new provider is one new column, no edits to any agent or skill
- **Per-provider metadata** — `scripts/lib/tool-map.json` (Claude tool names → provider equivalents, used to generate the body's "Tool conventions" preamble) and `scripts/lib/command-map.json` (per-provider output form for slash commands)
- **Per-command metadata** — `scripts/lib/commands.json` declares each `commands/<name>.md`'s tier + lead agent + description, removing any need to add frontmatter to source command bodies
- **`scripts/install-opencode.sh`** — installs dev-team-agents into a project's `.opencode/` (renders 17 agents with opencode-shaped frontmatter, symlinks `skills/`, copies the plugin at `opencode/plugin/dev-team-agents.ts`, deep-merges 27 `devteam:<name>` command keys into `.opencode/opencode.json`)
- **`scripts/install-codex.sh`** — installs dev-team-agents into a project's `.codex/` (renders 17 agents as `.codex/agents/<name>.toml`, renders 27 prompts as `.codex/prompts/devteam-<name>.md` → `/prompts:devteam-<name>`, symlinks `skills/`, writes 4 managed hooks to `.codex/hooks.json` wiring `SessionStart | PreToolUse | PreCompact | Stop` to the existing bash dispatchers)
- **opencode plugin** — `opencode/plugin/dev-team-agents.ts` binds opencode's `event`, `tool.execute.before`, and `experimental.session.compacting` hooks to the same `scripts/hooks/*.sh` that Claude Code uses. Hook behavior stays single-source; only the binding event adapts
- **CI matrix job** — `.github/workflows/ci.yml` runs `provider-matrix` across `claude | opencode | codex`, asserting each emits 17 agents + 27 commands and installs cleanly into a fixture project
- **`docs/providers.md`** — canonical reference for the provider port: tier map, install commands per provider, the `/devteam:plan` UX across providers, how to add a new provider (single column in `tiers.json` + a row in `tool-map.json` + a row in `command-map.json` + one install-$provider.sh shell)
- **README updates** — new "Other providers (opencode, Codex)" section in both `README.md` and `README.pt-BR.md`; CLAUDE.md gains a "Multi-provider port" reference section

### Changed
- **Per-agent model id is now derived from `tier:` + `tiers.json`** — `model:` in `agents/*.md` is kept as the Claude fallback; non-Claude installations ignore it and resolve model via `tiers.json[tier][provider]`
- **Codex slash-command divergence** — Codex CLI's custom-prompt namespace is hardcoded as `/prompts:<name>`, so dev-team-agents commands are exposed as `/prompts:devteam-<name>` in Codex (e.g., `/prompts:devteam-plan`). Claude Code and opencode both preserve the canonical `/devteam:<name>` UX. The divergence is documented in `docs/providers.md`

## [1.11.0] - 2026-07-24

### Added
- **Push & GitHub Actions monitoring** — new `skills/shared/github-actions/SKILL.md`. When the user explicitly asks to push and `gh` is configured, agents watch the triggered Actions run and, on failure, run a capped diagnose→fix→re-push loop (max 3 attempts) with a one-line summary each cycle. Wired into `/devteam:pr` and a new **Push & CI Monitoring Rule** in `CLAUDE.md`
- **README agent list** — both READMEs (EN/pt-BR) now list all 17 agents grouped by role with a one-line summary each
- **Mandatory post-implementation handoff** — `/devteam:backend`, `/devteam:frontend`, `/devteam:mobile`, and `/devteam:fullstack` now always hand off to `code-reviewer` + `qa-specialist` after implementation, presenting a single consolidated block of critical findings
- **`qa_browser` preference** — `qa-specialist` prefers the in-app Claude browser for browser testing; in the CLI it asks which browser to use (quiz) and can save the choice as the `qa_browser` default in `preferences.json`

### Changed
- **`/devteam:plan` reworked** — `product-analyst` is now the protagonist and produces a **business-only** requirements document ready to become sprints; `software-architect` joins only on explicit technical request. The `product-analyst` agent gained a fixed interrogation methodology (7 lenses), an anti-overengineering rule, and a 3-category finding model
- **Sprints reorganized** — sprint files now live under `.claude/docs/backlog/sprints/` as `sprint-<n>.md`, with a `sprints.md` status index (Planned → In progress → Done) kept current as sprints finalize
- **Test creation is now gated** — `/devteam:backend|frontend|mobile|fullstack|fix|refactor` create tests only when the project sets `TESTS_REQUIRED=yes` (absent key defaults to running tests); when `TESTS_REQUIRED=no` the test phase is skipped entirely
- **`/devteam:review` with no arguments** now asks a dynamic quiz — current local branch / another local branch / a PR link (GitHub, GitLab, Bitbucket, …) / other — and acts on the chosen target
- **Sprints designed for parallel execution** — `product-analyst` now decomposes scope for maximum parallelism and fills a **Parallel Execution Plan** (waves of mutually independent tasks). The `backlog-template` sprint file gained per-task `Wave` + `Worktree branch` fields and a waves table. Isolation model is explicit: worktree-per-task always; isolated Docker stack per worktree **only when the project uses Docker** — otherwise parallelism is by worktree alone

### Removed
- **Lifecycle workflow commands** — `/devteam:workflow-new`, `/devteam:workflow-maintenance`, `/devteam:workflow-bugfix`, `/devteam:workflow-inherited`, and `/devteam:workflow-security-patch`, plus their `workflows/*.md` files. These lifecycle concerns are now encapsulated in the agents (`software-architect` built-in behavior + the direct commands). Scope-specific workflows (design, fullstack, mobile, refactor, review) are retained

---

## [1.10.0] — 2026-07-21

### Added
- Worktree preferences in `preferences.json` — four keys (`worktree_active`, `worktree_base_branch`, `worktree_path`, `worktree_docker_isolate`) let coding agents default to a git worktree per task without asking. `scripts/lib/preferences-defaults.json` is the new canonical default schema, read by both `install.sh` and the session-start health check
- Health-check backfill — `session-start.sh` fills any missing `preferences.json` key from the canonical schema on every session (idempotent, preserves existing user values), self-healing installs that predate a newly added key
- Docker isolation per worktree — `skills/shared/worktree/references/docker-isolation.md` describes spinning up an isolated `docker compose -p <project>-wt-<ctx>-<title>` stack (namespaced containers/volumes/networks, host ports not published, teardown scoped to the isolated project only)
- `/devteam:learn` now declares a commit manifest in its plan (Step 3) and auto-commits the knowledge-base updates after execution (conventional commits, local only, no push). New `--no-commit` argument opts out

### Changed
- Worktree decision is now a three-level cascade — `.claude/.worktree-session` (per-session override) → `worktree_active` in `preferences.json` (default) → ask once (legacy installs). Propagated to the 8 coding agents, `software-architect` worktree detection, and `CLAUDE.md`
- Worktree base branch is auto-detected (`origin/HEAD` → current branch) instead of assuming `beta` or `master`; `worktree_path` makes the worktree location configurable (default `.claude/worktrees`)
- Worktree finalization enforces rebase-onto-base → resolve → merge → teardown of the worktree and its isolated Docker stack only, never the main infrastructure
- The coding agents' worktree prompt now uses `AskUserQuestion` (quiz-first) instead of a plain `(yes / no)` text prompt
- Synced the preferences schema across the `user-preferences` skill, `setup-assistant`, installation guides (EN/pt-BR), and both READMEs

---

## [1.9.3] — 2026-07-19

### Fixed
- `/devteam:update` now repairs a broken installation instead of falsely reporting "Up to date". When `.claude/user-data/.installed-version` is missing or empty (`Installed: unknown`), the version check exited silently and the command reported the install as current; it now force-reinstalls the latest release to rewrite the metadata and clears the cached ETag so a stale `304` cannot mask the mismatch
- `01-check-updates.sh` no longer treats an install that is behind the still-latest release as up to date. A `304 Not Modified` short-circuited before comparing the local version against the latest release, silencing the "update available" notification after its first fire. The resolved version is now cached alongside the ETag (`.last-releases-version`) and reused on `304` to complete the comparison

---

## [1.9.2] — 2026-07-17

### Added
- `/devteam:symlinks` command — detects the OS, runs `fix-symlinks.sh` to repair materialized `.claude/` links, and walks the user through the OS fix (quiz-first) when native symlinks are blocked

---

## [1.9.1] — 2026-07-17

### Fixed
- `scripts/fix-symlinks.sh` now removes the legacy `stop/02-graphify-refresh.sh` sub-script during an in-place repair. On stale Windows installs the old sub-script called a `graphify-refresh.sh` that exited non-zero when graphify was absent, looping the Stop hook; a full update already drops it via the install-dir replace, but a symlink-only repair did not

---

## [1.9.0] — 2026-07-16

### Added
- `scripts/fix-symlinks.sh` — repairs `.claude/` links materialized as plain files instead of symlinks (Windows without Developer Mode / `core.symlinks`); auto-fixes when the OS allows and otherwise prints three remediation options. Detected automatically at session start (`[DEVTEAM:SYMLINK_BROKEN]`) and verified at install time; health-check Category 1 now distinguishes OK / MATERIALIZED / MISSING

### Changed
- Documented the Windows materialized-symlink repair flow across README (EN/pt-BR) and the installation guide

---

## [1.8.2] — 2026-06-29

### Fixed
- `graphify-refresh.sh` exits `0` on skip instead of non-zero, preventing a Stop-hook loop when graphify is not installed

---

## [1.8.1] — 2026-06-28

### Fixed
- Removed an unused `_notify` function in `session-start.sh`

---

## [1.8.0] — 2026-06-28

### Added
- `/devteam:learn` command for consolidating session decisions, patterns, and discoveries into docs, wiki, and ADRs
- Post-execution review step in `software-architect` and auto-learn hand-off in `/devteam:commit`

---

## [1.7.4] — 2026-06-28

### Fixed
- Suppress WSL `BASH_ENV` bashrc noise on hook invocation (follow-up to 1.7.3)

---

## [1.7.3] — 2026-06-24

### Fixed
- Suppress WSL `BASH_ENV` bashrc noise on hook invocation

---

## [1.7.2] — 2026-06-24

### Fixed
- Enforce LF line endings in the target project `.gitattributes` on install

---

## [1.7.1] — 2026-06-24

### Added
- First-time setup guard with quiz in `project-context`
- `SessionStart` emits a structured signal when `preferences.json` is missing
- Installer injects a pre-compact auto-summary rule into the project `CLAUDE.md`; health-check detects and auto-fixes it when missing

### Changed
- Added `.gitattributes` to enforce LF line endings in the repository

---

## [1.7.0] — 2026-05-18

### Added
- Anonymous usage telemetry via PostHog, wired into `install.sh` and `update.sh`; `PRIVACY.md` documents what is collected and how to opt out

---

## [1.6.7] — 2026-05-18

### Fixed
- Prune stale skill symlinks during update
- Resolve shellcheck warnings in hook and lint scripts

---

## [1.6.6] — 2026-05-18

### Fixed
- Anchor the fingerprint uniqueness check to registration lines only

---

## [1.6.5] — 2026-05-18

Large refactor/performance release focused on reducing per-session and per-spawn context-budget usage.

### Added
- `stack-detection` skill wired to agents; iOS and Android platform skills
- `interaction-patterns` skill (quiz-first rule) and `push-notifications` skill
- `validate-commit-msg.sh` gate in `/devteam:commit`; `workflow-mobile` and `workflow-design` shortcut commands
- Fingerprint uniqueness check, orphan-template scanner, and additional CI scans

### Changed
- Fragmented `CLAUDE.md` into `CLAUDE-md/` sub-files; extracted large inline sections across agents and skills (project-context, mobile, integrations, frontend, ui-ux) to `references/` subdirectories
- Moved dev-only tools to `helpers/`; moved the context-cache path to `user-data/`; canonicalized tools order; added the Hook Files Map
- Made agents stack-agnostic — removed Docker-first and stack-prescriptive language

### Fixed
- Restored the worktree session-file gate across coding agents; hardened `rollback.sh` and `pre-compact.sh` guards; corrected the CI fast-path comparison and fingerprint regex

---

## [1.6.4] — 2026-05-13

### Fixed
- README sync check compares section counts instead of header text

---

## [1.6.3] — 2026-05-13

### Added
- `release-prep` skill; ADR, backlog-item, and runbook templates
- Context cache, discovery lockfile, and graphify skip conditions; PreCompact hook and rollback script
- `conventional-commits` `validate.sh`; size-limits check; mobile and design workflows

### Changed
- Reduced file sizes across architect, database, setup, and reviewer agents; extracted large devops and docs skills to `references/`
- Extended orphan-skill-scan to cover `commands/` and `workflows/`; added Portuguese translations for agents and installation guides

### Fixed
- Implemented the worktree session-file gate in all coding agents; removed non-canonical frontmatter keys from design skills

---

## [1.6.2] — 2026-05-12

### Changed
- Restructured README for first-time readability; extracted the agent reference and installation guide to `docs/`

---

## [1.6.1] — 2026-05-12

### Added
- `/devteam:mobile` and `/devteam:adr` commands
- Plan-gate enforcement across all implementation commands; context estimation via transcript tokens with a preferences fallback

### Changed
- Reduced the git-log window from `-20` to `-10` across 10 agents; expanded the preferences schema (`transcript_multiplier`, `model_max_tokens`)

### Fixed
- Disabled Claude co-authoring in git artifacts and added a Jira REST API fallback; reclassified plans as conversation items using the user's preferred language; added a daily gate to the notifier tip-of-session; fixed the graphify-setup skill path in `setup-assistant`

---

## [1.6.0] — 2026-05-11

### Added
- `mobile-developer` agent with React Native, Expo, and Flutter skills
- Material Design 3 and iOS HIG mobile design skills

---

## [1.5.5] — 2026-05-11

### Fixed
- `check-updates.sh` no longer exits with code 1 when the GitHub API returns an empty response

---

## [1.5.4] — 2026-05-11

### Fixed
- Exclude repo-only files from the distributed package
- Remove the rollback feature and `.previous` directory from the installer

---

## [1.5.3] — 2026-05-11

### Changed
- Trimmed all skill descriptions to reduce context-budget usage

---

## [1.5.2] — 2026-05-11

### Fixed
- Jira MCP setup checks deferred tools via ToolSearch before showing setup instructions

---

## [1.5.1] — 2026-05-11

### Fixed
- Skip the Graphify prompt when already configured; strip `agent-lint.sh` from the distributed package

---

## [1.5.0] — 2026-05-11

### Added
- User preferences system (`preferences.json`) with a language prompt on install; notification system and the `04-notifier.sh` stop sub-script
- `user-preferences` and `notifier` shared skills; per-engine database skills for all 7 engines
- Architecture skills (event-driven, rate-limiting, api-versioning); `diataxis-framework`; fullstack workflow; recovery paths in all workflows
- Community health files and GitHub templates; rollback support in the installer/update script; session-start staleness hook

### Changed
- Migrated command context detection to the `current-context` skill and `spawn-classifier`; rewrote `/devteam:refactor` with test-first coverage and dependency mapping; expanded database-specialist engine detection
- Untracked `session-summary.md` and added it to `.gitignore`

### Fixed
- Removed the manual shellcheck `apt-get install` step in CI

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

[Unreleased]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.3...HEAD
[1.9.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.2...v1.9.3
[1.9.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.1...v1.9.2
[1.9.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.9.0...v1.9.1
[1.9.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.2...v1.9.0
[1.8.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.1...v1.8.2
[1.8.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.8.0...v1.8.1
[1.8.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.4...v1.8.0
[1.7.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.3...v1.7.4
[1.7.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.2...v1.7.3
[1.7.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.7...v1.7.0
[1.6.7]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.6...v1.6.7
[1.6.6]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.5...v1.6.6
[1.6.5]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.4...v1.6.5
[1.6.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.3...v1.6.4
[1.6.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.2...v1.6.3
[1.6.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.1...v1.6.2
[1.6.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.6.0...v1.6.1
[1.6.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.5...v1.6.0
[1.5.5]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.4...v1.5.5
[1.5.4]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.3...v1.5.4
[1.5.3]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.2...v1.5.3
[1.5.2]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.1...v1.5.2
[1.5.1]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.5.0...v1.5.1
[1.5.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.16...v1.4.0
[1.3.16]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.3.0...v1.3.16
[1.3.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/Dev-Toolbelt/dev-team-agents/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/Dev-Toolbelt/dev-team-agents/releases/tag/v1.0.0
