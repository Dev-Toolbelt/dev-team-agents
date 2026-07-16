# Dev Team Agents

🇧🇷 [Veja a versão em Português do Brasil](README.pt-BR.md)

A global team of specialized Claude Code agents and skills for software development. Stack-agnostic, project-aware, and collaboratively maintained.

---

## What This Is

A set of Claude Code agents and skills that form a complete software development team. Each agent has a defined role, expertise, and workflow integration. They coexist with your project's own rules — project conventions always win.

17 agents cover the full development lifecycle: discovery, design, implementation, quality gates, and documentation. → See the full [Agent Reference](docs/agents.md).

---

## How to Install

### Prerequisites

- **Claude Code** — CLI, desktop app, or IDE extension. Install at [claude.ai/code](https://claude.ai/code).
- **Git** — the installer uses `git rev-parse` to verify the project root.
- **curl** or **wget** — used to download the release tarball.

### Install (latest version)

Run from your **project root**:

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
```

Example output:

```
[dev-team-agents] Fetching latest release...
[dev-team-agents] Installing v1.2.0...
[dev-team-agents] Extracting to .claude/dev-team-agents/
[dev-team-agents] Creating symlinks...
[dev-team-agents] Configuring hooks in .claude/settings.json...

? Which language should agents use when talking to you? (BCP 47 tag, e.g. en, pt-BR, es) [en]:

[dev-team-agents] Done. Installed v1.2.0.
[dev-team-agents] Run: "Help me set up this project with dev-team-agents"
```

### Language preference

During installation, the installer asks which language agents should use in conversation. Documents (ADRs, changelogs, code comments) always remain in English. Update at any time in `.claude/user-data/preferences.json`:

```json
{ "language": "pt-BR" }
```

Common values: `en` · `pt-BR` · `es` · `fr` · `de` · `ja` · `zh-CN`

> **Advanced options** — specific version, updates, version pinning, auto-update, notifications, and directory layout: [docs/installation.md](docs/installation.md)

---

## Getting Started

After installing, start the setup flow by telling Claude:

```
"Help me set up this project with dev-team-agents"
```

The `setup-assistant` will:

1. **Detect** whether this is a first-time setup or a refresh — and adapt accordingly
2. **Scan** existing files (README, CLAUDE.md, package manifests, git history) and summarize what it found
3. **Ask** which type of project this is: new from scratch, inherited/unfinished, or maintenance on a live system
4. **Collect** configuration in a single exchange: tests required, CI/CD platform, cloud provider, issue tracker
5. **Present a plan** for your approval before creating or modifying anything
6. **Generate** living context docs in `.claude/docs/` (stack, architecture, code standards, backlog index) and append a `## dev-team-agents` section to `CLAUDE.md`
7. **Confirm** what was configured and point you to the relevant workflow guide

The full setup typically takes 5–10 minutes. Re-running on an existing project triggers refresh mode — reads git history since the last run and patches only the affected docs.

---

## Slash Commands

After installation, 22 slash commands are available under the `/devteam:` namespace. Each command spawns the appropriate agents and scopes work to the current git branch or worktree.

| Command | What it does |
|---------|-------------|
| `/devteam:plan` | Planning — software-architect + product-analyst + database-specialist (+ backend/frontend/devops when relevant) |
| `/devteam:backend` | Backend implementation — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Frontend implementation — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Mobile implementation — mobile-developer + ui-ux-designer (when relevant) |
| `/devteam:fullstack` | Full-stack implementation — backend + frontend teams in parallel |
| `/devteam:design` | UI/UX design — ui-ux-designer |
| `/devteam:fix` | Bug fix — relevant developer(s) → test-specialist |
| `/devteam:refactor` | Refactoring — software-architect plans, then developer(s) execute |
| `/devteam:architect` | Architecture decisions and ADRs — software-architect |
| `/devteam:review` | Code review — code-reviewer + software-architect + security-specialist |
| `/devteam:qa` | Quality assurance — qa-specialist |
| `/devteam:security` | Security audit — security-specialist + software-architect |
| `/devteam:dba` | Database work — database-specialist + software-architect |
| `/devteam:devops` | Infrastructure / CI/CD — devops-specialist |
| `/devteam:tester` | Tests only — backend-test-specialist + frontend-test-specialist |
| `/devteam:docs` | Documentation — technical-writer |
| `/devteam:pr` | Pull request — drafts title + description, asks for confirmation before creating |
| `/devteam:commit` | Commit — reads staged changes, groups by layer, writes and runs commits |
| `/devteam:learn` | Knowledge capture — consolidates session decisions, patterns, and discoveries into docs, wiki, and ADRs |
| `/devteam:workflow-new` | Full new-project workflow |
| `/devteam:workflow-maintenance` | Maintenance / feature evolution workflow |
| `/devteam:workflow-bugfix` | Full bug-fix workflow |
| `/devteam:workflow-inherited` | Inherited project onboarding workflow |
| `/devteam:workflow-security-patch` | Security patch workflow |

**Usage examples:**

```
/devteam:plan add an export-to-PDF feature for the fueling report
/devteam:backend implement the PDF export endpoint
/devteam:review
/devteam:pr draft
```

---

## How to Use Agents

Agents are invoked by naming the role in your message to Claude:

```
"As the product-analyst, analyze this PRD: [document]"
"As the software-architect, define the architecture for this project."
"As the backend-developer, implement [task]"
"As the code-reviewer, review the changes in [files]."
```

This works in the Claude Code CLI (`claude`), desktop app, web app at [claude.ai/code](https://claude.ai/code), and IDE extensions (VS Code, JetBrains).

**Every agent presents a plan for approval before executing anything.** You review, adjust, and approve — then execution begins.

---

## Workflows

| Workflow | Command | Use when |
|----------|---------|----------|
| New project | `/devteam:workflow-new` | Starting from scratch |
| Inherited project | `/devteam:workflow-inherited` | Taking over unfinished work |
| Maintenance | `/devteam:workflow-maintenance` | Live project, ongoing tasks |
| Bug fix | `/devteam:workflow-bugfix` | Isolated bug |
| Security patch | `/devteam:workflow-security-patch` | Security vulnerability |
| Refactor | `/devteam:refactor` | Planned code restructuring |
| Code review | `/devteam:review` | PR review before merge |

Full workflow step-by-step guides live in the [`workflows/`](workflows/) directory.

---

## Committing the Installation

Because `install.sh` downloads a tarball (not a git clone), `.claude/dev-team-agents/` has no nested `.git` folder. **Commit it directly** so your whole team gets the agents on `git pull`:

```bash
git add .claude/dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

---

## Worktree Isolation

All coding agents ask once before editing any file:

> "Do you want this task isolated in a git worktree? [y/N]"

The answer is shared across all agents in the same task via `.claude/.worktree-session` — multi-agent workflows ask exactly once. On "yes", the agent creates `.worktrees/<ctx>/<title>/` and all work happens inside it. On "no", agents work on the current branch.

---

## Agent Memory

Agents start each session with no memory of previous ones. Three mechanisms minimize context loss:

- **Session summary** — at the end of any session where files changed, agents write an entry to `.claude/user-data/session-summary.md`. A `Stop` hook enforces this automatically.
- **ADRs** — significant, hard-to-reverse decisions are recorded as Architecture Decision Records in `.claude/docs/development/adrs/`. Create one with: `bash .claude/dev-team-agents/scripts/new-adr.sh "title"`
- **Project context skill** — defines the context-loading order every agent follows at startup, including the session summary and ADR index.

---

## Coexistence & Customization

Dev Team Agents is a **base layer**. Your project's own conventions always take precedence: `CLAUDE.md` → `AGENTS.md` → `.agents/<agent-name>.md`. If your project says use tabs, agents use tabs.

Do **not** modify files inside `.claude/dev-team-agents/` — they are overwritten on update. Override at the project level instead:

```bash
.agents/backend-developer.md          # per-agent override
CLAUDE.md                             # project-wide rules for all agents
.claude/docs/development/code-standards.md  # code standards used by reviewers
```

---

## Troubleshooting

**Agents are not recognized by Claude** — verify the symlink exists: `ls .claude/agents/dev-team/`. If missing, re-run the installer from your project root.

**Skills are not loaded** — check that `.claude/skills/` contains symlinks. Re-run the installer to restore broken links.

**Windows: the whole dev-team is missing (no `/devteam:*`, no agents, no skills)** — on Windows without Developer Mode, git/MSYS writes the `.claude/` links as plain ~62-byte text files instead of symlinks. `git-bash`'s `ls -la` still shows them as `lrwxrwxrwx`, but Claude Code sees files, so nothing loads. Confirm with `test -L .claude/commands/devteam && echo link || echo broken`. Fix it by running `bash .claude/dev-team-agents/scripts/fix-symlinks.sh` — it repairs automatically when it can, and otherwise prints three options: (1) enable **Developer Mode** (Settings → System → For developers — recommended, no admin), (2) run `git config core.symlinks true && git checkout -- .claude` once in an **elevated PowerShell**, or (3) run **Claude Code as administrator** (fully close it first, including the tray icon). Restart Claude Code after repairing so it re-indexes the dev-team.

**Update check hook fires on every tool call** — check that `.claude/user-data/.last-update-check` is a writable file (not a directory) and that `scripts/hooks/pre-tool-use/01-check-updates.sh` is executable.

**`setup-assistant` ran but the `## dev-team-agents` section is missing from CLAUDE.md** — tell Claude: `"As the setup-assistant, the dev-team-agents section is missing from CLAUDE.md — please add it."`

**An agent executed without showing a plan first** — check your project CLAUDE.md for any instruction that conflicts with plan mode.

---

## Anonymous Telemetry

dev-team-agents collects **anonymous, aggregate usage data** to help us understand which agents and commands are most valuable.

**What is collected:** agent/command names, install and update events, session counts, OS family, and installed version. No code, file paths, project names, or personal data is ever collected.

**Opt out at any time** by editing `.claude/user-data/preferences.json`:

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
