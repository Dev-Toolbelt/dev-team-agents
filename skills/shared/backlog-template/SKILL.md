---
name: backlog-template
description: Backlog — epics, sprints, tasks, DoD, dependencies, estimates.
---

# Backlog Template

## Document Structure

Generate the following files under `.claude/docs/backlog/`:

### `overview.md`
```markdown
# Project: [Name]

## Objective
[One paragraph: what problem this solves, for whom, and the expected outcome]

## Stakeholders
| Role | Name / Team | Responsibility |
|------|------------|----------------|
| Product Owner | ... | Prioritization, acceptance |
| Tech Lead | ... | Architecture, code quality |
| Dev Team | ... | Implementation |

## Constraints
- **Deadline**: [date or "not defined"]
- **Budget**: [if relevant]
- **Tech restrictions**: [e.g., "must integrate with legacy X"]
- **Compliance**: [LGPD, GDPR, PCI, etc.]

## Out of Scope
- [Explicit list of what will NOT be built in this phase]
```

### `dod.md` — Definition of Done
```markdown
# Definition of Done

A task is DONE when ALL of the following are true:

## Code
- [ ] Implements the acceptance criteria completely
- [ ] No known bugs introduced
- [ ] Code reviewed and approved
- [ ] Linters pass (no errors)
- [ ] No hardcoded secrets or sensitive data

## Tests (if project requires)
- [ ] Unit/integration tests written for new logic
- [ ] All existing tests pass
- [ ] Coverage does not decrease

## Documentation
- [ ] Public APIs documented (if applicable)
- [ ] README updated if setup steps changed
- [ ] ADR written if an architectural decision was made

## Deployment
- [ ] Works in the target environment
- [ ] No regressions in adjacent features
```

### `epics.md`
```markdown
# Epics

## Epic 1 — [Name]
**Goal**: [What this epic delivers]
**Acceptance Criteria**:
- [ ] ...
- [ ] ...

**Estimated effort**: [S / M / L / XL]
**Priority**: [High / Medium / Low]
**Dependencies**: [Epic X, external system Y]

---
## Epic 2 — [Name]
...
```

### `sprint-NN.md`

**One file per sprint.** Each sprint gets its own file: `sprint-01.md`, `sprint-02.md`, etc. Never merge multiple sprints into one file.

```markdown
# Sprint NN — [Theme]

**Goal**: [What should be achievable at the end of this sprint]
**Start**: YYYY-MM-DD
**End**: YYYY-MM-DD
**Estimated duration**: N weeks
**Agents**: [list of agents that will act in this sprint — see Agent Assignment table below]

## Tasks

### TASK-001 — [Name]
**Epic**: Epic 1
**Type**: [Feature | Fix | Chore | Spike]
**Agent**: [agent name — see Agent Assignment table]
**Estimate**: [hours or story points]
**Depends on**: [TASK-XXX or "none"]
**Status**: [ ] Pending

**Description**:
[What needs to be done — technical enough for a developer to start]

**Acceptance Criteria**:
- [ ] ...
- [ ] ...

---
### TASK-002 — [Name]
...

## Sprint Summary
| Tasks | Count |
|-------|-------|
| Total | N |
| Feature | N |
| Fix | N |
| Chore | N |
| Estimated total | Nh / N pts |
```

### Agent Assignment Table

When generating sprint files, use this table to assign agents to tasks. Multiple agents can be listed when tasks require collaboration.

| Task type | Primary agent | Secondary agent |
|-----------|--------------|----------------|
| API endpoint / service / business rule | `backend-developer` | `database-specialist` (if schema involved) |
| Frontend screen / component / UI flow | `frontend-developer` | `ui-ux-designer` (if new UI pattern) |
| Database schema / migration / query optimization | `database-specialist` | `backend-developer` |
| Design system / UX flow / visual spec | `ui-ux-designer` | — |
| CI/CD / Docker / infra / deploy | `devops-specialist` | — |
| Backend tests | `backend-test-specialist` | — |
| Frontend tests | `frontend-test-specialist` | — |
| Security audit / vulnerability fix | `security-specialist` | `software-architect` |
| Architecture decision / refactor | `software-architect` | relevant developer |
| Documentation / changelog / runbook | `technical-writer` | — |
| Full-stack feature | `backend-developer` + `frontend-developer` | `database-specialist` (if schema) · `ui-ux-designer` (if UI) |

At the top of each sprint file, list all agents that will be active in that sprint under the `**Agents**:` field.

## Time Estimation Guidelines

Use these benchmarks as starting points — adjust based on team familiarity with the stack:

| Size | Description | Typical range |
|------|-------------|---------------|
| XS | Config change, minor text fix | 0.5–1h |
| S | Simple CRUD endpoint or UI form | 2–4h |
| M | Feature with business logic + tests | 4–8h |
| L | Complex feature, multiple components | 1–3 days |
| XL | Epic-level effort, architectural impact | 1–2 weeks |

**Always add buffer**: multiply raw estimate × 1.3 for unknowns.

When generating sprint estimates, also provide:
- **Sprint total**: sum of all task estimates
- **Delivery forecast**: start date + total duration = expected completion date
- **Risk callout**: tasks with external dependencies or high uncertainty

## Dependency Notation

In task descriptions, always call out upstream dependencies:
- `Depends on: TASK-003` — cannot start until TASK-003 is done
- `Depends on: external API contract` — blocked by third party
- `Parallel with: TASK-005` — can run concurrently
