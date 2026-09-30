# devteam sync registers hook events the linked core version may not have

**Origin:** Task board work discovered sync registers PostToolUse and SessionEnd events whose scripts don't exist in an older linked core | 2026-09-30
**Tags:** devteam sync, hook, hooks.EVENTS, core version, linked tree, missing hook, symlink, scripts, core store

> `devteam sync` registers hook events listed in the running CLI's `hooks.EVENTS`, but the scripts those entries call are resolved through the project's symlink to the store's CURRENT core version.

---

## What it is

In v3 layout, each project links to a `core` tree in the global store. The `core` tree holds the canonical scripts (the installed version). When you run `devteam sync`, it reads hook event definitions from the **running CLI** — the one you invoked — and registers them in the project. But the event handlers (the bash scripts) are fetched from the **linked core** — the version that is pinned in the project.

If the running CLI is newer than the linked core, you register event handlers that don't exist yet.

## How it works

```
$ devteam sync  # Running a newer CLI than the linked core

1. Reads the running CLI's tiers.json, hook definitions, etc.
2. Registers hooks listed in hooks.EVENTS (e.g., "PostToolUse", "SessionEnd")
3. Writes `.dev-team-agents/.hooks.json` with entries like:
   {
     "pre_tool_use": [
       {"when": "post_tool_use", "run": "scripts/hooks/post-tool-use/01-task-board.sh", "async": true}
     ]
   }
4. Project's symlink → core/ → /var/…/core/v1.2.3/ (older, doesn't have 01-task-board.sh)
5. Next tool call fires the hook, runs the symlinked script path, gets 404

Result: "Not found" or script not found error on every matching tool call.
```

## Gotchas

- **The hook path is evaluated at runtime**, not at registration time. Linting, tests, and `devteam sync` all pass silently.
- **Every PreToolUse-triggered tool call reruns the hook.** If the hook is missing, the tool call itself fails *on every invocation*, not just once. Task creation stalls, planning stalls, and errors look like CLI breakage, not a missing hook.
- **The fix is to upgrade the core before running sync.** Install the newer core version the running CLI expects: `devteam store install --from <tree> --activate`, then `devteam sync`. Alternatively, wait for the next `devteam update` to resolve the linked core.
- **Pinned projects don't auto-resolve.** A project pinned to v1.2.3 will keep running against v1.2.3 until you unpin or explicitly sync to a newer version.

## References

- Core store management: `devteam store install`, `devteam store show`
- Layout v3 design: ADR-0013 (store layout)
- Hook registration: `.dev-team-agents/.hooks.json`
