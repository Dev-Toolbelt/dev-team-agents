# ADR-0035: Planning sequence owned by the main conversation, per-scope backlog, and routing in every provider's instruction file

**Date:** 2026-10-17  
**Status:** Accepted  
**Deciders:** dev-team-agents maintainers  
**Relates to:** [ADR-0033](0033-structured-user-choices-on-delegated-providers.md) (structured choices on delegated providers)

## Context

A feature-sized request reached planning through two doors that disagreed:

- `/devteam:plan` spawned `product-analyst` alone, business scope first, with `software-architect` joining on request or through the spec-gate contract rule.
- The `## dev-team-agents` routing section that setup writes into `CLAUDE.md` spawned `product-analyst`, `software-architect` and `database-specialist` in parallel for any planning keyword — technical design before the scope was closed, which `software-architect`'s own rule forbids. The v1→v2 migration skill already said to drop that keyword section; setup kept writing it.

Three further gaps surfaced in the same flow:

1. **Sub-agents cannot ask.** `product-analyst` runs a multi-round conversation and approval gates, but it is spawned as a sub-agent. On Claude Code a sub-agent has no `AskUserQuestion` (verified with a probe on 2026-10-17), and on every provider only its final message returns. Nothing defined who carried its questions to the user, and the spec-gate said "the command spawns `software-architect`" without naming who evaluates the gate.
2. **One backlog per project.** The deliverable was `docs/backlog/overview.md`, with single `epics.md` and `sprint-<n>.md` files, so planning a second scope overwrote or merged into the first.
3. **Routing reached Claude only.** The routing section lived in `CLAUDE.md`. Codex never reads it, and opencode does not when `AGENTS.md` exists — which `install-codex.sh` guarantees.

## Decision

1. **The main conversation owns the planning sequence.** Planning routing in the setup template delegates to the devteam `plan` command (`/devteam:plan`, `$devteam-plan`); `commands/plan.md` is the single definition. Its sequence: spawn `product-analyst` → relay its decisions and approvals → continue it for specs → evaluate the spec-gate and spawn `software-architect` per tripping spec → offer sprints.
2. **Sub-agent Question Relay** is a canonical rule in `skills/shared/interaction-patterns/SKILL.md`. A sub-agent without the question tool ends its report with `## Open Decisions`; the orchestrator asks and continues the same sub-agent. The rule is conditional on the tool being absent, so opencode agents rendered with `question: allow` (ADR-0033) keep asking directly, and Codex keeps `request_user_input` where its surface lists it.
3. **Backlog is per scope.** `overview-<scope-slug>.md`, `epics-<scope-slug>.md` and `sprints/<scope-slug>-sprint-<n>.md`; `dod.md` and the `sprints/sprints.md` index (with a Scope column) stay shared. Legacy unscoped files are kept and read as one more scope.
4. **Routing goes to every provider's instruction file.** Setup writes the `## dev-team-agents` section to `CLAUDE.md` for `claude` and `AGENTS.md` for `codex` and `opencode`, from `devteam detect` `providers.in_project`. The health check reports a missing `AGENTS.md` section and rewrites an unedited v1 planning section in place after copying it to quarantine.
5. **An approved sprint is executed by `/devteam:sprint`, orchestrated by the main conversation.** It runs waves in order off a `sprint/<scope-slug>-<n>` integration branch that has its own worktree (where merges run, the one-branch strategy works, and status is committed), one worktree per task branched from it; each wave is reviewed per task and merged before the next wave branches, because a later wave depends on what an earlier one produced. Status lives in the sprint file and `sprints.md` on the integration branch, which makes a run resumable. The command is bound to `software-architect` (`reasoning`) for the tier mirror and opencode's `agent` key, and is `interaction_mode: optional` so Codex without a question tool falls back to a numbered list instead of halting a wave. A spawn prompt that carries `WORKTREE_PATH`/`BRANCH` is now source 0 of the worktree Decision Cascade: the agent works there and the orchestrator owns merge and teardown.
6. **`/devteam:architect` follows the same ownership.** The architect sub-agent can spawn agents but cannot ask (verified 2026-10-17), so the main conversation relays its approvals, runs the Execution Strategy Gate, and continues it with `WORKTREE_PATH`/`BRANCH`.

## Consequences

### Positive
- The same request produces the same planning flow on every door and every provider, and an approved plan now has a path to execution.
- Every step of planning has a named owner; no approval gate depends on a tool a sub-agent lacks.
- A second planned scope no longer destroys the first one's requirements.

### Negative
- Each relay round costs one extra orchestrator turn and a sub-agent continuation.
- Setup now writes into `AGENTS.md`, a file `install-codex.sh` also edits; both only append under their own headings.
- Projects with a user-edited v1 section get a WARN and must merge by hand.

### Neutral
- Legacy `docs/backlog/overview.md`, `epics.md` and unscoped sprint files remain valid input.

## Alternatives Considered

| Alternative | Why rejected |
|-------------|-------------|
| Mirror the `/devteam:plan` steps inside the routing template | Recreates the second copy that had already drifted (Canonical Rule Homes) |
| Let `product-analyst` run in the main conversation instead of as a sub-agent | Loses model-tier selection and the run-banner evidence that the agent ran |
| Installers inject a fixed routing block into `AGENTS.md` | The section is filled from setup answers (`TESTS_REQUIRED`, agent activation); installers cannot produce it |
| Extend `/devteam:fullstack` to run sprints | `fullstack` runs one task; a sprint carries waves, dependencies, merges and status, which would turn it into two commands in one |
| Per-scope folders (`docs/backlog/<scope>/…`) | Moves every existing path, including `sprints/`, which other agents and the spec-gate already reference |
