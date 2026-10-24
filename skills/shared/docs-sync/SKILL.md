---
name: docs-sync
description: Maintains docs/ — surgical patches, no duplicate content.
---

# Docs Sync

Agents call this skill after completing any task that changes project state. It patches the affected section in `docs/` — it never rewrites a whole file.

---

## Token Economy Rules

| Rule | Detail |
|------|--------|
| **Line budgets** | Each file has a hard max (see schemas below). Trim oldest or least-relevant entries when adding. `## Source References` does not count toward the budget. |
| **Tables over prose** | All structured data must be tables or bullet lists — never paragraphs. |
| **No duplicates** | If the information is in `CLAUDE.md`, do not repeat it here. |
| **No history** | Docs record current state only. Past decisions belong in git commits and ADRs. **Exception:** the `## Amendment Log` section of an owner doc (`skills/shared/doc-flow/SKILL.md` § Amendment Log) — it is append-only and, like `## Source References`, does not count toward the line budget. |
| **Surgical patches** | Read the current file first. Replace only the changed section using Edit — never Write the whole file. |
| **Freshness marker** | Every file has `<!-- last-updated: YYYY-MM-DD -->` on line 1. Update it on every write. Line 1 is the canonical form: rewrite a date written elsewhere (`last-updated: …` lower in the file) into it. |
| **No boilerplate** | Omit sections that are empty, N/A, or unknown. |
| **One source of truth** | If two docs would say the same thing, keep it in the more specific one and link from the other. |

---

## Document Schemas

Each schema is named by its key in `scripts/lib/doc-layouts.json` (canonical); paths are shown for
the `development` layout (the default) and the `gated` layout where they differ. Resolve the actual
path with `bash .dev-team-agents/scripts/doc-path.sh <key>` — rules in
`skills/shared/doc-flow/SKILL.md` § Doc Layout. Facts follow § Owner Rule: one owning doc each.

### `project` — `docs/project.md` — max 80 lines

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Project: [name]
## What It Does
## Type & Config
PROJECT_TYPE / TESTS_REQUIRED / CICD_PLATFORM
## Active Areas
| Directory | Purpose | Last Active |
## Key Constraints
```

### `tech-stack` — `docs/development/tech-stack.md` · gated `docs/tech-stack.md` — max 60 lines

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Tech Stack
| Layer | Technology | Version | Notes |
## Dev Setup
## Notable Dependencies
## Source References
```

### `architecture` — `docs/development/architecture.md` · gated `docs/architecture.md` — max 100 lines

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Architecture
## System Type
## Layers | Directory | Responsibility
## Module Map | Module/Service | Purpose | Key Entry Points
## Data and Contracts
Links to the `data-model` and `api-contracts` docs — never a copy of a schema or an endpoint
## Source References
```

### `data-model` — `docs/development/database.md` · gated `docs/data-model.md` — max 150 lines

Data Model Specification, from `.dev-team-agents/templates/data-model-template.md`.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Data Model Specification
## Database Choice
## Logical Overview
## ER Diagram — [area]          (one Mermaid erDiagram per domain area)
## Data Dictionary | Table | Column | Type | Constraint | PII | Meaning
## Migration Strategy
## Indexing Guidelines
## Source References
```

### `api-contracts` — `docs/development/api-contracts.md` · gated `docs/api-contracts.md` — max 150 lines

```markdown
<!-- last-updated: YYYY-MM-DD -->
# API Contracts
## Style and Versioning
## Auth Model
## Envelopes | Response | Error
## Endpoints | Method | Path | Auth | Request | Response | Errors
## Source References
```

### `code-standards` — `docs/development/code-standards.md` · gated `docs/code-standards.md` — max 80 lines

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Code Standards
## Detected Config | Tool | Config File | Key Rules
## Naming Conventions
## Patterns in Use
## Anti-Patterns (project-specific)
## Source References
```

### `backlog-readme` — `docs/backlog/README.md` — max 40 lines (development layout only)

In the gated layout the `backlog-index` doc (`docs/backlog.md`) replaces it.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Backlog
## Tracker
## Sprint Files | File | Sprint | Status
```

### `design-system` — `docs/design/design-system.md` — max 80 lines (UI projects only)

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Design System
## UI Library / Color Tokens / Typography Scale / Component Inventory / Spacing Scale
```

In the **gated** layout the same file holds usage rules that reference token **names** plus the
component inventory: values live only in the `design-tokens` doc (`docs/design/tokens.json`), and
user flows in the `design-flows` doc (`docs/design/flows/<feature>.md`). In the development layout
values stay in `design-system.md` as above.

---

## Task Closure Rule

**This is the canonical statement of the rule. Agents reference it; they do not restate it.**

After completing any task, check whether the work delivered triggers an entry in the Update
Triggers table below. If it does, apply the surgical patch to the relevant `docs/` file. Run it
in parallel with the commit — it is part of finishing the task, not a follow-up to it.

## Document Lifecycle

**A document that no longer describes current behavior says so at its top — it is never deleted.** The wiki (`references/wiki-format.md` § Never Delete an Entry) and ADRs (`skills/shared/adr/SKILL.md` § Status Lifecycle) carry their own markers; this covers everything else under `docs/`.

| Document | Marker, directly under the H1 |
|----------|-------------------------------|
| Plan (`docs/development/plan-*.md`, or any document carrying acceptance criteria and steps) | `**Status:** Proposed \| Approved \| In progress \| Implemented \| Superseded \| Abandoned — <evidence: commit, PR, or replacing document>`, updated when the plan's state changes |
| Superseded plan or reference document | `> ⚠️ Historical — superseded by [<file>](<link>). Current behavior is documented there.` under the status line |
| Point-in-time snapshot (audit, gap report, incident, proposal) | `> 🗂️ Historical snapshot (YYYY-MM-DD). For current behavior see [<current source>](<link>).` |

`Implemented` needs evidence that it shipped; a plan whose state cannot be established says `Unknown — <why>` rather than guessing. `scripts/index-lint.sh` warns on a `plan-*.md` without a status line.

## When to Update What

Load `references/update-triggers.md` for: full trigger table (which work requires which doc), update protocol steps, and user-intent trigger patterns (convention signals, note-taking signals, approval signals).

Load `references/wiki-format.md` for: when to write wiki entries, entry format template, domain folder rules, wiki update protocol, and `wiki/README.md` format.
