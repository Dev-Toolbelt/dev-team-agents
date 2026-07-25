# Worktree Session Protocol

## Decision sources (in precedence order)

The worktree decision has three sources. Resolve them top-down and stop at the first that applies:

| # | Source | Action |
|---|--------|--------|
| 1 | `.dev-team-agents/.worktree-session` present | Follow the stored per-session decision silently |
| 2 | `worktree_active` in `preferences.json` | Use it **without asking**; then write the session file so every later agent in the session is consistent |
| 3 | key absent (legacy install) | Ask the user once (see below) |

The session file is the per-session **override**; `preferences.json` is the persistent **default**.

---

## Session file: `.dev-team-agents/.worktree-session`

Persists the resolved decision across agents in a multi-agent workflow so every agent does not re-resolve independently.

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
cat .dev-team-agents/.worktree-session 2>/dev/null
```

- `worktree=no branch=<b>` → operate on branch `<b>`; do not load the worktree skill
- `worktree=yes branch=<b>` → load `skills/shared/worktree/SKILL.md` using branch `<b>`
- File absent → fall through to the preferences default (below)

---

## Preferences default (when session file is absent)

Read the worktree keys from `.dev-team-agents/user-data/preferences.json`:

```bash
python3 -c "import json;d=json.load(open('.dev-team-agents/user-data/preferences.json'));print(d.get('worktree_active',False), d.get('worktree_base_branch') or '', d.get('worktree_path','.dev-team-agents/worktrees'), d.get('worktree_docker_isolate',True))" 2>/dev/null
```

- `worktree_active == true` → resolve the base branch (see below), then write
  `echo "worktree=yes branch=<base>" > .dev-team-agents/.worktree-session` and load the worktree flow. Do **not** show the worktree yes/no prompt.
- `worktree_active == false` → do **not** show the worktree yes/no prompt; ask only for a new branch name (suggest `<context>/<brief-title>`), run `git checkout -b <name>`, write `worktree=no branch=<name>`.
- key absent (legacy) → ask the user the yes/no question (next section).

### Resolving the base branch

Use the first that applies:

1. `worktree_base_branch` from `preferences.json` if non-null
2. Project override in `CLAUDE.md` / `AGENTS.md` (base branch convention)
3. Auto-detect the repository default branch:
   ```bash
   git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' \
     || git rev-parse --abbrev-ref HEAD
   ```
4. If none resolves, ask the user.

> Never hardcode `main`, `master`, or `beta` — always resolve in this order.

---

## Asking the user (only when the preference key is absent)

Use the `AskUserQuestion` tool with options [Yes, No]:
"Should this task use a git worktree (isolated working directory)?"

- **Yes** → ask for the base branch (default: auto-detected default branch), write `worktree=yes branch=<base>`, load `skills/shared/worktree/SKILL.md`
- **No** → ask for a new branch name (suggest `<context>/<brief-title>`), run `git checkout -b <branch-name>`, write `worktree=no branch=<branch-name>`

---

## Cleanup

The session file is ephemeral — remove it after the task is finalized (merged) and cleaned up:

```bash
rm -f .dev-team-agents/.worktree-session
```

Ensure it is gitignored (the installer already adds this):

```bash
grep -qxF '.dev-team-agents/.worktree-session' .gitignore 2>/dev/null \
  || echo '.dev-team-agents/.worktree-session' >> .gitignore
```
