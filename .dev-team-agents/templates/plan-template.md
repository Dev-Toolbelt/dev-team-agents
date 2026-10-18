<!--
CANONICAL PLAN FORMAT. Installed at .dev-team-agents/templates/plan-template.md —
use that path when referencing this file from an agent, skill, or command; a bare
`templates/…` path resolves only inside the dev-team-agents repository.
This file is the single source of truth for the plan structure, the Par.-column
semantics, and the approval closer. Do not restate them anywhere else.
-->
## Plan — [Task Name]

### Context
[One or two sentences: what triggered this task and why it matters. Reference the backlog item, issue, or user request if applicable.]

### Scope
**In scope:**
- [What WILL be changed or created]
- [What WILL be changed or created]

**Out of scope:**
- [What will NOT be touched — be explicit about boundaries]

### Approach
[One paragraph explaining the chosen strategy and the reasoning behind it. If an alternative approach was considered, mention it and why it was rejected. Keep it tight — the steps carry the detail.]

### Steps
| # | Action | Files / Areas Affected | Complexity | Par. |
|---|---|---|---|---|
| 1 | [action] | [files] | Low | A |
| 2 | [action] | [files] | Medium | A |
| 3 | [action] | [files] | Low | B |

Complexity scale: Low = routine change | Medium = multiple touch points | High = architectural impact
Par. column: steps sharing the same letter (A, B, C) can be sent as simultaneous agent prompts in a single message after approval. Use "---" for steps that must wait for the previous one to complete.

### Risks & Dependencies
- **Risk:** [description] — **Mitigation:** [how it will be handled]
- **Depends on:** [any prerequisite that must be true before execution]
- **Assumption:** [what is assumed about the current state of the codebase or environment]

### Definition of Done
- [ ] [acceptance criterion 1]
- [ ] [acceptance criterion 2]
- [ ] Linter / type-checker passes
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if applicable)

---
Awaiting your approval before proceeding.
Reply "approved" to execute or provide feedback to adjust.

After approving: steps that share the same Par. group letter can be sent as simultaneous agent prompts in a single message to run them in parallel and reduce total execution time.
