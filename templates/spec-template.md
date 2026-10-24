<!--
CANONICAL SPEC FORMAT. Installed at .dev-team-agents/templates/spec-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by product-analyst, business-level only — no stack, schema, or API shape.
See skills/shared/spec-gate/SKILL.md for the gate rule and scope-lock contract.
-->
---
status: draft # draft → approved (user approved the criteria) → implemented (every covering task Done, no [SPEC-DRIFT])
touches: [] # subset of [backend, frontend, database, mobile] — only layers that actually change
depends_on: [] # other spec filenames this one needs, or leave empty
ai: false # optional — true when the feature runs an AI/LLM task; in the gated layout spec-lint then requires its evals
---

## Spec — [Feature Name]

### User Story
As a [role], I want [capability], so that [outcome].

### Context
[One or two sentences: what triggered this feature and how it fits the approved scope overview (`docs/backlog/overview-<scope-slug>.md`).]

### Links
[Required. One line each — a path or ID, or `none — <reason>`. In the gated layout these are the
trace chain of `skills/shared/doc-flow/SKILL.md` § Trace Chain.]
- **PRD rules**: [`PRD-<section>-R<n>`, … — or "none — <reason>" (development layout: "none — no PRD")]
- **Contract**: [`docs/specs/<feature>-contract.md`, or "none — <reason>" (e.g. the spec-gate Gate Rule did not fire)]
- **Flow**: [`docs/design/flows/<feature>.md`, or "none — <reason>" (e.g. no UI)]

### Acceptance Criteria

**Scenario S1: [name]**
- Given [initial state]
- When [action]
- Then [expected outcome]

**Scenario S2: [edge case or error state]**
- Given [initial state]
- When [action]
- Then [expected outcome]

[Repeat one Given/When/Then block per scenario. This is the only definition of "done" — nothing
outside these blocks is in scope for implementation or QA. IDs (`S1`, `S2`, …) are stable: never
renumber or reuse one — a removed scenario keeps its ID retired. Sprint tasks cite them in
`**Covers**:` and tests carry `[spec:<feature>#S<n>]` (see `skills/shared/spec-gate/SKILL.md`).]

### Out of Scope
- [What this feature explicitly does NOT cover — be specific about the boundary]

### Dependencies
- **Depends on**: [other spec, or "none"]
- **Blocks**: [other spec that needs this one first, or "none"]

### Amendment Log
[Empty until execution amends this spec. One line per amendment — see `skills/shared/spec-gate/SKILL.md` § Living Spec.]
- YYYY-MM-DD | [agent] | [what changed] | [why]

---
Review the criteria above — tell me if anything needs to change before this becomes a sprint task.
