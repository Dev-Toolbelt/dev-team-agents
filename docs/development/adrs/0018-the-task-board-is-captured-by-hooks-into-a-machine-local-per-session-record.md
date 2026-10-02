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

## Amendment — 2026-09-30: agent spawns are tasks

**Context.** A live `/devteam:backend` run asked one question and delegated to two agents; no plan was
presented, so plan mirroring never fired and the board stayed empty. Commands delegate this way by
design.

**Decision.** The hooks record every agent a session spawns as a task — created on the spawn, completed
on its result (foreground, background hand-back, or Codex `wait_agent`), marked failed on a failure —
keyed by the spawn's own id. Provider built-ins and review/QA agents are excluded; a mirrored plan of
the same owner hides them on read. Full rules: `docs/specs/task-board.md` § Agent spawns are tasks.

**Why.** It restores Decision 1 for the dominant path: capture is automatic again, needing nothing from
the agent. Plan mirroring stays for sessions that do present a plan.

## Amendment — 2026-10-01: direct work is a task

**Context.** With plans mirrored and agents recorded, one kind of work still never reached the board:
what the main session does itself — a one-line fix that needs no plan, an inline edit, a commit. The
user's goal is that everything done in a session is followed there.

**Decision.** The hooks record the main session's own changes — an edit tool, or a shell call that
`tasks.writes()` reads as write-shaped — on **one `Direct work` card per session**, in progress while a
turn works and completed at `Stop`, keeping a redacted ≤100-character excerpt of each turn's prompt.
Work a plan step or an agent of the same turn already covers is not recorded; a subagent's never is.
Full rules: `docs/specs/task-board.md` § Direct work.

**Why.** It keeps Decision 1: capture stays automatic and asks nothing of the agent. The cost stays off
the hot path — python forks once per turn at most (a `.direct-<session>` marker), and a prompt forks
none (bash writes its slice beside the record).

**Consequences.** The shell heuristic can miss a write or count a harmless command; either costs a
card, never a wrong Done. Prompt text now reaches the record, so only a redacted first line is kept.
Codex's edit and shell tool names rest on its source, like `update_plan`; if they differ, Codex
sessions simply lack the card.

| Alternative | Why rejected |
|---|---|
| One card per turn | A long session of small fixes becomes a wall of cards; the turns are listed on one card instead |
| A card on every prompt | Questions would fill the board, and python would fork on every prompt |
| Diff the working tree at `Stop` | Misses commits, pushes and anything that leaves the tree clean |

## Amendment — 2026-10-02: a read-only turn is direct work too, in To Do

**Context.** A session that checked production container health ran only `ssh … docker ps`, `curl` and
`grep`, and never reached the board: the 2026-10-01 amendment recorded writes only. The user's goal is
that everything done in a session is followed there.

**Decision.** Any tool call of the main session feeds its one Direct work card; whether it wrote picks
the column. A read-only turn leaves the card in **To Do** — a question asked is something to do — and
it stays there after `Stop`; a write moves it to In progress and `Stop` completes it. The card follows
the latest turn. A To Do card is not abandoned work, and is retired at `Stop` when its turn created a
plan or an agent (that work has a better grain). The app hides a To Do card once its last turn is
older than an app-local lifetime (default 24 h). Full rules: `docs/specs/task-board.md` § Direct work.

**Why.** Recording only writes left investigations, reviews by hand and health checks invisible. A To
Do card says "asked, not acted on" without claiming work was done. The lifetime keeps an unanswered
question from lingering, and hides rather than deletes, so the No-Destruction Rule holds and a new turn
brings the card back.

**Consequences.** The gate forks python at most twice a turn — once for the first call, once for the
first write (`.direct-` / `.directw-` markers) — instead of once. Almost every session now has a card;
a prompt answered without any tool still has none. More prompt excerpts are stored locally, under the
same redaction.

| Alternative | Why rejected |
|---|---|
| A card on every prompt | A greeting or a one-line answer would be a card; the tool call is the cheapest signal that work happened |
| Read-only turns straight to Done | A question nobody followed up would look finished |
| Delete expired To Do cards | Breaks the No-Destruction Rule; hiding on read gives the same board |

## Amendment — 2026-10-01: PR/MR Created column and issue refs

