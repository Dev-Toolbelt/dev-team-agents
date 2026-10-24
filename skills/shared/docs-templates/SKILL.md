---
name: docs-templates
description: Templates for docs/ and the layout setup creates — development files or gated skeleton.
---

## Source Synthesis Rule

Before generating each doc, read every relevant file found in the Project Docs Discovery scan:

1. **Read** the source file
2. **Synthesize** — extract and condense into the target section (tables or bullets; never copy verbatim)
3. **Add `## Source References`** at the end listing every file that contributed content

```markdown
## Source References
| File | Sections Fed |
|------|-------------|
| [ARCHITECTURE.md](../../ARCHITECTURE.md) | System Type, Layers, Module Map |
```

Rules: only list files that provided content; use paths relative to project root; omit section if no sources found; future `docs-sync` updates must preserve and extend this section.

## Docs Layout on Setup

The layout is chosen once, on FIRST_RUN, from `PROJECT_TYPE` (`skills/shared/doc-flow/SKILL.md` § Doc Layout). Paths come from the map: resolve each key with `bash .dev-team-agents/scripts/doc-path.sh <key>` **after** the layout is recorded — never type a path the map owns.

| `PROJECT_TYPE` | Layout | Docs created |
|----------------|--------|--------------|
| `new` | `gated` — record it (below), then create § Gated Skeleton | § Gated Skeleton |
| `inherited`, `maintenance` | `development` — write no key; absent means `development` | § Development Docs, unchanged |

REFRESH never changes the layout. An existing project moves to `gated` only through the opt-in migration (`skills/shared/doc-flow/references/migration.md`).

### Recording the layout

`docs_layout` lives in `.dev-team-agents/project.json` — committed topology, so every other key is kept as it is. When the file is absent the project is not bound: ask with `AskUserQuestion` — **Bind first** (recommended: `devteam bind`, then record the key) or **Keep the development layout** (create § Development Docs instead).

```bash
python3 -I .dev-team-agents/scripts/docs-migrate.py set-layout gated   # prints: LAYOUT gated
bash .dev-team-agents/scripts/doc-path.sh --layout                      # must print: gated
```

`set-layout` validates the file and writes it atomically through the CLI's own writer; it is the only way this flow writes the key (the migration's `apply` calls the same code).

### Development Docs

Today's file list, kept exactly:

- Always: `docs/project.md` · `docs/development/tech-stack.md`, `architecture.md`, `code-standards.md` · `docs/backlog/README.md` · `docs/wiki/README.md` — the retrieval index, created with its `## Index` table header and no rows; agents append one row per entry (`skills/shared/docs-sync/references/wiki-format.md`). **Never overwrite an existing one**
- UI projects: `docs/design/design-system.md`
- **DevOps** (`Dockerfile`, `docker-compose*.yml`, CI/CD configs, IaC files, `vercel.json`/`netlify.toml`/etc.) → `docs/devops/infrastructure.md`
- **Tests** (`jest.config.*`, `vitest.config.*`, `playwright.config.*`, `pytest.ini`, `phpunit.xml`, test dirs) → `docs/tests/testing-strategy.md`

### Gated Skeleton

One row per map key setup creates. `When`: `always`; `ui` when `HAS_UI: yes`; `llm` when `USES_LLM: yes` (both recorded in `docs/project.md`). `/devteam:health-check` Category 14 reads this table — keep it a table of keys, one per row.

| Key | Seed | When |
|-----|------|------|
| `project` | § `docs/project.md` | always |
| `process` | `.dev-team-agents/templates/process-template.md` | always |
| `source` | `README.md` from § Read-only Folder README | always |
| `prd` | `.dev-team-agents/templates/prd-template.md` | always |
| `glossary` | `.dev-team-agents/templates/glossary-template.md` | always |
| `nfr` | `.dev-team-agents/templates/nfr-template.md` | always |
| `trd` | `.dev-team-agents/templates/trd-template.md` | always |
| `architecture` | § `architecture` doc | always |
| `tech-stack` | § `tech-stack` doc | always |
| `code-standards` | § `code-standards` doc | always |
| `data-model` | `.dev-team-agents/templates/data-model-template.md` | always |
| `api-contracts` | § `api-contracts` doc (gated) | always |
| `threat-model` | `.dev-team-agents/templates/threat-model-template.md` | always |
| `adr` | `README.md` with the ADR index header of `skills/shared/adr/SKILL.md` § ADR Index, no rows | always |
| `specs` | empty `.gitkeep` | always |
| `testing` | § `testing` doc (gated) | always |
| `backlog-index` | § `backlog.md` (gated) | always |
| `wiki` | `README.md` retrieval index, `## Index` header and no rows (`skills/shared/docs-sync/references/wiki-format.md`) | always |
| `design-tokens` | § `tokens.json` (gated) | ui |
| `design-system` | § `design-system` doc | ui |
| `design-prototypes` | `README.md` from § Read-only Folder README | ui |
| `design-flows` | empty `.gitkeep` | ui |
| `design-screens` | empty `.gitkeep` | ui |
| `evals` | `.dev-team-agents/templates/evals-template.md` | llm |

| Rule | Detail |
|------|--------|
| Never overwrite | `[ -e "$path" ] \|\| …` — an existing file or folder is left as it is and reported as kept |
| Directories | A resolved path ending in `/` is a folder: `mkdir -p` it, then write its seed inside |
| Templates | Copied **verbatim** (`cp -n`), placeholders included — the owner agent fills them at its stage, and the health check tells an unfilled doc by comparing it with its template |
| Inline seeds | Keep their `<!-- TODO: <owner> to … -->` markers; the health check reads a remaining marker as unfilled |
| Conditional docs | DevOps signals (§ Development Docs) still add the `infrastructure` doc |
| Not created here | `reuse-guidelines`, `conformance-report`, `overview`, `sprints` — their owners create them when first needed |

