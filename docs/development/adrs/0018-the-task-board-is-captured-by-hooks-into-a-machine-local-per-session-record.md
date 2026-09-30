# ADR-0018: The task board is captured by hooks into a machine-local per-session record

**Date:** 2026-09-30
**Status:** Accepted
**Deciders:** dev-team-agents maintainers

## Context

Agents keep a todo list while they work. Planning agents are told to track their work, and every
provider has a native tool for it: Claude Code `TaskCreate` / `TaskUpdate` (which replaced
`TodoWrite` by default), Codex `update_plan`, opencode `todowrite`. The list is visible only inside
the session that owns it. A developer with several sessions across several bound projects cannot see
what is pending, in progress or done anywhere else, nor how long anything has taken.

The desktop app is a pure CLI client (ADR-0015) whose only way into the store is the `--json`
contract (ADR-0011). ADR-0017 already established a channel of the same shape for notifications:
a hook writes a machine-local record, the CLI reads it, the app watches.

Verified while writing this ADR:

| Fact | Source |
|---|---|
| Claude Code hook input carries `agent_id` / `agent_type` when the call comes from a subagent, and a `SessionEnd` event exists | code.claude.com/docs/en/hooks |
| `TodoWrite` is disabled by default in favour of `TaskCreate`/`TaskUpdate`; neither tool's input shape is publicly documented | code.claude.com/docs/en/tools-reference |
| Codex and opencode already receive our `PreToolUse` dispatcher (`.codex/hooks.json`, plugin `tool.execute.before`) | `scripts/install-codex.sh`, `opencode/plugin/dev-team-agents.ts` |
| Codex fires `PreToolUse` for `update_plan`, with `tool_name: "update_plan"`, the parsed arguments as `tool_input`, `session_id`, `cwd`, and `agent_id`/`agent_type` from a subagent | Read in the Codex source (openai/codex @ `92bc601`): `PlanHandler` keeps the registry's default `pre_tool_use_payload`, and `command_input_json` in `codex-rs/hooks/src/events/pre_tool_use.rs` serializes those fields. Pinned by a test that replays that exact payload through the dispatcher. Not yet observed in a live Codex session |

## Decision

**A hook captures the provider's own todo tool; the CLI owns the record; the app only reads.**

1. **Capture is automatic, not cooperative.** Claude Code gets a new `PostToolUse` entry whose
   matcher is limited to the todo tools, plus a `SessionEnd` entry. Codex and opencode reuse the
   `PreToolUse` dispatcher they already have; a sub-script there filters on the tool name in bash
   before forking anything. Agents are not asked to report progress. *(Qualified by the amendment
   "approved plans become native tasks": agents are asked to keep an approved plan in the native list;
   capture itself stays automatic.)*
2. **One record per session**, `<state-dir>/task-board/<session>.json`, machine-local (ADR-0013). Only the
   CLI writes it (`devteam tasks record|mark`, invoked by the hook through the project's own
   `scripts/cli/devteam`), under a per-session lock, atomically. Per-session files mean two sessions
   never contend for a lock and a corrupt file costs one session, not the board.
3. **Status history, not a snapshot.** Each task keeps an append-only `history` of status changes
   (capped), so time-per-step is computable. Tasks missing from a replace-style list are marked
   `removed_at`, never deleted.
4. **Derived state is computed on read.** Session status (active / idle / ended), stale and abandoned
   tasks, and per-step durations are derived by `devteam tasks list|watch` from timestamps and
   thresholds passed as flags. Nothing runs in the background to maintain them.
5. **The board is read-only.** The app never writes the record, so it is not part of
   `compat.store_schemas()` — that gate answers "may this client write?", and it may not.
6. **Board settings are app-local** (stale threshold, done retention), like the display name
   (ADR-0016). They are view preferences, not framework behaviour, and a new `preferences.json` key
   would cost five mirrors.
7. **Notifications go through `notify.sh`.** The hook raises `tasks.session_done` and
   `tasks.session_abandoned` from what `devteam tasks` returns; the CLI does not write the queue.

## Consequences

- Every provider's todo list reaches the board with no change to any agent body. *(Qualified by the
  same amendment: planning now asks agents, through `plan-mode`, to open that list.)*
