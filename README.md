# Dev Team Agents

🇧🇷 [Veja a versão em Português do Brasil](README.pt-BR.md)

**Multi-agent development harness** — a harness for organizing AI agents in software development. Stack-agnostic, project-aware, and collaboratively maintained.

---

## What This Is

Not just a bundle of agents: it is the layer that governs how those agents plan, execute, test, review, and record their work.

Each agent has a defined role, expertise, and workflow integration. What makes it a harness rather than a collection is everything around them — the plan gate that blocks silent execution, the lifecycle hooks that enforce session memory, the review routing, the validators that keep the whole tree honest. They coexist with your project's own rules — project conventions always win.

17 agents cover the full development lifecycle: discovery, design, implementation, quality gates, and documentation. → See the full [Agent Reference](docs/agents.md).

---

## How It Works — Single Source, Multi-CLI

One canonical source of truth lives in this repo: `agents/`, `commands/`, `skills/`, `templates/`, `scripts/hooks/`, plus a small set of JSON metadata files (`scripts/lib/tiers.json`, `tool-map.json`, `command-map.json`, `commands.json`). Nothing provider-specific is checked in for any CLI.

A render engine (`scripts/render-provider.sh`, plain Python with stdlib only) reads the canonical source and emits the file tree each provider's CLI expects. Per-CLI installers translate agent frontmatter, prep a short per-provider "Tool conventions" note that maps Claude Code tool names to that CLI's native tools, and wire lifecycle hooks to the same bash dispatchers in `scripts/hooks/`.

```
                      ┌─────────────────────────────────────────────────────┐
                      │              THIS REPO (canonical source)           │
                      │     agents/  commands/  skills/  templates/         │
                      │     scripts/hooks/*.sh   (single bash dispatchers) │
                      │     scripts/lib/{tiers, tool-map, command-map,      │
                      │                   commands, preferences}.json       │
                      └──────────────────────────┬──────────────────────────┘
                                                 │
            ┌───────────────────────────────────┴────────────────────────────────────┐
            │                                                                          │
            ▼                                                                          ▼
  ┌───────────────────────────────────┐                            ┌──────────────────────────────┐
  │   scripts/render-provider.sh      │                            │   scripts/install.sh          │
  │   (python3, stdlib only)          │                            │   (Claude Code installer)     │
  │                                   │                            │   slim bundle to project's    │
  │   --provider claude | opencode |  │                            │   .dev-team-agents/    │
  │              codex                 │                            └───────────────┬──────────────┘
  └──┬────────────────┬───────────────┘                                            │ works
     │ renders         │ renders                                                    ▼ directly
     ▼                ▼                                              ┌──────────────────────────────┐
  .opencode/          .codex/                                        │  .claude/                    │
  agents/<n>.md       agents/<n>.toml    ← frontmatter reshape       │  agents/dev-team/<n>.md      │
  opencode.json       prompts/devteam-*  ← slash command form       │  commands/devteam/<n>.md    │
  plugins/dev-team-    hooks.json         ← wire bash dispatchers    │  skills/<name>/             │
  agents.ts            skills/ → symlink                              │  settings.json → hooks/*.sh │
  skills/ → symlink                                                   └──────────────────────────────┘
     │                                                                  ▼
     │ invoked from a Claude-slim project via                          │ handled by existing Claude
     │                                                                  │ install path — no extra
     │   bash <(curl -sSL .../install-provider.sh) opencode              │ bootstrap needed
     │   bash <(curl -sSL .../install-provider.sh) codex
     ▼
  /devteam:plan do a plan          ← identical UX across CLIs (Codex → /prompts:devteam-plan or $devteam-plan)
```

**Layered model — three concerns, kept separate:**

1. **Knowledge** (skills, agent role prompts, command flow prompts, hook behavior). Authored once, versioned in this repo, identical across providers.
2. **Adapters** (per-provider frontmatter shape, tool-name mapping table, slash-command output form). Defined once per provider in `scripts/lib/*.json` and rendered at install time. Adding a new provider = one column in `tiers.json` + one row in `tool-map.json` + one row in `command-map.json` + a thin `install-<provider>.sh`.
3. **Binding** (`.claude/settings.json` for Claude, `.opencode/plugins/dev-team-agents.ts` for opencode, `.codex/hooks.json` for Codex). All three invoke the SAME `scripts/hooks/*.sh` dispatchers — no per-provider hook duplication.

