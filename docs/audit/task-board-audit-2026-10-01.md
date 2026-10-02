## Audit Report: task-board

### Scope

The cross-project task board (ADR-0018, `docs/specs/task-board.md`), audited against the spec,
its Acceptance Criteria and Amendment Log, and the ADR's mandatory Security amendments.

- **Capture (hooks, bash):** `scripts/hooks/lib/task-board.sh`, `pre-tool-use/04-task-board.sh`,
  `post-tool-use/01-task-board.sh`, `post-tool-use/02-pr-created.sh`,
  `user-prompt-submit/01-task-board.sh`, `user-prompt-submit/02-issue-refs.sh`,
  `stop/04b-task-board.sh`, `session-end.sh`; opencode plugin and Codex hook wiring.
- **Record and derived state (CLI, python):** `scripts/lib/devteam/tasks.py`, `pr_refs.py`,
  `review_triggers.py`, the `tasks` subcommands in `cli.py`.
- **Desktop app:** `app/src/main/taskBoard.ts`, `taskBoardIpc.ts`, `settings.ts`,
  `app/src/preload/index.ts`, `app/src/renderer/screens/Board.tsx`, `boardModel.ts`.
- **Pattern:** hooks write one machine-local JSON record per session (locked, atomic); the CLI
  derives every column on read; the app is a pure CLI client over `tasks list/watch --json`.

Analysis ran in parallel: backend, frontend, security, devops, backend tests, frontend tests.
Before the fixes, the python board suites had 6 failing tests on `main`
(`test_task_board_pr` ×4, `test_review_board` ×2).

### Critical Issues

| # | Severity | Layer | Description | Suggested Fix |
|---|----------|-------|-------------|---------------|
| 1 | high | FE | `setBoardSettings` in the preload forwards only `staleAfterMinutes` and `doneRetentionDays`; main requires `directTodoTtlHours`, so every Save of Board settings is refused and none of the three settings can be changed | Forward `directTodoTtlHours` from the preload; test the real bridge payload against the main validator |
| 2 | med | BE | `review_result` (and its finish/re-read paths) computes `all_done` with the Direct work card counted, unlike `record()`/`mark()`; a session with a To Do direct card never raises `tasks.session_done` when a review result completes it, and the next Stop does not either | Pass `skip_direct=True` everywhere `review_result` evaluates done |
| 3 | med | BE | A PostToolUse payload forwarded by `02-pr-created.sh` that is not a PR/merge event (`git merge --abort`, `echo gh pr merge`, an MCP error) is folded in a second time as direct work after the turn's PreToolUse already took it; 4 existing tests fail on it | Treat a direct-shaped call that carries a tool result as an event only (`_record_event`), never as direct work |
| 4 | med | Both | `tasks watch` emits `{"removed": true}` only for a bound project that lost its tasks; a project that is unbound or whose folder is gone stays on the app's board until the stream restarts, while `tasks list` already drops it | Emit `removed` for every previously emitted project that left the bound set |
| 5 | low | FE | A rejected `openTaskLink` call shows `String(error)` in the toast, while the spec requires a generic error toast | Show the generic refusal message on rejection |
| 6 | low | FE | A failed manual Refresh only logs to stderr; the user gets no feedback | Surface the failure through the existing `problem` alert |

### Security Findings

Eight of the nine mandatory Security amendments are enforced end to end (parts-not-URLs, host
allow-list by kind, canonical round-trip, whole-line extraction, repo check, command-token
filter, ref regexes, IPC caps and rate limits). Electron hardening (context isolation, sandbox,
CSP, navigation and window-open blocks) is in place.

| # | Severity | Description | Fix |
|---|----------|-------------|-----|
| S1 | low | `pr_refs.ref_view` re-validates a stored GitHub issue ref only for shape, not against the bound repo or a current remote on the web host (amendment 1: re-validate on every read); a ref stays clickable after its remote is removed | Re-apply the write-time repo set on read |
| S2 | low | Only Direct work excerpts pass through `redact()`; agent task text and plan/todo item text are stored and shown verbatim, so a token in a subagent instruction is kept for good | Apply the same redaction and invisible-character strip to every task text |
| S3 | low | Common pasted credential shapes escape redaction: `Authorization: Basic …` / `token …`, hyphenated key names (`X-Api-Key:`), `mysql -p<secret>`, `pass is …` | Extend `_SECRET_PATTERNS` |

LGPD/GDPR (info): prompt excerpts and task texts have no retention limit; the spec records
pruning (`devteam tasks prune`) as future work. Not a code gap.

### Infrastructure Findings

- Hot path is healthy: the PreToolUse gate is pure bash (~0.03 s), at most two python forks per
  turn, every hook exits 0, every write is locked and atomic, no network calls, one long-lived
  `tasks watch` per app with a stamp-skip and restart backoff, hook wiring complete for
  `claude`, `opencode` and `codex`.
- Out of scope: unbounded growth of `task-board/` records (prune is listed as future work in
  the spec); explicit hook `timeout` entries for Claude/Codex (the lock wait is already capped
  at 10 s, under the providers' default timeout).

### Test Coverage Gaps

| Priority | Routine/Component | Why It Needs Tests | Suggested Scenarios |
|----------|-------------------|--------------------|--------------------|
| high | Preload → IPC → settings validator | Renderer tests mock the whole bridge, which is how issue 1 shipped | Real preload with a fake `ipcRenderer`: payload has all three keys and passes `boardSettingsProblem` |
| high | Existing red tests | 6 failures on `main` hide real regressions | Fix issue 3; prime the turn's allowed fork in the two stale fork-count tests (AC9 allows the first call of a turn to fork) |
| med | Review result with a direct card | Issue 2 | Direct `Read` + completed plan step + review `findings=0` → `became_all_done` |
| med | `watch` and project removal | Issue 4 | Unbind a project mid-watch → a `removed` event |
| med | Unwritable state dir (AC10) | Only malformed payloads are covered | `task-board/` replaced by a file → `record` exits cleanly, nothing raised |
| med | Refused link click | AC24 toast is untested in the renderer | `{ok:false}` and a rejection both show a generic toast with no URL or raw error |
| low | Redaction shapes | S2, S3 | Agent/todo text with a `ghp_` token; each new credential shape |

### Improvement Plan (ordered by value)

1. Forward `directTodoTtlHours` in the preload, with a real-bridge test — a shipped control is dead — XS
2. Stop re-recording post-call payloads as direct work — makes the 4 red PR tests green and stops late card promotion — S
3. `skip_direct=True` in the review-result done checks — restores `tasks.session_done` — XS
4. `watch` emits `removed` for projects that left the bound set — app matches `tasks list` — S
5. Fix the two stale fork-count tests — the suite is green again and guards AC9 — XS
6. Re-validate GitHub issue refs on read (S1) — closes the amendment-1 gap — S
7. Redact all task text and widen the secret patterns (S2, S3), with a spec Amendment Log row — S
8. Generic toast on a rejected link open; Refresh failure surfaced — XS
9. Spec drift: the Desktop app Settings bullet omits the direct-work lifetime — XS (docs)

### Recommended Next Steps

- Decide whether the overview still wants the "sessions with PR/MR Created tasks" badge the spec
  lists (the app shows the PR/MR Created count only).
- Decide whether the To Do column should explain direct cards hidden by the lifetime setting, as
  Done does for retention, and whether overview counts should exclude them.
- Schedule `devteam tasks prune` (spec future work) before the record directory grows large;
  it also answers the LGPD retention point.
- A Stop hook exiting 2 continues the turn after the prompt file was deleted, adding an empty
  turn that reopens the direct card — a product decision, not a code bug.
