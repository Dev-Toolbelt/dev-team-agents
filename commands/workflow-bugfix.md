Load and follow the workflow defined in `.claude/dev-team-agents/workflows/bug-fix.md`.

Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Follow every step in the workflow exactly as defined. Spawn the required agents via the Task tool at each step — do NOT handle steps inline. Present the output of each step to the user before proceeding to the next.

Bug description: $ARGUMENTS
