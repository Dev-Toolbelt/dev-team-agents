Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `mobile-developer` at `.claude/agents/dev-team/mobile-developer.md` — implement the mobile changes (React Native, Expo, Flutter, native iOS/Android)
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system adherence and visual decisions (spawn only if the task involves visual design, UX decisions, or platform UI guidelines)

Phase 2 — Tests (conditional) — spawn after Phase 1 completes:

**Test gate:** read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`. Write tests **only if `TESTS_REQUIRED=yes`** (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, **skip this phase entirely** and go straight to Phase 3.

- For React Native / Expo (JS/TS) suites → spawn `frontend-test-specialist` at `.claude/agents/dev-team/frontend-test-specialist.md`.
- For Flutter or native iOS/Android → the `mobile-developer` writes the platform-appropriate tests (e.g., `flutter test`, XCTest, Espresso) for the implemented changes.

## Phase 3 — Mandatory review handoff (automatic)

After Phase 1 (and Phase 2, if it ran) complete, **always** spawn the following in parallel via the Task tool — no user confirmation, this handoff is mandatory:

- `code-reviewer` at `.claude/agents/dev-team/code-reviewer.md` — scope: all files changed this session (`git diff` against the base branch); it will route to mobile-specific review as needed
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

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
