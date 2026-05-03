---
name: adr
description: Architecture Decision Records (ADR) authoring and management. Use when documenting architectural decisions, technology choices, design patterns adopted, or any significant technical decision that affects the project long-term. Follows the MADR (Markdown Architectural Decision Records) format.
---

# Architecture Decision Records (ADR)

ADRs document significant architectural decisions — the context, what was decided, why, and what was considered and rejected.

## File Location

```
.claude/docs/development/adrs/
  adr-001-database-choice.md
  adr-002-api-design-approach.md
  adr-003-authentication-strategy.md
```

## MADR Format

```markdown
# [Short title of the decision]

**Status**: [Proposed | Accepted | Deprecated | Superseded by ADR-XXX]
**Date**: YYYY-MM-DD
**Deciders**: [names or roles involved]

## Context

[Describe the issue motivating this decision, including forces at play: technical, political, social, project constraints. Be factual — no judgment yet.]

## Decision

[State the decision in active voice: "We will use X because..."]

## Rationale

[Explain why this option was chosen over the alternatives. Link to evidence, benchmarks, or constraints that drove the decision.]

## Alternatives Considered

### Option A — [Name]
- **Pros**: ...
- **Cons**: ...
- **Why rejected**: ...

### Option B — [Name]
- **Pros**: ...
- **Cons**: ...
- **Why rejected**: ...

## Consequences

**Positive**: [What becomes easier or possible]
**Negative**: [What becomes harder, what debt is accepted]
**Risks**: [What could go wrong, and how to mitigate]
```

## When to Write an ADR

Write an ADR when the decision:
- Is hard to reverse (database engine, auth strategy, monolith vs microservices)
- Affects multiple components or teams
- Has non-obvious reasoning that future developers will question
- Involves a significant tradeoff

Skip ADRs for: library versions, code style rules, trivial configuration.

## Status Lifecycle

`Proposed` → `Accepted` → (if superseded) `Deprecated` / `Superseded by ADR-XXX`

When superseding an ADR, update the old one's status and link to the new one.

## Tips

- Keep it short — 1-2 pages max
- Write it at decision time, not after implementation
- "We will" not "We should" — ADRs record decisions, not recommendations
- Link ADRs from `CLAUDE.md` or `development/architecture.md` so they're discoverable
