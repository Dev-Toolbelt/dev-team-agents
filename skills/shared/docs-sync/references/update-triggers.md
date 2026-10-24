# Docs Sync — Update Triggers

When work is delivered, patch the corresponding doc section immediately. Use the smallest possible Edit — one table row, one bullet, one field.

## Trigger Table

Every fact routes to exactly **one** owning doc (`skills/shared/doc-flow/SKILL.md` § Owner Rule). The
"Doc to patch" column is a key from `scripts/lib/doc-layouts.json`; resolve its path with
`bash .dev-team-agents/scripts/doc-path.sh <key>`. Rows marked *gated* apply only when that key
resolves to a path (empty output = the layout has no such doc — skip the row).

| Work delivered | Doc to patch (key) | Section |
|---------------|-------------|---------|
| New dep installed (language, framework, lib) | `tech-stack` | Tech Stack table |
| New service or module created | `architecture` | Module Map |
| New API endpoint or contract defined | `api-contracts` — never `architecture` | Endpoints |
| Schema migration applied | `data-model` — never `architecture` | Data Dictionary and the area's ER diagram |
| New code pattern established | `code-standards` | Patterns in Use |
| New linter/formatter rule added | `code-standards` | Detected Config |
| Sprint file created | `backlog-readme` (development) · `backlog-index` (gated) | Sprint Files · sprint row |
| New UI component added | `design-system` | Component Inventory |
| New color or typography token | `design-system` (development) · `design-tokens` (gated) | relevant section · token entry |
| Task completed touching a directory | `project` | Active Areas |
| Environment deployed for the first time, taken down, or its URL changed | `project` | Environments / status |
| Sprint closed, or the project moved to a new phase (MVP shipped, maintenance) | `project` | Current phase |
| Backlog or tracker moved to another location | `project` | Where work is tracked |
| Plan document implemented, abandoned, or replaced | the plan itself | `**Status:**` line — see `SKILL.md` § Document Lifecycle |
| ADR created, superseded, or deprecated | `adr` directory `README.md` | Index row — see `skills/shared/adr/SKILL.md` § ADR Index |
| Architectural layer added or renamed | `architecture` | Layers |
| Product rule added, changed, or retired *(gated)* | `prd` | Rule row `PRD-<section>-R<n>` with its source |
| Domain term introduced or renamed *(gated)* | `glossary` | Term row |
| Non-functional target set or its status changed *(gated)* | `nfr` | `NFR-<nn>` row |
| Technical doc added, moved, or retired *(gated)* | `trd` | Index link |
| New trust boundary, threat, or personal-data flow *(gated)* | `threat-model` | Boundary section / personal-data map |
| Screen flow added or changed *(gated)* | `design-flows` | `<feature>.md` |
| State screenshot approved *(gated)* | `design-screens` | `<feature>/<screen>--<state>.png` |
| LLM task, eval case, metric, or threshold changed *(gated)* | `evals` | The AI task's section |
| Test level, tooling, or fixture strategy changed | `testing` | relevant section |
| Stage gate, Definition of Ready, or owner table changed *(gated)* | `process` | relevant section |
| Sprint closed or global DoD/DoR changed *(gated)* | `backlog-index` | Sprint row · DoD · DoR |
| Non-obvious domain behavior discovered | `wiki` → `wiki/<domain>/<topic>.md` | New or updated wiki entry |
| User designates a specific component/class/helper, file location, or design rule as mandatory going forward | `reuse-guidelines` | New registry row — see `skills/shared/reuse-guidelines/SKILL.md` |
| User explicitly asks to standardize, note, or remember something (general convention, not a specific reusable component/path/rule) | `wiki/<domain>/<topic>.md` or `code-standards` | User-triggered wiki write |

An owner doc that changes after its stage gate was approved also gets an `## Amendment Log` row
(`skills/shared/doc-flow/SKILL.md` § Amendment Log).

---

