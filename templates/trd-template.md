<!--
CANONICAL TRD FORMAT. Installed at .dev-team-agents/templates/trd-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by software-architect at the `trd` doc (docs/trd.md in the gated layout), stage 2a of
skills/shared/doc-flow/SKILL.md. An INDEX OF LINKS ONLY — no rule, decision, or schema detail
lives here; each fact stays in its owner document.
-->
# Technical Reference — [Product Name]

| Document | Owns | Status |
|---|---|---|
| [Architecture](architecture.md) | System design, layers, module map | [draft · approved] |
| [Tech stack](tech-stack.md) | Chosen technologies, rationale, rejected alternatives | [draft · approved] |
| [Data model](data-model.md) | Data Model Specification — ER diagrams, data dictionary, PII tags | [draft · reviewed] |
| [API contracts](api-contracts.md) | API style, versioning, auth model, every endpoint | [draft · approved] |
| [Code standards](code-standards.md) | Patterns, naming, linting | [draft · approved] |
| [Threat model](security/threat-model.md) | Threats per trust boundary, personal-data map | [draft · signed off] |
| [ADRs](adr/README.md) | Architecture decisions | [n accepted] |
| [Testing](testing.md) | Testing strategy | [draft · approved] |
| [Evals](ai/evals.md) | LLM eval cases and thresholds — only when the product uses LLMs | [draft · approved] |

[Delete a row the product does not need. Links are relative to the docs root.]
