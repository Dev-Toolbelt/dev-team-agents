---
status: draft # draft → approved (the user approved it at the stage 1 gate)
---

<!--
CANONICAL NFR FORMAT. Installed at .dev-team-agents/templates/nfr-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by product-analyst at the `nfr` doc (docs/nfr.md in the gated layout), stage 1 of
skills/shared/doc-flow/SKILL.md. software-architect may propose targets at stage 2a; the user approves.
-->
# Non-Functional Requirements — [Product Name]

| ID | Category | Requirement | Target | How measured | Status | Source |
|---|---|---|---|---|---|---|
| NFR-01 | [performance · availability · security · privacy · accessibility · scalability · other] | [what must hold] | [number with unit, e.g. "p95 < 300 ms"] | [tool, metric, environment] | provisional | [`PRD-<section>-R<n>` or `docs/source/[YYYY-MM-DD-topic].md` § heading] |

[IDs are `NFR-<nn>`, never renumbered or reused. This doc owns every number (retention, SLA, latency);
PRD rules link the ID instead of restating it. `Status` is `approved` when the stage 1 gate approved the
target, whoever stated it, and `provisional` while it is still an assumption (cite its `[A<n>]` in Source).
A requirement with no measurable target stays provisional. Source may also be `<file>#Q<n>` · `[A<n>]`.]

### Amendment Log
<!-- Empty until the first change after approval; creating this document is not logged.
One line per change: `- YYYY-MM-DD | agent | what changed | why` — the reason is mandatory
(skills/shared/spec-gate/SKILL.md § Living Spec — Amendment Protocol). -->
