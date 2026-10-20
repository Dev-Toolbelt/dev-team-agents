## Audit Report: task-board

### Scope

Second audit of the cross-project task board (ADR-0018, ADR-0041, `docs/specs/task-board.md`,
`docs/specs/execution-trace.md`). The first one, `docs/audit/task-board-audit-2026-10-01.md`,
was followed by about 76 commits to this area. This audit focuses on how the board **updates**
tasks, agents and subagents, and sessions, across `claude`, `opencode` and `codex`.

| Layer | Files in scope |
|---|---|
| Capture | `scripts/hooks/lib/task-board.sh`; `pre-tool-use/04-task-board.sh`; `post-tool-use/01-task-board.sh`, `02-pr-created.sh`; `user-prompt-submit/01-task-board.sh`, `02-issue-refs.sh`; `stop/04b-task-board.sh`; `session-end.sh`, `session-retitle.sh` |
| Wiring | `scripts/lib/devteam/hooks.py`, `scripts/lib/codex_hooks_merge.py`, `opencode/plugin/dev-team-agents.ts` |
| Record and derived view | `scripts/lib/devteam/tasks.py`, `trace.py`, `pr_refs.py`, `review_triggers.py`, `cli.py` (`tasks` subcommands), `lock.py`, `jsonio.py` |
| Desktop app | `app/src/cli/operations.ts` (board parsers, `watchTasks`); `app/src/main/taskBoard.ts`, `taskBoardIpc.ts`, `settings.ts`; the preload bridge; `app/src/renderer/screens/Board.tsx`, `BoardTabs.tsx`; `app/src/renderer/boardTabs.ts`, `boardModel.ts` |

**How it works.** Hooks write one machine-local JSON record per session, under a lock and
atomically. The CLI derives every column when the record is read. The app is a pure client over
`tasks list/watch --json`, and each push replaces the whole feed.

**How the audit ran.** Agents ran in parallel for backend, frontend, security, devops, backend
tests and frontend tests.

**Test results.**
- Python: board suites, 720 tests, 1 failing (issue 9).
- App: main-process and model suites, 158 passing; renderer suites, 117 passing on Node 24.

**Prior audit (2026-10-01).**
- Items 1 to 6 and S1 to S2 are fixed.
- S3 is mostly fixed; what remains is issue 11.
- Retention and pruning are still open (see Infrastructure).

### Resolution (2026-10-20, branch `audit/board`)

| Item | Status |
|---|---|
| Issues 1-17 | Fixed with regression tests, except as noted below |
| Issue 3 | Fixed by skipping the alias-named child session; the Codex child-thread payload shape is inferred from the trace and was not captured live. Open: a Codex v2 spawn answered only with a task path writes no alias, so its child threads may still show as sessions, and a child hook that fires before the alias is written slips through — needs a live Codex payload |
| Issues 11, 12 | Reported on the CLI's stderr; the hook wrappers still send that stderr to `/dev/null`, so a hook-driven loss stays invisible (kept by decision: no tracebacks in the provider transcript) |
| S1, S3, S4, S5, S6 | Fixed |
| S2 | Fixed for Claude Code (ADR-0043), including a `.git` gitfile bypass and matches outside the project found in review; v2 installs get it on update. Codex and opencode launchers never follow a `cd` |
| S7 (retention) | Open: product decision |
| `live_title` | LRU eviction; the read for ended sessions is kept, because a rename after a session ended must still reach the board |
| Windows `os.replace` | Retried on `PermissionError` |
| Node for app tests | `app/.nvmrc` already pins 24.21.0; the shell's default Node 20 was the cause |
| `account.test.tsx` red test | Pre-existing on `main`; outside this audit |

### Critical Issues

