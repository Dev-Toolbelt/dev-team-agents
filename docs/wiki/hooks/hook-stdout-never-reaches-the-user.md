# A hook's stdout never reaches the user

**Origin:** the framework's notifications "never worked" — every trigger was right, and none was ever seen | 2026-09-29
**Tags:** hook, stdout, SessionStart, Stop, notification, banner, DEV TEAM AGENTS, model context, provider, desktop app

> SessionStart stdout is context for the model. Stop stdout is not displayed. Neither is a way to tell the user anything.

---

## What it is

Claude Code (and Codex, and opencode) run the framework's hooks and capture their output, but
what they do with it is not "show it":

| Hook | Where stdout goes |
|------|-------------------|
| `SessionStart` | Injected into the model's context. The agent sees it; the user does not |
| `Stop` | Not displayed (only a blocking decision, or verbose/transcript mode, surfaces anything) |
| `PreToolUse` | Only as `additionalContext` / a block reason — again to the model |

## How it works

The framework printed a boxed `━━ DEV TEAM AGENTS ━━` banner from `session-start.sh`
and `stop/04-notifier.sh`. The first went into the model's context; the second went nowhere. The
notifier was eventually disabled for costing python forks every turn "with no observed user-visible
benefit" — a correct observation about a channel that could not deliver.

The fix was a channel, not a better banner: hooks append to a queue
(`scripts/hooks/lib/notify.sh`), and the desktop app streams it and raises native OS notifications
(ADR-0017).

## Gotchas

- **Stdout is still the right place for an instruction to the agent** — the `[DEVTEAM:*]` markers
  (`FIRST_TIME_SETUP`, `SESSION_BANNER`, `TEST_SCOPE_RULE`) work precisely because SessionStart
  stdout is model context. Decide who the reader is before choosing the channel.
- A provider-specific output (Claude Code's `systemMessage` JSON) would reach the user in one
  provider only; the same hooks run under three.
- Test that a hook prints **nothing** on stdout when it only means to notify:
  `tests/test_notifications.py::NotifierHookTest::test_nothing_reaches_stdout`.
