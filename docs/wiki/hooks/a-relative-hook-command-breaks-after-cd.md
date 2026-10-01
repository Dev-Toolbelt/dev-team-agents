# A relative hook command breaks after the session changes directory

**Origin:** a live `/devteam:backend` run in a monorepo left the task board empty although two agents were spawned | 2026-09-30
**Tags:** hook, settings.json, hooks.json, relative path, cwd, cd, subdirectory, monorepo, CLAUDE_PROJECT_DIR, non-blocking error, empty board, credential guard

> The provider runs a hook where the session IS, not where it started — and a hook that cannot be found fails silently.

---

## What it is

Claude Code runs a hook command in the session's current working directory. A Bash call such as
`cd apps/api` persists across calls, so every hook fired after it ran from `apps/api`. The command
`env -u BASH_ENV -u ENV .dev-team-agents/scripts/hooks/pre-tool-use.sh` then names nothing:

```
env: .dev-team-agents/scripts/hooks/pre-tool-use.sh: No such file or directory
```

Codex runs hook commands through the user's `$SHELL -lc` in the session's working directory, which
is a subdirectory whenever Codex was started in one.

## How it works

The provider records the failure as a **non-blocking** hook error in the transcript and carries on.
Nothing reaches the screen, so every hook stops at once — the task board, the credential guard, the
full-suite guard, the Stop lint and the session-summary check — and the session looks normal.

The registered commands now enter the project root first; the per-provider command is in
`CLAUDE-md/hooks.md` § Hook Commands Run From the Project Root.

## Gotchas

- To diagnose, look in the session transcript (`~/.claude/projects/<dir>/<session>.jsonl`) for
  `hook_non_blocking_error` attachments, and compare the `cwd` field of the records around them.
- Fixing the hooks one by one does not work: the dispatcher itself is never found, and more than 25
  sub-scripts already treat `$PWD` as the root.
- A test that runs a hook from the root proves nothing here; run it from a subdirectory
  (`tests/test_hook_project_root.py`).
- An existing project keeps the old command until `devteam sync` rewrites it.
