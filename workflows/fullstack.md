# Workflow — Full-Stack Feature

Use when a feature requires coordinated backend and frontend changes. Phases run sequentially; agents within a phase run in parallel where noted.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:fullstack` runs this workflow.

---

## Phase 1 — Planning

Send both prompts in a single message to run them in parallel:

| Step | Agent | Par. |
|------|-------|------|
| 1 | software-architect | A |
| 2 | product-analyst | A |
| 3 | database-specialist _(if schema changes)_ | B |

```
Prompt: "As the software-architect, load project context and produce a technical
         design for: [feature description]. Include API contracts, component boundaries,
         and any cross-cutting concerns."

Prompt: "As the product-analyst, load project context and define acceptance criteria
         for: [feature description]. List user stories and edge cases."
```

If schema changes are needed, after steps 1–2 complete:

```
Prompt: "As the database-specialist, review the architect's design and propose the
         required schema changes or migrations."
```

▶ CHECKPOINT — await: architecture design + acceptance criteria (+ schema proposal if applicable)

---

## Phase 2 — Implementation

Send backend and frontend prompts in a single message to run in parallel:

| Step | Agent | Par. |
|------|-------|------|
| 4 | backend-developer | A |
| 5 | frontend-developer | A |
| 6 | database-specialist _(if migrations needed)_ | B |
| 7 | ui-ux-designer _(if new UI patterns needed)_ | B |

```
Prompt: "As the backend-developer, implement the backend for: [feature].
         Follow the architecture design from Phase 1."

Prompt: "As the frontend-developer, implement the frontend for: [feature].
         Follow the architecture design and acceptance criteria from Phase 1."
```

Steps 6 and 7 are independent and can run after or alongside 4–5 as needed.

▶ CHECKPOINT — await: backend + frontend implementation complete

---

## Phase 3 — Quality Gate

Send all prompts in a single message:

| Step | Agent | Par. |
|------|-------|------|
| 8 | backend-test-specialist | A |
| 9 | frontend-test-specialist | A |
| 10 | code-reviewer | B |

```
Prompt: "As the backend-test-specialist, write tests for the new backend logic
         and verify all acceptance criteria are covered."

Prompt: "As the frontend-test-specialist, write tests for the new frontend
         components and verify all acceptance criteria are covered."
```

After tests pass, send:

```
Prompt: "As the code-reviewer, review the full-stack implementation. Check for
         correctness, consistency between layers, and adherence to project standards."
```

Any [BLOCKING] finding requires a fix plan before proceeding.

▶ CHECKPOINT — await: tests passing + no blocking review findings

---

## Phase 4 — Commit & PR

```
Prompt: "/devteam:commit"
```

Then:

```
Prompt: "Please open a PR for these changes."
```

Or use `/devteam:pr` directly.

---

## Recovery Paths

| Failure point | Recovery |
|---------------|---------|
| Backend and frontend designs conflict | Re-run `software-architect` with both outputs as input; resolve before continuing |
| Schema change invalidates backend implementation | Re-run `database-specialist` + `backend-developer` in parallel |
| Blocking review finding | Spawn `backend-developer` or `frontend-developer` for targeted fix, then re-run `code-reviewer` |
| Tests fail after implementation | Run the relevant test-specialist again with the failure output |

---

## Workflow Closure

☐ Architecture design approved
☐ Acceptance criteria defined
☐ Backend and frontend implemented
☐ Tests written and passing
☐ Code review passed (no [BLOCKING] findings)
☐ Commit and PR created
☐ Session summary written

**Related workflows and commands:**
- `/devteam:fullstack` — command shortcut for this workflow
- `/devteam:backend` — backend-only changes → `workflows/` (no dedicated file; use agent directly)
- `/devteam:frontend` — frontend-only changes
- Need a security review? → `workflows/security-patch.md`
- Post-merge refactoring? → `workflows/refactor.md`