| # | Severity | Layer | Provider | Description | Suggested Fix |
|---|----------|-------|----------|-------------|---------------|
| 1 | med | BE | claude, codex | A subagent's own todo items (owner `ag-N`) stay `in_progress` after the agent finishes, so `all_done` never turns true and `tasks.session_done` never fires. The session goes stale after 1 h and is flagged abandoned at end (`tasks.py` `_end_agent` ~1200, `_apply_agent` ~1206). Verified. | Keep the runtime `agentId` on the agent task, and at agent end retire that owner's unfinished native tasks |
| 2 | med | BE | opencode | A child session's `todowrite`/`task` call carries `parent_id` but is recorded as its own session. Only direct mode skips `parent_id` (`pre-tool-use/04-task-board.sh:73-82`). The result is a phantom session per subagent, which its own `session.idle` then marks idle. Verified. | Skip todo and spawn payloads that carry `parent_id`, the same way direct mode does |
| 3 | med | BE | codex | Codex child threads hook under their own session id, while the board never reads `trace/aliases.json` (the trace does). Same phantom-session effect as issue 2. Plausible (no child-thread payload captured). | Resolve the alias map before recording |
| 4 | med | BE | codex | A v1 `spawn_agent` whose `wait_agent`/`close_agent` never arrives stays `in_progress` indefinitely, because only v2 `/path` refs are capped by `PENDING_MAX_AGE` (`_is_v2` ~1167, `_interrupt_agents` ~2264). The trace caps the same span at 6 h, so board and trace disagree. Verified (still open after 27 h). | Apply `PENDING_MAX_AGE` to every `agent_ref` task |
| 5 | med | FE | all | The CLI emits `interrupted: true` (`tasks.py:1194`, at Stop) but `asBoardTask` drops it, and the field is absent from `BoardTask`. An agent cut off by Esc, a v2 timeout or a thrown `task` looks like a successful Done card, while `session_done` is withheld for it (`tasks.py:1322`). Verified. | Parse `interrupted`, add it to `BoardTask`, and badge it next to Failed |
| 6 | med | BE | all | The `redact` long-token regex is quadratic on long runs with no spaces (12 s at 80 KB), and runs in PreToolUse and PostToolUse on every todo rewrite (`tasks.py:143`, `:705`). Verified. | Truncate to `MAX_TASK_TEXT` before `redact`; replace the look-aheads with a plain match and check the character classes in code |
| 7 | low-med | BE | claude | A background hand-back that names only `<task-id>` ends the trace span (matched by `agent_id`) but not the board task (matched only by `tool_use_id`) (`_scan_agent_tasks` ~2235). Plausible. | Match on the stored `agentId` too (same data as issue 1) |
| 8 | low-med | BE | all | `stop/04b-task-board.sh` runs after 13 lint and check scripts. If the provider's hook timeout fires first, the session is never marked idle, the direct card is never settled and no done notification is raised. Plausible. | Order the board Stop script ahead of the lints |
| 9 | low | BE | all | `tests/test_review_board.py:1096` is red: a review spawn in a session with no record now forks python once, for the trace. Verified. | Gate the trace call cheaply, or count non-trace forks and pin exactly one trace fork in a companion test |
| 10 | low | BE | opencode | `record` reads the stored title outside the lock and writes it back inside, so a `session.updated` retitle landing in between is overwritten (`tasks.py` ~2619/2661). The next Stop heals it. Plausible. | Inside the lock, prefer `rec["title"]` |
| 11 | low | BE | all | Lost silently: when the 10 s lock wait times out, the dropped `TaskCreate`/`TaskUpdate`/`agent_spawn`/`agent_end` leave no trace. A lost `agent_end` later shows as cancelled or interrupted. Plausible. | Write one line to the audit log or stderr when a call is dropped |
| 12 | low | BE | all | Lost silently: a record that fails `_valid_record` or has an unknown schema is never overwritten (correct) but disappears from the board with no signal. Plausible. | Emit a one-time notification or audit line naming the file |
| 13 | low | BE | all | There is no cap on tasks per record: 300 reworded todo lists produced 300 tasks and a 65 KB record, rewritten with fsync on every call. Verified. | Cap removed-and-unfinished tasks (drop the oldest past N) |
| 14 | low | FE | all | `boardModel.ts:243` counts only `status === 'active'` once a period narrows the view, while the CLI counts every non-ended session. The same project reads "1 active" for All time and "0 active" for Today. Verified. | Use `status !== 'ended'` |
| 15 | low | FE | all | A `taskBoard()` rejection that arrives after a push has delivered a feed still sets `loadFailed`, which hides live data (`Board.tsx:140-145`). Plausible. | In the reject branch, return when a push already arrived |
| 16 | low | FE | all | One invalid field silently drops a whole snapshot (`asBoardProject`, `operations.ts` ~2764). Before `ready` the project vanishes, after it the project freezes. A session with an empty provider is dropped while its tasks still count (~2674). Plausible. | Drop only the bad sessions, fall back to `unknown` for a missing provider, and log which field failed |
| 17 | low | FE | all | Two projects with the same folder name get identical tab labels and titles. Plausible. | Disambiguate with the parent directory on a clash |

