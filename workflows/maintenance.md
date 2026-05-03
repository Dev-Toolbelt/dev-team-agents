# Workflow C — Maintenance / Evolution of Production Project

Use this workflow when the project is live in production with an existing board of prioritized tasks (Jira, Linear, GitHub Projects, Trello, etc.).

The work here is primarily **context management** — ensuring agents understand exactly what they're changing and what they might break.

**Extra care with legacy code**: fragile, untested, or tightly coupled code requires slower, more deliberate changes with stronger regression focus.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

---

## How to Start a Task

### Step 1: Task Pickup

Provide the task description from your board (copy-paste the issue, ticket, or user story):

```
Prompt: "As the software-architect, I'm about to work on this task from our board:
         [paste task description, acceptance criteria, and any relevant context].

         Load the project context from CLAUDE.md and .claude/docs/development/.
         Identify what areas of the codebase are affected, assess regression risk,
         and flag anything I should be careful about."
```

The `software-architect` will:
- Present a plan (what to read, what to assess, format of the risk report)
- After approval: load existing project context (`.claude/docs/development/`, CLAUDE.md)
- If context doesn't exist: do a mini-audit of the affected area only
- Identify dependencies, blast radius, and risks
- Flag legacy or untested areas

### Step 2: Scope Validation (product-analyst — optional but recommended)

For anything more than a trivial bug fix:

```
Prompt: "As the product-analyst, review the acceptance criteria for this task:
         [paste task]. Are there any ambiguities or missing rules I should
         resolve before starting implementation?"
```

Resolve ambiguities before writing code — not after.

---

## Phase 2: DEVELOPMENT

### Issue Tracker Integration (if configured)

If an issue tracker MCP is configured:

```
Prompt: "As the software-architect, read the task [TICKET-123] from [Jira/Linear/GitHub]
         and load the relevant context before we start."
```

Agents have **read-only** access by default. To create or update issues:

```
Prompt: "Please update [TICKET-123] status to In Progress."
         → Agent will present a plan and ask for explicit consent before writing.
```

### Implementation

```
Prompt: "As the backend-developer, implement [task description].
         Be careful not to change what doesn't need to change.
         Document anything you find that's concerning in the legacy code."

Prompt: "As the frontend-developer, implement [task description].
         Follow the existing design system — do not introduce new patterns
         without checking with the ui-ux-designer first."
```

Each developer will:
- Present a plan (files to touch, approach, what will NOT be changed)
- Wait for your approval before writing any code

**Legacy code rules for developers:**
- Do not refactor code that isn't part of the task scope
- If you must touch legacy code, document what you found
- If you find a bug while implementing, flag it — don't fix it silently in the same PR

---

## Phase 3: QUALITY GATE (Regression Priority)

The `code-reviewer`, `qa-specialist`, and `security-specialist` (when applicable) are independent of each other. **Send them in a single message** to run in parallel:

```
Prompt: "As the code-reviewer, review the changes for this task.
         Pay special attention to legacy code that was touched —
         look for silent bugs, race conditions, and unintended side effects."

Prompt: "As the qa-specialist, validate that [task] meets its acceptance criteria.
         Also check adjacent features that share code with what was changed.
         Flag any regression risks."

Prompt: "As the security-specialist, review the changes — particularly if they
         touch auth, data handling, or APIs."
         [Use only when the task touches sensitive areas]

Prompt: "As the devops-specialist, what's the safest deploy strategy for this change?
         [blue-green / canary / rolling update]"
```

> ⚡ **Parallel tip**: copy all applicable prompts above into a single message. Quality gate agents run independently — sending them together cuts review time significantly.

Quality gate agents present their findings as a structured report. Any remediation step (fixing a finding) requires a new plan before execution.

---

## PR and Deploy

```
Prompt: "As the technical-writer, update the relevant documentation for this change
         and generate the changelog entry."
```

The `technical-writer` will present a plan (which docs to update, what to add to the changelog) before writing anything. All documentation is produced in **English**.

If GitHub/GitLab is configured:
```
Prompt: "Please open a PR for these changes."
         → Agent will present a plan and ask for consent before creating the PR.
```

---

## Coexistence in Maintenance Projects

These projects often have **no `.claude/docs/`** directory. In that case:
- The `software-architect` creates the documentation as they audit each area
- Over time, `.claude/docs/development/` becomes the living map of the project
- This documentation accumulates across tasks — each task adds to the project's knowledge base

Treat this as incremental archaeology: document what you find, so the next task starts with more context.
