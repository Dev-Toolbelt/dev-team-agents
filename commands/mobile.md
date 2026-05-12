Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

---

**MANDATORY:** Use the Task tool to spawn the agents below. Do NOT write code directly in the main context — always delegate. The only exception is if the user explicitly asks not to use agents.

Phase 1 — spawn in parallel:
- `mobile-developer` at `.claude/agents/dev-team/mobile-developer.md` — implement the mobile changes (React Native, Expo, Flutter, native iOS/Android)
- `ui-ux-designer` at `.claude/agents/dev-team/ui-ux-designer.md` — design system adherence and visual decisions (spawn only if the task involves visual design, UX decisions, or platform UI guidelines)

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.claude/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
