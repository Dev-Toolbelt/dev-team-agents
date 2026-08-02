<!--
CANONICAL SPEC FORMAT. Installed at .dev-team-agents/templates/spec-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by product-analyst, business-level only — no stack, schema, or API shape.
See skills/shared/spec-gate/SKILL.md for the gate rule and scope-lock contract.
-->
---
touches: [] # subset of [backend, frontend, database, mobile] — only layers that actually change
depends_on: [] # other spec filenames this one needs, or leave empty
---

## Spec — [Feature Name]

### User Story
As a [role], I want [capability], so that [outcome].

### Context
[One or two sentences: what triggered this feature and how it fits the approved `overview.md` scope.]

### Acceptance Criteria

**Scenario: [name]**
- Given [initial state]
- When [action]
- Then [expected outcome]

**Scenario: [edge case or error state]**
- Given [initial state]
- When [action]
- Then [expected outcome]

[Repeat one Given/When/Then block per scenario. This is the only definition of "done" — nothing
outside these blocks is in scope for implementation or QA.]

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
