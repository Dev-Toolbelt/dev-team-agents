# Worktree Session Protocol

## Session file: `.claude/.worktree-session`

The session file persists the worktree decision across agents in a multi-agent workflow. It prevents every agent from asking the same worktree question independently.

### File format

```
worktree=yes branch=<base-branch>
```
or
```
worktree=no branch=<branch-name>
```

### Reading the session file

```bash
cat .claude/.worktree-session 2>/dev/null
```

Decision logic:
- `worktree=no branch=<b>` → operate on branch `<b>`; do not load the worktree skill
- `worktree=yes branch=<b>` → load `skills/shared/worktree/SKILL.md` using branch `<b>`
- File absent → ask the user (see below)

### Writing the session file

After the user answers the worktree question, write immediately:

```bash
# If worktree=yes (ask for base branch first, default: current branch)
echo "worktree=yes branch=<base-branch>" > .claude/.worktree-session

# If worktree=no (ask for new branch name, suggest <context>/<brief-title>)
git checkout -b <branch-name>
echo "worktree=no branch=<branch-name>" > .claude/.worktree-session
```

### Asking the user (when file is absent)

Use the `AskUserQuestion` tool with options [Yes, No] to ask:
"Should this task use a git worktree (isolated working directory)?"

- **Yes** → ask for the base branch (default: current branch), write `worktree=yes branch=<base>`, load `skills/shared/worktree/SKILL.md`
- **No** → ask for a new branch name (suggest `<context>/<brief-title>`), run `git checkout -b <branch-name>`, write `worktree=no branch=<branch-name>`

### Cleanup

The session file is ephemeral — remove it after the task is merged and cleaned up:

```bash
rm -f .claude/.worktree-session
```

Ensure it is gitignored:

```bash
grep -qxF '.claude/.worktree-session' .gitignore 2>/dev/null \
  || echo '.claude/.worktree-session' >> .gitignore
```
