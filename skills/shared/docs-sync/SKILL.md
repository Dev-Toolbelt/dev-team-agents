---
name: docs-sync
description: Maintains .claude/docs/ — surgical patches, token-economy rules, no duplicate content.
---

# Docs Sync

Agents call this skill after completing any task that changes project state. It patches the affected section in `.claude/docs/` — it never rewrites a whole file.

---

## Token Economy Rules

These rules govern every document under `.claude/docs/`. Violating them defeats the purpose of the system.

| Rule | Detail |
|------|--------|
| **Line budgets** | Each file has a hard max (see schemas below). Trim oldest or least-relevant entries to stay within budget when adding. The `## Source References` section is navigation metadata and does not count toward the budget. |
| **Tables over prose** | All structured data (stack, patterns, constraints) must be tables or bullet lists — never paragraphs. |
| **No duplicates** | If the information is already in `CLAUDE.md`, do not repeat it here. These docs extend CLAUDE.md, not copy it. |
| **No history** | Docs record current state only. Past decisions and change history belong in git commits and ADRs — not in these files. |
| **Surgical patches** | Read the current file first. Replace only the changed section using Edit — never Write the whole file. |
| **Freshness marker** | Every file has `<!-- last-updated: YYYY-MM-DD -->` on line 1. Update it on every write. |
| **TODO markers** | Sections not yet populated use `<!-- TODO: <agent> to fill -->`. Remove on first write of that section. |
| **No boilerplate** | Omit sections that are empty, N/A, or unknown — do not include placeholder headings with no content. |
| **One source of truth** | If two docs would say the same thing, keep it in the more specific one and link from the other. If a project-native file (e.g., `ARCHITECTURE.md`) is the authoritative source, reference it in `## Source References` rather than duplicating its content. |
| **Preserve source references** | When patching any section, read the `## Source References` table first. Preserve existing entries; add a new row only if you read an additional project-native file to produce the patch. |

---

## Document Schemas

### `.claude/docs/project.md` — max 80 lines

Synthesized project overview. The fastest way for any agent to orient before reading anything else.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Project: [name]

## What It Does
[1-2 sentences]

## Type & Config
PROJECT_TYPE: [new|inherited|maintenance]
TESTS_REQUIRED: [yes|no]
CICD_PLATFORM: [platform]

## Active Areas
| Directory | Purpose | Last Active |
|-----------|---------|-------------|

## Key Constraints
[Rules from CLAUDE.md that ALL agents must respect — only rules not already obvious from CLAUDE.md itself]
```

### `.claude/docs/development/tech-stack.md` — max 60 lines

Detected and confirmed stack. Updated when dependencies are added or changed.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Tech Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| Language | | | |
| Framework | | | |
| Database | | | |
| Cache | | | |
| Queue | | | |
| Auth | | | |
| Testing | | | |
| CI/CD | | | |

## Dev Setup
[How to start locally — 1–3 commands max]

## Notable Dependencies
[Only non-obvious deps that affect how agents write code]

## Source References
| File | Sections Fed |
|------|-------------|
| [DEVELOPMENT.md](../../DEVELOPMENT.md) | Tech Stack table, Dev Setup |
```

> `## Source References` is optional — omit entirely if no project-native files were read to populate this doc.

### `.claude/docs/development/architecture.md` — max 100 lines

System structure and module responsibilities. Updated when new modules or services are added, or architectural patterns change.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Architecture

## System Type
[Monolith | Decoupled API+SPA | Microservices | Serverless | ...]

## Layers
| Layer | Directory | Responsibility |
|-------|-----------|---------------|

## Module Map
| Module/Service | Purpose | Key Entry Points |
|---------------|---------|-----------------|

## API Contracts
[Summary or link to api-contracts.md]

## Source References
| File | Sections Fed |
|------|-------------|
| [ARCHITECTURE.md](../../ARCHITECTURE.md) | System Type, Layers, Module Map |
```

> `## Source References` is optional — omit entirely if no project-native files were read to populate this doc.

### `.claude/docs/development/code-standards.md` — max 80 lines

Active conventions enforced in the project. Updated when new patterns are established by `code-reviewer` or `software-architect`.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Code Standards

## Detected Config
| Tool | Config File | Key Rules |
|------|------------|-----------|

## Naming Conventions
| Scope | Convention | Example |
|-------|-----------|---------|

## Patterns in Use
[Bullet list — only established patterns, not aspirational ones]

## Anti-Patterns (project-specific)
[Bullet list — things this project explicitly avoids]

## Source References
| File | Sections Fed |
|------|-------------|
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Naming Conventions, Patterns, Detected Config |
```

> `## Source References` is optional — omit entirely if no project-native files were read to populate this doc.

### `.claude/docs/backlog/README.md` — max 40 lines

Backlog index. Updated when sprints are created or the tracker configuration changes.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Backlog

## Tracker
[none | GitHub Projects: <url> | Jira: <workspace> | Linear: <team> | ...]

