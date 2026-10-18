# Command References Are Not Rewritten Per Provider

**Origin:** `/devteam:learn` nudge in `commands/merge.md` § Step 4 | 2026-10-18
**Tags:** _CODEX_BODY_REPLACEMENTS, render_provider.py, command-map.json, $devteam-, /devteam:, Codex, opencode, inline command invocation, learn --auto

> A command body that runs another devteam command inline must spell the invocation for each provider itself. The renderer does not translate `/devteam:<name>` for Codex.

---

## What it is
Each provider names a devteam command differently. Claude Code and opencode use `/devteam:<name>`. Codex uses `$devteam-<name>`, backed by the skill file `.codex/skills/devteam-<name>/SKILL.md`. The render engine rewrites some phrases for Codex, but it does not rewrite command names.

## How it works
- `scripts/lib/command-map.json` sets the Codex exposed name to `$devteam-{name}` and the target path to `.codex/skills/devteam-{name}/SKILL.md`.
- `scripts/lib/render_provider.py` `_CODEX_BODY_REPLACEMENTS` only rewrites `TodoWrite`, `the Task tool` variants, and `.claude/settings.json`. No pattern matches `/devteam:`.
- opencode exposes commands as `command."devteam:<name>".template` entries in `opencode.json`. No command file exists to read, so an agent cannot open `/devteam:<name>` as a file.
- A command body that says `/devteam:learn --auto` ships unchanged to Codex. The Codex agent then has no matching command to run.

## Gotchas
- Write the invocation per provider in the body: `/devteam:<name>` for Claude Code and opencode, `$devteam-<name>` for Codex. Name the source file (`commands/<name>.md`) so the agent can read the flow directly on every provider.
- Use the same pattern as `skills/shared/git-workflow/SKILL.md` § Dirty-Tree Pre-flight and the inline health-check in `commands/update.md`.
- A new inline delegation needs the same per-provider spelling. A reference that works only for Claude passes a Claude-only test and fails silently on Codex.

## References
- `tests/test_learn_nudge_render.py`: pins `/devteam:learn --auto` for claude and opencode and `$devteam-learn --auto` for codex. The parity guard fails when a provider in `ALL_PROVIDERS` has no case.
- `scripts/lib/command-map.json`, `scripts/lib/render_provider.py` (`_CODEX_BODY_REPLACEMENTS`)
- `commands/merge.md` § Step 4, `commands/learn.md`
