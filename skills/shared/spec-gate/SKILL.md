---
name: spec-gate
description: Spec layer between the scope overview and sprints — testable criteria, auto contract gate.
---

# Spec Gate

Sits between `docs/backlog/overview-<scope-slug>.md` (business scope) and `docs/backlog/sprints/` (execution
plan). One spec per feature/capability, written by `product-analyst`, in business language but with
a testable acceptance format. It becomes the scope boundary every downstream agent reads instead of
re-interpreting the overview or the sprint task description.

## Document Structure

```
docs/specs/
├── <feature>.md            ← business spec (product-analyst)
└── <feature>-contract.md   ← technical contract (software-architect, only when the gate fires)
```

`scripts/spec-lint.sh` checks both files and the sprint tasks that link them — § Mechanical Check.

## `<feature>.md` — Spec File

Structure from `templates/spec-template.md` (installed: `.dev-team-agents/templates/spec-template.md`):

- **Frontmatter**: `status:` (§ Spec Status), `touches: [backend, frontend, database, mobile]` (layers this feature affects —
  list only the ones that actually change), `depends_on: [<feature>, ...]` (other specs this one
  needs, or `[]`)
- **User Story**: as a [role], I want [capability], so that [outcome]
- **Acceptance Criteria**: one or more `Given / When / Then` blocks, each headed
  `**Scenario S<n>: <name>**` — this is the only place "done" is defined; nothing outside it is in
  scope. IDs are stable: never renumbered, never reused; a removed scenario's ID stays retired
- **Out of Scope**: explicit exclusions, same discipline as the scope overview

No stack, schema, or API shape in this file — that is the contract's job, not the spec's.

## Gate Rule (mechanical, not requested)

Immediately after `product-analyst` writes a spec, evaluate:

```
touches.length > 1  OR  the spec introduces a new API/schema/integration point
```

**True** → the orchestrating main conversation spawns `software-architect` automatically to write
`<feature>-contract.md` from `.dev-team-agents/templates/contract-template.md`. This does not require the user to ask for technical input — the gate
replaces that dependency. `software-architect` writes **only** the interface: request/response
shapes, schema fields, error format, and the technical dependency order between specs. It does not
touch the scope overview, does not restate the business rule, and does not make product decisions.

**False** (single layer, no new integration surface) → skip the contract; the sprint task links the
spec alone.

## Spec Status

| Status | Set by | When |
|---|---|---|
| `draft` | `product-analyst` | The spec is written |
| `approved` | `product-analyst`, or the command that stopped on the `draft` spec | The user approved its criteria (relayed by `/devteam:plan` or `/devteam:spec`, or asked at the draft stop below) |
| `implemented` | whichever command marks a task `[x] Done` (§ Task Resolution) | Every scenario of the spec is cited by a `[x] Done` task's `**Covers**:` and no `[SPEC-DRIFT]` is open |
| `implemented` (retroactive) | `product-analyst`, at the Close of `/devteam:spec` | Every scenario ID's latest `qa-specialist` verdict is `matches` (§ Retroactive Spec) |

- Execution starts only from an `approved` or `implemented` spec. A linked `draft` spec stops the
  command before any agent is spawned: ask the user to approve it (`AskUserQuestion`) or run
  `/devteam:plan` on it — never implement against unapproved criteria.
- An amendment (Living Spec below) never changes `status`; the Amendment Log records it. A business
  amendment still needs the user's confirmation of the new criteria before execution continues —
  that confirmation is the gate, not a status change.
- A spec with no `status:` key predates this field: treat it as `approved`. The edit that adds the
  key also gives every scenario its `S<n>` ID — from then on `spec-lint` blocks a missing one.

## Task Resolution

A command that receives a sprint task instead of a free-text description resolves it before
anything else:

| `$ARGUMENTS` names | Resolve to |
|---|---|
| `TASK-NNN` | The one `### TASK-NNN` block under `docs/backlog/sprints/` — two matches across scopes → ask which scope (`AskUserQuestion`) |
| A sprint file or `<scope-slug> <n>` | Every task of that sprint — this is `/devteam:sprint`'s input; a single-task command asks which task |
| A spec path | The spec itself, with no task |

From the task, read `**Spec**:` (spec, plus contract when listed) and `**Covers**:` (the scenario
IDs this task delivers; a task written before the field existed covers the whole spec). The task's
scope is **those scenarios only** — the Scope Lock below
applies to them, not to the whole spec. A task whose `**Spec**:` is `none` keeps its own
`**Acceptance Criteria**:` and runs without this skill's gates.

