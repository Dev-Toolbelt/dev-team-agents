Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.


**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `frontend-developer` at `.claude/agents/dev-team/frontend-developer.md` — implement the frontend changes
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system adherence and visual decisions (spawn only if the task involves visual design or UX decisions)

Phase 2 — Tests (conditional) — spawn after Phase 1 completes:

**Test gate:** read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`. Spawn the test-specialist below **only if `TESTS_REQUIRED=yes`** (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, **skip this phase entirely** and go straight to Phase 3.

- `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md` — write or update tests for the implemented changes

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

**If findings exist**, use the `question` tool to ask the user what to do. Read `.dev-team-agents/user-data/preferences.json` → `language` (default: `en`) and present the quiz in that language:

```json
{
  "questions": [{
    "question": "Aplicar findings?",
    "header": "Findings",
    "options": [
      { "label": "Aplicar todos os findings (Recomendado)", "description": "Re-spawn frontend-developer + frontend-test-specialist para corrigir tudo." },
      { "label": "Aplicar somente findings do Code Review", "description": "Re-spawn apenas frontend-developer para corrigir os apontamentos de código." },
      { "label": "Aplicar somente findings do QA", "description": "Re-spawn apenas frontend-test-specialist para ajustar os testes." },
      { "label": "Não aplicar nada agora", "description": "Ignorar os findings por enquanto." },
      { "label": "Outro", "description": "Especificar outra abordagem manualmente." }
    ]
  }]
}
```

Based on the user's choice:
- **Aplicar todos** → spawn `frontend-developer` + `frontend-test-specialist` in parallel via Task tool
- **Code Review** → spawn `frontend-developer` via Task tool to fix the findings
- **QA** → spawn `frontend-test-specialist` via Task tool to fix the findings
- **Não aplicar nada agora** → end the review
- **Outro** → ask the user to describe their desired approach, then adapt accordingly

**After the resolution agent(s) complete**, output a clear message indicating what was resolved:

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
