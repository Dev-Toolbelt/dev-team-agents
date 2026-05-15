---
name: interaction-patterns
description: Quiz-first rule — use AskUserQuestion for all user-facing choices; add "Other" when open input is valid.
---

# Interaction Patterns — Quiz-first Rule

## Core Rule

**Whenever you need to ask the user a question that has a finite set of reasonable answers, use the `AskUserQuestion` tool instead of plain text.**

This applies to:

| Situation | Use AskUserQuestion? |
|-----------|----------------------|
| Yes / No confirmation | ✅ Always |
| Multiple-choice selection (2–4 options) | ✅ Always |
| Picking between named alternatives (branch vs worktree, module by module vs all at once) | ✅ Always |
| Asking for a free-form name, title, or description with no obvious set of values | ❌ Ask as plain text |
| Reporting status or results (no question involved) | ❌ Plain output |

---

## "Other" Option Rule

Include an **"Other"** option (with `description: "Type your own answer."`) whenever:

- The predefined options cover the common cases but the user might have a custom value
- The question is a branch name, version, path, or any identifier the user may want to specify freely
- The question has 2–3 fixed options but the problem space is open

Do **not** add "Other" when:
- The question is a strict binary (Yes / No) with no valid third state
- The options are exhaustive by definition (e.g., enable / disable a toggle)

---

## Language Rule

Use the same language as the `language` field in `.claude/user-data/preferences.json` for:
- The `question` text
- The `header` label
- The `label` and `description` of each option

Fall back to English if the file is unreadable.

---

## AskUserQuestion JSON Patterns

### Yes / No

```json
{
  "questions": [
    {
      "question": "<question text>?",
      "header": "<short label, max 12 chars>",
      "multiSelect": false,
      "options": [
        { "label": "Yes", "description": "<what happens if yes>" },
        { "label": "No",  "description": "<what happens if no>" }
      ]
    }
  ]
}
```

### Multiple choice (with "Other")

```json
{
  "questions": [
    {
      "question": "<question text>?",
      "header": "<short label>",
      "multiSelect": false,
      "options": [
        { "label": "<Option A>", "description": "<explain A>" },
        { "label": "<Option B>", "description": "<explain B>" },
        { "label": "<Option C>", "description": "<explain C>" },
        { "label": "Other",      "description": "Type your own answer." }
      ]
    }
  ]
}
```

### Multi-select (checkboxes)

```json
{
  "questions": [
    {
      "question": "<question text>?",
      "header": "<short label>",
      "multiSelect": true,
      "options": [
        { "label": "<Option A>", "description": "<explain A>" },
        { "label": "<Option B>", "description": "<explain B>" },
        { "label": "<Option C>", "description": "<explain C>" }
      ]
    }
  ]
}
```

---

## Common Recurring Patterns

### Worktree isolation (coding agents)

```json
{
  "questions": [
    {
      "question": "Should I work in an isolated git worktree for this task?",
      "header": "Isolation",
      "multiSelect": false,
      "options": [
        { "label": "Yes — worktree", "description": "Create an isolated worktree. I'll ask for the base branch next." },
        { "label": "No — new branch", "description": "Stay in the current worktree and check out a new branch." }
      ]
    }
  ]
}
```

### Scope confirmation (large tasks)

```json
{
  "questions": [
    {
      "question": "This task covers a large scope and may consume significant tokens. How do you want to proceed?",
      "header": "Scope",
      "multiSelect": false,
      "options": [
        { "label": "Module by module", "description": "Process one module at a time with a checkpoint between each (safer)." },
        { "label": "All at once",      "description": "Process the entire scope in a single pass (faster, higher token cost)." },
        { "label": "Cancel",           "description": "Stop here — do not proceed." }
      ]
    }
  ]
}
```

### Pre-commit gate failure

```json
{
  "questions": [
    {
      "question": "Pre-commit checks failed. How do you want to proceed?",
      "header": "Gate failure",
      "multiSelect": false,
      "options": [
        { "label": "Fix and re-stage", "description": "Fix the issues now, re-stage, and retry the commit." },
        { "label": "Commit anyway",    "description": "Skip the failing checks and commit as-is." },
        { "label": "Abort",            "description": "Cancel the commit entirely." }
      ]
    }
  ]
}
```

### Plan approval gate

```json
{
  "questions": [
    {
      "question": "Plan ready. Do you approve?",
      "header": "Plan approval",
      "multiSelect": false,
      "options": [
        { "label": "Approved — proceed", "description": "Execute the plan as described." },
        { "label": "Adjust first",       "description": "I'll describe what to change before you proceed." },
        { "label": "Cancel",             "description": "Discard the plan and stop." }
      ]
    }
  ]
}
```