The implementation commands (`backend`, `frontend`, `fullstack`, `mobile`, `fix`) flip the task's
`**Status**:` — `[~] In progress` when they spawn its agents, `[x] Done` at session close only when
no BLOCKER is open (`fix`: after its review gate; a declined review leaves `[~]`) — and mirror the sprint's row in `docs/backlog/sprints/sprints.md` (`In progress`
on the first task, `Done` on the last). `/devteam:sprint` sets `[x] Done` after the task's merge
instead (its Step 5). `qa` and `tester` read the task and never flip it. Right after marking a task
Done, the same command checks its spec against the `implemented` row of § Spec Status and sets
`status: implemented` when it holds.

When a spec was resolved, every `qa-specialist` prompt carries the spec path, the contract path when
one exists, and the task's `**Covers**:` IDs — that is what the Spec Sync Gate runs on.

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

## Test-First Derivation (mechanical, not requested)

When a command's test gate resolves to running tests (`TESTS_REQUIRED=yes` or the key absent) **and** the task links a spec, tests are written **before** the implementing developer agent runs, not after:

1. The test author for the track — `backend-test-specialist`, `frontend-test-specialist`, or `mobile-developer` for Flutter/native suites — reads the spec's `Given/When/Then` blocks (only the task's `**Covers**:` IDs when a task was resolved) — the same ones the developer will treat as the implementation boundary — and writes one failing test per scenario, tagged per § Traceability. No implementation exists yet; these tests assert against the interface described in the spec (and contract, if one exists), not against code.
2. These tests are expected to fail (red) — that is the point. Commit them as-is; do not adjust assertions to make them pass against a stub.
3. Only after the red tests exist does the developer agent implement, iterating until every derived test is green plus the rest of its own scope.
4. On a spec that touches several layers, each track's test author derives only the scenarios whose `Then` is observable at its layer (the spec's `touches` and the contract say which) — a scenario is never tested twice at two layers for the same assertion.
5. If a `Given/When/Then` block cannot be turned into a concrete assertion (the criterion is genuinely ambiguous about expected output, not just under-specified on an edge case), that is the `<HARD-GATE>` in Scope Lock firing early — stop and ask, do not write a vague or tautological test to move forward.

Every implementation command applies this per track: backend, frontend, and mobile alike. A track whose tests the developer agent writes itself (`mobile-developer` on Flutter/native) runs it as two spawns of that agent — tests only, then implementation.

This does not replace the Scope Lock rule above — the developer still treats the spec as the boundary — it only moves the test-specialist's read of the spec to before the code instead of after. Commands without a linked spec, or with `TESTS_REQUIRED=no`, are unaffected and keep the existing test-after order.

## Traceability

Every test derived from a scenario carries the token `[spec:<feature>#S<n>]`, where `<feature>` is
the spec's filename without `.md`:

- In the test's description string when the framework has one (`it('[spec:checkout#S2] rejects an
  expired card', …)`, `@DisplayName`, a pytest `ids=`/docstring).
- Otherwise in a one-line comment directly above the test — the exception `comments-policy`
  records for this token.
- One test may carry several tokens; a scenario may be covered by several tests.

The token is how the Spec Sync Gate maps criteria to evidence, and how `spec-lint` reports an
`implemented` spec whose scenario no test references.

## Retroactive Spec

A feature that already exists gets its spec through `/devteam:spec <feature>`, never through
`/devteam:plan` (which scopes new work). Same format, same IDs, same statuses — no extra key. The
§ Gate Rule does not run: the interface already exists, so a contract is written only on request.

| Step | Owner | Rule |
|---|---|---|
| Draft | `product-analyst` | Reads the code, tests, and docs of the feature and writes `status: draft`. Scenarios describe behavior observable from outside — what a user or client does and sees — never the code path. A behavior with more than one plausible reading is an Open Decision, not a guess |
| Approve | `product-analyst`, on the user's approval | `status: approved` — verification starts only from here |
| Verify | `qa-specialist` | Executes the feature against **every** scenario ID and returns one verdict each: `matches`, or `diverges` with what it observed. A scenario it could not exercise is `diverges` with the reason — never left out. Read-only |
| Decide | the user, per `diverges` ID | **Describe current behavior** → `product-analyst` rewrites the scenario as built, logged `- YYYY-MM-DD \| product-analyst \| S<n> rewritten as built \| retroactive: user accepted the observed behavior`; the user confirms the new wording, and `qa-specialist` re-verifies that ID. **Keep the intended behavior** → the scenario stays and is a bug, offered as `/devteam:fix`; never fixed inside this flow |
| Tag | the test author per `touches` layer (§ Test-First Derivation, step 1) | Runs only after Decide, on the final wording. Adds `[spec:<feature>#S<n>]` to existing tests that already assert a scenario — description string or one-line comment only, no assertion changed — and lists the scenarios no test covers. Missing tests are offered only for `matches` scenarios, written only on the user's choice, change no production code, and a new test that fails today turns its scenario back into `diverges` |
| Close | `product-analyst` | Sets `status: implemented` when every ID's latest verdict is `matches`; otherwise leaves `approved` and names the IDs holding it there |

A rewrite as built is a business amendment (Living Spec below) and, like every amendment, does
not change the status — the Close row does, from the verdicts. Scenarios left untested because the
user declined new tests are accepted: `spec-lint` keeps warning about them, and the summary lists
them.

**Offer, never run.** When `/devteam:qa`, or `/devteam:fix` on a non-trivial bug, targets an
existing feature that has no spec, it offers `/devteam:spec <feature>` with `AskUserQuestion`
(offer first, continue without as the second option). An accepted offer runs `/devteam:spec`
through its Close step, skips its own `/devteam:fix` offers, and hands back to the calling command
with the spec linked.

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
  `database-specialist`, or `product-analyst` in a retroactive spec) edits the spec's
  `Acceptance Criteria` / `Out of Scope` directly.
