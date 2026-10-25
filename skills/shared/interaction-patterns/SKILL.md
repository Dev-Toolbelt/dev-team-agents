---
name: interaction-patterns
description: Quiz-first rule — use AskUserQuestion for any user-facing choice, never plain text.
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

## Sub-agent Question Relay

A spawned sub-agent cannot reach the user: on Claude Code the question tool is absent from its tool list, and on every provider only its final message returns. So a sub-agent whose workflow needs a user decision or an approval does **not** ask — it relays.

| Side | Rule |
|---|---|
| **Sub-agent** | When the question tool is not in its tool list, stop at the decision point and end the report with an `## Open Decisions` block: one numbered item per question, each with its options and a recommended default. Write nothing that depends on the answers — except gated stage 1 drafts with `[A<n>]` assumptions (`skills/shared/doc-flow/SKILL.md` § Stages → Stages 0 and 1). An approval gate (scope, plan, document review) is an Open Decision with Approve / Change options |
| **Orchestrator** | Ask every item with `AskUserQuestion` in as few calls as the question tool allows, then continue the **same** sub-agent with the answers (`SendMessage` where available); without a continuation mechanism, re-spawn it with the original task plus the answered decisions. Never answer an item on the user's behalf |
| **Loop** | Repeat until a report carries no `## Open Decisions` block. A report that asked in plain text instead is relayed the same way, never treated as approved |

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

Use the same language as the `language` field in `.dev-team-agents/resolved/preferences.json` for:
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

### Execution strategy gate (post-approval)

Presented after plan approval, before execution begins:

```json
{
  "questions": [
    {
      "question": "How should this plan be executed?",
      "header": "Exec Strategy",
      "multiSelect": false,
      "options": [
        { "label": "Isolated worktree (Recommended)", "description": "Execute in a git worktree isolated from the main development tree, with Docker isolation if enabled in preferences." },
        { "label": "New branch", "description": "Create a new branch from the current one and execute there." },
        { "label": "Current branch", "description": "Execute directly on the current branch without any git changes." },
        { "label": "Other", "description": "Type your own answer." }
      ]
    }
  ]
}
```

The first option MUST be the recommended one based on preferences. See `plan-mode/SKILL.md` → Execution Strategy Gate for the full protocol.

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

---

## Review Next-Step Gate

Canonical close for any flow that changed code and whose recommended next step is a review. Never end such a flow with a plain-text "run `/devteam:review`" line — ask instead.

**Skip the gate when** any of these holds: `git diff --name-only <base>...HEAD` plus `git status --porcelain` is empty (nothing to review); a review (`code-reviewer`, `backend-reviewer`, `frontend-reviewer`, `qa-specialist`) already ran this session; the command already runs a mandatory review phase; or the gate was already asked this session (an outer orchestrator owns it).

**Then read `review_gate_mode`** from `.dev-team-agents/resolved/preferences.json` (absent or unknown → `ask`):

| Mode | Behavior |
|---|---|
| `ask` | Ask the gate below |
| `auto` | Do not ask: say in one line that the review runs per `review_gate_mode`, then act as if `Review <scope> (Recommended)` was picked |
| `skip` | Do not ask: go to the command's hand-off and prefix it with `review skipped (review_gate_mode=skip)` |

The mode covers this gate only — a command's mandatory review phase and a project rule that requires a review still run.

