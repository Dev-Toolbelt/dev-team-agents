<!--
CANONICAL EVALS FORMAT. Installed at .dev-team-agents/templates/evals-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by software-architect at the `evals` doc (docs/ai/evals.md in the gated layout), stage 4 of
skills/shared/doc-flow/SKILL.md — only when the product uses LLMs. One `## <feature>` section per
AI feature; an AI task is ready only when its section has cases and thresholds.
-->
# LLM Evals — [Product Name]

## [feature]

**Spec:** `docs/specs/[feature].md` · **Covers:** [feature]#S1, [feature]#S2
**Model / prompt version:** [model id] · [prompt file or version]

### Cases
| ID | Input | Expected | Kind |
|---|---|---|---|
| E1 | [input or fixture path] | [expected output or property] | [happy · edge] |
| E2 | [input that must be refused] | [refusal with the expected message] | refusal |
| E3 | [input with no grounded answer] | [states it does not know; invents nothing] | hallucination |

### Metrics and Thresholds
| Metric | How measured | Threshold | Blocks release |
|---|---|---|---|
| [accuracy · groundedness · refusal rate · latency · cost per call] | [scorer, judge, or script] | [e.g. ≥ 0.9] | [yes · no] |

[Repeat one `## <feature>` section per AI feature.]

### Amendment Log
<!-- Empty until the first change after approval; creating this document is not logged.
One line per change: `- YYYY-MM-DD | agent | what changed | why` — the reason is mandatory
(skills/shared/spec-gate/SKILL.md § Living Spec — Amendment Protocol). -->
