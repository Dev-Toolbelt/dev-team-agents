Load and follow the workflow defined in `.claude/dev-team-agents/workflows/maintenance.md`.

Before starting, identify the current working context:
- Run `git branch --show-current` — active branch
- Run `git diff --name-only main...HEAD` — changes in this branch vs main
- Check `.claude/.worktree-session` if present — active worktree

Follow every step in the workflow exactly as defined. Spawn the required agents via the Task tool at each step — do NOT handle steps inline. Present the output of each step to the user before proceeding to the next.

Additional context or instructions: $ARGUMENTS
