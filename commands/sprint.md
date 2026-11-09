---
description: Execute approved sprints, each in its own isolated worktree
argument-hint: [<scope-slug> <n> … | path to a sprint file …]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/architecture/orchestration/SKILL.md` (Spawn Integrity, spawn prompt contract, consolidated summary) and `skills/shared/spec-gate/SKILL.md` (scope lock, test-first derivation, Spec Sync Gate). The sprint file format — waves, task fields, the sprint index — is defined in `skills/shared/backlog-template/SKILL.md`. The sprint index is the `backlog-index` doc: resolve its path with `bash .dev-team-agents/scripts/doc-path.sh backlog-index`; every "index" below means that file.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

**MANDATORY:** the main conversation is the orchestrator of this command. It owns every question, every worktree, every merge, and every status update; it spawns the implementation and review agents itself and never delegates the orchestration to a sub-agent. Do NOT write implementation code in the main context. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

---

## Step 1 — Pick the sprint

One run executes one or more sprints. Each argument names one:

- `<scope-slug> <n>` → `docs/backlog/sprints/<scope-slug>-sprint-<n>.md`; `<scope-slug>` must match `^[a-z0-9]+(-[a-z0-9]+)*$` and `<n>` be a positive integer. A path → resolve it; it must sit inside the repository's `docs/backlog/sprints/`. Anything else: refuse and stop.
- Empty → read the index and take the sprints whose status is not `Done`. One candidate → use it; several → ask which, multi-select (one option per sprint: scope, number, goal, `Runs with`), with the first pending sprint and the sprints its `**Runs with**:` lists as the recommended set; none → say there is no pending sprint and suggest `/devteam:plan`. Stop.

Several sprints run in parallel only when each lists every other in its `**Runs with**:` (`backlog-template` § Sprint Parallelism). When they do not, ask **Run only <first sprint> (Recommended)** / **Run in parallel anyway** — parallel sprints that share files meet as conflicts in their PRs.

When a sprint's integration worktree of Step 3 already exists, read its sprint file and the index from it — that is where a running sprint keeps its status.

## Step 2 — Pre-flight

Read each selected sprint file. For every task not yet `[x] Done`, check:

- `Agent` is a name from the orchestration Agent Roster.
- `devteam backlog lint <sprint> --json` reports no `problems` (the dependency graph, waves and branches). A dependency on another sprint's task must also be `[x] Done` there and already in the base branch — so two sprints where one waits on the other never run in the same set.
- `Spec` names a file that exists — plus `<feature>-contract.md` when the spec trips § Gate Rule of `spec-gate` — or is the template's `none — <reason>` form, which runs test-after. A linked spec is not `draft` (spec-gate § Spec Status).
- `bash .dev-team-agents/scripts/spec-lint.sh` reports no ERROR naming this sprint file or one of its specs (a `Covers` ID the spec does not define, a broken `depends_on`); errors in unrelated specs are reported, not blocking.
- `Worktree branch` passes `git check-ref-format --branch`, matches `^[a-z0-9][a-z0-9._/-]*$`, and contains no `..`.

Collect every failure into one list and stop on it, asking **Fix the sprint file with `product-analyst`** / **Stop** — plus **Drop the dependent sprint from this run** when the failure is a dependency between two selected sprints — and, when a spec is `draft`, **Approve the spec** / **Review it with `/devteam:plan`** instead. Never guess a missing agent, spec, or branch.

Worktrees start from committed history, so the sprint file, its specs and contracts must be committed on the base branch, and so must the documents the tasks decide from: `docs/project.md`, the architecture docs, the ADRs, the wiki, the reuse guidelines, the design system, the scope overview and, in the `gated` layout, the PRD, glossary, NFR and `docs/source/`. If any is uncommitted, ask **Commit the planning docs first (Recommended)** — runs the `/devteam:commit` flow on those paths only — / **Stop**.

A task's `Status` moves `[ ] Pending` → `[~] In progress` → `[x] Done`. A task already `[x] Done` is skipped; the first wave with an unfinished task is where execution resumes.

## Step 3 — Execution plan and strategy

Present the plan per the PLAN GATE below: one Steps row per task with its sprint, wave, agent, spec, and branch, and one `Par.` letter per sprint — the sprints run in parallel, the tasks inside one in order. Wait for approval — asked even under the Autonomous Sprint Protocol.

Then ask the strategy — it replaces the orchestration Execution Strategy Gate, so do not also run the `software-architect` agent's gate on providers where this command runs as that agent:

| Option | Effect |
|---|---|
| **Whole sprint in its own worktree** (Recommended — always) | Each sprint runs in its own integration worktree, with its own isolated infra when the project uses Docker; its tasks run one at a time in wave order; the selected sprints run in parallel |
| **Worktree per task** (offered only when one sprint is selected) | Tasks of a wave run in parallel, each in its own worktree, merged into the sprint's integration worktree |
| **Other** | The user describes the approach |

**Integration worktree** — one per sprint. Resolve the base branch per `skills/shared/worktree/SKILL.md` (never hardcoded) and create the worktree `<worktree_path>/sprint/<scope-slug>-<n>` on a new branch `sprint/<scope-slug>-<n>` with that skill's setup flow, including the isolated Docker stack of its `references/docker-isolation.md` when that applies — the stack is the sprint's own, never shared with another sprint or the main project. It is where the whole-sprint strategy works, where merges run, and where the sprint file and the index status are edited and committed. Reuse it on a resumed sprint only when `git merge-base --is-ancestor <base> sprint/<scope-slug>-<n>` holds, and list its commits ahead of base in the status report before the first wave.

**Claims** (machine-local, expiring — ADR-0044), per sprint. Claim every unfinished task before the first wave: `devteam backlog claim <sprint> <TASK-…> --path <integration worktree> --json`. Keep each sprint's returned `owner` for the whole run and pass `--owner <owner>` on every later `claim` and `release`; never reuse an owner this run did not receive. Exit 4 **with** `details.claims` means another orchestrator holds a live claim (its `owner_hint` and expiry are there): ask **Take over the sprint** (re-run with `--take-over`) / **Stop** (that sprint only, when several are selected). A resumed run in a new session, or one whose owner was lost in a compaction, meets its own earlier claims this way too. Exit 4 without `details.claims` is a busy lock: retry once, then continue without claims. Exit 3 (unbound project, unreadable claims file) → continue without claims and say so; claims are advisory, the sprint file stays the status.

No `.worktree-session` file is written: every spawn prompt carries `WORKTREE_PATH` and `BRANCH`, which is source 0 of the worktree skill's Decision Cascade — the agent works there and never merges or tears down.

**Autonomous Sprint Protocol** (the user asked not to be asked): the sprint set is Step 1's recommended set only when the `Runs with` lists agree (otherwise the first sprint alone), the strategy is **Whole sprint in its own worktree**, and task-gate findings are applied as **Apply all**. Pre-flight failures, a merge conflict, a `[SPEC-DRIFT]` and a BLOCKING still open after the fix stop the sprint and ask — none of them has a safe default.

## Step 4 — Run the tasks

Whole sprint → in rounds: each round takes, in every running sprint, its next unfinished task in wave order, and spawns those tasks **in parallel** — one per sprint, each in its sprint's integration worktree. Rounds are synchronized: the next one starts once every task of the current one has passed its gate. Worktree per task → wave by wave, every task of the wave in parallel. Before spawning, per sprint — "the batch" below is the round's task (whole sprint) or the wave's tasks (worktree per task):

1. Run `devteam backlog ready <sprint> --path <integration worktree> --json`. A task of the batch listed in `blocked` still has an open blocker (`blocked_by`): hold it back and say which. A task with an `external_note` has a prose dependency nothing can check — confirm it is met before spawning. Renew the claims (`devteam backlog claim … --owner <owner>`), then mark the batch `[~] In progress` in the sprint file, and the sprint `In progress` in the index, stamping their start times per `backlog-template` § Time Tracking — both in the integration worktree, committed there.
2. Whole sprint → the task works in the integration worktree, which must be clean; record its `HEAD` before spawning — the task's commit range starts there. A task resumed `[~] In progress` continues there. Worktree per task → one worktree per task from `sprint/<scope-slug>-<n>`, named from the task's `Worktree branch`, per the worktree skill's setup flow. A task resumed `[~] In progress` reuses its existing branch and worktree; a task whose branch is already in `git branch --merged sprint/<scope-slug>-<n>` is marked `[x] Done` instead of redone.

Each prompt carries `PLAN_APPROVED: sprint plan, Step 3` (plan-mode), the task's description, its `Covers` scenario IDs (its own acceptance criteria only when `Spec` is none), the spec and contract paths, its `Refs`, the condensed context of orchestration § Spawn Prompt Economy, `WORKTREE_PATH=<path>`, `BRANCH=<branch>`, the worktree rule of orchestration § Autonomous Sprint Protocol step 3, and: "Implement only the scenarios in Covers (spec-gate § Scope Lock) and amend it per § Living Spec when reality diverges. Before raising any question, apply interaction-patterns § Documented Answer First, and report its `Assumptions` and `Answered from` lists. Commit your work on BRANCH." Test authors are spawned with the same `PLAN_APPROVED:` line and Documented Answer First instruction. Every prompt also says Step 5 owns the review, so the agent runs no review gate; an agent that delegates (`software-architect`) spawns its children one at a time inside WORKTREE_PATH and passes them the same scope.

Tests follow the project's `TESTS_REQUIRED` gate (`skills/shared/auto-routing/SKILL.md` § Test Gate). When it is `yes` or absent, every spec-linked task runs spec-gate § Test-First Derivation on its `Covers` scenarios — the track's test author first (`backend-test-specialist`, `frontend-test-specialist`, or `mobile-developer` for Flutter/native), then the task's agent; work outside the scenarios (visual, styling), and any task without a spec, gets its test specialist after the agent. Every other agent runs the tests covering what it touched, per the scoped-test-execution rule.

## Step 5 — Task gate

After every task of the round or wave returned (Spawn Integrity check 3 — a task with no returned banner is `NOT RUN`, not done):

1. Review each task in parallel: `code-reviewer` and `qa-specialist` (which also runs the spec-gate Spec Sync Gate), plus `security-specialist` when the task's diff or description hits a security trigger of `skills/shared/spawn-classifier/SKILL.md`. Scope: the task's own commit range on `sprint/<scope-slug>-<n>`; worktree per task → the task branch's diff against it.
2. A task `NOT RUN` has no findings to ask about: it stops its sprint (worktree per task: stays out of the merge) and is reported in the status table. Findings → when `review_gate_mode` in `.dev-team-agents/resolved/preferences.json` is `auto`, apply them as **Apply all** and say so in one line, asking only about QUESTION rows and fixes that change behavior (`review-result` § Review Loop); otherwise one `AskUserQuestion`: **Apply all (Recommended)**, **Apply BLOCKING only**, **Accept and continue**, **Stop the sprint** (with several sprints running, only the sprint the findings belong to stops). Applying re-spawns the task's agent in its worktree with the findings and the `PLAN_APPROVED:` line, then one `code-reviewer` pass on the commits the fix added only. A task `NOT RUN`, a `[SPEC-DRIFT]` or a BLOCKING still open after that pass keeps the task out of the merge — whole sprint: stops its sprint, whose next tasks build on its commits — and **Accept and continue** is not offered for it.
3. Whole sprint → nothing to merge or tear down: the work is already on `sprint/<scope-slug>-<n>`. Worktree per task → merge each passing task into it from the integration worktree, following the worktree skill's finalization rule with `sprint/<scope-slug>-<n>` passed in as the base — there is no session file to read it from. A merge conflict is never resolved silently: stop, list the conflicting files, and ask **Resolve with `<task agent>`** / **Stop the sprint**.
4. Mark the tasks that passed the gate (and, per task, were merged) `[x] Done` with their finish time and time spent (§ Time Tracking; committed in the integration worktree) and release their claims (`devteam backlog release <sprint> <TASK-…> --owner <owner>`); renew the claims of the tasks still open, so a long wave never outlives them. Report the round or wave in one short status table (sprint · task · agent · review · gate), followed by each task's `Assumptions` and `Answered from`, one line each, then start the next one.

Worktree per task → a task that is not merged keeps out of later waves every task depending on it, directly or through another task; say which and why. Whole sprint → a task stopped at the gate stops its sprint, with the worktree left as it is for the user to inspect.

## Step 6 — Close

Per sprint, as each one finishes or stops — the others keep running:

1. Release every claim this run still holds for it (`devteam backlog release <sprint> --owner <owner>`), also when the sprint stops early. Each task marked Done ran the `implemented` check of spec-gate § Task Resolution. All tasks done → set the sprint `Done` in the index with its finish time and time spent (§ Time Tracking; integration worktree). Otherwise leave it `In progress` and list what is left; running `/devteam:sprint` again resumes there.
2. **Nudge `/devteam:learn`** — a sprint close is a finalization signal (doc-flow § Stages, stage 7). From that sprint's integration worktree, run the canonical learn-nudge check in `commands/merge.md` § Step 4 with `sprint/<scope-slug>-<n>` as the working branch, so the learn commits land on it and reach the PR.

Once every sprint of the run has closed:

3. Consolidated summary per the orchestration skill — the Agents table filled from returned banners only, plus each task's and each sprint's Started · Finished · Time spent, and every `Assumptions` entry of the run. No estimates (backlog-template § Estimates).
4. **Visual Check Gate** from the interaction-patterns skill when a task changed UI. The Review Next-Step Gate is skipped: every task was already reviewed.
5. Write the session summary entry (`<memory-dir>/session-summary.md`, `skills/shared/project-context/SKILL.md` § Memory Layers) and run the `skills/shared/feature-learn/SKILL.md` promotion pass.
6. Hand off in one line per sprint: `/devteam:pr` for `sprint/<scope-slug>-<n>` — parallel sprints each changed the shared indexes on their own branch (the sprint index, plus the wiki and ADR indexes when the learn nudge wrote), so a later PR meets row conflicts there: keep both sides' rows; the integration worktree is torn down by the worktree skill's finalization when that branch is merged.

---

**PLAN GATE — applies to Step 3 onward:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
