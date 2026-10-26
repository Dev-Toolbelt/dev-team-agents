---
name: architecture-docs
description: Where architecture documents live, what each contains, and the conformance report format.
---

# Architecture Documents

Canonical location, content contract, and conformance reporting format for the documents an
architect produces. Load when writing, updating, or validating any of them.

---

## Document Location Rule — CRITICAL

**Every architecture document is written to the path the doc-layout map resolves for its key.**
`scripts/lib/doc-layouts.json` is canonical — this table mirrors it for reading convenience; when
they disagree, the JSON wins. Resolve a path with `bash .dev-team-agents/scripts/doc-path.sh <key>`
(empty output means the project's layout has no such doc). Paths are relative to the docs write
root (`docs/` by default). Layout rules: `skills/shared/doc-flow/SKILL.md` § Doc Layout.

| Key | `development` layout (default) | `gated` layout |
|-----|-------------------------------|----------------|
| `trd` | — | `docs/trd.md` |
| `architecture` | `docs/development/architecture.md` | `docs/architecture.md` |
| `tech-stack` | `docs/development/tech-stack.md` | `docs/tech-stack.md` |
| `code-standards` | `docs/development/code-standards.md` | `docs/code-standards.md` |
| `data-model` | `docs/development/database.md` | `docs/data-model.md` |
| `api-contracts` | `docs/development/api-contracts.md` | `docs/api-contracts.md` |
| `threat-model` | — | `docs/security/threat-model.md` |
| `adr` | `docs/development/adrs/NNNN-*.md` | `docs/adr/ADR-NNNN-*.md` |
| `evals` | — | `docs/ai/evals.md` |
| `testing` | `docs/tests/testing-strategy.md` | `docs/testing.md` |
| `conformance-report` | `docs/development/conformance-report.md` | `docs/conformance-report.md` |

The ADR directory is always whatever `new-adr.sh --dir` prints (`skills/shared/adr/SKILL.md`).

**NEVER write architecture documents to:**

- `.opencode/` — opencode configuration only
- `.claude/` — Claude Code configuration only
- `.dev-team-agents/` — the framework installation directory
- Any hidden directory (starting with `.`)

---

## Content Contract per Document

| Key | Must contain |
|-----|--------------|
| `trd` | Index of the technical documents only — one link per doc with a one-line purpose. No rule-level detail. |
| `architecture` | System design, layers, component boundaries, integration patterns, and the layer depth chosen **per domain area**. Links to `data-model` and `api-contracts`; never repeats them. Every significant decision also gets an ADR. |
| `tech-stack` | Chosen technologies with rationale, including what was considered and **rejected**. |
| `code-standards` | Patterns, naming conventions, linting rules, and design patterns — specific to this project's stack, not generic advice. |
| `data-model` | **Data Model Specification**: database choice, logical overview, one Mermaid `erDiagram` per domain area, data dictionary (table, column, type, constraint, meaning), PII tags per column, migration approach, indexing guidelines. Template: `.dev-team-agents/templates/data-model-template.md`. Finalize only after `database-specialist` review. |
| `api-contracts` | API style (REST/GraphQL/RPC), versioning policy, auth model, response and error envelope, every endpoint. |
| `threat-model` | Threats per trust boundary and the personal-data map, from `security-specialist` findings. Template: `.dev-team-agents/templates/threat-model-template.md`. |
| `evals` | Only when the product uses LLMs: eval cases, metrics and pass thresholds per AI task. |
| `testing` | Testing strategy — levels, tooling, fixtures, what runs where. |

**Owner rule** — one fact, one owning doc (`skills/shared/doc-flow/SKILL.md` § Owner Rule): schema
facts live only in `data-model`, endpoints only in `api-contracts`. `architecture` and `trd` link to
them by section or ID, never repeat them.

**Spec self-review before handing off** — silently check every document for: placeholders and
TODOs, contradictions between documents, ambiguous decisions, YAGNI violations, and scope creep.
Fix inline before asking the user to review.

---

## Conformance Report

Produced or updated after each Quality Gate run. Flag every finding with one tag:

| Tag | Meaning |
|---|---|
| `[ARCH-DEVIATION]` | The code does not follow the decided architecture |
| `[TECH-DEBT]` | Acceptable shortcut, but it must be tracked |
| `[CONFORMANT]` | This is correct |

Write to the `conformance-report` doc (path from the table above). **This file accumulates across sprints —
append, never overwrite.**

```markdown
## Conformance Report — [Sprint / Date]

### Summary
[Overall conformance posture — 1-2 sentences]

### Deviations
| File / Area | Deviation | Severity | Action |
|---|---|---|---|
| service/OrderService.js | Business logic in controller | HIGH | Refactor before next sprint |

### Tech Debt Tracked
| Item | Introduced | Owner | Target Sprint |
|---|---|---|---|

### Conformant Areas
[List areas that were reviewed and passed]
```