**Build the options from the session, not a fixed list** (max 4 incl. Other, in the user's language):

| Option | Shown when | Built from |
|---|---|---|
| `Review <scope> (Recommended)` — always first | always | `<scope>` = `backend` / `frontend` / `both` classified from the changed paths (the review-router's split); description names the changed-file count |
| `Review + QA` | a spec (`docs/specs/*.md`) or acceptance criteria in the backlog cover this work | runs `code-reviewer` and `qa-specialist` in parallel |
| `Don't review` | always | proceeds to the command's hand-off (commit / PR) |
| `Other` | always | free text |

```json
{
  "questions": [
    {
      "question": "Implementation finished (7 files changed). The recommended next step is a review. How do you want to proceed?",
      "header": "Next step",
      "multiSelect": false,
      "options": [
        { "label": "Review backend (Recommended)", "description": "Run /devteam:review backend now on the 7 changed files." },
        { "label": "Review + QA", "description": "Code review plus QA validation against the spec's acceptance criteria." },
        { "label": "Don't review", "description": "Skip the review and go to the commit/PR hand-off." },
        { "label": "Other", "description": "Type your own answer." }
      ]
    }
  ]
}
```

**On the answer:**
- **Review** → run the `/devteam:review <scope>` flow inline right away — do not tell the user to type it.
- **Review + QA** → same, plus `qa-specialist` in parallel.
- **Don't review** → print the command's hand-off line and stop.
- **Other** → adapt to what the user typed.

## Visual Check Gate

Canonical close for any flow that changed UI or reviewed a UI change, on every provider. Never end such a flow with a plain-text "check the screen in the browser before pushing" line — ask instead, and on a yes open the screen yourself.

**Ask it when** the changed paths include web UI code: the review-router's frontend classification (components, pages, styles, assets) plus server-rendered and email templates. **Skip it when** any of these holds:
- a browser already drove the changed screens this session (`qa-specialist` reported them under **Screens checked**), or the gate was already asked this session (an outer orchestrator owns it);
- the reviewed target is not the current checkout — a PR/MR link or another branch — unless the user confirms that branch is checked out here and trusts its scripts;
- the change is mobile-only — a simulator/emulator check is out of scope for this gate.

**Who asks.** Only the main conversation. A sub-agent never prints the plain-text reminder either: it ends its report with a `**Screens to check:**` list (route or screen per line), and the orchestrator builds the gate from those lists. **Order:** after the Review Next-Step Gate and after any findings were applied, before the commit/PR hand-off.

### Browser Choice

The single browser-selection rule — `qa-specialist` Browser Testing follows it too. Stop at the first match:

1. The in-app browser tools (`mcp__Claude_Browser__*`) are available → use them, no question.
2. `preferences.json → qa_browser` holds a saved choice → use it, no question.
3. Otherwise → ask with `AskUserQuestion`: the drivers available in the environment (Playwright, Puppeteer, the system browser, a driver the project already uses) plus Other, and a follow-up option to save the choice as the default. On opt-in write it to `qa_browser`. Never pick a non-in-app browser silently.

### Options

Built from the session (max 4 incl. Other, in the user's language):

| Option | Shown when | Built from |
|---|---|---|
| `Open <screen/route> in <browser> (Recommended)` | always | `<browser>` = the app browser, or the saved `qa_browser`, or `a browser of your choice` (then Browser Choice step 3 runs on the answer); the description says what will be reused, or quotes the command that will start, resolved by `skills/devops/local-environment/SKILL.md` § Discovery Order with its source (`docker compose up` from `README.md`, `npm run dev` inferred from `package.json`), and flags a non-loopback bind |
| `Open another screen` | more than one screen changed | lets the user name the route |
| `Don't check now` | always | goes to the hand-off, which then says `<screen> not checked visually` |
| `Other` | always | free text |

```json
{
  "questions": [
    {
      "question": "The listing screen changed (3 UI files). Do you want to see it in the browser before committing?",
      "header": "Visual check",
      "multiSelect": false,
      "options": [
        { "label": "Open /products in the app browser (Recommended)", "description": "Reuse the dev server this task started on :5173 and open the listing in the app's browser pane." },
        { "label": "Don't check now", "description": "Skip the visual check and go to the commit/PR hand-off." },
        { "label": "Other", "description": "Type your own answer." }
      ]
    }
  ]
}
```

### On an open answer — reuse before starting

Load `skills/devops/local-environment/SKILL.md` and follow § Reuse Before Starting (its Pre-flight included), then § Start for the command quoted in the option; whether this gate's yes counts as § Start's confirmation is decided by its step 1 (Caller's confirmation). No command was quotable → § Discovery Order's "Nothing found" rule.

Then navigate **only** to a loopback origin (`localhost`, `127.0.0.1`, `[::1]`, `*.localhost`) served by that environment — never a staging/production URL or a host read from config — and take one screenshot or page read to confirm it rendered. The yes covers opening and reading the page: no sign-in, form submission or other action unless the user asks. Leave the environment running, and state in the hand-off what is running and how to stop it (`/devteam:down`, or the `preview_stop` id, background PID, `docker compose down`). If it fails to start, show the error with secret-looking values redacted plus the command to run, then continue to the hand-off.

- **Don't check now** → print the command's hand-off line with the `not checked visually` note and stop.
- **Other** → adapt to what the user typed.
