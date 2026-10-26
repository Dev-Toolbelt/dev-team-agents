---
name: doc-flow
description: Gated pre-implementation doc flow — stages, owners, trace chain, DoR, read-only inputs.
---

# Doc Flow

The documentation flow a **new** system walks before and during implementation. It applies only when the
project's layout is `gated` (§ Doc Layout); the `development` layout keeps today's flow unchanged.
`/devteam:plan` walks it (§ Stages); every other agent reads the rows that concern its role.

## Principles

| # | Principle | What it means in practice |
|---|---|---|
| 1 | Raw inputs are immutable | Meetings, brainstorms and design exports are saved as dated files and never edited. Working docs derive from them and cite them row by row — § Read-only Inputs, § Stages → Stages 0 and 1 |
| 2 | Single owner per fact | Every fact category has one owning document; every other doc links to it by ID. A change goes to the owner doc first, in the same PR as the code, with an amendment entry — § Owner Rule, § Amendment Log, and the "One source of truth" rule of `skills/shared/docs-sync/SKILL.md` |
| 3 | Stable IDs form a trace chain | A rule, an NFR, a scenario and a task each carry an ID that is never renumbered or reused — § Trace Chain |
| 4 | Iterative, not waterfall | Any stage may push a correction upstream, through the owner doc's amendment log. A later stage never works around an earlier doc it believes is wrong |
| 5 | Gaps block | An open question, an undrawn screen state, or a contract with an open point fails the Definition of Ready — § Definition of Ready |

## Doc Layout

| Item | Rule |
|---|---|
| Signal | `.dev-team-agents/project.json` key `docs_layout` ∈ {`development`, `gated`}. Absent means `development` |
| Who sets `gated` | `/devteam:setup` on FIRST_RUN of a new project. An existing project switches only through the opt-in migration (§ Migration) |
| Map | `.dev-team-agents/scripts/lib/doc-layouts.json` — one key per fact category, with its owning path per layout, owner agent and `readonly` flag. It is the only list of doc paths; this skill names keys and shows the gated path for orientation |
| Resolve a path | `bash .dev-team-agents/scripts/doc-path.sh <key>` prints `<write-root>/<path>`, or nothing when the layout has no such doc. `--layout` prints the layout; `--readonly` prints the read-only paths and `--writable` the writable owner-doc paths, one per line |
| Write root | `context_paths[0]` of `project.json` (`docs` by default). Every path in the map is relative to it |
| `development` layout | Today's behavior, byte for byte: `docs/development/…`, `docs/backlog/README.md`, `docs/backlog/sprints/sprints.md`. § Stages does not apply |
| Hardcoded paths | A `docs/development/<x>` path written anywhere in an agent, skill or command means the path the map resolves for that key — `skills/shared/project-context/SKILL.md` § Doc Layout |

## Stages

