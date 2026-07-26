---
name: output-format
description: Platform-agnostic output format — pure markdown, no box-drawing Unicode, no decorative symbols. Use for plans, reports, reviews, diagnostics, and any structured agent output.
---

# Output Format

Use this format for ALL structured output — plans, reports, reviews, diagnostics, conformance reports, post-implementation reviews, and any other agent-produced documents. It renders cleanly on any platform (Claude Code, opencode, Codex CLI, ChatGPT, any terminal or web UI).

## Core Rules

- **Pure markdown only** — no HTML, no raw ANSI, no escape sequences
- **No box-drawing Unicode** — never use `┌ ─ ┐ │ └ ┘ ┃ ━ ┏ ┓ ┗ ┛ ┣ ┫ ┳ ┻ ╋ ═ ║ ╔ ╗ ╚ ╝ ╠ ╣ ╦ ╩ ╬`
- **No decorative Unicode symbols** — never use `☐ ☑ ☒ ✓ ✗ ★ ☆ ✦ ✧ ❗ ❓ ➜ → ⇒ ⇨ · • ◦ ‣`
- **No emojis for decoration** — use `✅` `❌` `⚠️` `📌` `🔄` only when they carry real semantic meaning (completion, error, warning, action item, pending). Never use emojis purely decoratively.
- **Markdown tables** — use `|---|---|` syntax, never ASCII box-drawing tables

## Section Structure

```
## Title

### Subtitle

Body text with **bold** for emphasis and `inline code` for paths, commands, or filenames.

- List items with `-` for unordered lists
- Use `1.` for ordered lists

Code blocks with language tag:

```language
code or structured data
```
```

## Report Template

Use this structure for reports, reviews, and diagnostics:

```
## [Report Type] — [Brief Title]

### Summary
[1-3 sentences: overall verdict and key takeaway]

### [Section Name]
- **[LABEL]** [item] — [description and action]
  - Location: `path/to/file.ext:line`
  - Recommendation: [what to do]

### [Next Section]
- ...

---
```

### Severity Labels

Use these consistently:

| Label | When |
|---|---|
| `[BLOCKING]` | Must fix before proceeding |
| `[HIGH]` | Significant issue, should fix soon |
| `[MEDIUM]` | Moderate concern |
| `[LOW]` | Minor, take it or leave it |
| `[INFO]` | Information only, no action required |
| `[SUGGESTION]` | Improvement, not a blocker |
| `[QUESTION]` | Needs clarification |

## Conformance Report

```
## Conformance Report — [Sprint / Date]

### Summary
[1-2 sentences]

### Deviations
| File / Area | Deviation | Severity | Action |
|---|---|---|---|
| `path/to/file.ext` | [what] | [severity] | [fix] |

### Tech Debt Tracked
| Item | Introduced | Owner | Target |
|---|---|---|---|

### Conformant Areas
- [area that passed review]
```

## Post-Implementation Review

```
## Post-implementation review

### Code review (critical only)
- [bullets]

### QA (gaps / risks)
- [bullets]

### Summary
[1-2 sentences: verdict and recommended next step]
```

## Security Review

```
## Security Review — [Brief Title]

### Executive Summary
[2-3 sentences: overall risk posture]

### Critical Findings
- **[CRITICAL]** [title]
  - Location: `path/to/file.ext:line`
  - Description: [what the vulnerability is]
  - Attack scenario: [how an attacker would exploit this]
  - Remediation: [specific fix]

### High Findings
- **[HIGH]** [title]
  - ...

### Medium / Low / Info
- **[MEDIUM / LOW / INFO]** ...
```

## Plan Template

```
## Plan — [Task Name]

### Context
[One or two sentences: what triggered this task and why it matters]

### Scope
**In scope:**
- [what will be changed]

**Out of scope:**
- [what will NOT be touched]

### Approach
[One paragraph: chosen strategy and reasoning]

### Steps
| # | Action | Files | Complexity | Par. |
|---|---|---|---|---|
| 1 | [action] | `path/to/file` | [Low/Med/High] | [A/B/—] |

Complexity: Low=routine, Medium=multiple touch points, High=architectural
Par.: same letter = parallel, — = sequential

### Risks & Dependencies
- **Risk:** [description] — **Mitigation:** [how handled]
- **Depends on:** [prerequisite]
- **Assumption:** [assumed state]

### Definition of Done
- [ ] [acceptance criterion 1]
- [ ] [acceptance criterion 2]
- [ ] Linter / type-checker passes
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if applicable)

---
Awaiting your approval before proceeding.
Reply "approved" to execute or provide feedback to adjust.
```

## Diagnostics

```
## [Diagnostic Type] — [Brief Title]

### Status
[PASS / FAIL / WARNING] — [one-line summary]

### Details
- **Check:** [what was checked]
  - Expected: [value]
  - Actual: [value]
  - Result: [PASS / FAIL]

### Recommendations
- [if applicable]
```
