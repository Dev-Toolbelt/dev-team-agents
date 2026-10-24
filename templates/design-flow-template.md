---
spec: [feature].md # the business spec this flow serves
---

<!--
CANONICAL DESIGN FLOW FORMAT. Installed at .dev-team-agents/templates/design-flow-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
Written by ui-ux-designer at the `design-flows` doc (docs/design/flows/<feature>.md in the gated
layout), stage 4 of skills/shared/doc-flow/SKILL.md. Visual values are token names from
docs/design/tokens.json, never raw values. Every state PNG listed must be `approved` before a
frontend task on this feature is ready.
-->

# Flow — [Feature Name]

## Screen: [Screen Name]

**Route:** `[/path/:param]`
**Prototype:** `docs/design/prototypes/[feature]/[YYYY-MM-DD]/[file]`
**Covers:** [feature]#S1, [feature]#S2

### States
| State | Trigger | Frame / PNG | Status |
|---|---|---|---|
| loading | [what puts the screen here] | `docs/design/screens/[feature]/[screen]--loading.png` | draft |
| empty | [trigger] | `docs/design/screens/[feature]/[screen]--empty.png` | draft |
| error | [trigger] | `docs/design/screens/[feature]/[screen]--error.png` | draft |
| forbidden | [trigger] | `docs/design/screens/[feature]/[screen]--forbidden.png` | draft |
| [feature-specific] | [trigger] | `docs/design/screens/[feature]/[screen]--[state].png` | draft |

[Status is `draft` or `approved` (the user approved the PNG). Every state is reachable via `?state=<state>`.]

### Elements
| Element | Permission | Action → API | Success | Error key → copy |
|---|---|---|---|---|
| [button / field / link] | [permission, or "public"] | [`METHOD /path` from api-contracts, or "none"] | [what the user sees next] | [`error.key` → "[user-facing copy]"] |

### Navigation
| From | Event | To |
|---|---|---|
| [this screen] | [event] | [screen or route] |

### Refresh Policy
[When the data on this screen reloads: on mount, on focus, polling interval, after which mutations.]

[Repeat one `## Screen:` section per screen in the feature.]

### Amendment Log
<!-- Empty until the first change after approval; creating this document is not logged.
One line per change: `- YYYY-MM-DD | agent | what changed | why` — the reason is mandatory
(skills/shared/spec-gate/SKILL.md § Living Spec — Amendment Protocol). -->
