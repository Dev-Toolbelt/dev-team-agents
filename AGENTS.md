# AGENTS.md — dev-team-agents

## Contributor Rules

The contributor rules for this repository live in `CLAUDE.md`, the single source. It is not copied here: it is about 62 KB against Codex's 32 KiB project-doc cap, and two copies would drift.

- **Before any task**, read `CLAUDE.md` in full — plus the `CLAUDE-md/` companion sections it links when the task touches them — and follow it as if it were written in this file.
- Where `CLAUDE.md` names a Claude Code tool (`AskUserQuestion`, `Task`), use your provider's equivalent from `scripts/lib/tool-map.json`.
- Never write a contributor rule in this file: add it to `CLAUDE.md`. The block below is maintained by `scripts/install-codex.sh`; change it there, never here.

<!-- dev-team-agents: codex-session-banner -->
## Codex Session Banner

When the `SessionStart` hook context contains a line exactly equal to `[DEVTEAM:SESSION_BANNER]`, reproduce the lines that follow it, up to the first blank line, **verbatim, unmodified**, as the first thing in your **first reply of the session**.

Rules:
- Do not add any text before the banner.
- Do not translate, summarize, or reformat it.
- Do not fabricate the banner when the marker is absent.
- This rule applies to normal conversation too, not only `$devteam-*` skills.
