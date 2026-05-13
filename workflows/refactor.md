# Workflow — Refactor

Use when improving the internal structure of existing code without changing its external behavior. Applies to any scope: a single function, a module, a service layer, or a cross-cutting concern.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:refactor` runs this workflow.

---

## Before You Start

**Specify the scope explicitly.** This workflow requires a named routine, module, file, or class as its target. Broad scopes like "the whole project" or "everything" are accepted only after the user acknowledges the time and token cost and chooses a processing mode (module-by-module with checkpoints, or all at once).

**Saved plans.** At the end of Phase 2, the consolidated Refactoring Plan is saved to `.claude/docs/refactoring/<context>/<name>-<YYYY-MM-DD>.md`. You can resume the workflow in a future session by sharing that file — no need to regenerate the analysis.

---

## Step 0: Load Context

Load `skills/shared/current-context/SKILL.md` to detect the active branch and scope. If already loaded by a command wrapper, this step is a no-op.

---

## Phase 0: WORKTREE / BRANCH SETUP

Before any agent is spawned, decide where the work happens.

```
Prompt: "Should I work in a new worktree or on a new branch?
         (worktree / branch)"
```

The answer is written to `.claude/.worktree-session` so multi-agent sessions do not ask twice.

**If worktree:** the agent reads the last 20 branch names (`git branch -a`) to detect the project's naming convention, suggests a name that matches (e.g. `refactor/login-flow`), and asks for confirmation before creating.

**If branch:** same convention check, new branch created from current HEAD.

▶ CHECKPOINT — await: worktree or branch ready

**After the branch or worktree is confirmed**, create a safety tag before any changes:

```bash
git tag pre-refactor-<scope>-$(date +%Y%m%d%H%M%S)
```

Replace `<scope>` with a short slug of the target routine or module (e.g. `pre-refactor-auth-service-20260115143022`). This tag lets you recover the exact pre-refactoring state if the workflow is abandoned mid-way.

---

## Phase 1: ANALYSIS

### Step 1: Scope Document (software-architect)

```
Prompt: "As the software-architect, analyze [routine/module/file].
         Produce a scope document with:
         1. Code smells, dead code, coupling issues, and technical debt
         2. Dependency map — every file, class, module, and third-party
            library the scope uses or that depends on it (direct and
            relevant transitive)
         3. DB touchpoints — queries, ORM calls, migrations, schema refs

         Uncertainty rule: whenever you find something ambiguous —
         undocumented behavior, implicit dependency, non-obvious side
         effect — STOP and ask me a specific question. Do not assume.
         Do not infer silently."
```

The `software-architect` will:
- Produce the scope document as described
- Pause and ask the user any clarifying questions before continuing
- NOT change any code

▶ CHECKPOINT — await: scope document confirmed by user

---

## Phase 2: JOINT PLANNING

### Steps 2a + 2b + 2c + 2d — run in parallel after scope document is confirmed

Send all applicable prompts in a single message:

| Step | Agent | Condition | Par. |
|------|-------|-----------|------|
| 2a | software-architect | always | A |
| 2b | backend-test-specialist | backend scope | A |
| 2c | frontend-test-specialist | frontend scope | A |
| 2d | database-specialist | DB touchpoints found | A |
| 2e | security-specialist | always | A |

```
Prompt (software-architect):
"Using the approved scope document, produce the architectural
 refactoring plan: what changes, how it changes, exact file and
 class boundaries, and risks."

Prompt (backend-test-specialist or frontend-test-specialist):
"Using the approved scope document, produce the test coverage plan
 for the CURRENT behavior of [routine] — before any refactoring.

 Coverage goal: 100% of observable behavior.

 For every scenario you cannot cover, provide an explicit
 justification. Only these exclusions are acceptable without
 user confirmation:
 - Dead branches / unreachable code paths
 - Internal details with zero external effect

 Any exclusion that affects observable behavior must be flagged
 to the user for explicit confirmation before the plan is final."

Prompt (database-specialist — if applicable):
"Review the DB touchpoints in the scope document. Propose query,
 schema, or ORM optimizations that can be included in the
 refactoring plan without changing external behavior."

Prompt (security-specialist):
"Review the architectural refactoring plan. Verify that no
 security control, validation, or access check is weakened,
 removed, or bypassed by the planned changes. Flag any concern
 as [BLOCKING] or [ADVISORY]."
```

### Consolidation

After all agents finish, consolidate into a single **Refactoring Plan** document:

```
# Refactoring Plan — <context> — <YYYY-MM-DD>

