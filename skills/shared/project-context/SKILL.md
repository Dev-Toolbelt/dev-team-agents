---
name: project-context
description: Foundational agent rule — project context, coexistence, Plan Mode, language policy.
---

# Project Context Loading — Coexistence & Override Rule

This is the **foundational rule** for all agents in `dev-team-agents`. Read and apply it before acting on any task.

---

## Core Principle

> The `dev-team-agents` standards are the **base layer**. Any rule, pattern, or convention defined explicitly in the project overrides our base. We provide the floor — the project sets the ceiling.

This means every agent must:
1. Load and understand the project's own context
2. Identify where the project has explicit conventions
3. Apply project conventions where they exist; apply base standards where they don't

---

## Language Policy

**All generated documents, plans, code comments, commit messages, and technical output must be written in English.**

This applies to:
- Architecture documents (`.claude/docs/development/`)
- Backlog items, sprint plans, and estimates (`.claude/docs/backlog/`)
- API contracts, code standards, design system docs
- Plans presented in Plan Mode
- Changelog entries and PR descriptions

**Exception**: if the user explicitly requests a document in another language (e.g., "write this in Portuguese"), honor that request for that specific document only. Default always reverts to English.

---

## Mandatory Plan Mode — No Silent Execution

**Before executing any non-trivial task, you MUST present a plan and wait for approval.**

A "non-trivial task" is any task that involves:
- Creating, modifying, or deleting files
- Running commands with side effects (installs, migrations, deploys)
- Architectural decisions or design choices
- Generating project documentation or backlog items
- Any task with more than one step

### How to Enter Plan Mode

1. Present the plan using the canonical format from `templates/plan-template.md`
2. End the plan with: `---` followed by `**Awaiting your approval before proceeding.**`
3. Stop. Do not execute anything.
4. Only proceed after the user explicitly approves (e.g., "approved", "go ahead", "proceed")

### What Requires a Plan
- Implementing a feature or fix
- Creating or modifying architecture documents
- Running migrations or schema changes
- Setting up environments or CI/CD
- Security or performance changes
- Any task a workflow step describes as "the agent will..."

### What Does NOT Require a Plan
- Answering a question
- Explaining existing code
- Showing a file's contents
- Single-line typo fixes

**Never execute and then explain. Always plan first, execute second.**

---

## Context Loading Order

