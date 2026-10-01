# A background hand-back is HTML-escaped, and read late

**Origin:** a live `/devteam:backend` run left its two tasks in In Review as "result not read" although both reviewers ended with a marker | 2026-10-01
**Tags:** task board, review window, background agent, task-notification, hand-back, html escape, &lt;, marker, review-result, Stop, expiry, fix rule, result not read

> Claude Code escapes the `<result>` of a `<task-notification>`, and the Stop that reads it can come hours after it arrived.

---

## What it is

In the Claude Code desktop app an `Agent` call runs in the background by default. The agent's final
report reaches the transcript later, as a `<task-notification>` (a `queue-operation` entry plus a
mirroring `user` entry), and its `<result>` section is **HTML-escaped**: a reviewer's closing
`<!-- review-result: findings=3 -->` arrives as `&lt;!-- review-result: findings=3 --&gt;`.

The task board reads those hand-backs from the transcript at `Stop`, not when they arrive.

## How it works

Three things went wrong at once in the session that found this:

1. The marker regex looked for `<!--` and never matched the escaped text, so neither reviewer's
   result was read. The `<result>` section is now unescaped before the marker is read; the
   last-line rule still applies, so a marker quoted mid-report is still not a result.
2. The QA handed back one minute after launch, but the turn then waited on a question for eleven
   hours. The next `Stop` expired the window (6 h wait) **before** scanning the transcript, so the
   in-time result was never looked at. `Stop` now scans first; a hand-back timestamped after the
   wait ran out is still left to the expiry.
3. A result read at a late `Stop` was dated at that `Stop`, so the fix agents started meanwhile
   looked older than the result and the fix rule never released the tasks. A background result now
   counts from its hand-back's own timestamp, and only tasks created by then are excluded from the
   fix list.

## Gotchas

- Only the Claude background path is escaped. A foreground `Agent` result (PostToolUse), Codex
  `wait_agent` and opencode `tool.execute.after` all carry the report as plain text.
- To diagnose, grep the session transcript for `review-result` and compare the record's
  `reviews[].markers`, `queue_ids` and `consumed` with the notifications' `<tool-use-id>`.
- A record whose transcript cursor already passed the hand-backs is not repaired by the fix: the
  scan never re-reads what it has passed.
- Tests: `tests/test_review_board.py::BackgroundReviewTest` replays the live sequence.
