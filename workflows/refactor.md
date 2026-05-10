# Workflow — Refactor

Use when improving the internal structure of existing code without changing its external behavior. Applies to any scope: a single module, a service layer, or a cross-cutting concern.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:refactor` runs this workflow.

---

## Phase 1: ANALYSIS

### Step 1: Scope Definition (software-architect)

```
Prompt: "As the software-architect, load the project context and analyze [area/file/module].
         Define the refactor scope: what is wrong, what the target state looks like,
         and what the blast radius of the change is."
```

The `software-architect` will:
- Present a plan (what to read, how to assess the code area)
- Produce a refactor scope document: current state, target state, risks, and explicit boundaries
- Identify whether this is a backend, frontend, or full-stack change

Do not begin implementation until the scope is approved. Scope creep during a refactor is one of the most common sources of regressions.

▶ CHECKPOINT — await: software-architect scope document

---

## Phase 2: IMPLEMENTATION

### Step 2: Refactor (backend-developer or frontend-developer)

Choose the appropriate developer based on the scope identified in Phase 1.

**Backend:**
```
Prompt: "As the backend-developer, implement the refactor defined in the scope document.
         Do not change external behavior — no new features, no bug fixes beyond the scope."
```

**Frontend:**
```
Prompt: "As the frontend-developer, implement the refactor defined in the scope document.
         Do not change external behavior — no new features, no bug fixes beyond the scope."
```

**Both (full-stack scope):** send both prompts in a single message.

The developer will:
- Present a plan (exact files, approach, what will NOT be touched)
- Implement in small, reviewable steps
- Flag any bugs discovered during refactoring as separate items — never fix silently

▶ CHECKPOINT — await: implementation complete

---

## Phase 3: QUALITY GATE

### Step 3 + 3b: Code Review + QA (parallel)

Send both prompts in a single message to run them simultaneously:

| Step | Agent | Par. |
|------|-------|------|
| 3a | code-reviewer | A |
| 3b | qa-specialist | A |

```
Prompt: "As the code-reviewer, review the refactor. Confirm that external behavior is
         preserved, code quality improved, and no new issues were introduced."

Prompt: "As the qa-specialist, verify that the refactored code behaves identically to
         the original — run existing tests, check edge cases, and flag any regressions."
```

The `code-reviewer` produces a structured findings report. The `qa-specialist` produces a validation report. Any [BLOCKING] finding must be resolved before proceeding.

▶ CHECKPOINT — await: no [BLOCKING] findings from either agent

---

## Phase 4: COMMIT & PR

### Step 4: Commit

```
Prompt: "/devteam:commit"
```

The commit agent reads staged changes, groups them by layer, and writes commits following the project's commit pattern.

### Step 5: Pull Request (optional)

```
Prompt: "Please open a PR for this refactor."
```

The `technical-writer` (via `/devteam:pr`) drafts the PR title and body, summarizing what changed and why.

---

## Workflow Closure

☐ Refactor scope defined and approved
☐ Implementation complete — no behavior changes
☐ Code review passed (no [BLOCKING] findings)
☐ QA validated — no regressions
☐ Commit and PR created
☐ Session summary written

**Related workflows:**
- Found a bug during refactoring? → `workflows/bug-fix.md`
- Refactor involves architectural decisions? → use `/devteam:architect` first
- Security concerns surfaced? → `workflows/security-patch.md`
