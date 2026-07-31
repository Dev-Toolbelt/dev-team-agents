---
name: github-actions
description: Load when the user asks to push — watch GitHub Actions and auto-fix failures until green.
---

# Push & GitHub Actions Monitoring

Load this skill **only when the user explicitly asks to push** (e.g., "push", "faça o push", "push and open the PR"). Do not trigger on commits alone — a commit is not a push.

## Preconditions (check in order, stop if any fails)

1. `gh auth status` succeeds → the GitHub CLI is configured and authenticated.
2. The repo has at least one workflow: `.github/workflows/*.yml` or `*.yaml` exists.

If `gh` is **not** configured → push normally and skip the rest of this skill (do not attempt to install or configure `gh`).
If there are **no workflow files** → push normally and tell the user in one line there are no Actions to watch.

## Flow

### 1. Push

Run the push the user asked for. Capture the branch name.

### 2. Suggest watching the run

Immediately after a successful push, tell the user you will watch the triggered Actions run, then start watching:

```bash
# Give GitHub a moment to register the run, then find it for this branch/commit
gh run list --branch "<branch>" --limit 1 --json databaseId,status,workflowName
gh run watch <run-id> --exit-status
```

- `--exit-status` makes `gh run watch` exit non-zero if the run concludes in failure — use that as the trigger for the fix loop.
- If no run appears within a reasonable poll window, report that no Actions run was triggered by the push and stop.

### 3. On failure — diagnose → fix → re-push (capped loop)

When the run fails, enter the auto-fix loop. **Maximum 3 attempts.**

Each attempt:

1. Read the failure:
   ```bash
   gh run view <run-id> --log-failed
   ```
2. Diagnose the **root cause** from the failed job logs (lint error, failing test, type error, missing dependency, bad config, etc.).
3. Apply the fix in the working tree. Only fix what the logs point to — do not refactor beyond the failing cause.
4. Commit the fix following the project's commit convention (load `skills/shared/conventional-commits/SKILL.md` if drafting a Conventional Commit; never add AI attribution).
5. Push again and watch the new run (step 2).

**Give the user a one-line summary after every attempt**, e.g.:

> ⚙️ Actions failed on `test` job — `UserService` null check. Fixed and re-pushed (attempt 1/3), watching the new run.

### 4. Stop conditions

Stop the loop and report to the user when any of these is true:

- **Green** — the run concludes successfully. Report: `✅ Actions passing on <branch> (run <id>).`
- **Cap reached** — 3 attempts made without going green. Stop, summarize what was tried and the remaining failure, and hand control back to the user. Do not push a 4th time.
- **Non-auto-fixable failure** — the cause is outside the code you can safely change (e.g., missing repository secret, external service down, required approval, infra/permissions). Do not guess or push blindly. Report the specific blocker and what the user must do.

## Rules

- Never disable, delete, or skip a failing workflow to make it "pass" (no `continue-on-error`, no removing the job, no `[skip ci]` to dodge the gate).
- Never weaken a test or assertion to make it green — fix the cause.
- Keep the user informed with a **short** summary per cycle; do not dump full logs unless asked.
- Respect the project's commit convention for every fix commit.
- One push per attempt; always watch the run you just triggered before deciding the next action.