**Decision.** A new `pr_created` column appears between In Review and Done, optional and derived on read. A PR/MR mark is recorded only when its URL or number appears in `gh pr create` / `glab mr create` / MCP `create_pull_request` output — confirmed, not inferred — along with its head branch for later merge matching. Tasks entered this column when its membership is fixed at the next Stop: every completed task completed since the previous PR's `fixed_at` timestamp. A merge is observed when `gh pr merge` / `glab mr merge` / `/devteam:merge` / MCP `merge_pull_request` succeeds, recorded per session, and joined across sessions on read: a PR mark is merged when its (repo + number) matches or its head branch matches a merge's branch (at >= the mark's timestamp). Issue references are captured from the user prompt, branch name, and task text with strict rules per integration (Jira requires site + project binding; GitHub requires account + repository binding; no integration → no ref badge). Refs are stored as parsed parts, rebuilt and revalidated on every read against current remotes and config.

**Why confirmed-only.** A PR/MR is created by the provider's CLI or an MCP tool; the URL/number reaches the hook only in the tool's response. Inferring from the prompt would fire on `"I'll make a PR"` and stay silent on success — backward. A URL string taken from tool output or prompt is parsed into parts (kind, host, path segments, number/key), never stored raw, and rebuilt+revalidated on read against current remotes and integration config (see § SECURITY AMENDMENTS below).

**Why merge is joined on read by branch, not written cross-session.** Per-session locks remain untouched. A merge can happen in a different session than the PR's, and the Bash hook-side code cannot cross sessions (no store access). Branch matching (mark.head == merge.branch) lets the CLI join them on read, with no second write. If a merge is never observed (PR closed without merge, branch force-pushed), the task stays in `pr_created`.

**Why strict refs.** Integration config is an explicit user choice (connected account + project binding). Refs without config are omitted from the view (kept in the record). A GitHub ref without a connected account or binding does not validate; a Jira ref whose project key does not match the binding does not validate. This guards against a misconfigured state producing noise and against refs from a copy-pasted unrelated text.

**Implementation notes.** Detailed runtime behavior including cwd trust validation (hook cwd trusted only when inside the project root or one of its listed linked worktrees, checked before any git runs there), failure-events-create-only semantics (Claude PostToolUseFailure can only CREATE a PR/MR mark, never record a merge), task-less first-prompt records (a first prompt carrying a valid ref creates a record with no tasks; later tasks inherit the ref; records with no tasks do not appear on the board), and Jira base_path validation (path field in link_hosts, validated `^(/[A-Za-z0-9._~-]+)*$`) are documented in the spec at `docs/specs/task-board.md`.

**Consequences.** Hook matchers widen to catch `gh pr merge`, `glab mr merge`, `git merge` (via Bash PostToolUse), and MCP `merge_pull_request`. The CLI reads refs from the UserPromptSubmit hook (Claude, Codex), the session branch name (all), and task text (all). Tasks stored as parts not URLs survive config changes, and the app validates link hosts and path shapes before opening them. `tasks.pr_created` notification code registers with other notification types.

| Alternative | Why rejected |
|---|---|
| Trigger on prompt intent ("I'll make a PR") | Tool-independent URIs are the ground truth; intent parsing is error-prone (false positives on "should we make a PR?") and silent when the intent doesn't match the outcome |
| PreToolUse intent detection for refs | Refs are user- and agent-written, not yet known at PreToolUse time |
| Cross-session writes from the merge hook | Every session gets its own lock; a hook cannot write another session's record atomically |
| Loose refs without integration config | An unbound GitHub issue is still a URL; binding makes it canonical and auditable |
| Store URLs, validate on read | Removes the ability to detect a stale reference (e.g. a remote was removed) until the view is built |

### Security amendments (mandatory, override earlier sections where they differ)

**Refs and PR/MR handling security review approved 2026-10-01 with mandatory changes. Full enforcement per the app ADR listed below.**

1. **Store parts, not URLs.** Parse every URL/number from tool output and prompts into validated parts (kind, host, path segments, number/key), store those, rebuild the URL on every read, and re-validate on every read.
2. **Allow-list by kind.** The CLI computes `link_hosts` dynamically: `github.com` and the connected GitHub web host for PRs (plus `github_issue` when the bound repository is vouched for by a git remote on that host), `gitlab.com` and every other git-remote host for MRs — except punycode (`xn--`) hosts and known non-GitLab forges (Bitbucket, Codeberg, Azure DevOps, SourceForge) — and the connected Jira site. A mark never adds a host — it is a consistency check inside the CLI trust boundary, not a second trust anchor.
3. **Canonical round-trip and path shapes in the app.** Defined once, in ADR-0025 § Decision; the CLI applies the same shapes when it rebuilds a URL.
4. **Extraction.** CLI accepts a URL only when it appears whole on a line (gh/glab tools) or as `html_url`/`number` in JSON (MCP tools), validated before storing. MCP tools must parse structured responses only; free-text regex never.
5. **Repo check.** Normalize hosts (lowercase) and paths, strip `.git`, compare case-insensitively. Reject if the mark's host/owner/repo does not match one of the project's `git remote -v` entries (verified inside CLI trust boundary).
6. **Command-token filter.** The substring check `gh pr create`, `glab mr create`, etc. is a false-positive filter, NOT a security control — explicitly documented. Additionally refuse segments with env assignments for PATH, GH_HOST, GH_REPO, GITLAB_HOST, GLAB_*, or a function/alias redefining gh/glab.
7. **Ref regexes.** Jira: word-boundary + project-key regex. GitHub: owner/repo#N and closing-keyword patterns. Validate key/repo formats (Jira: `^[A-Z][A-Z0-9_]{1,9}$`; GitHub owner: `[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})`; repo: `[A-Za-z0-9._-]{1,100}`). A GitHub `owner/repo#N` or issue URL — from any source, prompt included — must name the bound repository or one a git remote on the web host names; the committed binding's `repository` counts only when a remote names it too.
8. **IPC in app.** Renderer sends only ids; main looks them up in its snapshot, validates paths/hosts, caps 20 prs[], 50 refs[], 50 merges[] per session, rate limits 1 open/750ms + 10/min.
9. **Testing mandate.** Unit-test the validator for IDN/punycode, trailing dot, uppercase host, percent-encoding, userinfo, port, fragment, shape mismatches, number divergence, cross-host mark reuse.

**Reference implementation:** ADR-0025: The desktop app opens allow-listed tracker links from the main process.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Agents report through `devteam tasks` by instruction | Depends on agent compliance. This repository measured closing run banners at 0 of 6 multi-message runs; a board fed that way goes stale without anyone noticing |
| Parse plan and sprint documents | Only persisted plans are visible, at sprint granularity, with no in-progress signal |
| One append-only event log for all sessions | Every reader replays the whole log, and one lock is shared by every concurrent session |
| Snapshot only, no history | Cannot answer how long a task spent in each step, which is a stated requirement |
