# Review State Is Inferred, Not Reported

**Origin:** In Review column implementation (ADR-0018 amendment) | 2026-09-30  
**Tags:** review state, task board, review window, marker, inferred, outcome

> No provider has a review status field — the column is inferred entirely from review triggers, window tracking, and the agent's result marker.

---

## What it is

The task board's optional **In Review** column exists only when a review is active in a session. A task enters because a review was triggered (agent spawn, command, or prompt keyword), and leaves when the review resolves (findings = 0) or the fixes are applied. No provider tool has a status for this — it is pure inference by the hooks from the window's lifecycle and the markers agents emit.

## How it works

**Window opens** when:
- A review/QA agent is spawned (`qa-specialist`, `code-reviewer`, `backend-reviewer`, `frontend-reviewer`)
- A review command is issued (`/devteam:review`, `/devteam:qa`)
- A prompt explicitly requests review (keyword: `review`, `revisar`, `revisão`, `QA`, `testar`, `test`, etc. with negation awareness)

**Tasks enter** the window from the session at the moment it opens:
- Every task currently `in_progress`
- Every task `completed` after the previous review window resolved (or ever, if none)
- Tasks created after the window opened do not enter

**Result is read from markers** — not a provider field:
- `<!-- review-result: findings=N -->` in the agent's final report (`PostToolUse` response on Claude, `wait_agent` on Codex, `task` output on opencode)
- For command/prompt triggers, the transcript's last assistant message is scanned at `Stop`
- No marker anywhere: `findings: null` (shown as "result not read")

**Window resolves** when:
- All sources have reported (no token left: foreground launches, background launches, the prompt/command scan flag). A finished turn retires still-outstanding foreground launches as unread; a window idle for 6 hours settles as unread
- `findings = 0`: resolution = `"passed"`, tasks return to `in_progress` or `done`
- `findings > 0`: tasks stay in review, awaiting fixes; `tasks.review_findings` notification
- `findings = null`: stays in review with the "result not read" badge until fixes or re-review resolve it

## Gotchas

- **No provider status exists.** If you try to read a provider's task status field expecting a `"in_review"` value, you will not find it. The column is computed entirely from the session's `reviews[]` array and derived timestamps.
- **Triggers can false-positive on innocent text.** A session summary or chat message mentioning "do a code review" for architectural reasons can open a window even though no review agent was spawned. The detection is deliberate (to catch implicit requests) but keyword-bounded and negation-aware to minimize surprises.
- **Parallel reviewers are summed, not merged.** Each report retires one slot and counts its last marker; the markers of distinct reports are summed. An unread reviewer (no marker) never turns another agent's zero into a pass — `findings` stays as is only when all seen sources are zero.
- **A task can re-enter the window.** If an agent sets a task back to `in_progress` while in review, it leaves immediately and re-enters if the review stays open or a new one opens later.
- **Worktree isolation is respected.** Each worktree keeps its own record; the main checkout's review window state does not leak into a linked worktree or vice versa.

## References

- `docs/specs/task-board.md` § "In Review — the fourth column" — the full spec with JSON schema and behavior rules
- `skills/shared/review-result/SKILL.md` — the marker template agents load and emit
- `scripts/hooks/pre-tool-use/01-task-board.sh` — Claude Code review trigger detection
- `scripts/lib/devteam/review_triggers.py` — centralized trigger matcher for all providers
