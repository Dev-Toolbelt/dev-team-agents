---
status: draft # draft → approved (the user approved it at the stage 1 gate)
---

<!--
CANONICAL PRD FORMAT. Installed at .dev-team-agents/templates/prd-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by product-analyst at the `prd` doc (docs/prd.md in the gated layout), stage 1 of
skills/shared/doc-flow/SKILL.md. Business rules only — no stack, schema, or API shape.
Every rule cites its source (doc-flow § Stages → Stages 0 and 1); source files are never edited.
Written as `status: draft`, every unconfirmed default tagged [A<n>] and listed in ## Assumptions.
-->

# Product Requirements — [Product Name]

## Purpose
[One or two sentences: the problem this product solves and for whom.]

## Users and Roles
| Role | Description | Source |
|---|---|---|
| [role] | [who they are, what they need] | `docs/source/[YYYY-MM-DD-topic].md` § Input |

## Rules

### [section] — [Section Name]
[`<section>` is a short lowercase slug, stable once used (e.g. `auth`, `billing`). Rule IDs are
`PRD-<section>-R<n>` — never renumbered, never reused; a removed rule keeps its ID retired.
Source is `docs/source/<file>.md` § Input (or a heading inside it), or — for a rule taken from a
default — `<file>#Q<n>` plus its `[A<n>]`. A number (retention, SLA, latency) links its `NFR-<nn>`
instead of being restated.]

| ID | Rule | Source |
|---|---|---|
| PRD-[section]-R1 | [one testable business rule, in the glossary's terms] | `docs/source/[YYYY-MM-DD-topic].md` § Input |
| PRD-[section]-R2 | [rule, e.g. "erased within the retention of NFR-01"] [A1] | `[YYYY-MM-DD-topic].md#Q1` · [A1] |

[Repeat one `###` block per section.]

## Out of Scope
- [What this product explicitly does not do — be specific about the boundary]

## Assumptions
[Every default the draft adopted for an open question in docs/source/. `open` until a later source file
answers that question, then `confirmed` — the rules tagged with it then state the answer.]
| ID | Assumption | Source question | Status |
|---|---|---|---|
| [A1] | [the default adopted] | `[YYYY-MM-DD-topic].md#Q1` | open |

## Related
- Glossary: `docs/glossary.md` · NFRs: `docs/nfr.md`

### Amendment Log
<!-- Empty until the first change after approval; creating this document is not logged.
One line per change: `- YYYY-MM-DD | agent | what changed | why` — the reason is mandatory
(skills/shared/spec-gate/SKILL.md § Living Spec — Amendment Protocol). -->
