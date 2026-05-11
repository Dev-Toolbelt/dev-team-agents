# Workflow — Code Review

Use before merging any branch. Covers preparation, structured review, findings resolution, and PR merge.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

> **Command shortcut**: `/devteam:review` runs this workflow.

---

## Phase 1: PREPARATION

### Step 1: Understand the Changeset (code-reviewer)

```
Prompt: "As the code-reviewer, load the project context and review the current branch.
         Summarize what changed, the scope (backend / frontend / both), and identify
         which specialized reviewers are needed."
```

The `code-reviewer` will:
- Run `git diff` against the base branch
- Load relevant project context (architecture, ADRs, conventions)
- Produce a changeset summary and routing decision

This step determines whether Phase 2 uses backend-reviewer, frontend-reviewer, or both in parallel.

▶ CHECKPOINT — await: code-reviewer changeset summary and routing decision

---

## Phase 2: REVIEW

### Step 2: Specialized Review (backend / frontend / both)

Based on the routing from Phase 1, send the appropriate prompt(s).

**Backend only:**
```
Prompt: "As the code-reviewer, perform a full backend review: correctness, security,
         performance, test coverage, and adherence to project conventions."
```

**Frontend only:**
```
Prompt: "As the code-reviewer, perform a full frontend review: component structure,
         accessibility, visual regression risk, and adherence to the design system."
```

**Both (parallel):** send both prompts in a single message.

| Step | Agent | Par. |
|------|-------|------|
| 2a | code-reviewer (backend scope) | A |
| 2b | code-reviewer (frontend scope) | A |

```
Prompt: "As the code-reviewer, perform a full backend review: correctness, security,
         performance, test coverage, and adherence to project conventions."

Prompt: "As the code-reviewer, perform a full frontend review: component structure,
         accessibility, visual regression risk, and adherence to the design system."
```

Each reviewer produces a structured findings report using severity labels:
- **[BLOCKING]** — must be fixed before merge
- **[SUGGESTION]** — recommended improvement, not required
- **[NITPICK]** — optional style/readability note

▶ CHECKPOINT — await: code-reviewer verdict

---

## Phase 3: FINDINGS RESOLUTION

### Step 3: Fix Blocking Issues

If there are [BLOCKING] findings, hand them to the appropriate developer:

```
Prompt: "As the backend-developer, address the [BLOCKING] findings from the code review:
         [list findings]. Present a plan before making any changes."
```

```
Prompt: "As the frontend-developer, address the [BLOCKING] findings from the code review:
         [list findings]. Present a plan before making any changes."
```

After fixes are applied, request a re-review:

```
Prompt: "As the code-reviewer, re-review the changes made to address the blocking findings."
```

Repeat until no [BLOCKING] findings remain.

▶ CHECKPOINT — await: all [BLOCKING] findings resolved

---

## Phase 4: MERGE & PR

### Step 4: Commit

```
Prompt: "/devteam:commit"
```

### Step 5: Merge / Pull Request

```
Prompt: "Please open a PR for these changes."
```

The `technical-writer` (via `/devteam:pr`) drafts the PR body. If the review has already been completed in this workflow, pass `review` as an argument to skip re-review:

```
Prompt: "/devteam:pr"
```

---

## Workflow Closure

☐ Changeset understood and scope routed
☐ Specialized review completed (backend / frontend / both)
☐ All [BLOCKING] findings resolved
☐ Re-review passed if fixes were required
☐ Commit and PR created
☐ Session summary written

**Related workflows:**
- For full deployment validation, see `workflows/maintenance.md`
- Found a security issue during review? → `workflows/security-patch.md`
- Review revealed need for broader cleanup? → `workflows/refactor.md`

---

## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Agent reports insufficient context | Spawn `software-architect` for clarifying questions; provide the missing info and re-run the phase |
| `[BLOCKING]` findings persist after 3 review cycles | Escalate: re-scope the change, or create an ADR for the contested decision |
| Commit or PR blocked by Git state | Run `/devteam:fix git-state` or resolve manually (`git status`, `git stash`, rebase) |
| User aborts mid-workflow | Workflow state is in `.claude/user-data/session-summary.md` — resume by reading the last entry and continuing from the last completed phase |