Gated layout only. Each stage ends at its exit gate. Stage 0's gate is mechanical — no user approval — and
stage 0 runs back to back with stage 1. Every other gate **stops for user approval**, and that approval is
the plan approval a command asks of its spawned agents (its PLAN GATE, or the provider's plan mode): a stage needs no separate plan, and saving a raw input needs none. A
stage run by a sub-agent returns its gate as an Open Decision, relayed per
`skills/shared/interaction-patterns/SKILL.md` § Sub-agent Question Relay — never approved on the user's behalf.

| Stage | Produces (map key → gated path) | Template | Owner | Exit gate |
|---|---|---|---|---|
| 0 Raw inputs | `source` → `docs/source/YYYY-MM-DD-<topic>.md` (shape in Stages 0 and 1 below) | — | `product-analyst` | Saved, dated, its open questions listed inside — mechanical, no approval |
| 1 Product | `prd` → `docs/prd.md` (rules `PRD-<section>-R<n>`, each citing its source; `## Assumptions` of `[A<n>]`) · `glossary` → `docs/glossary.md` · `nfr` → `docs/nfr.md` (`provisional` / `approved`) | `.dev-team-agents/templates/prd-template.md` · `.dev-team-agents/templates/glossary-template.md` · `.dev-team-agents/templates/nfr-template.md` | `product-analyst` | The user answers the question round and approves the drafts; the answers are saved as a new source file, no open question affects scope, the documents are set `approved` |
| 2a Technical | `trd` → `docs/trd.md` (index only) · `architecture` · `tech-stack` · `data-model` → `docs/data-model.md` · `api-contracts` · `code-standards` · `threat-model` → `docs/security/threat-model.md` · `adr` → `docs/adr/ADR-NNNN-*.md` | `.dev-team-agents/templates/trd-template.md` · `.dev-team-agents/templates/data-model-template.md` · `.dev-team-agents/templates/threat-model-template.md` · `.dev-team-agents/templates/adr-template.md` | `software-architect`; `database-specialist` reviews the schema; `security-specialist` provides findings (read-only) and the architect — or `technical-writer` on delegation — writes the threat model | ADRs accepted, schema reviewed, threat model drafted, security sign-off |
| 2b Design | `design-tokens` → `docs/design/tokens.json` (W3C Design Tokens) · `design-system` → `docs/design/design-system.md` · `design-prototypes` → `docs/design/prototypes/<feature>/<YYYY-MM-DD>/` · `design-screens` → `docs/design/screens/<feature>/<screen>--<state>.png` | — | `ui-ux-designer` | Tokens approved, no unconfirmed value; every feature screen has every state (loading, empty, error, forbidden, plus feature-specific) reachable via `?state=`; the user approves the PNGs |
| 3 Reconciliation | Fixes to the 2a and 2b owner docs | checklist in the `process` doc | `software-architect` + `ui-ux-designer` | § Reconciliation holds |
| 4 Feature | `specs` → `docs/specs/<feature>.md` and `<feature>-contract.md` · `design-flows` → `docs/design/flows/<feature>.md` · `evals` → `docs/ai/evals.md` (only when the product uses LLMs) · `testing` → `docs/testing.md` | `.dev-team-agents/templates/spec-template.md` · `.dev-team-agents/templates/contract-template.md` · `.dev-team-agents/templates/design-flow-template.md` · `.dev-team-agents/templates/evals-template.md` | `product-analyst` (spec) · `software-architect` (contract, evals, testing) · `ui-ux-designer` (flow) | Every document is complete for the feature; the contract has zero open points |
| 5 Plan | `backlog-index` → `docs/backlog.md` (global DoD, DoR, one row per sprint) · `overview` → `docs/backlog/overview-<scope-slug>.md` (deliveries + links only) · `sprints` → `docs/backlog/sprints/<scope-slug>-sprint-<n>.md` (DoD by link + sprint additions) | `skills/shared/backlog-template/SKILL.md` | `product-analyst` | Every scenario ID covered by at least one task; every task passes § Definition of Ready; the dependency graph is acyclic (`devteam backlog lint`) |
| 6 Implementation | Code, tests and owner-doc updates in the same PR | — | `software-architect` orchestrates | Definition of Done plus § Definition of Done Additions |
| 7 Learn | Wiki entries, ADRs, amendment logs | — | `/devteam:learn` | Run at feature close and again at sprint close |

| Ordering rule | Detail |
|---|---|
| 2b starts after PRD approval | It runs **in parallel** with 2a, never before stage 1's gate |
| 3 needs both | Reconciliation starts only when 2a and 2b have both passed their gates |
| 4 is per feature | Each feature passes stage 4 on its own; stage 5 plans only features that passed it |
| Upstream corrections | Any stage may reopen an earlier owner doc through its amendment log (Principle 4); the earlier gate is re-approved for the changed part only |
| The `process` doc | `docs/process.md` is copied from `.dev-team-agents/templates/process-template.md` on setup and carries this flow for humans; this skill stays the rule |

Stage 4 reuses the spec layer whole: format, `status`, the contract Gate Rule, scope lock and
`[SPEC-DRIFT]` belong to `skills/shared/spec-gate/SKILL.md`.

### Stages 0 and 1

| Item | Rule |
|---|---|
| Source file shape | A short header (title, date, participants or source), `## Input` holding the raw text verbatim, then `## Open Questions`. That framing is what "as received" allows; nothing else is added or condensed |
| Source file name | `YYYY-MM-DD-<topic>.md`, dated by the input itself (the meeting date), not the intake date. Same date and topic → suffix `-2`, `-3` |
| Language | `## Input` stays in its original language; `## Open Questions` (and `## Answers`) are written in English — `skills/shared/project-context/SKILL.md` § Language Policy |
| Question IDs | `Q<n>` within its file, cited everywhere as `<source-file>#Q<n>` |
| Answers | A **new** dated source file whose `## Answers` lists `<source-file>#Q<n>: <answer>`. A question is open until a later source file answers it; the file that raised it is never edited |
| Citations | `docs/source/<file>.md § Input` (or a heading inside it). A rule derived from the analyst's own default cites the question that raised it, `<file>#Q<n>` plus its `[A<n>]` — that is a valid source |
| Write order | Stage 1 documents are written as `status: draft`, every unconfirmed default tagged `[A<n>]` (the assumption IDs of `skills/shared/discovery-mode/SKILL.md`) and listed in the PRD's `## Assumptions`. The stage 1 gate is the scope approval that discovery-mode's and product-analyst's HARD-GATE require; nothing past stage 1 starts before it. This replaces, for stage 1 only, the "write nothing that depends on the answers" rule of interaction-patterns § Sub-agent Question Relay, which keeps governing non-gated planning |
| Questioning | One consolidated round in the stage owner's style (`product-analyst` Step 4: few `AskUserQuestion` calls, blocking decisions first). Only the HARD-GATE and the `[A<n>]` IDs come from discovery-mode — not its one-question-per-message pacing |
| NFR status | `approved` — the stage 1 gate approved that target, whoever stated it; `provisional` — still an assumption |
| Source Synthesis Rule | `skills/shared/docs-templates/SKILL.md`'s rule applies to working docs, never to stage 0 files. Owner docs cite per row in a Source column instead of a `## Source References` section |

## Trace Chain

Every downstream ID cites the upstream one it serves. A link that cannot be followed is a gap (Principle 5).

| Link | ID form | Lives in | Cites |
|---|---|---|---|
| Source | `docs/source/<file>.md` § Input (or a heading inside it) | `source` | — |
| Open question | `<source-file>#Q<n>` | `source` | — |
| Assumption | `[A<n>]` | `prd` § Assumptions | the question it answers by default |
| Product rule | `PRD-<section>-R<n>` | `prd` | source § Input, or `<file>#Q<n>` + `[A<n>]` |
| Non-functional requirement | `NFR-<nn>` | `nfr` | PRD rule or source |
| Scenario | `<feature>#S<n>` | `specs` | PRD rule IDs, NFR IDs |
| Contract section | `<feature>-contract.md` § `<heading>` | `specs` | scenario IDs; `data-model` and `api-contracts` entries by ID |
| Task | `TASK-NNN` | `sprints` | spec, contract, flow, ADR, `**Covers**:` scenario IDs |
| Test | `[spec:<feature>#S<n>]` | the test file | scenario ID — spec-gate § Traceability |

IDs are stable: never renumbered, never reused; a retired ID stays retired. PRD, NFR and glossary ID
formats are template conventions, checked by review; `scripts/spec-lint.sh` checks the spec layer
(spec-gate) and, in this layout, only the mechanical rows of § Definition of Ready.

## Owner Rule

| Rule | Detail |
|---|---|
| One owner | Each key in `doc-layouts.json` names its single owning document and owner agent. The map is the owner table; `docs/process.md` mirrors its gated column |
| Link, never copy | Another doc refers to an owned fact by ID or link (`PRD-auth-R3`, `data-model` § `orders`), never by restating it |
| Numbers | Retention periods, SLA and latency targets and other measured values are owned by `nfr`. A PRD rule links the NFR instead of restating the number: "Closed accounts are erased within the retention of `NFR-04`", not "within 30 days" |
| Change order | A change goes to the owner doc **first**, in the **same PR** as the code that depends on it, with an § Amendment Log entry |
| Non-owner finds a defect | Flags it to the owner agent (or the user); it does not edit the owner doc itself — the interface-level rule of spec-gate § Living Spec, applied to every owner doc |

## Amendment Log

Every owner doc in the gated layout ends with an `### Amendment Log` in the format and under the rules of
`skills/shared/spec-gate/SKILL.md` § Living Spec — Amendment Protocol (one line per change, a reason is
mandatory). The log starts empty: creating a document, and edits before its first approval, are not
logged, and a template ships an HTML comment explaining the format instead of a placeholder line — except the spec and contract templates, whose log format and placeholder handling spec-gate owns. An
amendment never changes a doc's status; the gate that accepted the doc re-approves the changed part.

## Read-only Inputs

| Item | Rule |
|---|---|
| Paths | Every key flagged `readonly` in the map — today `source` (`docs/source/`) and `design-prototypes` (`docs/design/prototypes/`). `doc-path.sh --readonly` lists them |
| Allowed | Creating a **new** dated file or folder (intake, design import) |
| Refused | Editing, overwriting, renaming or deleting an existing file there |
| A correction | A new dated file that supersedes the old one, cited from the working doc |
| Enforcement | By rule here and by `scripts/hooks/pre-tool-use/05-readonly-docs-guard.sh` |

## Design-tool Rule

| Rule | Detail |
|---|---|
| Visual reference only | A prototype is never production code. Implementation is rewritten with the project's real components and tokens |
| Tokens win | `design-tokens` is canonical. A value outside it means the token is updated (with user approval) or the prototype is wrong |
| Import check | On import, the importing agent diffs the prototype against the tokens and lists: values with no token, missing states, fields not in `api-contracts`, actions with no permission |
| Fidelity | Built screens follow the approved PNGs under the fidelity rule of `/devteam:relayout` (§ 1): references define *what*, the design system defines *how* |
| Tool choice | Out of scope — any tool whose export can be saved to the prototypes folder |

## Reconciliation

Stage 3 checklist, run jointly by `software-architect` and `ui-ux-designer`. Each miss is fixed in the
2a or 2b owner doc, with an amendment entry.

| Check | Passes when |
|---|---|
| Field coverage | Every field a screen shows or submits maps to an endpoint field in `api-contracts` and a column in `data-model` |
| Action coverage | Every screen action maps to an endpoint and a permission |
| State coverage | Every error state on a screen maps to an error the endpoint can return |
| Token coverage | Every visual value in the prototypes and screens maps to a token in `design-tokens` |
| Glossary | Every term on a screen and every table or endpoint name has its `glossary` row |

## Definition of Ready

A task enters a sprint only when all apply. `scripts/spec-lint.sh` checks the mechanical rows in the gated
layout; the rest are checked by `product-analyst` at stage 5.

| Applies to | Ready when |
|---|---|
| Every task | The spec is `approved` and the task cites its scenario IDs |
| Every task | The contract, when one exists, has no open points |
| Every task | No open question in `source` affects the task — open until a later source file answers it (§ Stages → Stages 0 and 1) |
| Every task | The ADRs it needs are `Accepted` |
| Every task | The fixtures it needs exist |
| Frontend task | Its `design-flows` file exists and every state PNG it lists is `approved` |
| AI task | Its `evals` section exists with cases and thresholds |

## Definition of Done Additions

Added to the project's DoD (`dod` key) in the gated layout.

| Applies to | Done also requires |
|---|---|
| Every task | Tests cite the scenario IDs they cover (`[spec:<feature>#S<n>]`) |
| Every task | Affected owner docs are updated in the same PR, with amendment entries |
| Frontend task | A screenshot of the built screen is compared against the approved PNG and stored as the visual-regression baseline — tooling per stack is out of scope |
| AI task | The eval suite passes its thresholds |

## Pacing

Default, overridable per project in its `process` doc:

| Item | When |
|---|---|
| Design system and navigation | Approved before stage 5 |
| Per-feature prototypes and state PNGs | One sprint ahead of the sprint that implements them — enforced by the frontend row of § Definition of Ready |

## Migration

Moving an existing `development`-layout project to `gated`: `references/migration.md`.