## Update Protocol

1. **Read** the target file completely before writing anything
2. **Identify** only the section that changed — one table row, one bullet, one field
3. **Edit** using the smallest possible `old_string` → `new_string` diff (Edit tool, not Write)
4. **Update** `<!-- last-updated: YYYY-MM-DD -->` on line 1 in the same edit
5. **Check line count** — if the file now exceeds its budget, remove the oldest or least-relevant entries in the same patch

**Never:**
- Write the entire file when only one section changed
- Add a "Changelog" or "History" section to any doc — the only exception is the `## Amendment Log` of an owner doc (`skills/shared/doc-flow/SKILL.md` § Amendment Log)
- Copy content verbatim from one doc to another (link instead)
- Create sections not defined in the schema without explicit user approval
- Leave a section with only a heading and no content — omit the heading instead

---

## User-Intent Triggers — Write Immediately

When the user's message matches any of these patterns, **treat it as an explicit wiki write request** — do not wait for the task to finish.

### Convention / Standardization Signals

| Pattern (PT) | Pattern (EN) | What to capture |
|---|---|---|
| "convencione …" | "establish as convention …" | The convention name, rule, and why |
| "coloque como padrão …" | "set as project standard …" | The pattern, its scope, and any exceptions |
| "torne padrão …" | "make the standard …" | The decision, rationale, and affected files/layers |
| "adote como padrão …" | "adopt as standard …" | Same as above |
| "defina como padrão …" | "define as the standard …" | The rule and where it applies |
| "a partir de agora … sempre" | "from now on … always" | The behavioral rule being established |
| "sempre que … faça …" | "whenever … do …" | The trigger → action pair as a project rule |
| "nunca mais …" / "não faça mais …" | "never again …" / "stop doing …" | The anti-pattern and why it was banned |
| "use somente …" / "apenas …" | "only use …" | The enforced choice and what it replaces |

### Memory / Note-Taking Signals

| Pattern (PT) | Pattern (EN) | What to capture |
|---|---|---|
| "anote isso …" | "note this …" | The fact or rule verbatim |
| "não esqueça …" | "don't forget …" | The constraint or reminder |
| "guarde essa informação …" | "save this information …" | The piece of knowledge |
| "registre que …" | "record that …" | The statement being registered |
| "lembre(-se) que …" | "remember that …" | The rule or fact |
| "isso é importante …" | "this is important …" | The highlighted rule or fact |
| "para referência futura …" | "for future reference …" | The reference material |

### Approval / Confirmation Signals

| Pattern | What to capture |
|---|---|
| "sim, siga esse padrão" / "yes, follow that pattern" | The pattern as an established convention |
| "exato, sempre assim" / "exactly, always like that" | The confirmed approach as a project rule |
| "pode adotar isso" / "you can adopt that" | The decision, now official |
| "fica assim então" / "let's go with that" | The finalized decision |

### Where to write user-triggered entries

0. **Check this first**: does the statement name a specific component, class, helper, file location, or design rule that must now be reused/followed project-wide (e.g. "use o componente XPTO em todo o projeto", "arquivos de upload sempre em xpto/pasta", "botões da seção X sempre à esquerda")? If so, this is a `reuse-guidelines` entry, not a wiki/code-standards one — run the classify → propose → confirm → append routine in `skills/shared/reuse-guidelines/SKILL.md` § Growing the Registry instead of the steps below. Confirm with: _"Catalogado em `docs/development/reuse-guidelines.md` — regra `<name>`."_
1. Use `code-standards.md` (`## Patterns in Use` or `## Anti-Patterns`) for code conventions
2. Use a wiki entry (`wiki/<domain>/<topic>.md`) for domain rules, behavioral constraints, or multi-layer decisions
3. If unsure which document fits, prefer the wiki — it is the more flexible format
4. Confirm with: _"Noted — recorded in `wiki/<domain>/<topic>.md`."_
