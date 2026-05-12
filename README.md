# dev-team-agents

🇧🇷 [Veja a versão em Português do Brasil](README.pt-BR.md)

A global team of specialized Claude Code agents and skills for software development. Stack-agnostic, project-aware, and collaboratively maintained.

---

## What This Is

A set of Claude Code agents and skills that form a complete software development team. Each agent has a defined role, expertise, and workflow integration. They coexist with your project's own rules — project conventions always win.

**Team:**

| Agent | Role | Phase | Model |
|-------|------|-------|-------|
| `product-analyst` | Closes scope, generates backlog with estimates | DISCOVERY | Opus |
| `software-architect` | Architecture decisions, tech stack, code standards | DISCOVERY + QUALITY GATE | Opus |
| `backend-developer` | Server-side implementation (API + monolith) | DEVELOPMENT | Sonnet |
| `frontend-developer` | Client-side implementation (SPA + templates) | DEVELOPMENT | Sonnet |
| `mobile-developer` | Mobile implementation (React Native, Expo, Flutter, native iOS/Android) | DEVELOPMENT | Sonnet |
| `ui-ux-designer` | Design system, visual consistency, UX (dual mode) | DESIGN + DEVELOPMENT | Sonnet |
| `database-specialist` | Schema design, query optimization, DB selection | DEVELOPMENT | Sonnet |
| `devops-specialist` | Docker, CI/CD, VPS, cloud deployment | DEVELOPMENT | Sonnet |
| `backend-test-specialist` | Backend test coverage (conditional) | DEVELOPMENT | Sonnet |
| `frontend-test-specialist` | Frontend test coverage (conditional) | DEVELOPMENT | Sonnet |
| `code-reviewer` | Routes to specialist reviewer based on diff (backend / frontend / both) | QUALITY GATE | Sonnet |
| `backend-reviewer` | Backend review: API contracts, transactions, N+1, auth, jobs, SOLID | QUALITY GATE | Sonnet |
| `frontend-reviewer` | Frontend review: components, re-renders, a11y, bundle, state, XSS | QUALITY GATE | Sonnet |
| `security-specialist` | OWASP, LGPD/GDPR, dependency CVEs | QUALITY GATE | Opus |
| `qa-specialist` | Behavioral validation, regression risk | QUALITY GATE | Sonnet |
| `technical-writer` | API docs, READMEs, runbooks, changelogs | SUPPORT | Haiku |
| `setup-assistant` | Project setup + version management | SETUP | Sonnet |

---

## Prerequisites

