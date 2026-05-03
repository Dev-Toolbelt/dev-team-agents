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
| `ui-ux-designer` | Design system, visual consistency, UX (dual mode) | DESIGN + DEVELOPMENT | Sonnet |
| `database-specialist` | Schema design, query optimization, DB selection | DEVELOPMENT | Sonnet |
| `devops-specialist` | Docker, CI/CD, VPS, cloud deployment | DEVELOPMENT | Sonnet |
| `backend-test-specialist` | Backend test coverage (conditional) | DEVELOPMENT | Sonnet |
| `frontend-test-specialist` | Frontend test coverage (conditional) | DEVELOPMENT | Sonnet |
| `code-reviewer` | Code quality, patterns, linting, bugs | QUALITY GATE | Sonnet |
| `security-specialist` | OWASP, LGPD/GDPR, dependency CVEs | QUALITY GATE | Opus |
| `qa-specialist` | Behavioral validation, regression risk | QUALITY GATE | Sonnet |
| `technical-writer` | API docs, READMEs, runbooks, changelogs | SUPPORT | Haiku |
| `setup-assistant` | Project setup + version management | SETUP | Sonnet |

---

## Installation — Project Level

`dev-team-agents` installs **inside your project** under `.claude/`, not globally. This keeps each project's agent configuration self-contained and version-pinned.

### One-line install (latest version)

Run from your **project root**:

```bash
curl -sSL https://raw.githubusercontent.com/vaironaegos/dev-team-agents/main/scripts/install.sh | bash
```

### Install a specific version

```bash
curl -sSL https://raw.githubusercontent.com/vaironaegos/dev-team-agents/main/scripts/install.sh | bash -s v1.0.0
```

### Update to latest (after first install)

```bash
.claude/dev-team-agents/scripts/install.sh latest
```

### Pin to a specific version / downgrade

```bash
.claude/dev-team-agents/scripts/install.sh v1.0.0
```

After installation, `.claude/` will contain:

```
.claude/
├── dev-team-agents/   ← cloned repository (source of truth)
├── agents/
│   └── dev-team/      ← symlink → .claude/dev-team-agents/agents/
├── skills/
│   ├── project-context/   ← symlink → skill directory
│   ├── plan-mode/         ← symlink → skill directory
│   └── ...                ← one symlink per skill
└── settings.json      ← update-check hook configured automatically
```

---

## .gitignore Recommendation

You can choose to commit `.claude/dev-team-agents/` (version-locked, reproducible) or ignore it (always fetched fresh). The agents and skills symlinks should follow the same decision.

```gitignore
# Option A: ignore the installation (each developer installs locally)
.claude/dev-team-agents/
.claude/agents/dev-team/
.claude/skills/

# Option B: commit everything (version-locked in repo)
# (no entry needed — git will track it)
```

---

## Versioning

This repository uses **semantic versioning via git tags** (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Updates are released as tags — no auto-update on every commit
- A session-start hook checks for new tags daily (configured automatically by `scripts/install.sh`)
- You control when to update — the system only notifies, never auto-updates
- Downgrade to any version: `.claude/dev-team-agents/scripts/install.sh v1.0.0`

---

## Getting Started — Any Project

After installing, run the setup-assistant:

```
"Help me set up this project with dev-team-agents"
```

The `setup-assistant` will scan existing files, ask about the project type, configure `CLAUDE.md`, and create the `.claude/docs/` structure.

---

## How to Use Agents

Agents are invoked by role:

```
"As the product-analyst, analyze this PRD: [document]"
"As the software-architect, define the architecture for this project."
"As the backend-developer, implement [task from .claude/docs/backlog/sprint-01.md]"
"As the code-reviewer, review the changes in [files]."
```

Claude will automatically load the right agent based on the role you specify.

**Every agent presents a plan for approval before executing anything.** You review, adjust, and approve — then execution begins.

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

## `frontend-design` Skill (Auto-installed)

The `frontend-developer` and `ui-ux-designer` agents require the `frontend-design` skill. It provides component patterns, layout techniques, and visual design guidance.

**`scripts/install.sh` installs it automatically** by symlinking it from the Claude Code marketplace cache (no network call, no manual step). If the cache is not available on the machine, the installer will display a one-time manual step — run `/plugins → frontend-design → install` in Claude Code, then re-run the installer to pick it up.

---

## Repository Structure

```
dev-team-agents/
├── agents/          ← agent definitions (.md files)
├── skills/          ← modular skill knowledge
│   ├── shared/      ← used by multiple agents (project-context, plan-mode, adr, comments-policy, ...)
│   ├── architecture/
│   ├── testing/
│   ├── security/
│   ├── design/
│   ├── devops/      ← one skill per platform (docker, vps, ci/cd, aws, gcp, azure, cloudflare)
│   └── integrations/ ← platform/integration-specific reference skills (supabase, gotrue, jwt, kong, realtime, database-debug, pwa, offline-first)
├── workflows/       ← step-by-step workflow guides
├── templates/       ← document templates (plan, backlog, ADR, etc.)
├── scripts/         ← install.sh, check-updates.sh
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
