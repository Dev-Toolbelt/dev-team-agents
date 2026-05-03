# Workflow — Bug Fix

Use for isolated bugs in any project type. Faster than full workflow — focus on diagnosis, fix, and regression.

---

## Step 1: Diagnosis

```
Prompt: "There's a bug: [describe behavior, error message, stack trace, or steps to reproduce].
         As the software-architect, load the project context and identify the root cause."
```

Do not jump to fixing before the root cause is confirmed. A symptom fix without root cause understanding usually produces another bug.

---

## Step 2: Fix (backend-developer or frontend-developer)

```
Prompt: "As the backend-developer, fix the root cause identified: [description].
         Do not change anything beyond what's needed to fix this bug."
```

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

---

## Step 4: Code Review (code-reviewer)

```
Prompt: "As the code-reviewer, review the bug fix — check that it actually fixes 
         the root cause, doesn't introduce new issues, and follows project standards."
```

---

## Step 5: Test (backend-test-specialist / frontend-test-specialist)

If project requires tests:

```
Prompt: "As the backend-test-specialist, write a regression test that would have 
         caught this bug, and ensure it passes with the fix in place."
```
