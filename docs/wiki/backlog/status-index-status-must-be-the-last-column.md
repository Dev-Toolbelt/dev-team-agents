# Status index: Status must stay the last column

**Origin:** embedded learn pass, sprint time-tracking columns (ADR-0044 backlog claims) | 2026-10-31
**Tags:** sprints.md, status index, devteam backlog, _index_in_progress, backlog prime, Time Tracking column order, In progress, ADR-0044

> Keep `Status` as the last column of every sprint status index: `_index_in_progress` reads only the last cell, so a column added after it hides running sprints from `devteam backlog prime`.

---

## What it is

The sprint status index is a Markdown table that lists every sprint and its state. `devteam backlog` reads it to find sprints that are running. It applies to `docs/backlog/sprints/sprints.md` and, in the gated layout, to the `## Sprints` table of `docs/backlog.md`.

## How it works

`scripts/lib/devteam/backlog.py`, function `_index_in_progress`, does this for each row:

1. Splits the row on `|` and strips each cell.
2. Skips the row unless it has at least three cells and `cells[-1]` equals `in progress`, case-insensitive.
3. Reads the sprint name from `cells[1]` and the scope from `cells[0]`.

The function does not look up a column by its header. It assumes Status is the last cell.

`prime(root)` calls `_index_in_progress` after a context compaction or resume. A sprint missing from the result loses its claim-based recovery.

## Gotchas

- **The trap.** The Started, Finished and Time spent columns were added after Status. The last cell became `Time spent`, which shows `—` while a sprint runs. `prime` then stopped finding running sprints once their claims expired.
- **Tests did not catch it.** `tests/test_backlog.py` index fixtures use 5-column rows. No test covers the 8-column index, so the regression passed the suite. An architecture review found it.
- **The rule.** Add new columns before `Status`. Never after it.
- **Correct form.** `skills/shared/backlog-template/SKILL.md` § Time Tracking and its index tables already follow this order: Scope, Sprint, Theme, Goal, Started, Finished, Time spent, Status.
- **Migrating an old index.** Insert the new columns before `Status` in place and fill existing rows with `—`. Do not rewrite the table.
- **Check after editing.** Run `devteam backlog prime` against a sprint marked `In progress` with an expired claim. It must still report the sprint.

## References

- ADR-0044, decision 4: the post-compaction `prime` that reads this index.
- `scripts/lib/devteam/backlog.py` § `_index_in_progress`.
- `skills/shared/backlog-template/SKILL.md` § Time Tracking.