- **Interface-level divergence** (a contract exists and the schema/API shape no longer holds): the
  executing agent does **not** edit `<feature>-contract.md` itself — it flags the mismatch to the
  user and `software-architect`, who amends the contract and logs it in the contract's own
  `### Amendment Log`.
- Either way, append one line to the spec's `### Amendment Log`:
  `- YYYY-MM-DD | <agent> | <what changed> | <why>`. An amendment with no logged reason does not
  count — the spec is stale, not living, until the log entry exists.
- Amending is not optional when a real divergence is confirmed — an agent that implements around a
  stale criterion without updating it has violated the scope lock above just as much as one that
  implemented something the spec never asked for.

## Spec Sync Gate (mandatory, end of work)

Before the mandatory review handoff (`code-reviewer` + `qa-specialist`) on a spec-linked task is
considered complete, `qa-specialist` verifies:

1. Every `Given/When/Then` in the spec still matches what was actually built — and, when
   `TESTS_REQUIRED` is not `no`, at least one test carries its `[spec:<feature>#S<n>]` token. A
   scenario with no token is reported as uncovered, not silently passed.
2. Every `Amendment Log` entry carries a reason — no blank or placeholder entries.

Report a mismatch as `[SPEC-DRIFT]` in the QA Report and treat it as a `[BLOCKER]` — deploy is
blocked until the spec is corrected, not until the QA report is edited to match the code.

**Accepted drift is not the end of the story.** A `[SPEC-DRIFT]` blocker resolves one of two ways:
the code is changed to match the spec, or the user explicitly accepts the built behavior and the
spec is amended to match it (Living Spec above). The second case is a standardization decision, not
just a spec fix — if the accepted behavior represents a pattern the team wants to hold onto (a naming
convention, a reusable shape, a path rule), route it to `skills/shared/reuse-guidelines/SKILL.md`
(via `/devteam:rule` or its passive-capture path) in addition to the Amendment Log entry. The
Amendment Log records that this spec changed; the registry is what stops the same drift from
recurring silently in the next feature.

## Sprint Linkage

Each `TASK-NNN` in a sprint file (`backlog-template` skill) carries a `**Spec**:` field pointing at
`docs/specs/<feature>.md` (and `<feature>-contract.md` when it exists) and a `**Covers**:` field
listing the scenario IDs it delivers. The task does not restate the criteria — the spec is their
only home. Task ordering across waves respects `depends_on` from the linked specs, not just
file-level collisions.

## Mechanical Check

`scripts/spec-lint.sh` (installed: `.dev-team-agents/scripts/spec-lint.sh`) runs from the Stop hook
and on demand. It is a no-op when `docs/specs/` does not exist.

| Blocks (exit 1) | Warns only |
|---|---|
| `status`/`touches` outside their allowed values | A spec with no frontmatter or no `status:` key (legacy) — its structural findings, missing `depends_on` targets included, are reported here too |
| A scenario without an `S<n>` ID, or a duplicated ID | An `implemented` spec's scenario no test references — skipped when `TESTS_REQUIRED=no` |
| `depends_on` naming a missing spec, or a dependency cycle | |
| An Amendment Log line with an empty or placeholder reason | |
| A task's `**Spec**:` path missing, or a `**Covers**:` ID absent from that spec | |
| A `<feature>-contract.md` with no `<feature>.md` beside it | |

Fix what it reports in the spec or the task — never by deleting the scenario or the log line.
