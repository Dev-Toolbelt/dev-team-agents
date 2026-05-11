Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

---

## Scope Guard

Before spawning any agent, evaluate $ARGUMENTS:

- If the argument is vague — "projeto inteiro", "tudo", "codebase", "all", "everything", or any similarly broad term — warn the user:
  > "This scope may take a long time and consume a significant number of tokens. Do you want to proceed? If so, specify whether you want to process module by module (safer, with a checkpoint between each) or all at once."
  Do NOT proceed until the user explicitly confirms.

- If the argument is specific (a module, file, class, function, or named routine), proceed normally.

---

## Worktree / Branch

Read `.claude/.worktree-session` before asking:
- If the file exists and contains a decision (`worktree=no` or `worktree=yes branch=<b>`), follow it silently.
- If absent, ask the user once:
  > "Should I work in a new worktree or a new branch? (worktree / branch)"
  Write the answer to `.claude/.worktree-session`, then act.

**If worktree is selected:** load `skills/shared/worktree/SKILL.md` and enforce the project's branch naming pattern before creating anything. Read the last 20 branch names from `git branch -a` to detect the convention in use (e.g. `refactor/`, `feat/`, kebab-case, ticket prefix). Suggest a name that matches and ask the user to confirm before creating.

---

## Phase 0 — Confirmed. Now spawn the phases in order:

### Phase 1 — Analysis

Spawn:
- `software-architect` at `.claude/agents/dev-team/software-architect.md`

Prompt:
> "Analyze the following scope: $ARGUMENTS
>
> Produce a scope document containing:
> 1. Code smells, dead code, coupling issues, and technical debt
> 2. Dependency map: every file, class, module, and third-party library the scope uses or that depends on it — direct and relevant transitive dependencies
> 3. DB touchpoints: queries, ORM calls, migrations, and schema references found in scope
>
> Uncertainty rule: whenever you find something ambiguous — undocumented behavior, implicit dependency, logic with non-obvious side effects — STOP and ask the user a direct, specific question before continuing. Do not assume. Do not infer silently.
>
> Nothing changes in the code. The scope document must be confirmed by the user before any next step."

▶ CHECKPOINT — await: scope document confirmed by user

---

### Phase 2 — Joint Planning

Spawn in parallel after Phase 1 is confirmed:

- `software-architect` at `.claude/agents/dev-team/software-architect.md`
- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` (if backend scope)
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` (if frontend scope)

Architect prompt:
> "Using the approved scope document, produce the architectural refactoring plan:
> what changes, how it changes, exact boundaries, and risks."

Test-specialist prompt:
> "Using the approved scope document, produce the test coverage plan for the CURRENT behavior of the routine — before any refactoring happens.
>
> Coverage goal: 100% of the routine's observable behavior. For every scenario you cannot cover, provide an explicit justification. Only the following exclusions are acceptable without user confirmation:
> - Code paths that do not affect the observable contract (dead branches, unreachable conditions)
> - Genuinely irrelevant internal details with no external effect
>
> Any exclusion that affects observable behavior MUST be flagged and confirmed by the user before the plan is finalized."

Also spawn conditionally:
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — if scope document includes DB touchpoints
- `security-specialist` at `.claude/agents/dev-team/security-specialist.md` — always; verify no security controls are weakened or removed by the planned changes

Consolidate all outputs into a single **Refactoring Plan** containing:
- Architectural changes
- Test coverage plan with explicit exclusion justifications
- DB optimizations (if applicable)
- Security review findings

**Save the consolidated plan to:**
`.claude/docs/refactoring/<context>/<name>-<YYYY-MM-DD>.md`

Where `<context>` is the module/routine slug and `<name>` is a short descriptive slug of the refactoring goal. Create the directory if it does not exist. Display the saved path to the user.

Present the full plan to the user and await explicit approval. Nothing changes in the code until the plan is approved.

▶ CHECKPOINT — await: Refactoring Plan approved by user

---

### Phase 3 — Implementation

Spawn after plan approval:
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` (if backend scope)
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` (if frontend scope)

Implementation order is **inviolable**:

**Block 1 — Test commits (must be green before Block 2 starts)**
Write all tests from the coverage plan. Each commit must cover a cohesive unit — one test group, one scenario set, one file — following the project's commit pattern. All tests must pass against the original (unmodified) code before proceeding.

**Block 2 — Refactoring commits**
Execute the architectural plan. Each commit covers one logical unit of change (extract a method, move a class, simplify a query, etc.), following the project's commit pattern. Atomic and descriptive — never a single "big bang" commit.

No refactoring commit may precede the last test commit.

▶ CHECKPOINT — await: all tests green on original code (Block 1 done)

---

### Phase 4 — Quality Gate

Spawn in parallel:
- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md`
- `qa-specialist` at `.claude/agents/dev-team/qa-specialist.md`

Code-reviewer prompt:
> "Review the refactoring. Confirm external behavior is preserved, code quality improved, and no new issues introduced. All tests must still pass."

QA-specialist prompt:
> "Validate that the refactored code behaves identically to the original. Run the full test suite, check edge cases from the coverage plan, and flag any regressions."

Any `[BLOCKING]` finding from either agent must be resolved before a PR is created.

After quality gate passes, spawn:
- `technical-writer` at `.claude/agents/dev-team/technical-writer.md` — draft the PR body with a before/after summary of what changed and why.

---

## Fast Track (small scope, no DB)

If the scope is a single small file with no DB touchpoints and the test-specialist confirms existing tests already cover the behavior, Phases 1–2 may be compressed:
- Architect and test-specialist produce a joint single-document plan (no separate scope document step)
- database-specialist and security-specialist may be skipped if no DB or security-relevant code is in scope — the architect must explicitly confirm this before skipping

Fast track still requires user approval of the plan before any implementation begins.

---

Task: $ARGUMENTS
