# Workflow — Bug Fix

Use for isolated bugs in any project type. Faster than the full workflow — focus on diagnosis, fix, and regression.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:fix` runs this workflow.

---

## Step 1: Diagnosis

```
Prompt: "There's a bug: [describe behavior, error message, stack trace, or steps to reproduce].
         As the software-architect, load the project context and identify the root cause."
```

The `software-architect` will:
- Present a plan (what to read, how to trace the issue)
- After approval: identify the root cause and produce a short diagnosis report

Do not jump to fixing before the root cause is confirmed. A symptom fix without root cause understanding usually produces another bug.

▶ CHECKPOINT — await: software-architect diagnosis

---

## Step 2: Fix (backend-developer or frontend-developer)

```
Prompt: "As the backend-developer, fix the root cause identified: [description].
         Do not change anything beyond what's needed to fix this bug."
```

The developer will:
- Present a plan (exact files to change, lines to touch, approach)
- State explicitly what will NOT be changed
- Wait for your approval before modifying any file

**Rules for bug fixes:**
- Fix the root cause, not the symptom
- Do not refactor surrounding code in the same change
- Do not add features while fixing a bug
- If you find another bug while fixing, open a separate issue/task — don't fix both silently

---

## Step 3 + 4: Regression Check + Code Review (parallel)

The `qa-specialist` and `code-reviewer` are independent. Send both prompts in a single message to run them simultaneously:

| Step | Agent | Par. |
|------|-------|------|
| 3 | qa-specialist | A |
| 4 | code-reviewer | A |

```
Prompt: "As the qa-specialist, verify the bug is fixed and check that the fix
         doesn't break adjacent functionality."

Prompt: "As the code-reviewer, review the bug fix — check that it actually fixes
         the root cause, doesn't introduce new issues, and follows project standards."
```

The `qa-specialist` presents a validation plan before running checks. The `code-reviewer` presents findings as a structured report. Any remediation step requires a new plan.

---

## Step 5: Test (backend-test-specialist / frontend-test-specialist)

If project requires tests:

```
Prompt: "As the backend-test-specialist, write a regression test that would have
         caught this bug, and ensure it passes with the fix in place."
```

The test specialist presents a plan (test file, cases to cover, expected assertions) before writing any test code.

---

## Step 6: Commit & PR

After all findings are resolved and tests pass:

```
Prompt: "/devteam:commit"
```

Then optionally:

```
Prompt: "Please open a PR for these changes."
```

---

## Step 7: Documentation Update (technical-writer — optional)

If the bug fix changes documented behavior — an API contract, a described flow, or a rule in the README:

```
Prompt: "As the technical-writer, check whether this bug fix changes any documented
         behavior and update the relevant docs."
```

Skip if the fix is purely internal (no user-visible behavior change, no API contract change).

---

## Workflow Closure

☐ Root cause identified and documented
☐ Fix implemented and reviewed
☐ Regression test added (if project has test culture)
☐ Quality gate passed (no [BLOCKING] findings)
☐ Commit and PR created
☐ Session summary written

**Related workflows:**
- Found a security issue? → `workflows/security-patch.md`
- Fix requires broader refactoring? → `workflows/refactor.md`

---

## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Agent reports insufficient context | Spawn `software-architect` for clarifying questions; provide the missing info and re-run the phase |
| `[BLOCKING]` findings persist after 3 review cycles | Escalate: re-scope the change, or create an ADR for the contested decision |
| Commit or PR blocked by Git state | Run `/devteam:fix git-state` or resolve manually (`git status`, `git stash`, rebase) |
| User aborts mid-workflow | Workflow state is in `.claude/user-data/session-summary.md` — resume by reading the last entry and continuing from the last completed phase |
| Root cause cannot be reproduced | Add a "cannot reproduce" label in the tracker; document findings in session-summary |
