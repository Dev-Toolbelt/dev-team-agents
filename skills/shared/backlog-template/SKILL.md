---
name: backlog-template
description: Backlog — epics, sprints, tasks, DoD, dependencies, estimates.
---

# Backlog Template

## Document Structure

Generate under `docs/backlog/`:

- `overview-<scope-slug>.md` — business requirements document, one per planned scope (the planning deliverable). `<scope-slug>` is the scope name in kebab-case, 2–4 words (`checkout-coupons`). Re-planning the same scope updates its file; a second planned scope gets its own file; it never overwrites or merges into another scope's overview.
- `epics-<scope-slug>.md` — epics of that scope
- `dod.md` — Definition of Done, shared by every scope
- `sprints/` — one file per sprint, named after its scope, plus one status index for all scopes (see below)

Every per-scope file carries the same `<scope-slug>` as its overview. Legacy unscoped files (`overview.md`, `epics.md`, `sprints/sprint-<n>.md`) are kept as is and read as one more scope — never renamed or deleted.

**Sprint files live in the `sprints/` subfolder**, never at the backlog root:

```
docs/backlog/
├── overview-<scope-slug>.md
├── epics-<scope-slug>.md
├── dod.md
└── sprints/
    ├── sprints.md                  ← index: every sprint of every scope + status
    ├── <scope-slug>-sprint-1.md
    ├── <scope-slug>-sprint-2.md
    └── ...
```

### `overview-<scope-slug>.md`
```markdown
# Scope: [Name]

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
- [ ] Implements the acceptance criteria completely — the `Covers` scenarios of the linked spec, or the task's own criteria when it has no spec
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

### `epics-<scope-slug>.md`
```markdown
# Epics

## Epic 1 — [Name]
**Goal**: [What this epic delivers]
**Specs**: [`docs/specs/<feature>.md`, … — the epic's criteria live there, never restated here]

**Estimated effort**: [S / M / L / XL]
**Priority**: [High / Medium / Low]
**Dependencies**: [Epic X, external system Y]

---
## Epic 2 — [Name]
...
```

### `sprints/<scope-slug>-sprint-<n>.md`

**One file per sprint**, in the `sprints/` subfolder: `sprints/<scope-slug>-sprint-1.md`, `sprints/<scope-slug>-sprint-2.md`, etc. Numbering restarts at 1 for each scope. Never merge multiple sprints into one file.

```markdown
# Sprint <n> — [Theme]

**Goal**: [What should be achievable at the end of this sprint]
**Start**: YYYY-MM-DD
**End**: YYYY-MM-DD
**Estimated duration**: N weeks
**Agents**: [list of agents that will act in this sprint — see Agent Assignment table below]

## Parallel Execution Plan

Tasks are grouped into **waves**. Every task in the same wave is mutually
independent and can be built **in parallel**, each in its own git worktree
(and its own isolated Docker stack when the project uses Docker — see below).
A wave starts only after every task in the previous wave is done.

| Wave | Tasks (parallel) | Blocks (why the next wave waits) |
|------|------------------|----------------------------------|
| A | TASK-001, TASK-002 | Wave B needs the schema from TASK-001 |
| B | TASK-003, TASK-004 | — |

**Isolation model:**
- **Worktree per task** — always. Each task gets its own branch/worktree so
  parallel tasks never touch the same working tree.
- **Isolated infra per worktree** — **only when the project uses Docker**
  (a compose file exists). Then each worktree runs its own namespaced Docker
  Compose stack (isolated containers, volumes, networks, host ports), so
  parallel tasks don't collide on services or ports. **No Docker → skip this;
  parallelism is achieved by worktree alone.**

## Tasks

### TASK-001 — [Name]
**Epic**: Epic 1
**Type**: [Feature | Fix | Chore | Spike]
**Agent**: [agent name — see Agent Assignment table]
**Estimate**: [hours or story points]
**Wave**: A
**Worktree branch**: [suggested `<context>/<brief-title>`, e.g. `feat/user-schema`]
**Spec**: [`docs/specs/<feature>.md` (+ `-contract.md` if the gate fired), or "none — see spec-gate skip reason"]
**Covers**: [scenario IDs from the spec this task delivers, e.g. `S1, S3` — omit when Spec is "none"]
**Depends on**: [TASK-XXX or "none"]
**Status**: [ ] Pending  <!-- [ ] Pending → [~] In progress → [x] Done; the executing command updates it -->

**Description**:
[What needs to be done — technical enough for a developer to start]

**Acceptance Criteria**: [only when Spec is "none" — a spec-linked task's criteria are its `Covers` scenarios, never a second copy]
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
| Waves | N |
| Max parallelism | N tasks (largest wave) |
| Estimated total | Nh / N pts |
```

**Covers rule**: every scenario of a linked spec is cited by at least one task's `Covers` — a scenario no task covers is a planning gap, not an implicit extra. Status flips are owned by the executing command (`skills/shared/spec-gate/SKILL.md` § Task Resolution).

### `sprints/sprints.md` — status index

A single index at `docs/backlog/sprints/sprints.md` summarizing **every** sprint of every scope and its status. An existing index without the Scope column gets it added in place, with `legacy` on the rows already there — never a rewritten table. Create it when the first sprint is generated and **keep it current** — flip a sprint's status as it moves forward, and set it to `Done` in the same pass that finalizes the sprint.

```markdown
# Sprints

| Scope | Sprint | Theme | Goal (one line) | Status |
|-------|--------|-------|-----------------|--------|
| [scope-slug] | [sprint-1]([scope-slug]-sprint-1.md) | [Theme] | [What it delivers] | Planned |
| [scope-slug] | [sprint-2]([scope-slug]-sprint-2.md) | [Theme] | [What it delivers] | Planned |
```

Status values: **Planned → In progress → Done**.

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

`devteam backlog lint` checks this graph mechanically, and `devteam backlog ready` derives the ready frontier and the waves it implies. A prose dependency (`external API contract`) cannot be evaluated: it is reported as the task's `external_note` and never holds the task back — whoever starts the task checks it.

**Design for parallelism.** Keep the dependency graph as flat as possible so
each wave holds as many tasks as it can. A task with `Depends on: none` belongs
to Wave A; a task moves to a later wave only when it truly cannot start before
another task finishes. When two tasks *would* collide (same file, same schema),
prefer splitting the work so they land in the same wave over serializing them —
only serialize when the dependency is real.