**Per-agent model id is rigid per tier.** Every agent declares one of `reasoning | backend-exec | frontend | repetitive`. Each tier is resolved to a concrete model id through `tiers.json` per provider, so switching providers is a one-column change — no agent body edits. On Claude Code that means architecture and security work runs on Opus, implementation and review on Sonnet, and doc generation on Haiku, instead of every subagent sharing the session's model.

**Every agent opens with a run banner** — an agent/tier/model/effort table printed before it does anything else, on all three providers, so you can always see which model is doing the work.

> Full reference: [docs/providers.md](docs/providers.md)

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

After installation, slash commands are available under the `/devteam:` namespace. Each command spawns the appropriate agents and scopes work to the current git branch or worktree.

| Command | What it does |
|---------|-------------|
| `/devteam:setup` | Onboarding — detects first run vs refresh, then setup-assistant configures `CLAUDE.md`, `docs/`, the wiki, and your preferences |
| `/devteam:plan` | Planning — product-analyst leads and produces a business-only requirements doc ready for sprints; software-architect joins on explicit technical request |
| `/devteam:backend` | Backend implementation — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Frontend implementation — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Mobile implementation — mobile-developer + ui-ux-designer (when relevant) |
| `/devteam:fullstack` | Full-stack implementation — backend + frontend teams in parallel |
| `/devteam:design` | UI/UX design — ui-ux-designer |
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
| `/devteam:pr` | Pull request — drafts title + description, asks for confirmation before creating |
| `/devteam:commit` | Commit — reads staged changes, groups by layer, writes and runs commits |
| `/devteam:learn` | Knowledge capture — consolidates session decisions, patterns, and discoveries into docs, wiki, and ADRs, then auto-commits the result (declares the commit manifest in its plan) |
| `/devteam:explain` | Glossary on demand — explains a term, acronym, or piece of jargon you saw in the session. Short by design: expands every acronym, states the problem it solves, gives one example in your project's language, and draws a mermaid diagram when the term is a shape (a flow, an exchange between parties, a hierarchy, a lifecycle) rather than just a definition. Closes by offering an interactive quiz |
| `/devteam:health-check` | Installation diagnostics — detects the active provider (Claude / opencode / Codex), runs 9 checks (symlinks, scripts, user data, provider config, graphify, CLAUDE.md, .gitignore, preferences, notifier) and applies safe auto-fixes |
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

**Which model a command runs on.** Every command declares a tier in `scripts/lib/commands.json`, and on opencode and Codex that tier resolves to a concrete model at install time. On Claude Code the body is symlinked as-is, so the tier reaches it only through a `model:` key in the command's frontmatter — and that key is used on the seven `repetitive` commands alone (`docs`, `pr`, `commit`, `learn`, `update`, `symlinks`, `health-check`), which run on Haiku. Every other command inherits whatever model your session is set to. The reason is deliberate: `model:` overrides the session, so pinning a planning command to Opus would silently undo a session you lowered to save cost, while a Haiku pin can only ever cost less than what you chose.

For **Codex specifically**, that tier pin applies to the rendered **agents** in `.codex/agents/*.toml`. The `/prompts:devteam-*` files are plain Markdown prompts, so they do not carry runtime `model` or `model_reasoning_effort` fields of their own — they rely on the agents they spawn to enforce the Codex-side model/effort policy.

---

## Agents

The team has **17 agents** covering the full lifecycle. Full details in the [Agent Reference](docs/agents.md).

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

