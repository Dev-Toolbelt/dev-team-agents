---
status: draft # draft → reviewed (database-specialist reviewed) → approved (stage 2a gate)
---

<!--
CANONICAL DATA MODEL FORMAT. Installed at .dev-team-agents/templates/data-model-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by software-architect at the `data-model` doc (docs/data-model.md in the gated layout),
stage 2a of skills/shared/doc-flow/SKILL.md; database-specialist reviews it before the gate.
Feature contracts reference entities and columns here by name, never restate them.
-->

# Data Model Specification — [Product Name]

## Logical Overview
[Two to five bullets: the main areas (bounded contexts), the engine(s), and the cross-area relations.]

| Area | Entities | Owner module |
|---|---|---|
| [area] | [entity, entity] | [module] |

## Area: [Area Name]

```mermaid
erDiagram
    [ENTITY_A] ||--o{ [ENTITY_B] : "[relation]"
    [ENTITY_A] {
        [type] [column] PK
        [type] [column]
    }
```

[Repeat one `## Area:` section with its own `erDiagram` per area.]

## Data Dictionary

### [table_or_collection]
[Purpose in one sentence. Glossary term: [term].]

| Column | Type | Null | Default | Constraints | PII | Description |
|---|---|---|---|---|---|---|
| [column] | [type] | [yes · no] | [value or —] | [PK · FK → table.column · unique · check] | [none · personal · sensitive] | [meaning] |

**Indexes:** [name — columns — why]

[Repeat one `###` block per table. Every column tagged `personal` or `sensitive` appears in the
personal-data map of docs/security/threat-model.md.]

### Amendment Log
<!-- Empty until the first change after approval; creating this document is not logged.
One line per change: `- YYYY-MM-DD | agent | what changed | why` — the reason is mandatory
(skills/shared/spec-gate/SKILL.md § Living Spec — Amendment Protocol). -->
