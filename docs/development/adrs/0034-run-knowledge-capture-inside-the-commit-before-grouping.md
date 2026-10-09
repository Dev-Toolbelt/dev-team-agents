# ADR-0034: Run knowledge capture inside the commit, before grouping

**Date:** 2026-10-09  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers

## Context

`/devteam:commit` has run `/devteam:learn` from three places. The first was a pre-commit Step 0. It was moved because its evidence (`git log`) could not see the pending commit, and because its marker recorded the pre-commit HEAD. As a result, a second commit in the same session skipped learn (2.45.1). The second was a post-commit Step 6. That position printed learn's whole plan, asked once per reuse rule, and left the docs it wrote uncommitted. Users read it as an interruption, not as part of committing.

## Decision

Learn runs at `/devteam:commit` § Step 2.7, after staging and before grouping, as `/devteam:learn --embedded`. It prints one status line and asks nothing. The docs it writes are committed with the work as the Docs layer. Both sides of the contract live in `skills/shared/feature-learn/SKILL.md` § Embedded Commit Capture.

- **The two 2.45.1 faults stay fixed.**
  - Evidence is the staged diff, which is the work about to be committed.
  - Learn never writes the marker. The commit writes it once at least one commit exists, holding the branch tip after any rebase or merge.
- **Guards stand in for the approval that was removed:**
  - Learn never asks the user anything (`AskUserQuestion` is forbidden).
  - ADRs are written as `Proposed`.
  - Reuse rules come back as suggestions only.
  - Only files under `docs/` that are not ignored and have no prior unstaged edits are staged.
  - The index is snapshotted, so any other change an agent makes to the index is caught.
  - Learn docs are scanned for secrets before the pre-commit gate.
  - A gate failure caused only by a learn doc is advisory.
  - The learn files are listed under **Added by learn** in the commit plan.
  - When no commit is made, the learn docs are unstaged.

## Consequences

### Positive
- Knowledge capture no longer interrupts a commit, and its docs are never left uncommitted.
- Each guard is defined in one place, `feature-learn` § Embedded Commit Capture, and both commands delegate to it.

### Negative
- A learn agent's output is committed without anyone reading it first. The allowlist, the index snapshot and the secret scan reduce that risk but do not remove it.
- The session guard compares file modification times. A git operation that touches modification times can cause an extra learn run.

### Neutral
- `--skip-learn` and `auto_learn_before_commit: false` still opt out.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep Step 6 and just silence it | The docs still land outside the user's commits, as an extra commit series or uncommitted. |
| Restore Step 0 unchanged | Reintroduces the 2.45.1 skip (stale evidence, pre-commit marker). |
| Keep asking for approval | This is the interruption the change exists to remove. |
