# Dev Team Agents

🇧🇷 [Veja a versão em Português do Brasil](README.pt-BR.md)

**Multi-agent development harness** — a harness for organizing AI agents in software development. Stack-agnostic, project-aware, and collaboratively maintained.

---

## What This Is

Not just a bundle of agents: it is the layer that governs how those agents plan, execute, test, review, and record their work.

Each agent has a defined role, expertise, and workflow integration. What makes it a harness rather than a collection is everything around them — the plan gate that blocks silent execution, the lifecycle hooks that enforce session memory, the review routing, the validators that keep the whole tree honest. They coexist with your project's own rules — project conventions always win.

18 agents cover the full development lifecycle: discovery, design, implementation, quality gates, and documentation. → See the full [Agent Reference](docs/agents.md).

---

## Prerequisites

**Python 3** must be installed on your system — it powers the render engine, graphify, and safe JSON merges into `settings.json`. Nothing else is required beyond your CLI of choice.

If it's missing, the installer, updater, and `/devteam:health-check` will warn you and continue in degraded mode. Install it with:

| OS | Command |
|----|---------|
| macOS | `brew install python3` |
| Linux (Debian/Ubuntu) | `sudo apt install python3` |
| Linux (Fedora/RHEL) | `sudo dnf install python3` |
| Windows | [python.org/downloads](https://www.python.org/downloads/) or `winget install Python.Python.3` |

---

## Quick Install

| CLI | One command | Docs |
|-----|-------------|------|
| **Claude Code** | `curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh \| bash` | [docs/install-claude.md](docs/install-claude.md) |
| **opencode** | `bash <(curl -sSL .../scripts/install-provider.sh) opencode` | [docs/install-opencode.md](docs/install-opencode.md) |
| **Codex CLI** | `bash <(curl -sSL .../scripts/install-provider.sh) codex` | [docs/install-codex.md](docs/install-codex.md) |

Run the command from your **project root**. The Claude installer asks for your preferred conversation language. opencode and Codex CLI are **not bundled** in the Claude slim install — they bootstrap on demand via `install-provider.sh`.

> Full model-tier map, known limitations, and adding a new provider: [docs/providers.md](docs/providers.md)

After Claude install, start the setup flow by typing:

```
Help me set up this project with dev-team-agents
```

> **Advanced Claude options** — specific version, update, version pinning, auto-update, notifications, and directory layout: [docs/installation.md](docs/installation.md)

---

## Getting Started

After installing, start the setup flow by telling your CLI:

```
"Help me set up this project with dev-team-agents"
```

The `setup-assistant` will:

1. **Detect** whether this is a first-time setup or a refresh — and adapt accordingly
2. **Scan** existing files (README, CLAUDE.md, package manifests, git history) and summarize what it found
3. **Ask** which type of project this is: new from scratch, inherited/unfinished, or maintenance on a live system
4. **Collect** configuration in a single exchange: tests required, CI/CD platform, cloud provider, issue tracker
5. **Present a plan** for your approval before creating or modifying anything
6. **Generate** living context docs in `docs/` (stack, architecture, code standards, backlog index) and append a `## dev-team-agents` section to `CLAUDE.md`
7. **Confirm** what was configured and point you to the relevant workflow guide

The full setup typically takes 5–10 minutes. Re-running on an existing project triggers refresh mode — reads git history since the last run and patches only the affected docs.

---

## Slash Commands

After installation, Claude Code and opencode expose slash commands under the `/devteam:` namespace. In Codex, the project-local default is the generated skill path `$devteam-<name>`. Each entrypoint spawns the appropriate agents and scopes work to the current git branch or worktree.

| Command | What it does |
|---------|-------------|
| `/devteam:setup` | Onboarding — detects first run vs refresh, then setup-assistant configures `CLAUDE.md`, `docs/`, the wiki, and your preferences |
| `/devteam:plan` | Planning — product-analyst leads and produces a business-only requirements doc ready for sprints; software-architect joins on explicit technical request |
| `/devteam:backend` | Backend implementation — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Frontend implementation — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Mobile implementation — mobile-developer + ui-ux-designer (when relevant) |
| `/devteam:fullstack` | Full-stack implementation — backend + frontend teams in parallel |
| `/devteam:design` | UI/UX design — ui-ux-designer |
| `/devteam:relayout` | Redesign an existing screen to match visual references — ui-ux-designer + frontend-developer, mandatory reference/target-screen gate, isolated worktree, automatic post-execution review |
| `/devteam:seo` | SEO quality gate — seo-specialist (technical, on-page, Core Web Vitals, structured data, GEO/LLM readiness) |
| `/devteam:fix` | Bug fix — relevant developer(s) → test-specialist |
| `/devteam:refactor` | Refactoring — software-architect plans, then developer(s) execute |
| `/devteam:architect` | Architecture decisions and ADRs — software-architect |
| `/devteam:review` | Code review — code-reviewer + software-architect + security-specialist + qa-specialist |
| `/devteam:qa` | Quality assurance — qa-specialist |
| `/devteam:audit` | Deep module/area analysis — backend-developer + frontend-developer + security-specialist + devops-specialist; saves report to `docs/audit/` |
| `/devteam:security` | Security audit — security-specialist + software-architect |
| `/devteam:dba` | Database work — database-specialist + software-architect |
| `/devteam:devops` | Infrastructure / CI/CD — devops-specialist |
| `/devteam:tester` | Tests only — backend-test-specialist + frontend-test-specialist |
| `/devteam:docs` | Documentation — technical-writer |
| `/devteam:pr` | Pull request — drafts title + description, asks for confirmation before creating; before the push, asks a CI/CD-aware quiz (watch Actions vs. push-only) when GitHub Actions is configured |
| `/devteam:push` | Push — asks a CI/CD-aware quiz (watch CI + auto-fix vs. push-only vs. other) when GitHub Actions is configured; pushes normally otherwise |
| `/devteam:commit` | Commit — reads staged changes, groups by layer, writes and runs commits |
| `/devteam:learn` | Knowledge capture — consolidates session decisions, patterns, and discoveries into docs, wiki, and ADRs, then auto-commits the result (declares the commit manifest in its plan) |
| `/devteam:rule` | Standardization — catalogs a mandatory reuse rule (e.g. `/devteam:rule use o componente XPTO em todo o projeto`) into `docs/development/reuse-guidelines.md`, so future work never overlooks it. Classified as `code-pattern`, `path-convention`, or `design-rule`; enforced by the review gate and, for the mechanizable types, by a Stop-hook lint |
| `/devteam:sync-rules` | Backfill — scans `docs/` for conventions already documented in prose but never cataloged in `reuse-guidelines.md`, then runs `/devteam:rule`'s classify → propose → confirm → append routine per candidate, one confirmation at a time. Suggested after install/update and flagged by `/devteam:health-check` |
| `/devteam:explain` | Glossary on demand — explains a term, acronym, or piece of jargon you saw in the session. Short by design: expands every acronym, states the problem it solves, gives one example in your project's language, and draws a mermaid diagram when the term is a shape (a flow, an exchange between parties, a hierarchy, a lifecycle) rather than just a definition. Closes by offering an interactive quiz |
| `/devteam:health-check` | Installation diagnostics — detects the active provider (Claude / opencode / Codex), runs 13 checks (symlinks, scripts, user data, provider config, graphify, CLAUDE.md, .gitignore, preferences, notifier, credentials, memory artifacts, python prerequisite, productivity/token-efficiency tools) and applies safe auto-fixes. It never deletes: anything it can't place is moved to `.dev-team-agents/user-data/legacy/<date>/`, and files that hold accumulated knowledge are adapted in place, never regenerated |
| `/devteam:adr` | Architecture Decision Record — runs `scripts/new-adr.sh` to scaffold a numbered ADR, then software-architect fills the template |
| `/devteam:update` | Update — checks for a new dev-team-agents release and applies it |
| `/devteam:symlinks` | Symlink repair — detects the OS, repairs links materialized as plain files, and guides the fix when the OS blocks native symlinks |

**Usage examples:**

```
/devteam:plan add an export-to-PDF feature for the fueling report
/devteam:backend implement the PDF export endpoint
/devteam:review
/devteam:pr draft
/devteam:explain SPA, SSR, tenant, middleware
```

Model-tier resolution, provider rendering, and Codex-specific orchestration details live in [Harness Architecture](docs/harness.md).

---

## Agents

The team has **18 agents** covering the full lifecycle. Full details in the [Agent Reference](docs/agents.md).

**Planning & architecture**

| Agent | What it does |
|-------|-------------|
| `product-analyst` | Lead of planning — turns a request into a closed, **business-level** requirements document ready to become sprints |
| `software-architect` | System design, trade-offs, API contracts, design patterns, and ADRs |
| `database-specialist` | Schema design, migrations, and query optimization |

**Implementation**

| Agent | What it does |
|-------|-------------|
| `backend-developer` | Server-side code — APIs, services, business logic |
| `frontend-developer` | Client-side code — screens, components, UI flows |
| `mobile-developer` | Mobile features — React Native, Expo, Flutter, native iOS/Android |
| `ui-ux-designer` | Design system, UX flows, and visual decisions |
| `seo-specialist` | SEO quality gate — technical, on-page, Core Web Vitals, structured data, GEO/LLM readiness |
| `devops-specialist` | CI/CD, Docker, infrastructure, and deploy scripts |

**Quality & review**

| Agent | What it does |
|-------|-------------|
| `code-reviewer` | Entry-point reviewer — routes to the backend/frontend reviewers and synthesizes a single verdict |
| `backend-reviewer` | Deep structural review of backend changes |
| `frontend-reviewer` | Deep structural review of frontend changes |
| `qa-specialist` | Validates product behavior, user flows, and regression risk |
| `security-specialist` | Security audits, vulnerability analysis, OWASP concerns |
| `backend-test-specialist` | Writes and maintains backend tests |
| `frontend-test-specialist` | Writes and maintains frontend tests |

**Enablement**

| Agent | What it does |
|-------|-------------|
| `technical-writer` | Docs, changelogs, runbooks, release notes, and PR descriptions |
| `setup-assistant` | Configures dev-team-agents for a project and runs health checks |

---

## How to Use Agents

Agents are invoked by naming the role in your message:

```
"As the product-analyst, analyze this PRD: [document]"
"As the software-architect, define the architecture for this project."
"As the backend-developer, implement [task]"
"As the code-reviewer, review the changes in [files]."
```

---

## Common Tasks

Pick the command that matches your goal — the lifecycle handling (new project, bug fix, maintenance, inherited code, security patch) is now built into the agents, no separate workflow command needed.

| Goal | Command |
|------|---------|
| Plan a feature / new project | `/devteam:plan` |
| Fix a bug | `/devteam:fix` |
| Refactor | `/devteam:refactor` |
| Security audit / patch | `/devteam:security` |
| Architecture decision, inherited/maintenance change | `/devteam:architect` |
| Code review before merge | `/devteam:review` |

Each scope-specific concern (design, fullstack, mobile, refactor, review) is handled by its dedicated `/devteam:<scope>` command, which delegates to the right agent — no separate workflow directory.

---

## Committing the Installation

Because `install.sh` downloads a tarball (not a git clone), `.dev-team-agents/` has no nested `.git` folder. **Commit it directly** so your whole team gets the agents on `git pull`:

```bash
git add .dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

Worktree isolation, notification thresholds, language settings, and other local runtime knobs now live in [User Preferences](docs/user-preferences.md).

For staging/production access structure, see [Credentials Reference](docs/credentials.local.md).

---

## Agent Memory

Agents start each session with no memory of previous ones. Five layers minimize context loss, each holding one kind of thing:

| Layer | Where | Holds | Lifespan |
|-------|-------|-------|----------|
| Structural | `docs/project.md`, `docs/development/` | Stack, architecture, standards | Rewritten — always describes now |
| Episodic | `.dev-team-agents/user-data/session-summary.md` | What happened, in order | Decays after ~30 days |
| Semantic | `docs/wiki/` | What isn't derivable from the code | Permanent; superseded, never deleted |
| Decisional | `docs/development/adrs/` | Why a hard-to-reverse choice was made | Permanent and immutable |
| Mechanical | `graphify-out/graph.json` | Where things are in the code | Regenerated |

**One question decides where something goes: is it derivable by reading the code?** If yes, it isn't written down at all — that rule is what keeps the memory from becoming a second, aging source of truth that contradicts the repository.

- **Session summary** — written at the end of any session where files changed; a `Stop` hook enforces it. Before old entries are trimmed, agents check whether the decisions in them were ever promoted to an ADR or wiki entry, and tell you which weren't rather than dropping them silently.
- **Wiki** — `docs/wiki/README.md` is a keyword index, one row per entry. Agents grep it for the task at hand and open only what matches, so a wiki with 200 entries costs the same at startup as one with 5.
- **ADRs** — create one with `bash .dev-team-agents/scripts/new-adr.sh "title"`.
- **`/devteam:learn`** — promotes what a session learned from the episodic layer into the durable ones.

Nothing in this system deletes knowledge automatically. The episodic layer is the sole exception, by design, and the promotion check above is what guards it.

---

## Coexistence & Customization

Project-level overrides, precedence rules, and customization guidance now live in [Harness Architecture](docs/harness.md).

---

## Troubleshooting

**Agents are not recognized by the CLI** — verify the symlink exists: `ls .claude/agents/dev-team/` (Claude Code), `ls .opencode/agents/` (opencode), `ls .codex/agents/` (Codex CLI). If missing, re-run that provider's installer from your project root.

**Skills are not loaded** — check that `.claude/skills/` (or `.opencode/skills/`, `.codex/skills/`) contains symlinks. Re-run the installer to restore broken links.

**Windows: the whole dev-team is missing (no `/devteam:*`, no agents, no skills)** — on Windows without Developer Mode, git/MSYS writes symlinks as plain ~62-byte text files: the `.claude/` links for the Claude Code install, and the `skills/` link under `.opencode/` or `.codex/` for the other providers. `git-bash`'s `ls -la` still shows them as `lrwxrwxrwx`, but the CLI sees plain files, so nothing loads. Confirm with `test -L .claude/commands/devteam && echo link || echo broken`. Repair the Claude tree by running `bash .dev-team-agents/scripts/fix-symlinks.sh` — it repairs automatically when it can, and otherwise prints three options: (1) enable **Developer Mode** (Settings → System → For developers — recommended, no admin), (2) run `git config core.symlinks true && git checkout -- .claude` once in an **elevated PowerShell**, or (3) run **your CLI as administrator** (fully close it first, including the tray icon). For opencode and Codex, re-run that provider's installer once native symlinks are enabled. Restart your CLI after repairing so it re-indexes the dev-team.

**Update check seems stuck / not firing** — the check runs once per session from `SessionStart` (`scripts/hooks/session-start.sh`), not on every tool call. Verify `.dev-team-agents/user-data/.last-update-check` is a writable file (not a directory) and that `session-start.sh` is executable. The notifier, telemetry, and automatic Graphify refresh hooks are currently disabled by default — see `CLAUDE-md/hooks.md` § Disabled Hooks for status and how to re-enable.

**`setup-assistant` ran but the `## dev-team-agents` section is missing from CLAUDE.md** — tell your CLI: `"As the setup-assistant, the dev-team-agents section is missing from CLAUDE.md — please add it."`

**An agent executed without showing a plan first** — check your project CLAUDE.md for any instruction that conflicts with plan mode.

---

## Anonymous Telemetry (BETA)

dev-team-agents can collect **anonymous, aggregate usage data** to help us understand which agents and commands are most valuable. **It is disabled unless you turn it on.**

**Consent:** the installer asks once, on first install, by opening your terminal directly — so the prompt shows up even on the `curl … | bash` path. Answering `n`, not answering within 60 seconds, setting `DEVTEAM_NONINTERACTIVE=1`, or having no terminal at all each leave it **disabled**. Nothing is queued or sent until `preferences.json` says `"telemetry": true`.

**What is collected** (only when enabled): agent/command names, install and update events, session counts, OS family, and installed version. No code, file paths, project names, or personal data is ever collected.

**Change it at any time** by editing `.dev-team-agents/user-data/preferences.json` — `false` to opt out, `true` to opt in:

```json
{ "telemetry": false }
```

Full details in [PRIVACY.md](PRIVACY.md).

---

## Contributing

1. Fork the repository
2. Create a branch: `fix/agent-name-improvement` or `feat/new-skill`
3. Follow the authoring standards in `CLAUDE.md`
4. Open a PR with a clear description of what changed and why

---

## License

MIT
