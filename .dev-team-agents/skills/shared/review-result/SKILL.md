---
name: review-result
description: Findings table, clean-verdict evidence, review loop and the closing review-result marker.
---

# Review Result Marker

A review or QA pass moves the session's tasks into the task board's **In Review** column. The board
learns the outcome only from this marker; without it the cards show **result not read** and stay in
review. Design: `docs/specs/task-board.md` § In Review.

## Rule

The last line of the final report of any review or QA pass is exactly:

```
<!-- review-result: findings=N -->
```

| Field | Value |
|-------|-------|
| `N` | Number of findings the user must act on: every blocking or non-blocking defect, gap or failed check you reported. `0` means the work passed |

- Emit it once, after the **Ran on:** table, as the final line.
- Count what you reported, not what you considered: a finding you dropped as speculative is not counted.
- A pass that could not run (missing environment, nothing to review) emits no marker — say why instead.
- Parallel reviewers each emit their own marker; the board sums the markers of distinct reports. A report counts once, by its last marker, so never repeat a marker earlier in the same report.
- A routing-only pass (`code-reviewer` in router mode, which only delegates) emits no marker: the specialists it spawns each emit theirs.
- Do not emit it from a pass that is not a review or QA of work done (planning, implementation, docs).

## Findings Table

The closing index of a review or QA report: one row per finding the report raised, placed before
the **Ran on:** table. It does not replace the agent's own report sections — it indexes them, so
the marker can count them and the [Review Loop](#review-loop) can compare rounds. `N` in the marker
is the number of rows.

| # | Severity | Finding | Location | Evidence |
|---|----------|---------|----------|----------|
| 1 | BLOCKING | [specific title] | `path:line` | [failing command, test, or the rule/contract it violates] |

| Column | Rule |
|--------|------|
| Severity | The labels of `skills/shared/pr-review/SKILL.md` — `BLOCKING`, `SUGGESTION`, `NITPICK`, `QUESTION` — never a second vocabulary; rows ordered most severe first. An agent whose report grades differently writes the mapped label: `BLOCKER`, `CRITICAL` → `BLOCKING`; `MAJOR`, `HIGH`, `MEDIUM` → `SUGGESTION`; `MINOR`, `LOW`, `INFO` → `NITPICK` |
| Finding | Specific enough to tell two findings apart — never "improve error handling" |
| Location | `path:line` when the finding has one; `—` for a general finding |
| Evidence | What makes it real: a reproducible failure, command output, or a named rule. A row without evidence is speculation — drop it |

The detail of each finding stays in the agent's own report sections; the table repeats only what
tells findings apart.

## Clean Verdict Evidence

`findings=0` claims the work passed, so it must rest on something executed in this pass, not on
reading the code and finding it plausible. A report with zero findings carries one line above the
**Ran on:** table:

```
**Verified:** <command or check that ran in this pass> → <result>
```

- List each check that ran (tests covering the diff, a lint, a reproduction of the original bug). Which tests to run is decided by `skills/shared/scoped-test-execution/SKILL.md`.
- When nothing could be executed (no test setup, missing environment), say so on that line — `**Verified:** nothing executable — <reason>; verdict is from reading only`. Never omit the line.
- Mocks, prose or the author's intent are not evidence when running the code was feasible.

## Review Loop

The fix-and-re-review loop an orchestrator runs after the user chose to apply findings. Owned by the
main conversation or the outermost command, never by a spawned reviewer.

| Point | Rule |
|-------|------|
| **Round** | One round = the reviewers run, the findings are applied. Round 1 is the original review |
| **Re-review** | After applying, re-spawn only the reviewers whose last report had a `BLOCKING` or `SUGGESTION` row, on the same target. Each prompt carries that reviewer's previous Findings Table and asks it to confirm each row is fixed and to report regressions the fixes introduced |
| **Cap** | 3 rounds in total |
| **Apply** | "Apply all" applies `BLOCKING` and `SUGGESTION` rows of later rounds without asking; `NITPICK` rows are listed; `QUESTION` rows go to the user. "Apply selected" asks again each round. A fix that needs a new file, a behavior change or anything outside the reviewed scope is asked about, never applied silently |

The loop ends in exactly one terminal state, reported in one line (`Review loop: clean after 2 rounds`):

| State | When |
|-------|------|
| `clean` | No re-spawned reviewer returned a `BLOCKING` or `SUGGESTION` row; a reviewer with `findings=0` carries its **Verified:** line. Remaining `NITPICK` rows are listed, not looped on |
| `exhausted` | Round 3 ended with findings left |
| `stalled` | Two consecutive rounds returned the same findings — same Location and Finding — so applying is not making progress |
| `blocked` | Every remaining finding needs a user decision (a `QUESTION` row, scope, behavior change, missing environment) |

On any state other than `clean`, list the remaining rows and ask with `AskUserQuestion` whether to
keep fixing them by hand or leave them open. Never start a fourth round, and never mark a finding
resolved without a reviewer confirming it.
