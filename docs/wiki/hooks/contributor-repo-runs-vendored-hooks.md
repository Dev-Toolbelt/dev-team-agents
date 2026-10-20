# A hook edit in this repo does not run until the vendored copy is synced

**Origin:** /devteam:learn consolidation, execution trace work (ADR-0041) | 2026-10-19
**Tags:** hook, vendored hooks, .dev-team-agents/scripts/hooks, scripts/hooks, settings.json, post-tool-use, trace, interrupted spans, self-heal, sync

> In this repository, editing a hook under `scripts/hooks/` changes nothing for the post-tool-use hooks until that code is synced into `.dev-team-agents/scripts/hooks/`, the copy those hooks execute.

---

## What it is

This repository is its own installed project. `.claude/settings.json` wires each hook one of two ways. Both forms exist side by side for some events.

## How it works

| Hook event | Entry | Runs |
|------------|-------|------|
| PostToolUse, PostToolUseFailure | wrapper | `.dev-team-agents/scripts/hooks/post-tool-use.sh` (vendored) |
| PreToolUse | plain | `scripts/hooks/pre-tool-use.sh` (repo root) |
| PreToolUse | wrapper | `.dev-team-agents/scripts/hooks/pre-tool-use.sh` (vendored) |
| PreCompact | plain and wrapper | repo root, then vendored |
| SessionStart, Stop | plain | `scripts/hooks/<name>.sh` (repo root) |

The wrapper resolves the project root and runs the vendored copy. When a core store is linked (`core-dir`), it runs `self-heal.sh` against that store's current version instead.

## Gotchas

- An edit to `scripts/hooks/post-tool-use*` has no effect on the running session. The vendored copy keeps the old code until it is synced.
- Plain entries pick up repo-root edits at once. Wrapper entries do not. Two edits to the same hook family can therefore take effect at different times.
- During the execution trace work, the vendored `.dev-team-agents/scripts/hooks/post-tool-use/01-task-board.sh` had no trace code. The plain PreToolUse entry from the repo root still recorded each span at spawn, but the vendored post-tool-use never delivered the agent's result. Stop then settled those spans as `interrupted`. The trace was not empty; its spans all ended as `interrupted`.

## References

- `.claude/settings.json` — the wiring
- Check: `grep -n '"command"' .claude/settings.json`, then `diff -r scripts/hooks .dev-team-agents/scripts/hooks`
