# Contradiction Guard

When a user request contradicts a rule, decision, or requirement that was previously established and recorded, **do not silently comply**. Instead:

1. **Stop and flag the contradiction** before taking any action
2. **Identify the source**: state exactly where the conflicting rule is defined (file + section)
3. **Describe the divergence**: explain what the user is asking vs. what was decided
4. **Ask for confirmation**: let the user decide whether to override the established rule

## Contradiction Template

> ⚠️ **This request conflicts with a previously established rule.**
>
> **What you asked**: [user request summary]
>
> **What was decided**: [rule/requirement] — found in `[source file]` › `[section]`
>
> **Divergence**: [specific explanation of the conflict]
>
> Do you want to override the established rule and proceed anyway? If yes, I'll update the relevant documentation to reflect the change.

## Sources to Check for Conflicts

Before acting on any significant request, verify it does not contradict:

| Source | What it governs |
|--------|----------------|
| Project `CLAUDE.md` | Explicit project rules and agent behavior overrides |
| `docs/development/adrs/` | Hard architectural decisions — costly to reverse, changed only by a superseding ADR |
| `docs/development/architecture.md` | System design, layer rules, tech stack decisions |
| `docs/development/code-standards.md` | Coding patterns and anti-patterns |
| `docs/development/reuse-guidelines.md` | Registered reuse and standardization rules — only rows whose `scope` covers the files in question |
| `docs/specs/*.md` | Acceptance criteria and scope of the feature being worked on |
| `docs/backlog/sprints/*sprint-*.md` | Scope of the current sprint (out-of-scope requests) |

A conflict between two of these sources is itself a contradiction — flag it with both sources cited, even when the user's request agrees with one of them.

A contradiction is only binding when the rule was **explicitly stated** in one of these sources — not inferred from code patterns alone. When in doubt, flag it.