Role-naming works in every supported CLI — Claude Code (the `claude` CLI, desktop app, web app at [claude.ai/code](https://claude.ai/code), IDE extensions), opencode, and Codex CLI — because the agents are rendered from one canonical source per provider.

**Every agent presents a plan for approval before executing anything.** You review, adjust, and approve — then execution begins.

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

---

## Worktree Isolation

Coding agents resolve the worktree decision from a **three-level cascade**:

1. **`.dev-team-agents/.worktree-session`** (per-session override) — shared across all agents in the task, so multi-agent workflows resolve it exactly once.
2. **`preferences.json` defaults** — `worktree_active` is `true` out of the box, so agents create a worktree per task **without asking**; set it to `false` to work directly on a branch instead. The base branch comes from `worktree_base_branch` (or is auto-detected — never hardcoded to `main`/`master`), and worktrees are created under `worktree_path` (default `.dev-team-agents/worktrees/<ctx>/<title>/`).
3. **Ask once** — only on legacy installs where the preference key is absent.

**Docker isolation** — when `worktree_active` is on and the project uses Docker Compose, agents can spin up an **isolated compose stack per worktree** (`worktree_docker_isolate: true`). Containers, networks, and volumes are namespaced with a clear name (`<project>-wt-<ctx>-<title>`), host ports are not published, and nothing touches the main stack.

**Finalization** — when you ask to merge, the agent **rebases onto the base branch**, resolves conflicts, commits, merges, and then tears down **only** the worktree and its isolated Docker stack.

| Preference | Default | Purpose |
|-----------|---------|---------|
| `worktree_active` | `true` | Create a worktree per task by default (no prompt) |
| `worktree_base_branch` | `null` | Base branch (`null` = auto-detect) |
| `worktree_path` | `.dev-team-agents/worktrees` | Where worktrees are created |
| `worktree_docker_isolate` | `true` | Isolated Docker stack per worktree (when Docker is present) |

---

## Agent Memory

Agents start each session with no memory of previous ones. Three mechanisms minimize context loss:

- **Session summary** — at the end of any session where files changed, agents write an entry to `.dev-team-agents/user-data/session-summary.md`. A `Stop` hook enforces this automatically.
- **ADRs** — significant, hard-to-reverse decisions are recorded as Architecture Decision Records in `docs/development/adrs/`. Create one with: `bash .dev-team-agents/scripts/new-adr.sh "title"`
- **Project context skill** — defines the context-loading order every agent follows at startup, including the session summary and ADR index.

---

## Coexistence & Customization

Dev Team Agents is a **base layer**. Your project's own conventions always take precedence: `CLAUDE.md` → `AGENTS.md` → `.agents/<agent-name>.md`. If your project says use tabs, agents use tabs.

Do **not** modify files inside `.dev-team-agents/` — they are overwritten on update. Override at the project level instead:

```bash
.agents/backend-developer.md          # per-agent override
CLAUDE.md                             # project-wide rules for all agents
docs/development/code-standards.md  # code standards used by reviewers
```

---

## Troubleshooting

**Agents are not recognized by the CLI** — verify the symlink exists: `ls .claude/agents/dev-team/` (Claude Code), `ls .opencode/agents/` (opencode), `ls .codex/agents/` (Codex CLI). If missing, re-run that provider's installer from your project root.

**Skills are not loaded** — check that `.claude/skills/` (or `.opencode/skills/`, `.codex/skills/`) contains symlinks. Re-run the installer to restore broken links.

**Windows: the whole dev-team is missing (no `/devteam:*`, no agents, no skills)** — on Windows without Developer Mode, git/MSYS writes symlinks as plain ~62-byte text files: the `.claude/` links for the Claude Code install, and the `skills/` link under `.opencode/` or `.codex/` for the other providers. `git-bash`'s `ls -la` still shows them as `lrwxrwxrwx`, but the CLI sees plain files, so nothing loads. Confirm with `test -L .claude/commands/devteam && echo link || echo broken`. Repair the Claude tree by running `bash .dev-team-agents/scripts/fix-symlinks.sh` — it repairs automatically when it can, and otherwise prints three options: (1) enable **Developer Mode** (Settings → System → For developers — recommended, no admin), (2) run `git config core.symlinks true && git checkout -- .claude` once in an **elevated PowerShell**, or (3) run **your CLI as administrator** (fully close it first, including the tray icon). For opencode and Codex, re-run that provider's installer once native symlinks are enabled. Restart your CLI after repairing so it re-indexes the dev-team.

**Update check hook fires on every tool call** — check that `.dev-team-agents/user-data/.last-update-check` is a writable file (not a directory) and that `scripts/hooks/pre-tool-use/01-check-updates.sh` is executable.

**`setup-assistant` ran but the `## dev-team-agents` section is missing from CLAUDE.md** — tell your CLI: `"As the setup-assistant, the dev-team-agents section is missing from CLAUDE.md — please add it."`

**An agent executed without showing a plan first** — check your project CLAUDE.md for any instruction that conflicts with plan mode.

---

## Anonymous Telemetry

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
