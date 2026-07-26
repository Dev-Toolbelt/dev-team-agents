Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `backend-developer` at `.claude/agents/dev-team/backend-developer.md` — implement server-side changes
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement client-side changes
- `database-specialist` at `.claude/agents/dev-team/database-specialist.md` — handle schema, migrations, queries (spawn only if the task involves database changes)
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system and visual decisions (spawn only if the task involves visual design or UX decisions)

Phase 2 — Tests (conditional) — spawn after Phase 1 completes:

**Test gate:** read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`. Spawn the test-specialists below **only if `TESTS_REQUIRED=yes`** (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, **skip this phase entirely** and go straight to Phase 3.

- `backend-test-specialist` at `.claude/agents/dev-team/backend-test-specialist.md` — tests for backend changes
- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — tests for frontend changes

## Phase 3 — Mandatory review handoff (automatic)

After Phase 1 (and Phase 2, if it ran) complete, **always** spawn the following in parallel via the Task tool — no user confirmation, this handoff is mandatory:

- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md` — scope: all files changed this session (`git diff` against the base branch)
- `qa-specialist` at `.claude/agents/dev-team/qa-specialist.md` — scope: validate the behavior of the changes against acceptance criteria and regression risk

**After both complete**, synthesize their outputs into a single consolidated block of **critical findings only** and present it to the user:

```
## Post-implementation review

### Code review (critical only)
[bullets]

### QA (gaps / risks)
[bullets]

### Summary
[1–2 sentences: verdict and recommended next step]
```

If both agents report no findings, output exactly:

```
Post-implementation review: no issues found.
```

**If findings exist**, use the `question` tool to ask the user what to do:

```json
{
  "questions": [{
    "question": "O que fazer com os findings acima?",
    "header": "Findings",
    "options": [
      { "label": "Resolver Code Review findings", "description": "Re-spawn backend-developer + frontend-developer para corrigir os apontamentos de código." },
      { "label": "Resolver QA findings", "description": "Re-spawn backend-test-specialist + frontend-test-specialist para ajustar os testes." },
      { "label": "Resolver Code Review + QA findings", "description": "Re-spawn todos os agentes para corrigir tudo." },
      { "label": "Nenhum agora", "description": "Ignorar os findings por enquanto." }
    ]
  }]
}
```

Based on the user's choice:
- **Code Review** → spawn `backend-developer` + `frontend-developer` in parallel via Task tool
- **QA** → spawn `backend-test-specialist` + `frontend-test-specialist` in parallel
- **Both** → spawn all four agents in parallel
- **Nenhum agora** → end the review

**After the resolution agent(s) complete**, output clearly:

```
✅ Code review findings resolvidos
```

or

```
✅ QA findings resolvidos
```

or

```
✅ Code review e QA findings resolvidos
```

depending on which were selected.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