### Security Findings

No injection, path traversal or XSS route was found. Session and agent ids are validated before
they become file names. Writes are atomic, with 0600 files in 0700 directories. Board IPC is
validated and rate-limited, and the renderer uses no `innerHTML` or markdown rendering.

| # | Severity | Description | Fix |
|---|----------|-------------|-----|
| S1 | med | ReDoS in `redact` (see issue 6) blocks PreToolUse and PostToolUse | Truncate first; drop the look-aheads |
| S2 | med | Hook launcher walks up from `$PWD` to the nearest `.dev-team-agents/scripts/hooks` or `core-dir` pointer (`hooks.py:101-106`, `codex_hooks_merge.py:58-62`). A nested untrusted checkout the agent `cd`'d into could have its own hooks run. Affects every hook, not just the board. The walk was simulated; whether providers really run hooks in a `cd`'d directory is unconfirmed | Prefer `$CLAUDE_PROJECT_DIR` or the git toplevel; refuse a nested match outside the session root; confirm the pointer target is inside the store |
| S3 | low | `(?im)^\W*merged!?\W*$` (`pr_refs.py:68`) lets `\W*` cross newlines: 80 s on 200 KB of `glab mr merge` output. No state is lost, because no lock is held at that point | `^[^\S\n]*merged!?[^\S\n]*$` |
| S4 | low | Patterns redaction still misses (remainder of prior S3): `pass is X`, `PGPASSWORD=`, `curl -u`, `sshpass -p`, `redis-cli -a`, `docker login -p`, `Cookie:`, PEM bodies, `hf_` tokens | Extend `_SECRET_PATTERNS`, one test case per pattern |
| S5 | low | Session titles are not redacted, stripped of invisible characters or capped (`tasks.py` ~2401, 2505, 2662). opencode derives titles from the first prompt | Pass titles through `_task_text` |
| S6 | info | `.prompt-<sid>` (raw first prompt line) and `.direct-*` markers leak when Stop never runs. 18-day-old ones exist on the real store | Sweep stale markers (see Infrastructure) |
| S7 | info (LGPD) | Records, traces and aliases have no retention | Product decision: `devteam tasks prune` |

### Infrastructure Findings

- **Hot path is still healthy.** A python fork costs about 0.11 s and the PreToolUse dispatcher about 75 ms for a non-board tool. Direct work forks at most twice per turn, and a spawn costs two forks.
- **`live_title` cache** (`tasks.py:2421-2434`) is cleared wholesale at 512 entries and stats every record, ended ones included. Past 512 Claude sessions, each recompute re-reads transcript tails (up to 1 MiB each). Fix: evict the oldest entry instead of clearing, and skip ended sessions.
- **Watch cost grows with history.** `project_view` re-derives every record, and `since` is applied only after `session_view`. Fix: apply the period and retention before deriving.
- **Leaked markers.** Sweep `.prompt-`/`.direct-`/`.directw-` files older than a TTL that have no live session, as a side effect of `record` or `mark`.
- **opencode has no session-end mapping.** `mark ended` and `tasks.session_abandoned` never run, and that provider's markers survive. The spec documents the gap. Fix: map `session.deleted` if opencode exposes it.
- **Hook timeouts.**
  - opencode: a spawn chains two 10 s lock waits against a 12 s plugin timeout.
  - claude and codex: hook entries set no `timeout` (still open from the prior audit).
- **Windows writes.** `write_json_atomic` does not retry `os.replace` on `PermissionError` (a Windows sharing violation). Under Git Bash, with the watcher polling every second, the board event is silently lost.
- **App tests and Node.** Renderer suites fail to load under the shell's default Node 20, because jsdom needs Node 22/24 and the app's engines field says ≥24.15. This is an environment trap, not a config break. Fix: an `.nvmrc` or an engines check in the test script.

### Test Coverage Gaps

