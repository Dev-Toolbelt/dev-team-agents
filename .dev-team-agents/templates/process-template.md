<!--
CANONICAL PROCESS DOC. Installed at .dev-team-agents/templates/process-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Copied by /devteam:setup to the `process` doc (docs/process.md in the gated layout) for the humans on
the project. The rule itself lives in skills/shared/doc-flow/SKILL.md; when the two disagree, the skill
wins. The Owner Table mirrors the gated column of .dev-team-agents/scripts/lib/doc-layouts.json and
tests/test_process_template_mirror.py fails on drift — change the map first, then this table.
-->
# Process — [Product Name]

## Flow
Every stage stops at its exit gate until the user approves. Any stage may correct an earlier document
through that document's Amendment Log.

| Stage | Produces | Owner | Exit gate |
|---|---|---|---|
| 0 Raw inputs | `source/YYYY-MM-DD-<topic>.md` | product-analyst | Saved, dated, open questions listed inside |
| 1 Product | `prd.md`, `glossary.md`, `nfr.md` | product-analyst | No open question affects scope; user approves |
| 2a Technical | `trd.md` (index), architecture, tech stack, data model, API contracts, code standards, threat model, ADRs | software-architect | ADRs accepted, schema reviewed, threat model drafted, security sign-off |
| 2b Design (parallel to 2a, after PRD approval) | `design/tokens.json`, `design/design-system.md`, `design/prototypes/`, `design/screens/` | ui-ux-designer | Tokens approved; every screen has every state via `?state=`; PNGs approved |
| 3 Reconciliation | Fixes to 2a / 2b documents | software-architect + ui-ux-designer | Reconciliation checklist below passes |
| 4 Feature | `specs/<feature>.md`, `specs/<feature>-contract.md`, `design/flows/<feature>.md`, `ai/evals.md` (LLM only), `testing.md` | product-analyst, software-architect, ui-ux-designer | All complete for the feature; contract has zero open points |
| 5 Plan | `backlog.md`, `backlog/overview-<scope-slug>.md`, `backlog/sprints/<scope-slug>-sprint-<n>.md` | product-analyst | Every scenario ID covered; every task ready; dependency graph acyclic |
| 6 Implementation | Code, tests, owner-doc updates in the same PR | software-architect orchestrates | Definition of Done |
| 7 Learn | Wiki, ADRs, amendment logs (`/devteam:learn`) | — | At feature close and sprint close |

## Reconciliation Checklist
- [ ] Every field a screen shows or submits ↔ an endpoint field in `api-contracts.md` and a column in `data-model.md`
- [ ] Every screen action ↔ an endpoint and a permission
- [ ] Every screen error state ↔ an error the endpoint returns
- [ ] Every visual value ↔ a token in `design/tokens.json`
- [ ] Every screen term and every table / endpoint name ↔ a `glossary.md` row

## Definition of Ready
- [ ] Spec approved; the task cites its scenario IDs
- [ ] Contract has no open points
- [ ] No open question in `source/` affects the task
- [ ] Required ADRs accepted
- [ ] Frontend task: flow file exists and every state PNG is approved
- [ ] AI task: eval cases and thresholds exist
- [ ] Required fixtures exist

## Read-only Inputs
`source/` and `design/prototypes/` accept new dated files only — never an edit, rename, or delete.

## Owner Table
Paths are relative to the docs root (`context_paths[0]`, `docs` by default).

| Key | Path | Owner | Read-only |
|---|---|---|---|
| `source` | `source/` | `product-analyst` | yes |
| `prd` | `prd.md` | `product-analyst` | no |
| `glossary` | `glossary.md` | `product-analyst` | no |
| `nfr` | `nfr.md` | `product-analyst` | no |
| `trd` | `trd.md` | `software-architect` | no |
| `architecture` | `architecture.md` | `software-architect` | no |
| `tech-stack` | `tech-stack.md` | `software-architect` | no |
| `code-standards` | `code-standards.md` | `software-architect` | no |
| `reuse-guidelines` | `reuse-guidelines.md` | `software-architect` | no |
| `data-model` | `data-model.md` | `software-architect` | no |
| `api-contracts` | `api-contracts.md` | `software-architect` | no |
| `threat-model` | `security/threat-model.md` | `software-architect` | no |
| `adr` | `adr/` | `software-architect` | no |
| `conformance-report` | `conformance-report.md` | `software-architect` | no |
| `design-tokens` | `design/tokens.json` | `ui-ux-designer` | no |
| `design-system` | `design/design-system.md` | `ui-ux-designer` | no |
| `design-prototypes` | `design/prototypes/` | `ui-ux-designer` | yes |
| `design-screens` | `design/screens/` | `ui-ux-designer` | no |
| `design-flows` | `design/flows/` | `ui-ux-designer` | no |
| `specs` | `specs/` | `product-analyst` | no |
| `evals` | `ai/evals.md` | `software-architect` | no |
| `testing` | `testing.md` | `software-architect` | no |
| `process` | `process.md` | `software-architect` | no |
| `backlog-index` | `backlog.md` | `product-analyst` | no |
| `dod` | `backlog.md` | `product-analyst` | no |
| `overview` | `backlog/` | `product-analyst` | no |
| `sprints` | `backlog/sprints/` | `product-analyst` | no |
| `project` | `project.md` | `setup-assistant` | no |
| `wiki` | `wiki/` | `technical-writer` | no |
| `infrastructure` | `devops/infrastructure.md` | `devops-specialist` | no |

## Pacing
- Design system and navigation are approved before the plan (stage 5).
- Per-feature prototypes and state PNGs land one sprint ahead of their implementation.

[Override the pacing here if this project needs a different cadence.]
