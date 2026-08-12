---
description: Implement backend changes
argument-hint: <task description>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

If the task links a spec (`docs/specs/<feature>.md`), load `skills/shared/spec-gate/SKILL.md` — every spawned agent below treats its Given/When/Then as the implementation boundary and asks rather than assumes when something isn't covered.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

**Test gate:** read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`.

**If `TESTS_REQUIRED=no`:** Phase 1 — spawn in parallel:
- `backend-developer` — implement the backend changes
- `database-specialist` — handle schema, migrations, and queries (spawn only if the task involves database changes)

Skip straight to Phase 3.

**If `TESTS_REQUIRED=yes` (or the key is absent — default to running tests) AND the task links a spec (`docs/specs/<feature>.md`):** follow the loaded spec-gate skill's § Test-First Derivation — this is test-first, not test-after:

- Phase 1a — spawn `backend-test-specialist` alone: derive failing tests from the spec's Given/When/Then, commit them red.
- Phase 1b — after Phase 1a completes, spawn `backend-developer` (+ `database-specialist` if DB changes are involved) to implement until the derived tests are green plus the rest of its scope.

**If `TESTS_REQUIRED=yes` but no spec is linked:** Phase 1 — spawn in parallel:
- `backend-developer` — implement the backend changes
- `database-specialist` — handle schema, migrations, and queries (spawn only if the task involves database changes)

Phase 2 — spawn after Phase 1 completes:
- `backend-test-specialist` — write or update tests for the implemented changes

## Phase 3 — Mandatory review handoff (automatic)

After Phase 1 (and Phase 2, if it ran) complete, **always** spawn the following in parallel via the Task tool — no user confirmation, this handoff is mandatory:

- `code-reviewer` — scope: all files changed this session (`git diff` against the base branch)
- `qa-specialist` — scope: validate the behavior of the changes against acceptance criteria and regression risk

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
      { "label": "Aplicar todos os findings (Recomendado)", "description": "Re-spawn backend-developer + backend-test-specialist para corrigir tudo." },
      { "label": "Aplicar somente findings do Code Review", "description": "Re-spawn apenas backend-developer para corrigir os apontamentos de código." },
      { "label": "Aplicar somente findings do QA", "description": "Re-spawn apenas backend-test-specialist para ajustar os testes." },
      { "label": "Não aplicar nada agora", "description": "Ignorar os findings por enquanto." },
      { "label": "Outro", "description": "Especificar outra abordagem manualmente." }
    ]
  }]
}
```

Based on the user's choice:
- **Aplicar todos** → spawn `backend-developer` + `backend-test-specialist` in parallel via Task tool
- **Code Review** → spawn `backend-developer` via Task tool to fix the findings
- **QA** → spawn `backend-test-specialist` via Task tool to fix the findings
- **Não aplicar nada agora** → end the review
- **Outro** → ask the user to describe their desired approach, then adapt accordingly

**After the resolution agent(s) complete**, output a clear message indicating what was resolved:

## Session close (mandatory)

After the phases above complete — including any resolution agents:

1. **Session summary** — append this session's contribution to today's entry in `.dev-team-agents/user-data/session-summary.md`: one `### <agent-name>` sub-heading per agent that acted, each with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading. Skip only if no file was created or modified.
2. **Lessons learned (automatic)** — load `skills/shared/feature-learn/SKILL.md` and run its scoped promotion pass; skip silently if it finds nothing to promote.
3. **Hand off** — the working tree is left dirty on purpose. Close with one line naming the next step: `/devteam:commit` to group and commit the changes, then `/devteam:pr` when the branch is ready for review.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
