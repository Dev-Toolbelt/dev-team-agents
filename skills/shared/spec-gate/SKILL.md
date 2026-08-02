---
name: spec-gate
description: Spec layer between overview.md and sprints — testable criteria, auto contract gate.
---

# Spec Gate

Sits between `docs/backlog/overview.md` (business scope) and `docs/backlog/sprints/` (execution
plan). One spec per feature/capability, written by `product-analyst`, in business language but with
a testable acceptance format. It becomes the scope boundary every downstream agent reads instead of
re-interpreting the overview or the sprint task description.

## Document Structure

```
docs/specs/
├── <feature>.md            ← business spec (product-analyst)
└── <feature>-contract.md   ← technical contract (software-architect, only when the gate fires)
```

## `<feature>.md` — Spec File

Structure from `templates/spec-template.md` (installed: `.dev-team-agents/templates/spec-template.md`):

- **Frontmatter**: `touches: [backend, frontend, database, mobile]` (layers this feature affects —
  list only the ones that actually change), `depends_on: [<feature>, ...]` (other specs this one
  needs, or `[]`)
- **User Story**: as a [role], I want [capability], so that [outcome]
- **Acceptance Criteria**: one or more `Given / When / Then` blocks — this is the only place
  "done" is defined; nothing outside it is in scope
- **Out of Scope**: explicit exclusions, same discipline as `overview.md`

No stack, schema, or API shape in this file — that is the contract's job, not the spec's.

## Gate Rule (mechanical, not requested)

Immediately after `product-analyst` writes a spec, evaluate:

```
touches.length > 1  OR  the spec introduces a new API/schema/integration point
```

**True** → the command spawns `software-architect` automatically to write
`<feature>-contract.md`. This does not require the user to ask for technical input — the gate
replaces that dependency. `software-architect` writes **only** the interface: request/response
shapes, schema fields, error format, and the technical dependency order between specs. It does not
touch `overview.md`, does not restate the business rule, and does not make product decisions.

**False** (single layer, no new integration surface) → skip the contract; the sprint task links the
spec alone.

## Scope Lock — Execution Agents

Every coding agent (`backend-developer`, `frontend-developer`, `mobile-developer`,
`database-specialist`) reads the spec (and contract, if one exists) linked from its sprint task
**before** writing code, and treats the `Given/When/Then` blocks as the implementation boundary:

- Implement what the criteria require — nothing the criteria don't cover.
- If the task seems to need something the spec doesn't state (a field, a flow branch, an error
  case), **stop and ask** — via `AskUserQuestion` if it has a finite set of reasonable answers,
  otherwise flag it to the user in plain text. Do not assume and proceed.
- If the spec and its contract disagree, the contract wins on interface shape; a business
  contradiction goes back to `product-analyst`, not a silent implementation choice.

<HARD-GATE>
A feature is never marked implemented or `done` while an open assumption remains. Every assumption
made during execution resolves, before hand-off, to exactly one of: an answered question, a spec
amendment (see Living Spec below), or an explicit blocker stated to the user. "I assumed X and moved
on" is not a valid end state at any severity — this holds even when the assumption turned out
correct.
</HARD-GATE>

## QA Validation

`qa-specialist` validates behavior against the linked spec's `Given/When/Then` blocks — the same
criteria the execution agent read, not a re-derived interpretation of the sprint task or the
original request. A criterion the spec doesn't cover is out of scope for the PASS/FAIL verdict;
note it as an exploratory finding instead (see `test-strategy` skill).

## Living Spec — Amendment Protocol

The spec stays the source of truth **after** implementation too. When execution discovers that
reality doesn't match a `Given/When/Then` — a missing scenario, a wrong assumption, a field that
needs to change — the spec is **amended in place**, never silently coded around and never abandoned.

- **Business-level divergence** (the criteria are wrong or incomplete, no interface shape changes):
  the executing agent (`backend-developer`, `frontend-developer`, `mobile-developer`,
  `database-specialist`) edits the spec's `Acceptance Criteria` / `Out of Scope` directly.
- **Interface-level divergence** (a contract exists and the schema/API shape no longer holds): the
  executing agent does **not** edit `<feature>-contract.md` itself — it flags the mismatch to the
  user and `software-architect`, who amends the contract.
- Either way, append one line to the spec's `### Amendment Log`:
  `- YYYY-MM-DD | <agent> | <what changed> | <why>`. An amendment with no logged reason does not
  count — the spec is stale, not living, until the log entry exists.
- Amending is not optional when a real divergence is confirmed — an agent that implements around a
  stale criterion without updating it has violated the scope lock above just as much as one that
  implemented something the spec never asked for.

## Spec Sync Gate (mandatory, end of work)

Before the mandatory review handoff (`code-reviewer` + `qa-specialist`) on a spec-linked task is
considered complete, `qa-specialist` verifies:

1. Every `Given/When/Then` in the spec still matches what was actually built.
2. Every `Amendment Log` entry carries a reason — no blank or placeholder entries.

Report a mismatch as `[SPEC-DRIFT]` in the QA Report and treat it as a `[BLOCKER]` — deploy is
blocked until the spec is corrected, not until the QA report is edited to match the code.

## Sprint Linkage

Each `TASK-NNN` in a sprint file (`backlog-template` skill) carries a `**Spec**:` field pointing at
`docs/specs/<feature>.md` (and `<feature>-contract.md` when it exists). Task ordering across waves
respects `depends_on` from the linked specs, not just file-level collisions.
