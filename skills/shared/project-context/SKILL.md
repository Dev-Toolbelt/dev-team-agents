---
name: project-context
description: Foundational rule for all dev-team-agents. Defines how agents must load and reconcile project-specific context against the global base standards. Covers coexistence, project override, language policy, mandatory Plan Mode, immutability warnings, and context loading order. Every agent must apply this rule before acting.
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
1. README.md                  ← project overview, setup, conventions
2. CLAUDE.md                  ← Claude-specific rules (highest precedence)
3. .claude/docs/project.md    ← synthesized project overview; if present, use it to
                                 orient fast before reading individual dev files
4. AGENTS.md                  ← agent-specific instructions for this project
5. .claude/settings.json      ← Claude Code configuration
6. .agents/ (directory)       ← project-level agent overrides
7. .claude/docs/development/  ← architecture, code-standards, tech-stack
8. .claude/docs/backlog/      ← current sprint and task context
```

**When `.claude/docs/project.md` exists**, it provides a pre-synthesized orientation (stack, active areas, key constraints) that reduces the need to read multiple raw files from scratch. Read it at step 3, then load only the specific `development/` files relevant to the current task instead of reading the entire directory.

Read each file that exists. Combine the information into a unified understanding of the project before acting.

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
