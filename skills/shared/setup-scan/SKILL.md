---
name: setup-scan
description: Setup-assistant scan — commands, discovery table, skill/MCP checks.
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
source .dev-team-agents/scripts/lib/state.sh 2>/dev/null
state_get installed_version .dev-team-agents/user-data/state.json 2>/dev/null || echo "unknown"
```

Read: `README.md`, `CLAUDE.md`, `AGENTS.md`, `.claude/` directory structure.

Summarize findings (files + stack + commit history + installed version) before asking questions.

---

## Skill Availability Checks

Run when the project has UI or frontend work:

| Skill | Check | If missing |
|-------|-------|-----------|
| `frontend-design` | `test -d .claude/skills/frontend-design` | **Claude Code:** `/plugins` → search `frontend-design` → install → re-run installer. Other CLIs: install the skill through that CLI's own mechanism, then re-run the installer |
| `web-design-guidelines` | `test -d .claude/skills/web-design-guidelines` | `npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines` → re-run installer |

Both `frontend-developer` and `ui-ux-designer` depend on these skills.

---

## Project Docs Discovery

Run before generating any `docs/` file:

```bash
# Root-level markdown (excluding already-read files)
find . -maxdepth 1 -name "*.md" ! -name "README.md" ! -name "CLAUDE.md" ! -name "AGENTS.md" | sort

# Documentation directories (up to 3 levels) — markdown and office formats
find . -maxdepth 3 \( -path "*/docs/*" -o -path "*/documentation/*" -o -path "*/doc/*" -o -path "*/wiki/*" \) \
  \( -name "*.md" -o -name "*.txt" -o -name "*.rst" -o -name "*.pdf" \
     -o -name "*.doc" -o -name "*.docx" -o -name "*.xls" -o -name "*.xlsx" \
     -o -name "*.csv" -o -name "*.yaml" -o -name "*.yml" \) 2>/dev/null | sort

# AI/agent config directories — may contain project instructions or conventions
find . -maxdepth 2 \( -path "./.cursor/*" -o -path "./.agents/*" -o -path "./.github/*" \) \
  -name "*.md" 2>/dev/null | sort
