# dev-team-agents

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

## Installation

```bash
git clone https://github.com/YOUR_ORG/dev-team-agents.git ~/.claude/dev-team-agents
~/.claude/dev-team-agents/install.sh
```

To install a specific version:
```bash
~/.claude/dev-team-agents/install.sh v1.0.0
```

To update to latest:
```bash
~/.claude/dev-team-agents/install.sh latest
```

---

## Versioning

This repository uses **semantic versioning via git tags** (`v1.0.0`, `v1.1.0`, `v2.0.0`).

- Updates are released as tags — no auto-update on every commit
- The `setup-assistant` configures a session-start hook that checks for new tags daily
- You control when to update — the system only notifies, never auto-updates
- Downgrade to any version: `install.sh v1.0.0`

---

## Getting Started — Any Project

```
"Help me set up this project with dev-team-agents"
```

The `setup-assistant` will ask about the project type, configure `CLAUDE.md`, create the `.claude/docs/` structure, and set up the update check hook.

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

---

## Workflows

| Workflow | File | Use when |
|----------|------|----------|
| New project | `workflows/new-project.md` | Starting from scratch |
| Inherited project | `workflows/inherited-project.md` | Taking over unfinished work |
| Maintenance | `workflows/maintenance.md` | Live project, ongoing tasks |
| Bug fix | `workflows/bug-fix.md` | Isolated bug |
| Security patch | `workflows/security-patch.md` | Security vulnerability |

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

Do **not** modify files inside `~/.claude/dev-team-agents/` — they will be overwritten on update.

Instead, override at the project level:

```bash
# Project-level agent override (takes precedence over base agent)
.agents/backend-developer.md

# Project-level rules for all agents
.claude/CLAUDE.md  # add a ## Project Rules section

# Project-specific code standards (used by code-reviewer and developers)
.claude/docs/development/code-standards.md
```

---

## Optional: `anthropic-skills:frontend-design`

The `frontend-developer` and `ui-ux-designer` agents work best with the `anthropic-skills:frontend-design` skill installed. It provides additional UI component patterns and layout techniques.

Install the `anthropic-skills` plugin to enable it.

---

## Repository Structure

```
dev-team-agents/
├── agents/          ← agent definitions (.md files)
├── skills/          ← modular skill knowledge
│   ├── shared/      ← used by multiple agents
│   ├── architecture/
│   ├── testing/
│   ├── security/
│   ├── design/
│   └── devops/      ← one skill per platform
├── workflows/       ← step-by-step workflow guides
├── scripts/         ← install and update scripts
└── templates/       ← document templates
```

---

## Contributing

1. Fork the repository
2. Create a branch: `fix/agent-name-improvement` or `feat/new-skill`
3. Follow the skill/agent authoring standards in `docs/authoring.md`
4. Open a PR with a clear description of what changed and why
5. Releases are tagged by maintainers — your change ships in the next version

---

## License

MIT
