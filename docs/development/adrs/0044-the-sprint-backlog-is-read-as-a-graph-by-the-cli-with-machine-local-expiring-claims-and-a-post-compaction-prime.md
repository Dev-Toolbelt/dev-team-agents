# ADR-0044: The sprint backlog is read as a graph by the CLI, with machine-local expiring claims and a post-compaction prime

**Date:** 2026-10-20  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Applies to:** `scripts/lib/devteam/backlog.py`, `scripts/lib/spec_lint.py`, `scripts/hooks/backlog-prime.sh`, `scripts/hooks/session-start.sh`, `opencode/plugin/dev-team-agents.ts`, `commands/sprint.md`  
**Relates to:** [ADR-0013](0013-portable-and-machine-local-split-of-the-data-store.md) (machine-local records), [ADR-0014](0014-store-schemas-as-the-normative-write-gate-and-the-json-contract-deprecation-policy.md) (`--json` contract), [ADR-0035](0035-planning-sequence-owned-by-the-main-conversation-per-scope-backlog-and-routing-in-every-provider-s-instruction-file.md) (per-scope backlog, `/devteam:sprint`), [ADR-0037](0037-spec-status-scenario-ids-and-a-mechanical-spec-lint-close-the-spec-driven-loop.md) (spec-lint)

## Context

A sprint file (`skills/shared/backlog-template/SKILL.md`) already carries a dependency graph — `Depends on`, `Wave`, `Status` per task — but only an agent reads it. `/devteam:sprint` Step 2 checked dependencies, waves and branches by eye, and picked the next wave from a table the planner wrote by hand. Three gaps followed, all visible in tools built for agent task graphs (beads' `bd ready` / `--claim` / `bd prime` were the reference):

1. **No computed frontier.** A hand-written wave table can disagree with the dependencies it summarises, and nothing caught a cycle, a dependency on a task no sprint defines, or a dependency placed in the same wave.
2. **No ownership across sessions.** Inside one `/devteam:sprint` run the main conversation is the only orchestrator, so its agents never race. Two sessions on the same sprint (a resume in another window, the app and a terminal) did: both read `[ ] Pending` and both started the task.
3. **Compaction drops the sprint.** After a compaction the agent no longer knew which sprint, task or scenarios it was on. `pre-compact.sh` only forces the session summary.

## Decision

1. **The CLI reads the backlog; the sprint file stays the only status.** `devteam backlog ready` and `devteam backlog lint` parse the sprint files, resolve dependencies (same-scope sprints first for a cross-sprint id) and derive the ready frontier, the computed waves (Kahn layering) and the defects. They never write a sprint file. Status still moves `[ ]` → `[~]` → `[x]` in git, by the executing command.
2. **Claims are machine-local, advisory and expiring.** `devteam backlog claim` / `release` keep `backlog-claims.json` in the project's machine-local state directory (listed in `paths.MACHINE_LOCAL_RECORDS`). A claim names an owner token the first claim mints (`own-<hex>`) — no provider exposes a session id to a shell command, so the orchestrator keeps the token for the run. Claims of a call are all-or-none under the store lock; a live claim of another owner is a `ConflictError` (exit 4) unless `--take-over`, passed only after the user chose it. A claim expires after `DEFAULT_TTL` (4 h, renewed at each wave); an expired one is free. Released claims are marked rather than removed at release time; past `MAX_CLAIMS` the oldest released ones are dropped, and of the entries this release cannot read only the newest `MAX_FOREIGN_ENTRIES` are carried over; a claims file this release cannot read is refused on write, never overwritten. Everything a claim shows to anyone but its claimer (`ready`, `prime`, a conflict's `details`) carries an `owner_hint` — the first eight characters — never the full token, so a second session cannot quietly renew a claim it did not make.
3. **Claims are keyed to the main checkout.** The record lives under the main checkout's state directory, resolved from `git rev-parse --git-common-dir`, so a sprint claimed from its integration worktree and a hook in the main checkout read the same record on layout 1 as well as layout 2.
4. **A post-compaction prime on every provider.** `scripts/hooks/backlog-prime.sh` prints `devteam backlog prime`: a block of at most `PRIME_MAX_LINES` lines and `PRIME_MAX_BYTES` bytes with each in-progress sprint (from the `sprints.md` index or a live claim), its in-progress and claimed tasks, the ready frontier and the blockers — silent when idle. Sprint text is data in that block: every field is reduced to one line without control, format or separator characters, and task names are quoted, so a sprint file cannot fake a line of its own. A claimed sprint is read from the checkout furthest along, preferring a worktree on a tie, because a running sprint edits its status in the integration worktree.
   - **Claude Code and Codex**: `session-start.sh` runs it on `source=compact|resume`. Both fire `SessionStart` again after a compaction with that source (Codex's hooks documentation lists `startup`, `resume`, `clear`, `compact`, `fork`), and both registered matchers accept every source.
   - **opencode**: no event follows a compaction, so the plugin runs it from `experimental.session.compacting` and appends it to `output.context`. Two accepted gaps: that context feeds the summarizer rather than the next turn directly, and a resume gets no prime, because opencode's `session.created` output never reaches the context. Neither has a hook that would do better today.
5. **One reader of the task block.** `backlog.parse` is the only parser of a sprint task: `scripts/lib/spec_lint.py` reads `Spec` and `Covers` through it (`spec_refs`, `covers`) and lists sprint files through `backlog.sprint_files`, so the two checks agree on where a task's fields end (the next `#`–`###` heading line — a `# comment` inside a fenced block in a task body counts, so fields belong at the top of the block, as the template puts them) and on which files they read (no symlink, no file over `MAX_FILE_BYTES`, no sprints directory leading outside the checkout).
6. **Gate classification.** `ready`, `lint` and `prime` are `compat.READ_ONLY`; `claim` and `release` are `compat.STORE_NEUTRAL` (they write a machine-local record no client declares). `backlog prime` is exempt from the account gate, like the `tasks` hook plumbing: a hook must never wait on the account check.

## Consequences

### Positive
- `/devteam:sprint` Step 2 gets a mechanical lint for the graph defects, and Step 4 takes the next wave from the frontier instead of from a table that can be stale.
- A second session on a running sprint is told, with the owner and expiry, instead of redoing a task.
- A long sprint survives a compaction on all three providers for ~1k tokens.

### Negative
- A claim is only as good as the orchestrator keeping its owner token. A run that loses it — a fresh session, or a compaction whose summary dropped it — meets its own claim as foreign and is asked to take it over. That question is accepted on purpose: the prime shows only an `owner_hint`, because a full token anywhere another session reads it would let that session renew the claim silently.

### Neutral
- `--json` output of the new commands is additive (ADR-0014); nothing existing changes shape.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Adopt beads (`bd`) itself | Go binary plus a Dolt database outside git; the backlog would stop being reviewable in `docs/`, and three installers would gain a heavy dependency |
| Keep status in the store instead of the sprint file | Two sources of truth; the git history of a sprint would stop telling what was done |
| Key claims by session id | No provider passes a session id to a shell command; the hook payload has one, the command run by the agent does not |
| A `PreCompact` hook for the prime | Its output does not reach the context after the compaction on Claude Code, and Codex ignores PreCompact stdout |