ls .cursor/rules/ .cursor/*.md .agents/*.md .github/CODEOWNERS .github/CONTRIBUTING.md \
  .github/pull_request_template.md 2>/dev/null || true

# OpenAPI / Swagger specs
find . -maxdepth 3 \( -name "openapi.yaml" -o -name "openapi.json" -o -name "swagger.yaml" -o -name "swagger.json" \) 2>/dev/null | sort

# Linting / convention configs
find . -maxdepth 2 \( -name ".eslintrc*" -o -name ".prettierrc*" -o -name "phpcs.xml" -o -name "pyproject.toml" -o -name ".rubocop.yml" -o -name "golangci.yml" -o -name ".stylelintrc*" \) 2>/dev/null | sort
```

| Found File Pattern | Feeds Into |
|-------------------|-----------|
| `ARCHITECTURE.md`, `docs/architecture*` | `architecture.md` → System Type, Layers, Module Map |
| `CONTRIBUTING.md`, `docs/contributing*`, `docs/development*` | `code-standards.md` → Naming Conventions, Patterns |
| `docs/api*`, `API.md`, `openapi.yaml`, `swagger.yaml` | the `api-contracts` doc (`project-context` § Doc Layout) — never `architecture.md` |
| `docs/stack*`, `docs/tech*`, `DEVELOPMENT.md`, `TECH*.md` | `tech-stack.md` → Tech Stack table, Dev Setup |
| `.eslintrc*`, `.prettierrc*`, `phpcs.xml`, `pyproject.toml`, etc. | `code-standards.md` → Detected Config |
| `CHANGELOG.md`, `docs/changelog*` | `project.md` → Active Areas |
| `docs/design*`, `DESIGN*.md` | `design/design-system.md` → UI conventions |
| `.cursor/rules/*`, `.cursor/*.md` | `code-standards.md` → Cursor AI conventions |
| `.agents/*.md` | `project.md` → Agent overrides in effect |
| `.github/CODEOWNERS`, `.github/CONTRIBUTING.md`, `.github/pull_request_template.md` | `code-standards.md` → Review process, PR standards |
| `docs/infra*`, `docs/devops*`, `docs/deploy*`, `*.tf`, `docker-compose*` | `docs/devops/` → Infrastructure and deployment docs |
| `docs/test*`, `docs/qa*`, `jest.config*`, `vitest.config*`, `playwright.config*` | `docs/tests/` → Test strategy and configuration |

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

Configure tokens in the active CLI's MCP settings — Claude Code: `~/.claude/settings.json` or `/mcp`; opencode: the `mcp` block of `opencode.json`; Codex CLI: its own MCP config. Never store credentials in project files. Agents read tasks but only write with explicit user consent.

---

## GitHub Repository Provisioning

Runs when the user picks **GitHub** (Issues or Projects) as the tracker or backlog location. The user is never told to create the repository themselves: setup does it, after consent. Skip every step already true and say so. Steps 1–4 change only local state (step 2 behind its Command Run Plan); steps 5–8 touch GitHub and each waits for its own `AskUserQuestion` answer — one answer never covers another step.

**Values.** Validate before use, re-asking on a mismatch and never normalizing silently: `owner` against `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`, `name` against `^[A-Za-z0-9._-]{1,100}$`. Quote every value in a shell command, end options with `--` where the tool supports it, and take a remote's slug from `gh repo view --json nameWithOwner`, never from parsing the URL.

| Step | Check | Action |
|---|---|---|
| 1. Git | `git rev-parse --is-inside-work-tree` | Not a repository → `git init` (the branch name follows `init.defaultBranch`; never rename it). Then re-run `skills/shared/client-briefing/SKILL.md` § Inputs "Kept out of git" on every private input present (the briefing form, the brand image), because that check was skipped while the folder was not a repository |
| 2. CLI | `gh --version` | Missing → `gh` is outside the helper-tool set, so list the install command for the OS (`brew install gh`, `winget install GitHub.cli`, or the distro package) in a Command Run Plan and run it after approval; an install that needs `sudo` pauses for the user. Still missing → report it and stop this section, setup continues |
| 3. Auth | `gh auth status` | Not signed in → interactive (browser sign-in): pause per `skills/shared/interaction-patterns/SKILL.md` § Command Run Plan, let the user run `gh auth login`, and continue once they confirm. Never read, ask for or store a token: no `gh auth token`, no `gh auth status --show-token`, no echo of `GH_TOKEN` / `GITHUB_TOKEN` |
| 4. Remote | `git remote get-url origin` | Present → `gh repo view --json nameWithOwner,viewerPermission,visibility -- "<slug>"`. A GitHub remote that resolves goes to step 5b; anything else is reported and left untouched. Absent → step 5 |
| 5. Create | `gh repo create` | Ask once with `AskUserQuestion`: **owner** (the signed-in account or one of its organizations, from `gh api user/orgs`), **name** (default: the project folder name, validated), **visibility** (**private** first and recommended, then public). State the exact command, then run it on the user's yes: `gh repo create "<owner>/<name>" --private\|--public --source=. --remote=origin`. Never `--push` an empty history |
| 5b. Reuse | the step 4 result | Ask with `AskUserQuestion` whether this existing repository is the project's tracker, showing its owner and the user's `viewerPermission`. No → leave everything untouched and record no tracker. Yes → continue; step 6 needs `viewerPermission` to be `ADMIN` |
| 6. Issues | `gh repo view --json hasIssuesEnabled` | Disabled → `gh repo edit --enable-issues -- "<slug>"` on a repository just created in step 5, or an existing one after the step 5b yes with `ADMIN`; otherwise report it and change nothing |
| 7. Pre-push | `devteam tools` (gitleaks) | Before any push, scan the whole history for secrets with gitleaks (false positives are suppressed as ADR-0059 says: `.gitleaksignore` or an inline comment, never a bypass) and confirm no private input is tracked (`git ls-files --error-unmatch -- "<path>"`). A hit blocks step 8 and is reported |
| 8. First push | `git log -1` | A commit exists and step 7 passed → ask with `AskUserQuestion` naming the branch, the remote slug, the visibility and the commit count (for a public repository: "this publishes N commits to a PUBLIC repository"), with **Don't push** as an option; on yes `git push -u origin -- "<branch>"`. No commit yet → say the first `/devteam:commit` comes before the push |

Record `ISSUE_TRACKER: github-projects` or the matching backlog value as usual, and the repository slug in the report. A failed `gh` call is reported with its message and the manual command; it never fails the setup.
