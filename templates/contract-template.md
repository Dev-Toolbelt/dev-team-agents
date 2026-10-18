<!--
CANONICAL CONTRACT FORMAT. Installed at .dev-team-agents/templates/contract-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by software-architect at docs/specs/<feature>-contract.md, only when the spec-gate
Gate Rule fires. Interface only — no business rule, no product decision.
See skills/shared/spec-gate/SKILL.md for the gate rule and the amendment protocol.
-->
---
spec: <feature>.md # the business spec this contract serves
---

## Contract — [Feature Name]

### Interfaces
[One block per endpoint, message, or function boundary the spec introduces or changes.]

**[METHOD /path or event name]** — covers S1, S2
- **Request**: [fields, types, required/optional]
- **Response**: [fields, types, status codes]
- **Errors**: [code → condition, in the project's error format]

### Schema
[Tables/collections/fields added or changed, with types and constraints. "none" when no storage changes.]

### Error Format
[The shape every error above follows, or a pointer to the project's existing one in `docs/development/api-contracts.md`.]

### Dependency Order
[Which spec or layer must land first, and why — the technical order `depends_on` alone does not express.]

### Amendment Log
[Empty until execution amends this contract. Only software-architect writes here — see `skills/shared/spec-gate/SKILL.md` § Living Spec.]
- YYYY-MM-DD | software-architect | [what changed] | [why]
