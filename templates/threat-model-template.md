---
status: draft # draft → signed-off (security-specialist sign-off at the stage 2a gate)
---

<!--
CANONICAL THREAT MODEL FORMAT. Installed at .dev-team-agents/templates/threat-model-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by software-architect (or technical-writer on delegation) at the `threat-model` doc
(docs/security/threat-model.md in the gated layout), stage 2a of skills/shared/doc-flow/SKILL.md.
security-specialist is read-only: it provides the findings and the sign-off, it does not write this file.
-->

# Threat Model — [Product Name]

## Trust Boundaries
| ID | Boundary | Between | Data crossing it |
|---|---|---|---|
| TB-1 | [e.g. public internet → API] | [actor/zone] ↔ [actor/zone] | [data] |

## Threats

### TB-1 — [Boundary Name]
| ID | Threat | Category | Likelihood | Impact | Mitigation | Status |
|---|---|---|---|---|---|---|
| TM-1 | [what an attacker does] | [spoofing · tampering · repudiation · disclosure · denial of service · elevation] | [low · medium · high] | [low · medium · high] | [control, with the ADR / NFR / endpoint it lives in] | [open · mitigated · accepted] |

[Repeat one `###` block per trust boundary.]

## Personal-Data Map
| Data | Store (table.column / bucket / log) | Legal basis | Retention | Erasure path |
|---|---|---|---|---|
| [data item] | [`table.column`] | [consent · contract · legal obligation · legitimate interest · other] | [period, or "until account deletion"] | [endpoint, job, or manual procedure that erases it] |

[Every column tagged `personal` or `sensitive` in docs/data-model.md has a row here.]

## Sign-off
- [YYYY-MM-DD] | security-specialist | [findings reviewed: TM-IDs] | [signed off · changes requested]

### Amendment Log
<!-- Empty until the first change after approval; creating this document is not logged.
One line per change: `- YYYY-MM-DD | agent | what changed | why` — the reason is mandatory
(skills/shared/spec-gate/SKILL.md § Living Spec — Amendment Protocol). -->