## Scope
[routine/module targeted]

## Architectural Changes
[from software-architect]

## Test Coverage Plan
[from test-specialist — including exclusion justifications]

## DB Optimizations
[from database-specialist, or "N/A"]

## Security Review
[from security-specialist findings]

## Commit Order
Block 1 — Test commits (list of planned commits)
Block 2 — Refactoring commits (list of planned commits)
```

**Save the plan to:**
`.claude/docs/refactoring/<context>/<name>-<YYYY-MM-DD>.md`

Create the directory if it does not exist. Display the saved path to the user.

Present the full plan and await explicit approval. No code changes until approved.

▶ CHECKPOINT — await: Refactoring Plan approved by user

---

## Phase 3: IMPLEMENTATION

### Step 3: Execute the approved plan

Spawn based on scope:
- `backend-developer` — backend scope
- `frontend-developer` — frontend scope
- Both in parallel — full-stack scope

```
Prompt: "Execute the approved Refactoring Plan at [saved plan path].

         BLOCK 1 — Test commits first:
         Write all tests from the coverage plan. Each commit must
         cover a cohesive unit (one test group, one scenario set,
         one file) following the project's commit pattern.
         All tests must pass against the original, unmodified code
         before you write a single line of refactoring.

         BLOCK 2 — Refactoring commits (only after Block 1 is green):
         Execute the architectural changes. Each commit covers one
         logical unit (extract a method, move a class, simplify a
         query) following the project's commit pattern.
         Atomic and descriptive — never a single big-bang commit.

         No refactoring commit may precede the last test commit.
         If you find a bug while refactoring, do NOT fix it silently —
         flag it as a separate item for the user to decide."
```

▶ CHECKPOINT — await: Block 1 green (all tests passing on original code)
▶ CHECKPOINT — await: Block 2 complete (all refactoring commits done)

---

## Phase 4: QUALITY GATE

### Steps 4a + 4b — run in parallel

Send both prompts in a single message:

| Step | Agent | Par. |
|------|-------|------|
| 4a | code-reviewer | A |
| 4b | qa-specialist | A |

```
Prompt (code-reviewer):
"Review the refactoring. Confirm that:
 - External behavior is preserved
 - Code quality improved relative to the scope document findings
 - No new issues introduced
 - All tests still pass"

Prompt (qa-specialist):
"Validate that the refactored code behaves identically to the
 original. Run the full test suite, verify every scenario from
 the coverage plan, and flag any regression."
```

Any `[BLOCKING]` finding from either agent must be resolved before a PR is created. Non-blocking `[ADVISORY]` findings are logged but do not block.

### Step 5: PR

```
Prompt: "As the technical-writer, draft the PR body for this
         refactoring. Include: what changed, why, before/after
         summary, and a note that behavior is preserved."
```

Then run `/devteam:pr` to create the pull request.

---

## Workflow Closure

☐ Scope confirmed and dependency map produced
☐ Refactoring Plan approved and saved to `.claude/docs/refactoring/`
☐ Block 1 complete — all tests passing on original code
☐ Block 2 complete — all refactoring commits done
☐ Quality gate passed — no `[BLOCKING]` findings
☐ PR created with before/after summary
☐ Session summary written

---

## Fast Track (small scope, no DB)

If the scope is a single small file with no DB touchpoints and existing tests already cover the behavior:

1. Architect and test-specialist produce a joint single-document plan (no separate scope document checkpoint)
2. `database-specialist` and `security-specialist` may be skipped **only if** the architect explicitly confirms no DB or security-relevant code is in scope
3. User approval of the plan is still required before any implementation

---

## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Agent reports insufficient context | Architect asks clarifying questions; provide missing info and re-run the phase |
| Test-specialist cannot reach 100% coverage | Flag exclusions to user; confirm before finalizing plan |
| `[BLOCKING]` finding persists after 3 cycles | Re-scope the change or create an ADR for the contested decision |
| Block 1 tests fail on original code | Tests have a bug — fix the tests first, do not touch the source code |
| Block 2 introduces a regression | Revert the offending refactoring commit; isolate and re-plan that unit |
| Commit or PR blocked by git state | Run `/devteam:fix git-state` or resolve manually |
| User aborts mid-workflow | Resume by sharing the saved plan file from `.claude/docs/refactoring/` |

---

**Related workflows:**
- Found a bug during refactoring? → `workflows/bug-fix.md`
- Refactor involves architectural decisions? → use `/devteam:architect` first
- Security concerns surfaced? → `workflows/security-patch.md`