| Priority | Routine/Component | Why It Needs Tests | Suggested Scenarios |
|----------|-------------------|--------------------|--------------------|
| P0 | `pre-tool-use/04` fork budget | Red today (issue 9) | Review spawn with no record makes only the allowed trace fork, per provider; Bash/Read payloads that only name an agent make 0 forks |
| P0 | Subagent-owned todos (issue 1) | Blocks `session_done` | Agent `ag-1` owns an `in_progress` todo, agent ends, so `_all_done` is true and one notification is raised (claude, codex) |
| P0 | opencode child session (issue 2) | Phantom sessions | `todowrite`/`task` with `parent_id` creates no child record and no duplicate parent task (`test_task_list_mirroring.py` plus `opencode-plugin.test.mjs`) |
| P0 | Codex v1 never waited on (issue 4) | Card stuck forever | Past `PENDING_MAX_AGE` the task is interrupted; one second before, it is not |
| P0 | `asBoardTask` `interrupted` (issue 5) | Silent success | Parsed when true, false when absent or non-boolean, badged on the card |
| P0 | Redaction and regex time (S1, S3, S4) | Hook stalls; secrets kept | 80 KB run and 200 KB glab output finish under a budget; a table of secret shapes is absent from the stored record |
| P1 | CLI ↔ app key contract | Prevents a repeat of issue 5 | Every key from `_task_view`/`session_view`/`project_view` is either parsed or listed in an allowlist with a reason, and the Python side pins the key set |
| P1 | `done_pending` path in `mark` | No test mentions it | `mark idle` with open work leaves it pending and silent; finishing the last task notifies once; reopening and finishing notifies again |
| P1 | Lock timeout and unreadable record (issues 11, 12) | Silent loss | With the timeout patched to about 0.1 s, the dropped call is surfaced and nothing is half-written; a corrupt or future-schema record is reported, and other sessions are unaffected |
| P1 | `record` vs `retitle` race (issue 10) | Lost rename | A retitle committed between the read and the write keeps the new title |
| P1 | Background hand-back by `<task-id>` (issue 7) | Board and trace diverge | The hand-back closes both the board task and the trace span |
| P1 | Tab lifecycle | Only the pure function is tested | Removed, pruned, shown as gone, reappears without auto-reopening, opens on click; nothing pruned while starting or failed |
| P1 | Session counts and late reject (issues 14, 15) | Wrong figures; data hidden | A narrowed period counts idle sessions; a late reject after a push keeps live data |
| P2 | opencode end, marker sweep, `live_title` LRU, Windows replace retry, title redaction | Operational | See Infrastructure and S5 |

### Improvement Plan (ordered by value)

1. Retire a finished subagent's own tasks and keep its `agentId` (issues 1 and 7). This restores `session_done` and makes hand-back matching agree with the trace. Effort: S.
2. Skip opencode `parent_id` todo and spawn payloads, and resolve Codex child-thread aliases (issues 2 and 3). This removes phantom sessions. Effort: S.
3. Parse and badge `interrupted` in the app, and add the CLI ↔ app key contract test (issue 5). An unfinished agent stops looking successful. Effort: S.
4. Age-cap every Codex `agent_ref` task (issue 4). No more forever-running cards, and board and trace agree. Effort: XS.
5. Truncate before `redact`, fix both slow regexes, and extend the secret patterns (issue 6, S1, S3, S4, S5). Hooks can no longer stall a tool call, and fewer secrets are kept. Effort: S.
6. Fix the red fork-budget test without loosening it (issue 9). The suite is green again. Effort: XS.
7. Run the board Stop script before the lints (issue 8). Idle and done no longer depend on lint time. Effort: XS.
8. Surface lost lock calls and unreadable records (issues 11 and 12). Silent loss becomes visible. Effort: S.
9. Small app fixes: the active-sessions count, a late reject, the partial-snapshot salvage and tab labels (issues 14 to 17). Effort: S.
10. Hold the title inside the lock (issue 10), sweep stale markers (S6), `live_title` LRU, the `os.replace` retry, and cap tasks per record (issue 13). Effort: S.

### Recommended Next Steps

These need a product decision before any code:
- **Retention.** A `devteam tasks prune` policy for records, traces and markers (LGPD; also bounds watch cost).
- **Hidden agents and done.** With a mirrored plan, should hidden agent tasks still count toward done? Today `session_done` can fire while a background agent runs.
- **Session-summary continuation.** The Stop continuation reopens the completed direct card on most editing sessions (open since the prior audit).
- **Interrupted turns.** Esc fires no Stop. Should the next `UserPromptSubmit` settle the previous turn?
- **opencode session end.** Whether opencode exposes an event usable for session end.
- **Hook launcher (S2).** Confirm whether Claude Code and Codex run hooks in an agent-`cd`'d directory, then harden the walk-up in a separate, hook-wide change.

Also add an `.nvmrc` (Node 24) so app tests cannot silently fail to load.
