# Rendered paths must match what shipped scripts use

**Origin:** audit backlog — path rewrite in tool-map.json broke commands when shipped scripts didn't follow it | 2026-10-02
**Tags:** render, path rewrite, tool-map.json, adr, script, render_provider.py, opencode, codex, tool_unavailable, docs/development

> A path rewrite in `tool-map.json` is only safe if the shipped scripts (new-adr.sh, reuse-lint.sh, etc.) use the same path. A rewrite that breaks that assumption silently creates broken references.

---

## What it is

The render engine can rewrite paths in agent and command bodies at render time, e.g., `docs/development/` → `docs/` for opencode and Codex. This works only if the shipped scripts that run in the target project also use the rewritten path. If the script still refers to `docs/development/adr` but the rendered command body says `docs/adr`, the command will fail.

A previous iteration rewrote `docs/development/` for opencode and Codex, causing `/devteam:adr` and `/devteam:rule` to read from directories those scripts never wrote to, and `new-adr.sh`, `reuse-lint.sh`, `03e-adr-gap-check.sh` (which run in the project) did not know about.

## How it works

Before adding a path rewrite:

1. **Find all scripts that hard-code the path** (`grep -r "docs/development"` in `scripts/`).
2. **Check whether they ship to user projects** (in `KEEP_ROOT` / visible to the render engine).
3. **If yes:** either drop the rewrite (simplest) or patch **all** occurrences in **all** shipped scripts in the same commit.
4. **If no:** the rewrite is safe only if no rendered agent/command references it.

Also: load `tool_rewrites` and emit them to the rendered output. Previously, the tool-map declared `tool_rewrites` but never emitted them; the renderer now includes them. Tools with no provider equivalent get a `tool_unavailable` entry describing the fallback, never an invented tool name.

## Gotchas

- **Path rewrites are not backward-compatible.** A rewrite applied to opencode breaks every prior project that has stored scripts or hooks that refer to the old path.
- **The rewrite must be symmetric.** If opencode renders `docs/` (from `docs/development/`), every shipped script must read from `docs/`. A mismatch is discovered only when the script runs in the user's project.
- **Tool rewrites must be declared and emitted.** A silent mapping helps no one — the provider sees an invalid tool name and fails.

## References

- `scripts/lib/tool-map.json` — `path_rewrites`, `tool_rewrites`, `tool_unavailable`
- `scripts/lib/render_provider.py` — `render_run_banner()`, emission of tool rewrites
- `tests/test_render_tool_map.py` — iteration over ALL_PROVIDERS, path consistency check
- `scripts/new-adr.sh`, `reuse-lint.sh`, `scripts/hooks/stop/03e-adr-gap-check.sh` — shipped scripts that must be checked