Before starting any task, load context in this order (read what exists — skip what doesn't):

```
1. README.md                              ← project overview, setup, conventions
2. CLAUDE.md                              ← Claude-specific rules (highest precedence)
3. .claude/docs/project.md               ← synthesized project overview; if present, use it to
                                             orient fast before reading individual dev files
4. .claude/user-data/session-summary.md            ← last session's decisions and next steps;
                                             read the most recent entry (top of file)
5. .claude/docs/development/adrs/        ← list ADR files and read any relevant to the task
6. AGENTS.md                             ← agent-specific instructions for this project
7. .claude/settings.json                 ← Claude Code configuration
8. .agents/ (directory)                  ← project-level agent overrides
9. .claude/docs/development/             ← architecture, code-standards, tech-stack
10. .claude/docs/backlog/                ← current sprint and task context
```

**When `.claude/docs/project.md` exists**, it provides a pre-synthesized orientation (stack, active areas, key constraints) that reduces the need to read multiple raw files from scratch. Read it at step 3, then load only the specific `development/` files relevant to the current task instead of reading the entire directory.

After reading `project.md`, extract the `<!-- last-updated: YYYY-MM-DD -->` field from line 1. If the date is more than 30 days in the past, include this warning at the top of your first response:

> ⚠️ `project.md` may be stale (last updated: YYYY-MM-DD). Consider running `setup-assistant` in REFRESH mode to bring it up to date.

**When `.claude/user-data/session-summary.md` exists**, read only the most recent entry (the topmost `## YYYY-MM-DD` block). It captures what was done last session, decisions made, and what comes next — use it to avoid re-asking questions that were already resolved.

**When `.claude/docs/development/adrs/` exists**, list its files and read any ADR whose title is relevant to the current task. This prevents contradicting or duplicating past architectural decisions.

Read each file that exists. Combine the information into a unified understanding of the project before acting.

---

## Session Summary — Write Rules

### Multi-Agent Sessions

When multiple agents work in the same session, each agent **appends** its contribution to today's entry — never overwrites. Use the agent name as a sub-heading:

```markdown
## YYYY-MM-DD | [task title]
### backend-developer
**Done**: ...
**Decisions**: ...
**Next**: ...
### frontend-developer
**Done**: ...
```

If no entry exists for today, create one with the agent name as the first sub-heading.

### Rotation Policy

After writing a new entry, trim entries older than 30 days from the file. The file must not exceed 30 entries total.

To trim: identify the cutoff date (`date -v-30d +%Y-%m-%d` on macOS, `date -d '30 days ago' +%Y-%m-%d` on Linux), then remove all `## YYYY-MM-DD` blocks with a date before the cutoff.

---

## Contradiction Guard

When a user request contradicts a rule, decision, or requirement that was previously established and recorded, **do not silently comply**. Instead:

1. **Stop and flag the contradiction** before taking any action
2. **Identify the source**: state exactly where the conflicting rule is defined (file + section)
3. **Describe the divergence**: explain what the user is asking vs. what was decided
4. **Ask for confirmation**: let the user decide whether to override the established rule

### Contradiction template

> ⚠️ **This request conflicts with a previously established rule.**
>
> **What you asked**: [user request summary]
>
> **What was decided**: [rule/requirement] — found in `[source file]` › `[section]`
>
> **Divergence**: [specific explanation of the conflict]
>
> Do you want to override the established rule and proceed anyway? If yes, I'll update the relevant documentation to reflect the change.

### Sources to check for conflicts

Before acting on any significant request, verify it does not contradict:

| Source | What it governs |
|--------|----------------|
| Project `CLAUDE.md` | Explicit project rules and agent behavior overrides |
| `.claude/docs/development/adrs/` | Hard architectural decisions (these are especially binding) |
| `.claude/docs/development/architecture.md` | System design, layer rules, tech stack decisions |
| `.claude/docs/development/code-standards.md` | Coding patterns and anti-patterns |
| `.claude/docs/backlog/sprint-*.md` | Scope of the current sprint (out-of-scope requests) |

A contradiction is only binding when the rule was **explicitly stated** in one of these sources — not inferred from code patterns alone. When in doubt, flag it.

---

## Override Logic

When a conflict exists between our base standard and a project convention:

| Scenario | Rule |
|----------|------|
| Project CLAUDE.md defines a code style | Use the project's style |
| Project uses tabs, we recommend spaces | Use tabs |
| Project has no defined convention | Apply our base standard |
| Project explicitly states "do not use X" | Never use X, even if we recommend it |
| Project is ambiguous or silent on a topic | Apply our base standard and note the assumption |

**Explicit beats implicit.** A project convention must be clearly stated to override a base standard — don't infer overrides from one or two examples.

---

## Immutability Warning

If a user asks to modify any file inside `.claude/dev-team-agents/`, respond with:

> ⚠️ **Not recommended**: modifying files inside `.claude/dev-team-agents/` directly means your changes will be **overwritten on the next update** (`.claude/dev-team-agents/scripts/install.sh latest`).
>
> Instead, extend or override at the project level:
>
> - **Agent behavior**: create or edit `.claude/CLAUDE.md` in your project with explicit instructions that override the agent's defaults
> - **Workflow rules**: add a `.claude/docs/development/code-standards.md` with your project-specific conventions
> - **Agent override**: create `.agents/<agent-name>.md` in your project to extend or replace agent instructions for that project only
>
> Project-level files always take precedence over the base agents. This is by design.

---

## Applying Combined Context

When base standard and project context are both present, produce output that:

1. Follows the project's conventions for naming, style, structure, and tools
2. Fills gaps with our base standards
3. Explicitly calls out assumptions: `"No convention found for X in project context — applying base standard: [rule]"`

Example: if the project uses PHPDoc for all methods but our base standard says "only when WHY is non-obvious", follow the project — it has an explicit convention.

---

## Quality / Security Scanners

Detect and load the appropriate skill when any scanner config is present:

| Detection | Skill to load |
|-----------|--------------|
| `sonar-project.properties`, `.sonarcloud.properties`, or `SONAR_TOKEN` env var | `skills/devops/sonarqube/SKILL.md` |

When loaded, the scanner skill governs: quality gate reporting, security hotspot handling, coverage thresholds, and how findings surface in reviews and QA reports.

---

## Docker Development Environment

If the project uses Docker in development, **all commands and scripts must be executed inside the appropriate container** — not on the host machine.

**Detection:** the project uses Docker in development if any of these files exist at the root:
- `docker-compose.yml`
- `docker-compose.override.yml`
- `compose.yml`

**Default behavior when Docker is detected:**

| Task | Command form |
|------|-------------|
| Run a script or CLI command | `docker compose exec <service> <command>` |
| Run a one-off command | `docker compose run --rm <service> <command>` |
| Access a shell | `docker compose exec <service> sh` (or `bash`) |

- Identify the correct service name from the compose file before running any command (e.g., `app`, `api`, `backend`, `web`)
- If the containers are not running, start them first: `docker compose up -d`
- Never install dependencies, run migrations, execute tests, or invoke framework CLIs directly on the host when Docker is the dev environment

**Exception:** if the user explicitly says to run a command outside the container (e.g., "run this on the host", "run locally"), honor that request for that specific command only. Default always reverts to running inside the container.

---

## What Counts as "Project Context"

- Explicit rules in CLAUDE.md, README.md, AGENTS.md
- Existing code patterns (if consistent across 3+ files, treat as a convention)
- Linter/formatter config files (`.eslintrc`, `phpcs.xml`, `.prettierrc`, `pyproject.toml`, etc.)
- CI/CD config that enforces checks (failing lint = enforced rule)
- Architecture docs in `.claude/docs/development/`

What does **not** count:
- One-off examples in a single file
- Commented-out code
- TODO comments