### Read-only Folder README

```markdown
# [Raw inputs | Design prototypes]

Read-only raw input (`.dev-team-agents/skills/shared/doc-flow/SKILL.md` § Read-only Inputs).
Add a new dated file or folder here; never edit, rename or delete an existing one — a correction is a
new dated file that supersedes the old one, cited from the working doc.
```

---

## `docs/project.md`

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Project: [name from README or directory]

## What It Does
[1-2 sentences from README or inferred from scan]

## Type & Config
PROJECT_TYPE: [new|inherited|maintenance]
TESTS_REQUIRED: [yes|no]
CICD_PLATFORM: [detected or answered in Step 3]
HAS_UI: [yes|no]
USES_LLM: [yes|no — new projects only; yes when the product runs an LLM task]
[CLOUD_PROVIDER: omit if not applicable]
[ISSUE_TRACKER: omit if none]

## Active Areas
[From git log — omit for new projects with no commits]
| Directory | Purpose | Last Active |
|-----------|---------|-------------|

## Key Constraints
[Hard rules from existing CLAUDE.md; omit if no prior CLAUDE.md]
```

---

## `tech-stack` doc

`docs/development/tech-stack.md` · gated `docs/tech-stack.md`.

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Tech Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
[From package.json / composer.json / requirements.txt / Gemfile / go.mod / Cargo.toml / Dockerfile.
Include: language, framework, database, cache, queue, auth, test runner, CI/CD.
Omit rows for layers not present.]

## Dev Setup
[From README or package.json scripts — 1–3 commands; omit if unknown]

## Notable Dependencies
[Non-obvious deps that affect how agents write code — omit well-known framework staples]
```

---

## `architecture` doc

`docs/development/architecture.md` · gated `docs/architecture.md`.

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Architecture

## System Type
[inherited/maintenance: infer from scan (e.g., "Decoupled REST API + React SPA")]
[new: <!-- TODO: software-architect to define -->]

## Layers
| Layer | Directory | Responsibility |
|-------|-----------|---------------|
[inherited/maintenance: infer from top-level directory structure]
[new: <!-- TODO: software-architect to define -->]

## Module Map
| Module/Service | Purpose | Key Entry Points |
|---------------|---------|-----------------|
[inherited/maintenance: populate from scan]
[new: <!-- TODO: software-architect to complete -->]
```

---

## `code-standards` doc

`docs/development/code-standards.md` · gated `docs/code-standards.md`.

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Code Standards

## Detected Config
[From .eslintrc / .prettierrc / phpcs.xml / pyproject.toml / .rubocop.yml / golangci.yml.
Omit section if no config files found.]
| Tool | Config File | Key Settings |
|------|------------|-------------|

## Naming Conventions
<!-- TODO: software-architect to define, or auto-detect from existing code patterns -->

## Established Patterns
<!-- TODO: software-architect or code-reviewer to complete -->
```

---

## `backlog-readme` doc (development layout)

`docs/backlog/README.md`.

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Backlog

## Tracker
[From Step 3: "None" | "GitHub Projects: <url>" | "Jira: <workspace>" | "Linear: <team>" | ...]

## Sprint Files
| File | Sprint | Status |
|------|--------|--------|
| — | No sprints created yet | — |
```

---

## `design-system` doc (UI projects only)

`docs/design/design-system.md` in both layouts.

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Design System

## UI Library
[Detected from package.json: shadcn/ui, MUI, Ant Design, Bootstrap, Chakra UI — or "Not yet chosen"]

## Color Tokens
<!-- TODO: ui-ux-designer to complete in Design Mode -->

## Typography Scale
<!-- TODO: ui-ux-designer to complete -->

## Component Inventory
<!-- TODO: ui-ux-designer to complete -->
```

---

## `api-contracts` doc (gated)

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# API Contracts

## Conventions
<!-- TODO: software-architect to define — API style, versioning, auth model, error and pagination envelopes -->

## Endpoints
<!-- TODO: software-architect to complete — one section per endpoint, cited from feature contracts by heading -->

### Amendment Log
- YYYY-MM-DD | [agent] | [what changed] | [why]
```

---

## `testing` doc (gated)

```markdown
<!-- last-updated: [YYYY-MM-DD] -->
# Testing Strategy

## Levels
<!-- TODO: software-architect to define — which levels run, what each covers, where each runs -->

## Tooling and Fixtures
<!-- TODO: software-architect to complete -->

## Traceability
Tests cite the scenario they cover as `[spec:<feature>#S<n>]`.

### Amendment Log
- YYYY-MM-DD | [agent] | [what changed] | [why]
```

---

## `backlog.md` (gated)

The single backlog index (global Definition of Done, Definition of Ready, one row per sprint). Its one template is `skills/shared/backlog-template/SKILL.md` § Gated Layout (`docs/backlog.md`): write that skeleton with its bracketed placeholders replaced: `## Definition of Done` becomes `<!-- TODO: product-analyst to complete -->` (the health check reads a remaining marker as unfilled), `### Project additions` becomes `- none`, and the `## Sprints` table keeps its header with one `| — | No sprints created yet | — | — | — |` row. Sprint files stay under `docs/backlog/sprints/`.

---

## `tokens.json` (gated, UI projects only)

```json
{
  "$description": "W3C Design Tokens — ui-ux-designer fills this at stage 2b; every visual value in the product maps to a token here"
}
```
