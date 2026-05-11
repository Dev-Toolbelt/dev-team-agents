# Workflow B — Inherited / Unfinished Project

Use this workflow when taking over a project from another team — unfinished, poorly documented, or with unknown state.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

---

## Sub-scenario B1: Codebase + Client Task List Available

### Phase 1: AUDIT

**Run in parallel (send all prompts in one message):**
| Step | Agent | Par. |
|------|-------|------|
| 1a | software-architect | A |
| 1b | database-specialist | A |
| 1c | security-specialist | A |

```
Prompt: "As the software-architect, audit the existing codebase. Document the current
         architecture, tech debt, questionable decisions, and risks in
         .claude/docs/development/"

Prompt: "As the database-specialist, audit the existing database schema. Connect to
         the running database if credentials are available in the environment, run
         diagnostic queries to map the actual data state, and identify modeling
         problems, missing indexes, missing foreign keys, bloat, and migration gaps."

Prompt: "As the security-specialist, do a quick security audit of the existing codebase.
         Flag any CRITICAL or HIGH issues found."
```

Each agent will:
- Present a plan (scope of audit, areas to examine, output documents to create)
- Wait for your approval before reading files or generating reports

All output documents are created in **English**.

**ADR trigger**: any architectural decision you uncover during the audit should be documented as an ADR:
```bash
bash .claude/dev-team-agents/scripts/new-adr.sh "decision-title"
```
Fill in the generated template and set status to `Accepted` if the decision is already in effect, or `Proposed` if it should be revisited.

**Audit exit criteria** — the discovery phase is complete when:
- (a) `.claude/docs/development/architecture.md` exists and is populated
- (b) at least one session-summary entry exists in `.claude/user-data/session-summary.md`
- (c) all major unknowns have been documented or escalated (no silent gaps)

▶ **CHECKPOINT — await: software-architect (1a), database-specialist (1b), security-specialist (1c)**
All three audit reports must exist before moving to Phase 2.

### Phase 2: CLIENT SCOPING CYCLE

When the client provides a task list with thin context:

#### Round 1

```
Prompt: "As the product-analyst, I have a task list from the client: [paste document].
         Analyze it together with the existing codebase and generate the clarification
         questions needed to close the scope."
```

The `product-analyst` will:
- Present a plan (what to read, how to structure the Q&A)
- After approval: save questions to `.claude/docs/backlog/client-clarifications.md`

#### Send to Client → Receive Answers → Round 2+

```
Prompt: "As the product-analyst, the client responded to our questions: [paste responses].
         Evaluate if the scope is now closed or if more questions are needed."
```

Repeat until the `product-analyst` confirms scope is 100% closed.

**The `client-clarifications.md` file is a project artifact** — it records the full Q&A history in English.

### Phase 3: GAP ANALYSIS

```
Prompt: "As the product-analyst, generate the full backlog for what remains to be done,
         including sprint plans with time estimates and delivery forecast."

Prompt: "As the software-architect, based on the audit and new scope, define the
         strategy: what to refactor, what to keep, what to rewrite.
         Update .claude/docs/development/architecture.md with your decisions."
```

Each agent presents a plan before generating any document.

### Phase 4: DEVELOPMENT + QUALITY GATE

Follow the same flow as Workflow A, with extra attention to:
- `code-reviewer` auditing legacy code that is touched
- `qa-specialist` prioritizing regression testing

---

## Sub-scenario B2: No Codebase Yet (Only Client Document)

Start with the CLIENT SCOPING CYCLE (Phase 2) before any technical audit.

```
Prompt: "As the product-analyst, I have a document from a client with requirements
         for a project I'm taking over: [paste document].
         I don't have the codebase yet. Generate the clarification questions
         to close the scope."
```

When the codebase arrives, resume from Phase 1 (AUDIT) with the scope already partially defined.

---

## Delivery Forecasting

After the backlog is complete, the `product-analyst` will include:
- Estimated hours/days per sprint
- Dependencies between tasks that affect the critical path
- A delivery forecast date based on team velocity

Use this to communicate predictability to the client.

---

## Coexistence Reminder

The audit phase may discover that the existing project has conventions and patterns already established. Document them in `.claude/docs/development/code-standards.md`. All agents will then follow the project's patterns, not just the base standards.

---

## Workflow Complete

When the backlog is approved, the gap analysis is done, and development + quality gate have completed:

1. `technical-writer` — generate initial documentation (architecture summary, API reference if applicable)
2. `/devteam:commit` — group staged changes by layer and write commits following the project's convention
3. `devops-specialist` — confirm the environment is ready for the first delivery and handle SHIP (see `## SHIP` in `agents/devops-specialist.md`)

If GitHub is configured and `gh` is installed:
```
Prompt: "Please open a PR for these changes."
         → Agent will present a plan and ask for consent before creating the PR.
```

Hand off to the team for final review and deployment.

The workflow is complete when the client confirms the delivered scope meets the agreed acceptance criteria. There is no automated completion signal — the decision is yours.

Once the project is stable and in production, switch to `workflows/maintenance.md` for all ongoing feature work and bug fixes.

---

## Workflow Closure

Before closing out the session, verify:

- [ ] All three audit reports exist under `.claude/docs/development/`
- [ ] Audit exit criteria met: `architecture.md` populated, session summary written, major unknowns documented
- [ ] At least one ADR created for significant architectural decisions discovered during audit
- [ ] Backlog approved by client and gap analysis complete
- [ ] Quality gate passed (code-reviewer, qa-specialist, security-specialist)
- [ ] Commits made and PR opened (if GitHub is configured)
- [ ] Session summary written to `.claude/user-data/session-summary.md`

---

## Recovery Paths

| Failure point | Recovery |
|---------------|----------|
| Agent reports insufficient context | Spawn `software-architect` for clarifying questions; provide the missing info and re-run the phase |
| `[BLOCKING]` findings persist after 3 review cycles | Escalate: re-scope the change, or create an ADR for the contested decision |
| Commit or PR blocked by Git state | Run `/devteam:fix git-state` or resolve manually (`git status`, `git stash`, rebase) |
| User aborts mid-workflow | Workflow state is in `.claude/user-data/session-summary.md` — resume by reading the last entry and continuing from the last completed phase |