- **Claude Code** — CLI, desktop app, or IDE extension. Install at [claude.ai/code](https://claude.ai/code) if not already available.
- **Git** — the installer uses `git rev-parse` to verify the project root.
- **curl** or **wget** — used to download the release tarball. One of the two is available on most systems by default.

No other global dependencies required.

---

## Installation — Project Level

`dev-team-agents` installs **inside your project** under `.claude/`, not globally. This keeps each project's agent configuration self-contained and version-pinned.

### One-line install (latest version)

Run from your **project root**:

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash
```

### Install a specific version

```bash
curl -sSL https://raw.githubusercontent.com/Dev-Toolbelt/dev-team-agents/main/scripts/install.sh | bash -s v1.0.0
```

### Update to latest (after first install)

```bash
.claude/dev-team-agents/scripts/update.sh
```

### Pin to a specific version / downgrade

```bash
.claude/dev-team-agents/scripts/update.sh v1.0.0
```

### Language preference

During installation, the installer asks which language agents should use when conversing with you. Documents and technical output (ADRs, changelogs, code comments) always remain in English. Plans presented for your approval and all direct responses use the configured language.

You can update this at any time by editing `.claude/user-data/preferences.json`:

```json
{ "language": "pt-BR" }
```

Common values: `en` · `pt-BR` · `es` · `fr` · `de` · `ja` · `zh-CN`

### Enable automatic updates (opt-in)

```bash
.claude/dev-team-agents/scripts/update.sh --enable-auto
```

When enabled, the daily update check will apply new versions automatically instead of just showing a notification. You can also set `auto_update: true` in `.claude/user-data/preferences.json`. Disable at any time:

```bash
.claude/dev-team-agents/scripts/update.sh --disable-auto
```

### Notification system

Agents and hooks emit notifications in the DEV TEAM AGENTS format throughout your sessions:

- **ℹ️ info** — rotating tips and best practices (one per session)
- **⚠️ warning** — context window approaching limit, stale docs, missing config
- **🚨 critical** — context window at limit, broken installation

Notification behavior is configurable in `preferences.json`:

```json
{
  "context_window_percent_warning": 55,
  "context_window_percent_limit": 60,
  "suppress_notifications": false,
  "transcript_multiplier": 1.8,
  "model_max_tokens": 200000
}
```

Set `suppress_notifications` to `true` to silence all notifications, or to `["info"]` to suppress only a specific type.

Context window warnings use transcript token counts (from the Stop hook payload) multiplied by `transcript_multiplier` to estimate the full context size. Adjust `transcript_multiplier` up if warnings fire too early, or down if they fire too late for your typical session. Set `model_max_tokens` to match your model's actual context window if you switch to a non-200k model.

After installation, `.claude/` will contain:

```
.claude/
├── dev-team-agents/   ← extracted from tarball (no .git folder — safe to commit)
├── user-data/         ← user state and config (preserved across updates)
│   ├── preferences.json    ← language, thresholds, notification settings (gitignored)
│   ├── graphify.json       ← created by Graphify setup (if enabled) — commit this
│   ├── session-summary.md  ← gitignored (entire user-data/ dir is ignored by installer)
│   ├── .installed-version  ← gitignored
│   └── .last-update-check  ← gitignored
├── agents/
│   └── dev-team/      ← symlink → .claude/dev-team-agents/agents/
├── skills/
│   ├── project-context/   ← symlink → skill directory
│   ├── plan-mode/         ← symlink → skill directory
│   └── ...                ← one symlink per skill
├── commands/
│   └── devteam/       ← symlink → .claude/dev-team-agents/commands/ (invoke as /devteam:plan etc.)
└── settings.json      ← hook dispatchers configured automatically (single entry per event type)
```

---

## Committing to Your Project

Because `install.sh` downloads a tarball (not a git clone), `.claude/dev-team-agents/` contains no nested `.git` folder. **Commit it directly** — your whole team gets the agents and skills on `git pull`, no extra setup step needed.

```bash
git add .claude/dev-team-agents/ .claude/agents/ .claude/skills/ .claude/commands/ .claude/settings.json
git commit -m "chore: add dev-team-agents"
```

If you prefer each developer to install locally instead (e.g. for a personal/experimental setup), add the following to `.gitignore`:

```gitignore
# Optional: ignore the installation (each developer installs locally)
.claude/dev-team-agents/
.claude/agents/dev-team/
.claude/skills/
.claude/commands/devteam/

# Always ignore the ephemeral worktree session file
.claude/.worktree-session
```

---

## Slash Commands

After installation, 22 slash commands are available under the `/devteam:` namespace. Each command spawns the appropriate agents via the Task tool and automatically scopes its work to the current git branch or worktree. All devteam commands are grouped under `.claude/commands/devteam/` — separate from any project-specific commands.

| Command | What it does |
|---------|-------------|
| `/devteam:plan` | Planning phase — software-architect + product-analyst + database-specialist (+ backend/frontend/devops when relevant) |
| `/devteam:backend` | Backend implementation — backend-developer + database-specialist → backend-test-specialist |
| `/devteam:frontend` | Frontend implementation — frontend-developer + ui-ux-designer → frontend-test-specialist |
| `/devteam:mobile` | Mobile implementation — mobile-developer + ui-ux-designer (when relevant) |
| `/devteam:fullstack` | Full-stack implementation — backend + frontend teams in parallel |
| `/devteam:design` | UI/UX design — ui-ux-designer |
| `/devteam:fix` | Bug fix — relevant developer(s) → test-specialist |
| `/devteam:refactor` | Refactoring — software-architect plans, then developer(s) execute |
| `/devteam:architect` | Architecture decisions, ADRs, trade-offs — software-architect only |
| `/devteam:review` | Code review — code-reviewer + software-architect + security-specialist |
| `/devteam:qa` | Quality assurance — qa-specialist |
| `/devteam:security` | Security audit — security-specialist + software-architect |
| `/devteam:dba` | Database work — database-specialist + software-architect |
| `/devteam:devops` | Infrastructure / CI/CD — devops-specialist |
| `/devteam:tester` | Tests only — backend-test-specialist + frontend-test-specialist |
| `/devteam:docs` | Documentation — technical-writer |
| `/devteam:pr` | Pull request — drafts title + description, asks for confirmation before creating |
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
/devteam:pr review base staging
```

All commands accept optional `$ARGUMENTS` to narrow or expand the scope.

---

## Quick Try

If you want to test an agent before running the full setup, you can invoke any agent directly after installation:

```
"As the code-reviewer, review the file src/api/users.ts and flag any issues."
"As the software-architect, explain the high-level architecture of this codebase."
"As the backend-developer, what would be the cleanest way to add pagination to this endpoint?"
```

No additional configuration is required — agents read your project files and apply their role. The full `setup-assistant` flow is recommended for sustained team use, but there is no mandatory setup before your first agent invocation.

---

## Versioning

This repository uses **semantic versioning via git tags** (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Updates are released as tags — no auto-update on every commit
- A hook checks for new versions daily via the GitHub API (configured automatically by `scripts/install.sh`)
- By default the system only notifies — run `update.sh` to apply, or enable auto-updates with `update.sh --enable-auto`
- Downgrade to any version: `.claude/dev-team-agents/scripts/update.sh v1.0.0`

---

## Getting Started — Any Project

After installing, start the setup flow by telling Claude:

```
"Help me set up this project with dev-team-agents"
```

The `setup-assistant` will:

1. **Detect** whether this is a first-time setup or a refresh of an existing setup — and adapt accordingly
2. **Scan** existing files — README, CLAUDE.md, package manifests, git history — and summarize what it found, including the installed version
3. **Ask** which type of project this is: new from scratch, inherited/unfinished, or maintenance on a live system
4. **Collect** configuration in a single exchange: tests required, CI/CD platform, cloud provider, issue tracker
5. **Present a plan** for your approval before creating or modifying anything
6. **Generate** living context docs in `.claude/docs/` populated with real project data (stack, architecture, code standards, backlog index) and append a `## dev-team-agents` section to `CLAUDE.md`
7. **Confirm** what was configured and point you to the relevant workflow guide

The full setup typically takes 5–10 minutes.

**Re-running setup-assistant** on an existing project triggers refresh mode: it reads git history since the last run, identifies what changed, and patches only the affected docs — no full Q&A repeated.

---

## Design Skills (Required for UI work)

The `frontend-developer` and `ui-ux-designer` agents require two design skills that are bundled directly in this repository:

| Skill | Path | Purpose |
|-------|------|---------|
| `frontend-design` | `skills/design/frontend-design/` | Component patterns, layout techniques, and visual design guidance |
| `web-design-guidelines` | `skills/design/web-design-guidelines/` | Audits UI code against Vercel's Web Interface Guidelines — design, accessibility, and UX coverage |

Both skills are linked automatically by `scripts/install.sh` along with all other skills — no extra steps required. To update them, edit the `SKILL.md` files directly in this repository and re-run the installer.

---

## How to Use Agents

Agents are invoked by naming the role in your message to Claude:

```
"As the product-analyst, analyze this PRD: [document]"
"As the software-architect, define the architecture for this project."
"As the backend-developer, implement [task from .claude/docs/backlog/sprint-01.md]"
"As the code-reviewer, review the changes in [files]."
```

This works in the Claude Code CLI (`claude`), the desktop app, the web app at [claude.ai/code](https://claude.ai/code), and IDE extensions (VS Code, JetBrains).

**Every agent presents a plan for approval before executing anything.** You review, adjust, and approve — then execution begins. No agent writes files or runs commands until you confirm.

If an agent is not recognized, check that `.claude/agents/dev-team/` exists and contains the agent `.md` files. Re-run the installer if the symlink is missing or broken.

---

## Worktree Isolation

All coding agents (`backend-developer`, `frontend-developer`, `mobile-developer`, `database-specialist`, `devops-specialist`, `ui-ux-designer`, `backend-test-specialist`, `frontend-test-specialist`) ask **once** before editing any file:

> "Do you want this task isolated in a git worktree? [y/N]"

**The answer is shared across all agents in the same task** via `.claude/.worktree-session`. If a workflow involves multiple agents (e.g. backend + frontend + tests), only the first agent asks — the rest read the stored decision silently.

| Answer | Behavior |
|--------|----------|
| Yes | Agent asks for a base branch (default: `main`), creates `.worktrees/<ctx>/<title>/`, and all subsequent work happens inside it |
| No | All agents work on the current branch |

The session file is removed automatically when the worktree is cleaned up (Step 8 of the worktree skill). Add it to `.gitignore` — the worktree skill does this automatically on cleanup:

```gitignore
.claude/.worktree-session
```

---

## Agent Memory System

Agents start each session with no memory of previous ones. Three mechanisms work together to minimize context loss:

### 1 — Session Summary (automatic enforcement)

At the end of any session where files were changed, agents write an entry to `.claude/user-data/session-summary.md`:

```
## YYYY-MM-DD | [brief task title]
**Done**: what was implemented or changed
**Decisions**: key choices made and why
**Next**: what remains or is recommended next
```

A `Stop` dispatcher (`scripts/hooks/stop.sh`) is registered automatically by `install.sh`. It runs all sub-scripts in `scripts/hooks/stop/` in order — including session-summary enforcement, orphan skill scan, and agent frontmatter lint. Sub-scripts are added to that folder (e.g. by `graphify-setup`) without touching `settings.json`.

At the start of every session, agents read the most recent entry from this file before acting.

### 2 — Architecture Decision Records (ADRs)

Significant, hard-to-reverse decisions are recorded as ADRs in `.claude/docs/development/adrs/`. To create one:

```bash
bash .claude/dev-team-agents/scripts/new-adr.sh "title of the decision"
```

The script auto-numbers the file and fills a MADR template. Agents read relevant ADRs at startup to avoid contradicting past decisions.

### 3 — Project Context Skill

`skills/shared/project-context` defines the context-loading order every agent follows at startup. It includes the session summary and ADR index, ensuring a consistent baseline across all agents and sessions.

The installer automatically ignores the entire `.claude/user-data/` directory, with one exception: `graphify.json` is explicitly kept (`!.claude/user-data/graphify.json`) because it contains project-level Graphify config that the whole team should share. The installer also adds `.claude/.worktree-session` to `.gitignore`.

---

## Language

**All generated documents are in English by default.** To request a specific document in another language, say so explicitly for that document. The default always reverts to English.

---

## Workflows

| Workflow | File | Use when |
|----------|------|----------|
| New project | `workflows/new-project.md` | Starting from scratch |
| Inherited project | `workflows/inherited-project.md` | Taking over unfinished work |
| Maintenance | `workflows/maintenance.md` | Live project, ongoing tasks |
| Bug fix | `workflows/bug-fix.md` | Isolated bug |
| Security patch | `workflows/security-patch.md` | Security vulnerability |
| Refactor | `workflows/refactor.md` | Planned code restructuring |
| Code review | `workflows/review.md` | PR review before merge |

### A — New Project from Scratch

```
  [Input: requirements document]
               │
               ▼
  ┌────────────────────────────┐
  │         DISCOVERY          │
  │                            │
  │  product-analyst           │
  │    · closes scope          │
  │    · generates backlog     │
  │    · sprint estimates      │
  │                            │
  │  software-architect        │
  │    · architecture.md       │
  │    · tech-stack.md         │
  │    · code-standards.md     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    DESIGN  (optional)      │
  │                            │
  │  ui-ux-designer            │
  │    · design-system.md      │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │        DEVELOPMENT         │
  │                            │
  │  devops-specialist         │
  │    · dev environment       │
  │  backend-developer         │
  │    · implements tasks      │
  │  frontend-developer        │
  │    · implements UI         │
  │  database-specialist       │
  │    · schema + migrations   │
  │  [test-specialists]        │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       QUALITY GATE         │
  │                            │
  │  code-reviewer             │
  │  security-specialist       │
  │  qa-specialist             │
  │  software-architect        │
  │    · conformance check     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │           SHIP             │
  │                            │
  │  technical-writer          │
  │    · changelog + docs      │
  └────────────────────────────┘
```

### B — Inherited / Unfinished Project

```
  [Input: codebase + client task list]
               │
               ▼
  ┌────────────────────────────┐
  │          AUDIT             │
  │                            │
  │  software-architect        │
  │    · architecture audit    │
  │    · tech debt mapping     │
  │  database-specialist       │
  │    · schema audit          │
  │  security-specialist       │
  │    · critical findings     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │      CLIENT SCOPING        │
  │                            │
  │  product-analyst           │
  │    · clarification Q&A     │
  │    · iterate until scope   │
  │      is 100% closed        │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       GAP ANALYSIS         │
  │                            │
  │  product-analyst           │
  │    · full backlog          │
  │    · delivery forecast     │
  │  software-architect        │
  │    · refactor vs rewrite   │
  └─────────────┬──────────────┘
                │
                ▼
     DEVELOPMENT + QUALITY GATE
        (same as Workflow A)
```

### C — Maintenance / Live Project

```
  [Input: ticket from board]
               │
               ▼
  ┌────────────────────────────┐
  │       TASK PICKUP          │
  │                            │
  │  software-architect        │
  │    · loads project context │
  │    · blast radius analysis │
  │    · flags legacy risks    │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    SCOPE VALIDATION        │
  │       (recommended)        │
  │                            │
  │  product-analyst           │
  │    · validates acceptance  │
  │      criteria              │
  │    · resolves ambiguities  │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       DEVELOPMENT          │
  │                            │
  │  backend-developer         │
  │  frontend-developer        │
  │    · minimal scope         │
  │    · no silent refactors   │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │  QUALITY GATE              │
  │  (regression priority)     │
  │                            │
  │  code-reviewer             │
  │  qa-specialist             │
  │  [security-specialist]     │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │       PR + DEPLOY          │
  │                            │
  │  technical-writer          │
  │  devops-specialist         │
  └────────────────────────────┘
```

### Bug Fix

```
  [Input: bug report / stack trace]
               │
               ▼
  ┌────────────────────────────┐
  │        DIAGNOSIS           │
  │                            │
  │  software-architect        │
  │    · root cause analysis   │
  │    · diagnosis report      │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │           FIX              │
  │                            │
  │  backend-developer  or     │
  │  frontend-developer        │
  │    · fix root cause only   │
  │    · no extra changes      │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    REGRESSION CHECK        │
  │                            │
  │  qa-specialist             │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │      CODE REVIEW           │
  │                            │
  │  code-reviewer             │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │   REGRESSION TEST          │
  │    (if required)           │
  │                            │
  │  backend-test-specialist   │
  │  frontend-test-specialist  │
  └────────────────────────────┘
```

### Security Patch

```
  [Input: CVE / security finding]
               │
               ▼
  ┌────────────────────────────┐
  │     ASSESS SEVERITY        │
  │                            │
  │  security-specialist       │
  │    · CVSS score            │
  │    · attack surface        │
  │    · exploitation evidence │
  └─────────────┬──────────────┘
                │
        ┌───────┴────────┐
        │   CRITICAL?    │
        └──┬─────────────┘
      yes  │          no │
       ▼                 │
  escalate +             │
  notify                 │
  stakeholders           │
           └─────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │          PATCH             │
  │                            │
  │  backend-developer         │
  │    · minimal scope fix     │
  │  devops-specialist         │
  │    · dependency upgrade    │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    SECURITY REVIEW         │
  │                            │
  │  security-specialist       │
  │    · verify patch          │
  │    · no new attack vectors │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │    CODE REVIEW + QA        │
  │                            │
  │  code-reviewer             │
  │  qa-specialist             │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │         DEPLOY             │
  │                            │
  │  devops-specialist         │
  │    · fastest safe strategy │
  └─────────────┬──────────────┘
                │
                ▼
  ┌────────────────────────────┐
  │      POST-INCIDENT         │
  │                            │
  │  technical-writer          │
  │    · security-incidents.md │
  └────────────────────────────┘
```

---

## Coexistence — Project Rules Override Base Standards

These agents are a **base layer**. The project's own conventions always take precedence:

- `CLAUDE.md` → highest priority — Claude-specific project rules
- `AGENTS.md` → agent-specific project overrides
- `README.md` → project setup and conventions
- `.agents/<agent-name>.md` → per-project agent override

**If your project says use tabs, agents use tabs. If your project defines a specific pattern, agents follow it. The base standards only fill the gaps.**

---

## Customizing for a Project

Do **not** modify files inside `.claude/dev-team-agents/` — they will be overwritten on update.

Instead, override at the project level:

```bash
# Project-level agent override (takes precedence over base agent)
.agents/backend-developer.md

# Project-level rules for all agents
CLAUDE.md  # add a ## Project Rules section

# Project-specific code standards (used by code-reviewer and developers)
.claude/docs/development/code-standards.md
```

---

## Troubleshooting

**Agents are not recognized by Claude**
Verify the symlink exists: `ls .claude/agents/dev-team/`. If the directory is missing, re-run the installer from your project root.

**Skills are not loaded**
Check that `.claude/skills/` contains symlinks pointing to each skill directory. Re-run the installer to restore broken links: `.claude/dev-team-agents/scripts/install.sh latest`.

**Update check hook fires on every tool call**
The hook sub-script reads a timestamp file and only outputs a message once per day. If it prints every time, check that `.claude/user-data/.last-update-check` is a writable file (not a directory) and that `scripts/hooks/pre-tool-use/01-check-updates.sh` is executable.

**`setup-assistant` ran but the `## dev-team-agents` section is missing from CLAUDE.md**
The assistant appends to an existing file — it never replaces content. Search for `## dev-team-agents` in your CLAUDE.md. If it is absent, tell Claude: `"As the setup-assistant, the dev-team-agents section is missing from CLAUDE.md — please add it."`

**An agent executed without showing a plan first**
Every agent is configured to present a plan before acting. If this did not happen, your project CLAUDE.md may contain a rule that conflicts with the plan requirement. Check for any instruction that disables plan mode.

---

## Repository Structure

```
dev-team-agents/
├── agents/          ← agent definitions (.md files)
├── skills/          ← modular skill knowledge
│   ├── shared/      ← 25 skills — project-context, docs-sync, plan-mode, adr, comments-policy, conventional-commits, worktree, token-efficiency, current-context, spawn-classifier, reviewer-base, reviewer-mindset, diataxis-framework, discovery-mode, git-workflow, incident-response, and more
│   ├── architecture/ ← 24 skills — api-design, api-versioning, async-jobs, caching, design-patterns, event-driven, feature-flags, graphql, i18n, monorepo-patterns, object-calisthenics, performance-budgets, rate-limiting, resilience, and more
│   ├── database/    ← 9 skills — postgres, mysql, mongodb, redis, sqlserver, cassandra, sqlite, db-comparison, migration-zero-downtime
│   ├── testing/     ← 6 skills — test-strategy, test-pyramid, contract-testing, mutation-testing, snapshot-testing, visual-regression
│   ├── security/    ← 8 skills — owasp-top-10, security-checklist, dependency-vulnerabilities, idor, iso27001-sgsi, sast-pipeline, secret-management, supply-chain
│   ├── design/      ← 3 skills — design-system-audit, frontend-design, web-design-guidelines
│   ├── devops/      ← 19 skills — docker-dev, docker-prod, vps-linux, cicd-base, cicd-github, cicd-gitlab, cicd-bitbucket, cicd-jenkins, aws, gcp, azure, cloudflare, iac-terraform, monitoring, sonarqube, sentry, vercel, ssh-remote-access, graphify-setup
│   ├── mobile/      ← 4 skills — react-native, flutter, ios-hig, material-design
│   ├── integrations/ ← 12 skills — supabase, gotrue, jwt, kong, realtime, database-debug, database-multitenancy, database-production, pwa, offline-first, jira, linear
│   └── ui-libraries/ ← 6 skills — shadcn, mui, antd, bootstrap, chakra-ui, jquery
├── workflows/       ← step-by-step workflow guides
├── templates/       ← document templates (plan, backlog, ADR, etc.)
├── scripts/         ← install.sh, update.sh, new-adr.sh, graphify-refresh.sh
│   └── hooks/       ← dispatchers + sub-scripts (pre-tool-use/, stop/)
└── CLAUDE.md        ← authoring conventions for this repo
```

---

## Contributing

1. Fork the repository
2. Create a branch: `fix/agent-name-improvement` or `feat/new-skill`
3. Follow the authoring standards in `CLAUDE.md`
4. Open a PR with a clear description of what changed and why
5. Releases are tagged by maintainers — your change ships in the next version

---

## License

MIT
