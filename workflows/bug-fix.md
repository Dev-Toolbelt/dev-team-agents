# Workflow — Bug Fix

Use for isolated bugs in any project type. Faster than the full workflow — focus on diagnosis, fix, and regression.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

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

## Step 3: Regression Check (qa-specialist)

```
Prompt: "As the qa-specialist, verify the bug is fixed and check that the fix
         doesn't break adjacent functionality."
```

The `qa-specialist` presents a validation plan (what to check, how to verify the fix, what adjacent areas to probe) and waits for approval before running any checks.

---

## Step 4: Code Review (code-reviewer)

```
Prompt: "As the code-reviewer, review the bug fix — check that it actually fixes
         the root cause, doesn't introduce new issues, and follows project standards."
```

The `code-reviewer` presents findings as a structured report. Any remediation step requires a new plan.

---

## Step 5: Test (backend-test-specialist / frontend-test-specialist)

If project requires tests:

```
Prompt: "As the backend-test-specialist, write a regression test that would have
         caught this bug, and ensure it passes with the fix in place."
```

The test specialist presents a plan (test file, cases to cover, expected assertions) before writing any test code.
