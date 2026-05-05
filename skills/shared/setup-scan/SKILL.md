---
name: setup-scan
description: Reference material for the setup-assistant's project scan phase. Contains scan commands, Project Docs Discovery table, skill availability checks, and issue tracker MCP configuration guide.
---

## Step 1 — Scan Commands

```bash
# Package files (infer stack)
ls package.json composer.json requirements.txt Gemfile go.mod Cargo.toml Dockerfile 2>/dev/null

# CI configs
ls .github/workflows/ Jenkinsfile .gitlab-ci.yml 2>/dev/null

# Git history and uncommitted state
git log --oneline -20
git status

# Installed version
cat .claude/user-data/.installed-version 2>/dev/null || echo "unknown"
```

Read: `README.md`, `CLAUDE.md`, `AGENTS.md`, `.claude/` directory structure.

Summarize findings (files + stack + commit history + installed version) before asking questions.

---

## Skill Availability Checks

Run when the project has UI or frontend work:

| Skill | Check | If missing |
|-------|-------|-----------|
| `frontend-design` | `test -d .claude/skills/frontend-design` | Open Claude Code → `/plugins` → search `frontend-design` → install → re-run installer |
| `web-design-guidelines` | `test -d .claude/skills/web-design-guidelines` | `npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines` → re-run installer |

Both `frontend-developer` and `ui-ux-designer` depend on these skills.

---

## Project Docs Discovery

Run before generating any `.claude/docs/` file:

```bash
# Root-level markdown (excluding already-read files)
find . -maxdepth 1 -name "*.md" ! -name "README.md" ! -name "CLAUDE.md" ! -name "AGENTS.md" | sort

# Documentation directories (up to 3 levels)
find . -maxdepth 3 \( -path "*/docs/*" -o -path "*/documentation/*" -o -path "*/doc/*" -o -path "*/wiki/*" \) -name "*.md" 2>/dev/null | sort

# OpenAPI / Swagger specs
find . -maxdepth 3 \( -name "openapi.yaml" -o -name "openapi.json" -o -name "swagger.yaml" -o -name "swagger.json" \) 2>/dev/null | sort

# Linting / convention configs
find . -maxdepth 2 \( -name ".eslintrc*" -o -name ".prettierrc*" -o -name "phpcs.xml" -o -name "pyproject.toml" -o -name ".rubocop.yml" -o -name "golangci.yml" -o -name ".stylelintrc*" \) 2>/dev/null | sort
```

| Found File Pattern | Feeds Into |
|-------------------|-----------|
| `ARCHITECTURE.md`, `docs/architecture*` | `architecture.md` → System Type, Layers, Module Map |
| `CONTRIBUTING.md`, `docs/contributing*`, `docs/development*` | `code-standards.md` → Naming Conventions, Patterns |
| `docs/api*`, `API.md`, `openapi.yaml`, `swagger.yaml` | `architecture.md` → API Contracts |
| `docs/stack*`, `docs/tech*`, `DEVELOPMENT.md`, `TECH*.md` | `tech-stack.md` → Tech Stack table, Dev Setup |
| `.eslintrc*`, `.prettierrc*`, `phpcs.xml`, `pyproject.toml`, etc. | `code-standards.md` → Detected Config |
| `CHANGELOG.md`, `docs/changelog*` | `project.md` → Active Areas |
| `docs/design*`, `DESIGN*.md` | `design/design-system.md` → UI conventions |

Content is synthesized (not duplicated) into the target doc. Use `<!-- TODO: <agent> to fill -->` only for sections with no data yet.

---

## Issue Tracker MCP Configuration

| Tracker | MCP | What's needed |
|---------|-----|---------------|
| GitHub Projects | `github` | Personal access token (read:project scope) |
| GitLab Issues | `gitlab` | Personal access token (read_api scope) |
| Jira | `atlassian` | API token + workspace URL |
| Linear | `linear` | API key (read-only) |
| ClickUp | `clickup` | Personal API token |
| Others | none required | Agents read from user-provided markdown exports |

**Supported trackers:** GitHub Projects, GitLab Issues, Jira, Linear, ClickUp, Trello, Asana, Monday.com, Notion, Azure DevOps Boards, Shortcut.

Configure tokens in Claude Code MCP settings (`~/.claude/settings.json` or via `/mcp`). Never store credentials in project files. Agents read tasks but only write with explicit user consent.