- A rewritten task text appears as a new task: replace-style tools carry no stable id, so identity
  is the normalized text. Accepted and documented; ids are used where the provider gives one.
- Times have the granularity of the agent's own updates.
- "Ended" is exact only on Claude Code (`SessionEnd`); elsewhere it is inferred from inactivity.
- Codex coverage rests on the Codex source, not on a live run. If a Codex release stops firing
  `PreToolUse` for `update_plan`, Codex sessions are simply absent from the board; nothing fails.
- Records accumulate. Retention hides old data in the app; deleting it is a future explicit
  command, never an automatic side effect (No-Destruction Rule).
- `devteam tasks list|watch --json` are public API from their first release.

## Amendment — 2026-09-30: an inferred In Review column

**Decision.** Tasks can pass through an optional In Review column. A review is a *window* recorded
per session, opened by a hook when a review/QA agent is spawned, a review command runs, or the user
asks for a review in the prompt; the tasks in progress and those completed since the last review
enter it. The window's result is read from a `<!-- review-result: findings=N -->` marker that our
review/QA agents emit; zero findings releases the tasks, findings keep them in review until the fix
list created afterwards is completed or a later review returns zero. Full rules:
`docs/specs/task-board.md` § In Review.

**Why a marker and not the report text.** Every reviewer formats findings differently; a heuristic
count would be wrong silently. A missing marker is shown as "result not read", never as a pass.

**Why inferred and not agent-reported.** Same reason as the rest of this ADR: capture must not depend
on an agent remembering to report. Triggers come from hooks; only the result needs the agent, and
its absence is visible.

**Consequences.** `UserPromptSubmit` joins the Claude and Codex hook sets, `PostToolUse` joins the
Codex set (for `wait_agent`), and the opencode plugin binds `chat.message` and `tool.execute.after`.
Keyword triggers can produce false positives; they cost a badge, not a wrong Done.

## Amendment — 2026-09-30: approved plans become native tasks

**Context.** A live test showed the board empty for a whole planning session: the agents of this
framework write their plan to chat or to a file, and use the provider's native task list only when
the provider itself decides to. Capture by hooks was working; there was nothing to capture.

**Decision.** Every approved plan's Steps table becomes the provider's native task list, per the
rule in `skills/shared/plan-mode/SKILL.md` § Task List Mirroring — its single home. The skill names
each provider's tool itself, because skills are read raw by every provider and nothing rewrites them.

**What it qualifies.** Decision 1 ("Agents are not asked to report progress") and the first
consequence ("no change to any agent body") — both marked inline above. Capture stays exactly as
decided: the hooks, the record and the read-only app are unchanged.

**Why this is not a reversal.** What depends on the agent is only *that a list exists*, and the
instruction rides on a habit the agent already has (the per-step Progress Reporting message). If it is
skipped, the board is empty. The rule also pins what the board needs to stay right — frozen step
titles and ids, each provider's own way to drop a step, one list per plan on whole-list tools —
because a renamed or replaced step would otherwise show twice. `agent-lint.sh` fails when the section
disappears, an agent that plans stops loading plan-mode, or a plan-gated command stops pointing at it.

| Alternative | Why rejected |
|---|---|
| A Stop/UserPromptSubmit hook parsing the Steps table from the transcript | Finds the plan but not its progress: nothing in the transcript says which step started or finished, so every task would sit in To do |
| Agents calling `devteam tasks` directly | A second channel beside the provider's own list, and the one this ADR already rejected for depending on agent compliance — with none of the provider UI benefit |
| Accept an empty board for planned sessions | The board's purpose is following planned work; empty in exactly those sessions defeats it |

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Agents report through `devteam tasks` by instruction | Depends on agent compliance. This repository measured closing run banners at 0 of 6 multi-message runs; a board fed that way goes stale without anyone noticing |
| Parse plan and sprint documents | Only persisted plans are visible, at sprint granularity, with no in-progress signal |
| One append-only event log for all sessions | Every reader replays the whole log, and one lock is shared by every concurrent session |
| Snapshot only, no history | Cannot answer how long a task spent in each step, which is a stated requirement |
