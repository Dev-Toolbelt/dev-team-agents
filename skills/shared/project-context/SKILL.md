---
name: project-context
description: Foundational rule — context, coexistence, Plan Mode, language.
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

### Documents — Always English

**All generated documents, code comments, commit messages, and technical output must be written in English.**

This applies to:
- Architecture documents (`.claude/docs/development/`)
- Backlog items, sprint plans, and estimates (`.claude/docs/backlog/`)
- API contracts, code standards, design system docs
- Changelog entries and PR descriptions

**Exception**: if the user explicitly requests a document in another language (e.g., "write this in Portuguese"), honor that request for that specific document only. Default always reverts to English.

### Conversation — User's Preferred Language

**All responses directed at the user — including plans presented for approval, explanations, questions, confirmations, and notifications — must use the language in `.claude/user-data/preferences.json` → `language` field.**

Read this value at the start of every session:

```bash
python3 -c \
  "import json; d=json.load(open('.claude/user-data/preferences.json')); print(d.get('language','en'))" \
  2>/dev/null || echo "en"
```

If `preferences.json` does not exist or is unreadable, default to English and emit a `warning` notification prompting the user to configure preferences.

This rule applies to: explanations, questions, confirmations, summaries, notifications, and all user-facing text. It does NOT apply to document content, code comments, or commit messages.

When emitting system notifications (context window warnings, missing config, tips), load `skills/shared/notifier/SKILL.md` to apply the correct DEV TEAM AGENTS format and suppression rules.

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

After writing a new entry, trim entries according to `.claude/user-data/preferences.json`:
- `session_summary_max_days` (default: 30) — remove entries older than this many days
- `session_summary_max_entries` (default: 30) — keep at most this many entries total

To trim: identify the cutoff date (`date -v-${MAX_DAYS}d +%Y-%m-%d` on macOS, `date -d "${MAX_DAYS} days ago" +%Y-%m-%d` on Linux), then remove all `## YYYY-MM-DD` blocks with a date before the cutoff. If the remaining count still exceeds `session_summary_max_entries`, remove the oldest entries until within the limit.

---

## Contradiction Guard

Automatically enforced by all agents. Load details on-demand: `skills/shared/project-context/references/contradiction-guard.md`

---

## Wiki Knowledge Base

Every project gets a wiki at `.claude/docs/wiki/`. Load full protocol: `skills/shared/project-context/references/wiki.md`

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

## Interaction Patterns — Quiz-first Rule

**Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question.**

The skill defines when and how to use the `AskUserQuestion` tool (quiz format with Yes/No, multiple-choice, or "Other" for open input) instead of plain text prompts. Apply it to every confirmation, choice, and gate in your workflow.

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
