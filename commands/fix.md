---
description: Fix a bug — auto-routes to backend, frontend, or mobile
argument-hint: <bug description>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

If the bug links a spec (`docs/specs/<feature>.md`), load `skills/shared/spec-gate/SKILL.md` — treat its Given/When/Then as the fix boundary and ask rather than assume when something isn't covered.

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn based on where the bug lives (in parallel if both apply):
- `backend-developer` — fix backend issues (spawn if the bug is in server-side code)
- `frontend-developer` — fix frontend issues (spawn if the bug is in client-side code)

Also spawn if the bug is in mobile code (ios/, android/, *.swift, *.kt, App.tsx, pubspec.yaml, *.dart):
- `mobile-developer` — diagnose and fix bugs in mobile-specific code (React Native, Flutter, native iOS/Android)

Phase 2 — Tests (conditional) — spawn after Phase 1 completes:

**Test gate:** read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`. Spawn the test-specialist(s) below **only if `TESTS_REQUIRED=yes`** (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, **skip this phase entirely**.

- `backend-test-specialist` — add or update tests to cover the fix (spawn if backend was touched)
- `frontend-test-specialist` — add or update tests to cover the fix (spawn if frontend was touched)

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
