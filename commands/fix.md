---
description: Fix a bug — auto-routes to backend, frontend, or mobile
argument-hint: <bug description>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

Load `skills/shared/spawn-classifier/SKILL.md` and apply its decision tree to $ARGUMENTS to determine which conditional agents below to spawn.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

If the bug links a spec (`docs/specs/<feature>.md`), load `skills/shared/spec-gate/SKILL.md` — treat its Given/When/Then as the fix boundary and ask rather than assume when something isn't covered. This also loads its § Test-First Derivation rule, used below.

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

**Test gate:** read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`.

**If `TESTS_REQUIRED=no`:** Phase 1 — spawn based on where the bug lives (in parallel if both apply):
- `backend-developer` — fix backend issues (spawn if the bug is in server-side code)
- `frontend-developer` — fix frontend issues (spawn if the bug is in client-side code)
- `mobile-developer` — diagnose and fix bugs in mobile-specific code (spawn if the bug is in mobile code: ios/, android/, *.swift, *.kt, App.tsx, pubspec.yaml, *.dart)

Skip tests entirely.

**If `TESTS_REQUIRED=yes` (or the key is absent — default to running tests):** test-first — a failing regression test is written before the fix, per track:

- Phase 1a — spawn the test-specialist(s) for the touched track(s) (`backend-test-specialist` and/or `frontend-test-specialist`) to write a test that reproduces the bug and fails against the current (broken) code. Derive the repro from the bug description in `$ARGUMENTS` as an implicit Given (repro state) / When (triggering action) / Then (expected correct behavior) — or from the linked spec's Given/When/Then if one exists, per the loaded skill's Test-First Derivation rule. If the expected correct behavior is ambiguous from the description alone, stop and ask via `AskUserQuestion` rather than guessing an assertion.
- Phase 1b — after Phase 1a's tests are committed red, spawn the matching developer agent(s) in parallel to fix the bug until those tests (and the rest of the suite) are green:
  - `backend-developer` (if backend was touched)
  - `frontend-developer` (if frontend was touched)
  - `mobile-developer` (if mobile was touched — same detection signals as above)

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
