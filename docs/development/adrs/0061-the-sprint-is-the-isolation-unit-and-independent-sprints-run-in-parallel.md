# ADR-0061: The sprint is the isolation unit and independent sprints run in parallel

**Date:** 2026-10-31  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `commands/sprint.md`, `skills/shared/backlog-template/SKILL.md`, `agents/product-analyst.md`, `scripts/lib/commands.json`

## Context

`/devteam:sprint` recommended a worktree per task: every task of a wave ran in parallel in its own
worktree and was merged into the sprint's integration branch at the end of the wave. Parallelism
lived inside one sprint, and sprints ran one at a time. In practice that meant a merge per task,
a Docker stack per task when the project uses Docker, and conflicts between tasks of the same
sprint, which by design work on the same feature area. Nothing in planning made two sprints
independent of each other, so there was no way to run them side by side. ADR-0035 decision 5 recorded
that per-task default, and ADR-0044 renews claims per wave; this ADR changes the first and keeps the
second, renewed per round.

## Decision

- The sprint is the unit of isolation. `/devteam:sprint` always recommends **Whole sprint in its
  own worktree**: the sprint runs in its integration worktree `sprint/<scope-slug>-<n>`, with its
  own isolated Docker stack when the project uses Docker and `worktree_docker_isolate` holds. Its
  tasks run one at a time, in wave order, and each task is reviewed on its own commit range. It
  replaces the former "One branch, tasks in sequence" option, and `worktree_active` no longer picks
  the recommended strategy.
- One run may execute several sprints. Each gets its own worktree, stack and claim owner; each
  round spawns the next task of every running sprint in parallel. Rounds are synchronized: the next
  one starts once every task of the current one passed its gate. A sprint whose task gate fails
  stops alone; the others keep running, and each sprint closes with its own PR.
- `product-analyst` plans sprints to run together: no task of one depends on a task of another in
  the same group, and they touch disjoint files, schema and migrations. Each sprint file names its
  group in `**Runs with**:` (`backlog-template` § Sprint Parallelism). `/devteam:sprint` runs
  several sprints in parallel only when their `Runs with` lists agree, and otherwise recommends
  running one.
- **Worktree per task** stays as the alternative for a single sprint.

## Consequences

- Fewer merges and stacks: one per sprint instead of one per task. Tasks of a sprint build on each
  other's commits without a merge step.
- A single sprint runs slower than before, because its tasks no longer run in parallel. The speed
  comes from running independent sprints at once, which depends on the planning step splitting
  scope well.
- The slowest sprint sets the pace of a round for every sprint in the run — the price of one gate
  question at a time and claims renewed in one place.
- Conflicts move from task merges to the PRs of parallel sprints. `Runs with` is the planner's
  claim that none exist; the user can override a missing one and then owns the risk. The shared files are the indexes — the sprint
  index, and the wiki and ADR indexes when a sprint's learn nudge writes: each sprint adds or flips
  its own rows on its branch, so a later PR meets row conflicts that keep both sides.
- The `devteam backlog` parser is unchanged: `Runs with` sits in the sprint header, and the parser
  reads only task fields. Waves keep their meaning as the order of tasks.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Keep worktree per task as the default | A merge and a stack per task, and conflicts between tasks of the same feature area |
| Run a wave's tasks in parallel inside the sprint worktree | Agents sharing one working tree collide on files, test runs and infra |
| Let each sprint advance independently, without rounds | Gate questions from several sprints interleave, and claims renew from many places at once |
| Derive sprint parallelism from task dependencies only | Dependencies do not show shared files or schema; the planner has to declare the group |