## Sprint Files
| File | Sprint | Status |
|------|--------|--------|
```

### `.claude/docs/design/design-system.md` — max 80 lines (UI projects only)

UI conventions. Created by `ui-ux-designer`, updated when new components or tokens are added.

```markdown
<!-- last-updated: YYYY-MM-DD -->
# Design System

## UI Library
[Library name + version]

## Color Tokens
| Token | Value | Usage |
|-------|-------|-------|

## Typography Scale
| Name | Size | Weight | Usage |
|------|------|--------|-------|

## Component Inventory
| Component | Location | Notes |
|-----------|---------|-------|

## Spacing Scale
[Token → value table or reference to library docs]
```

---

---

## Wiki — `.claude/docs/wiki/`

The wiki captures **domain knowledge that isn't derivable from reading the code** — non-obvious behaviors, multi-component flows, platform-specific gotchas, and concepts that work differently in this project than their name implies.

### When to write a wiki entry

Write a new page (or update an existing one) when a task reveals:
- A flow that spans multiple layers or services in a non-obvious way
- A concept whose behavior in this codebase differs from what the name implies
- A gotcha, invariant, or constraint that would surprise a new agent
- A sync/dispatch behavior, state machine edge case, or offline-first deviation
- A business rule that lives nowhere obvious in the code

**Do NOT write** for: things clear from reading the code, standard library patterns, or anything already in `CLAUDE.md`.

### Domain folders — dynamic, project-driven

Domains are **not predefined**. Agents create folders based on the project's actual domain concepts. Examples:

| Domain example | Use for |
|----------------|---------|
| `auth/` | Authentication flows, JWT behavior, RBAC quirks |
| `payments/` | Payment states, webhook handling, idempotency |
| `orders/` | Order state machine, transition guards, edge cases |
| `sync/` | Outbox/inbox pattern, dispatch rules, ordering constraints |
| `uploads/` | Multipart flow, chunk handling, retry behavior |
| *(any domain)* | Create the folder the first time an entry belongs there |

When a topic spans two domains, place the file in the more specific one and link from the other.

### Wiki entry format

```markdown
# [Concept or Flow Title]

**Origin:** [task or feature context] | YYYY-MM-DD

> [One-sentence "read this first" callout — the most important gotcha for a new agent]

---

## What it is
[1–3 sentences of context]

## How it works
[Diagram, code block, or numbered flow — the mechanics]

## Gotchas
[Bullets — only surprises, not documentation of the obvious]
```

Omit sections that add no value. Keep entries under 80 lines.

### Wiki update protocol

1. **Read** `.claude/docs/wiki/README.md` and the target domain folder before writing
2. **Decide**: new file or patch an existing one?
   - New concept → new file (`kebab-case.md`, e.g., `order-state-machine.md`)
   - Additional detail to existing concept → Edit the existing file
3. **Write / Edit** the entry
4. **Update** `wiki/README.md`: add a new domain row if the folder is new; update the entry count
5. **Never** include session dates, author names, or task history in the body

### wiki/README.md format

```markdown
# Wiki

## Domains

| Folder | Covers | Entries |
|--------|--------|---------|
| `auth/` | Authentication, JWT, RBAC | 2 |
| `orders/` | Order state machine, transitions | 1 |
```

---

## Update Triggers

| Work delivered | Doc to patch | Section |
|---------------|-------------|---------|
| New dep installed (language, framework, lib) | `tech-stack.md` | Tech Stack table |
| New service or module created | `architecture.md` | Module Map |
| New API endpoint or contract defined | `architecture.md` | API Contracts |
| New code pattern established | `code-standards.md` | Patterns in Use |
| New linter/formatter rule added | `code-standards.md` | Detected Config |
| Sprint file created | `backlog/README.md` | Sprint Files |
| New UI component added | `design/design-system.md` | Component Inventory |
| New color or typography token | `design/design-system.md` | relevant section |
| Task completed touching a directory | `project.md` | Active Areas |
| Schema migration applied | `architecture.md` | Module Map or API Contracts |
| Architectural layer added or renamed | `architecture.md` | Layers |
| Non-obvious domain behavior discovered | `wiki/<domain>/<topic>.md` | New or updated wiki entry |

---

## Update Protocol

1. **Read** the target file completely before writing anything
2. **Identify** only the section that changed — one table row, one bullet, one field
3. **Edit** using the smallest possible `old_string` → `new_string` diff (Edit tool, not Write)
4. **Update** `<!-- last-updated: YYYY-MM-DD -->` on line 1 in the same edit
5. **Check line count** — if the file now exceeds its budget, remove the oldest or least-relevant entries in the same patch

**Never:**
- Write the entire file when only one section changed
- Add a "Changelog" or "History" section to any doc
- Copy content verbatim from one doc to another (link instead)
- Create sections not defined in the schema above without explicit user approval
- Leave a section with only a heading and no content — omit the heading instead
