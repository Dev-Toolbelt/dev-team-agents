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

Reference global documents by ID, never restate them: an endpoint already described in the
`api-contracts` doc, and every table/field described in the `data-model` doc (`docs/api-contracts.md`
and `docs/data-model.md` in the gated layout; resolve either with `bash .dev-team-agents/scripts/doc-path.sh <key>`),
is cited by its entry ID or heading anchor. Only what this feature adds or changes is written out here —
and the same change is made in the owner doc (`skills/shared/doc-flow/SKILL.md` § Owner Rule).

**[METHOD /path or event name]** — covers S1, S2 — [`api-contracts` entry ID, or "new"]
- **Request**: [fields, types, required/optional]
- **Response**: [fields, types, status codes]
- **Errors**: [code → condition, in the project's error format]

### Schema
[`data-model` entry IDs this feature reads or changes, plus only the fields it adds or alters (types,
constraints). "none" when no storage changes.]

### Error Format
[A pointer to the project's existing error format in the `api-contracts` doc, or the shape every error above follows when the project has none yet.]

### Dependency Order
[Which spec or layer must land first, and why — the technical order `depends_on` alone does not express.]

### Open Points
[Unresolved interface questions, one bullet each. Must hold zero points before any task linking this
contract is Ready (`skills/shared/doc-flow/SKILL.md` § Definition of Ready) — `scripts/spec-lint.sh`
reads this heading. Zero points is no bullet, or the single bullet `- none`.]
- none

### Amendment Log
[Empty until execution amends this contract. Only software-architect writes here — see `skills/shared/spec-gate/SKILL.md` § Living Spec.]
- YYYY-MM-DD | software-architect | [what changed] | [why]
