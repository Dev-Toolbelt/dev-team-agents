---
name: plan-mode
description: Plan-before-execute — structured plan, approval, replanning.
---

# Plan Mode — Mandatory Planning Protocol

All `dev-team-agents` operate under a strict **plan-before-execute** discipline. No non-trivial task may be executed without a prior approved plan.

---

## When a Plan Is Required

A plan is required whenever a task involves:

| Category | Examples |
|----------|---------|
| File operations | Creating, modifying, deleting, or moving any file |
| Commands with side effects | Installs, migrations, deploys, cache clears, git operations |
| Architecture or design decisions | Choosing tech stack, defining API contracts, schema design |
| Document generation | Backlog items, sprint plans, ADRs, code standards |
| Multi-step implementations | Any task with 2 or more sequential steps |
| Multi-agent delegations | Any task that spawns one or more subagents |

**A plan is NOT required for:**
- Answering a question
- Explaining or reading existing code
- Showing a file's contents or grep results
- Single-character / single-line typo fixes explicitly requested

When in doubt: **write the plan**.

---

## Plan Format

**Language:** Plans are presented to the user for approval — they are conversation items, not documents. Present plans in the user's preferred language from `.dev-team-agents/user-data/preferences.json` → `language` (default: English).

Use this exact structure. Copy it, fill it in, present it.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PLAN  ·  [Task Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTEXT
  [One or two sentences: what triggered this task and why it matters.
   Reference the backlog item, issue, or user request.]

SCOPE
  In scope
  ─────────
  · [Item 1]
  · [Item 2]

  Out of scope
  ─────────────
  · [Item A — will NOT be changed]

APPROACH
  [One paragraph explaining the chosen strategy and the reasoning behind it.
   If there was an alternative approach considered, mention it and why it was
   rejected. Keep it tight — the steps below carry the detail.]

STEPS
  ┌────┬────────────────────────────────────────────────────┬───────────────────────────────┬────────────┬──────┐
  │ #  │ Action                                             │ Files / Areas Affected        │ Complexity │ Par. │
  ├────┼────────────────────────────────────────────────────┼───────────────────────────────┼────────────┼──────┤
  │  1 │ [What will be done]                                │ path/to/file.ext              │ Low        │ A    │
  │  2 │ [What will be done]                                │ path/to/file.ext              │ Medium     │ A    │
  │  3 │ [What will be done]                                │ path/to/file.ext              │ High       │ —    │
  └────┴────────────────────────────────────────────────────┴───────────────────────────────┴────────────┴──────┘

  Complexity scale: Low = routine change | Medium = non-trivial, multiple touch points | High = architectural impact
  Par. column: steps sharing the same letter (A, B, C…) can be sent as simultaneous agent prompts after approval.
               Use "—" for steps that must wait for the previous one to complete.

RISKS & DEPENDENCIES
  · Risk: [Description] → Mitigation: [How it will be handled]
  · Depends on: [Prerequisite that must be true before step N]
  · Assumption: [What is being assumed about the current state]

DEFINITION OF DONE
  ☐ [Acceptance criterion 1]
  ☐ [Acceptance criterion 2]
  ☐ Linter / type-checker passes
  ☐ Tests pass (if applicable)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Awaiting your approval before proceeding.
 Reply "approved" to execute · or provide feedback to adjust.

 ⚡ After approving: steps that share the same Par. group letter
    can be sent as simultaneous agent prompts in a single message
    to run them in parallel and reduce total execution time.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Approval Protocol

After presenting the plan:

1. **Stop.** Do not execute any step.
2. **Wait** for an explicit approval signal from the user.
3. **Approval signals**: "approved", "go ahead", "proceed", "yes", "looks good", "do it"
4. **Rejection signals**: any feedback, correction, question, or "no"

On **rejection**: acknowledge the feedback, adjust the plan, re-present the full plan. Never partially execute before replanning.

On **approval**: execute steps in order. Report progress after each step. If execution reveals a problem that changes the plan, **stop and replan** before continuing.

---

## Replanning During Execution

If you discover mid-execution that a step cannot be done as planned:

1. Stop immediately.
2. Describe what was found and why the original plan needs to change.
3. Present an updated plan covering only the remaining steps.
4. Wait for approval again before continuing.

**Do not silently improvise.** If the plan changes, the user must know.

---

## Agents Must Self-Enforce

Every agent in `dev-team-agents` is responsible for applying this protocol independently. The plan-mode rule is not optional and is not enforced by an external system — it is part of each agent's operating discipline.

If a user asks an agent to "just do it" without a plan: explain that the plan takes less than a minute to write, protects against misunderstandings, and produces better results. Then write the plan. Never skip it.

---

## Context Self-Monitoring

After any response that involved reading many large files, producing long outputs, or running multiple tool calls in sequence, add a brief context advisory when appropriate:

> ⚡ **Context advisory**: this session has accumulated significant context. If responses start feeling less precise, run `/compact` or start a fresh session before the next task.

Apply this judgment after: reading 5+ files, producing 3+ large tool outputs, or a long back-and-forth session. You cannot see the exact percentage — err toward mentioning it. This supplements the automated hook-based warning, which fires based on a transcript token estimate.
