---
description: Execute an approved sprint wave by wave
argument-hint: [<scope-slug> <n> | path to a sprint file]
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/architecture/orchestration/SKILL.md` (Spawn Integrity, spawn prompt contract, consolidated summary) and `skills/shared/spec-gate/SKILL.md` (scope lock, test-first derivation, Spec Sync Gate). The sprint file format — waves, task fields, `sprints.md` index — is defined in `skills/shared/backlog-template/SKILL.md`.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

**MANDATORY:** the main conversation is the orchestrator of this command. It owns every question, every worktree, every merge, and every status update; it spawns the implementation and review agents itself and never delegates the orchestration to a sub-agent. Do NOT write implementation code in the main context. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

---

## Step 1 — Pick the sprint

- `<scope-slug> <n>` → `docs/backlog/sprints/<scope-slug>-sprint-<n>.md`; `<scope-slug>` must match `^[a-z0-9]+(-[a-z0-9]+)*$` and `<n>` be a positive integer. A path → resolve it; it must sit inside the repository's `docs/backlog/sprints/`. Anything else: refuse and stop.
- Empty → read `docs/backlog/sprints/sprints.md` and take the sprints whose status is not `Done`. One candidate → use it; several → ask which (one option per sprint: scope, number, goal); none → say there is no pending sprint and suggest `/devteam:plan`. Stop.

When the integration worktree of Step 3 already exists, read the sprint file and `sprints.md` from it — that is where a running sprint keeps its status.

## Step 2 — Pre-flight

Read the sprint file. For every task not yet `[x] Done`, check:

- `Agent` is a name from the orchestration Agent Roster.
- `devteam backlog lint <sprint> --json` reports no `problems` (the dependency graph, waves and branches). A dependency on another sprint's task must also be `[x] Done` there and already in the base branch.
- `Spec` names a file that exists — plus `<feature>-contract.md` when the spec trips § Gate Rule of `spec-gate` — or is the template's `none — <reason>` form, which runs test-after. A linked spec is not `draft` (spec-gate § Spec Status).
- `bash .dev-team-agents/scripts/spec-lint.sh` reports no ERROR naming this sprint file or one of its specs (a `Covers` ID the spec does not define, a broken `depends_on`); errors in unrelated specs are reported, not blocking.
- `Worktree branch` passes `git check-ref-format --branch`, matches `^[a-z0-9][a-z0-9._/-]*$`, and contains no `..`.

Collect every failure into one list and stop on it, asking **Fix the sprint file with `product-analyst`** / **Stop** — and, when a spec is `draft`, **Approve the spec** / **Review it with `/devteam:plan`** instead. Never guess a missing agent, spec, or branch.

Worktrees start from committed history, so the sprint file, its specs and contracts must be committed on the base branch. If any is uncommitted, ask **Commit the planning docs first (Recommended)** — runs the `/devteam:commit` flow on those paths only — / **Stop**.

A task's `Status` moves `[ ] Pending` → `[~] In progress` → `[x] Done`. A task already `[x] Done` is skipped; the first wave with an unfinished task is where execution resumes.

## Step 3 — Execution plan and strategy

Present the plan per the PLAN GATE below: one Steps row per task, its wave as the `Par.` letter, its agent, spec, and branch. Wait for approval — asked even under the Autonomous Sprint Protocol.

Then ask the strategy — it replaces the orchestration Execution Strategy Gate, so do not also run the `software-architect` agent's gate on providers where this command runs as that agent:

| Option | Effect |
|---|---|
| **Worktree per task** (Recommended when `worktree_active` is `true` or absent) | Tasks of a wave run in parallel, each in its own worktree |
| **One branch, tasks in sequence** (Recommended when `worktree_active` is `false`) | Same order, no parallelism, every task in the integration worktree |
| **Other** | The user describes the approach |

**Integration worktree.** Resolve the base branch per `skills/shared/worktree/SKILL.md` (never hardcoded) and create the worktree `<worktree_path>/sprint/<scope-slug>-<n>` on a new branch `sprint/<scope-slug>-<n>` with that skill's setup flow. It is where merges run, where the one-branch strategy works, and where the sprint file and `sprints.md` status are edited and committed. Reuse it on a resumed sprint only when `git merge-base --is-ancestor <base> sprint/<scope-slug>-<n>` holds, and list its commits ahead of base in the status report before the first wave.

**Claims** (machine-local, expiring — ADR-0044). Claim every unfinished task before the first wave: `devteam backlog claim <sprint> <TASK-…> --path <integration worktree> --json`. Keep the returned `owner` for the whole run and pass `--owner <owner>` on every later `claim` and `release`; never reuse an owner this run did not receive. Exit 4 **with** `details.claims` means another orchestrator holds a live claim (its `owner_hint` and expiry are there): ask **Take over the sprint** (re-run with `--take-over`) / **Stop**. A resumed run in a new session, or one whose owner was lost in a compaction, meets its own earlier claims this way too. Exit 4 without `details.claims` is a busy lock: retry once, then continue without claims. Exit 3 (unbound project, unreadable claims file) → continue without claims and say so; claims are advisory, the sprint file stays the status.

No `.worktree-session` file is written: every spawn prompt carries `WORKTREE_PATH` and `BRANCH`, which is source 0 of the worktree skill's Decision Cascade — the agent works there and never merges or tears down.

**Autonomous Sprint Protocol** (the user asked not to be asked): the strategy follows `worktree_active`, and wave-gate findings are applied as **Apply all**. Pre-flight failures, a merge conflict, a `[SPEC-DRIFT]` and a BLOCKING still open after the fix stop the sprint and ask — none of them has a safe default.

## Step 4 — Run the waves, in order

For each wave, before spawning:

1. Run `devteam backlog ready <sprint> --path <integration worktree> --json`. A task of the wave listed in `blocked` still has an open blocker (`blocked_by`): hold it back and say which. A task with an `external_note` has a prose dependency nothing can check — confirm it is met before spawning. Renew the claims (`devteam backlog claim … --owner <owner>`), then mark the wave's tasks `[~] In progress` in the sprint file, and the sprint `In progress` in `sprints.md` — both in the integration worktree, committed there.
2. Worktree per task → one worktree per task from `sprint/<scope-slug>-<n>`, named from the task's `Worktree branch`, per the worktree skill's setup flow. A task resumed `[~] In progress` reuses its existing branch and worktree; a task whose branch is already in `git branch --merged sprint/<scope-slug>-<n>` is marked `[x] Done` instead of redone.

Spawn every task of the wave **in parallel** (one branch: one at a time, in the integration worktree). Each prompt carries the task's description, its `Covers` scenario IDs (its own acceptance criteria only when `Spec` is none), the spec and contract paths, `WORKTREE_PATH=<path>`, `BRANCH=<branch>`, the worktree rule of orchestration § Autonomous Sprint Protocol step 3, and: "Implement only the scenarios in Covers (spec-gate § Scope Lock) and amend it per § Living Spec when reality diverges. Commit your work on BRANCH."

Tests follow the project's `TESTS_REQUIRED` gate (`skills/shared/auto-routing/SKILL.md` § Test Gate). When it is `yes` or absent, every spec-linked task runs spec-gate § Test-First Derivation on its `Covers` scenarios — the track's test author first (`backend-test-specialist`, `frontend-test-specialist`, or `mobile-developer` for Flutter/native), then the task's agent; work outside the scenarios (visual, styling), and any task without a spec, gets its test specialist after the agent. Every other agent runs the tests covering what it touched, per the scoped-test-execution rule.

## Step 5 — Wave gate

After every task of the wave returned (Spawn Integrity check 3 — a task with no returned banner is `NOT RUN`, not done):

1. Review each task in parallel: `code-reviewer` and `qa-specialist` (which also runs the spec-gate Spec Sync Gate), plus `security-specialist` when the task's diff or description hits a security trigger of `skills/shared/spawn-classifier/SKILL.md`. Scope: the task branch's diff against `sprint/<scope-slug>-<n>`; one branch → the task's own commit range.
2. Findings → one `AskUserQuestion`: **Apply all (Recommended)**, **Apply BLOCKING only**, **Accept and continue**, **Stop the sprint**. Applying re-spawns the task's agent in its worktree (one branch: the integration worktree) with the findings, then one `code-reviewer` pass on the commits the fix added only. A `[SPEC-DRIFT]` or a BLOCKING still open after that pass keeps the task out of the merge, and **Accept and continue** is not offered for it.
3. Merge each passing task into `sprint/<scope-slug>-<n>` from the integration worktree, following the worktree skill's finalization rule with `sprint/<scope-slug>-<n>` passed in as the base — there is no session file to read it from. One branch → nothing to merge or tear down. A merge conflict is never resolved silently: stop, list the conflicting files, and ask **Resolve with `<task agent>`** / **Stop the sprint**.
4. Mark merged tasks `[x] Done` (committed in the integration worktree) and release their claims (`devteam backlog release <sprint> <TASK-…> --owner <owner>`); renew the claims of the tasks still open, so a long wave never outlives them. Report the wave in one short status table (task · agent · review · merged), then start the next wave.

A task that is not merged keeps out of later waves every task depending on it, directly or through another task; say which and why.

## Step 6 — Close

1. Release every claim this run still holds (`devteam backlog release <sprint> --owner <owner>`), also when the sprint stops early. Each task marked Done ran the `implemented` check of spec-gate § Task Resolution. All tasks done → set the sprint `Done` in `sprints.md` (integration worktree). Otherwise leave it `In progress` and list what is left; running `/devteam:sprint` again resumes there.
2. Consolidated summary per the orchestration skill — the Agents table filled from returned banners only.
3. **Visual Check Gate** from the interaction-patterns skill when a task changed UI. The Review Next-Step Gate is skipped: every wave was already reviewed.
4. Write the session summary entry (`<memory-dir>/session-summary.md`, `skills/shared/project-context/SKILL.md` § Memory Layers) and run the `skills/shared/feature-learn/SKILL.md` promotion pass.
5. Hand off in one line: `/devteam:pr` for `sprint/<scope-slug>-<n>`; the integration worktree is torn down by the worktree skill's finalization when that branch is merged.

---

**PLAN GATE — applies to Step 3 onward:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
