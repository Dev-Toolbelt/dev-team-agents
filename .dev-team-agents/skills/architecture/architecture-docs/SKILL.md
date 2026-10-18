---
name: architecture-docs
description: Where architecture documents live, what each contains, and the conformance report format.
---

# Architecture Documents

Canonical location, content contract, and conformance reporting format for the documents an
architect produces. Load when writing, updating, or validating any of them.

---

## Document Location Rule — CRITICAL

**All architecture documents MUST be written to `docs/development/` at the project root.**

| Document | Location |
|----------|----------|
| Architecture design | `docs/development/architecture.md` |
| Tech stack decisions | `docs/development/tech-stack.md` |
| Code standards | `docs/development/code-standards.md` |
| Database decisions | `docs/development/database.md` |
| API contracts | `docs/development/api-contracts.md` |
| ADRs | `docs/development/adrs/NNNN-*.md` |
| Conformance reports | `docs/development/conformance-report.md` |

**NEVER write architecture documents to:**

- `.opencode/` — opencode configuration only
- `.claude/` — Claude Code configuration only
- `.dev-team-agents/` — the framework installation directory
- Any hidden directory (starting with `.`)

---

## Content Contract per Document

| Document | Must contain |
|----------|--------------|
| `architecture.md` | System design, layers, component boundaries, integration patterns, and the layer depth chosen **per domain area**. Every significant decision also gets an ADR. |
| `tech-stack.md` | Chosen technologies with rationale, including what was considered and **rejected**. |
| `code-standards.md` | Patterns, naming conventions, linting rules, and design patterns — specific to this project's stack, not generic advice. |
| `database.md` | Database choice, schema strategy, migration approach, indexing guidelines. Finalize only after `database-specialist` review. |
| `api-contracts.md` | API style (REST/GraphQL/RPC), versioning policy, auth model, response and error envelope. |

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

Write to `docs/development/conformance-report.md`. **This file accumulates across sprints —
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
