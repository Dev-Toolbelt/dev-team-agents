Load `skills/shared/current-context/SKILL.md` to identify the active branch, modified files, and worktree state before acting. Restrict all actions to the detected scope unless $ARGUMENTS explicitly requests broader.

Load `skills/shared/interaction-patterns/SKILL.md` before asking the user any question with a finite set of answers.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT plan inline — always delegate. The only exception is if the user explicitly asks not to use agents.

## Protagonist — product-analyst

Always spawn:
- `product-analyst` at `.claude/agents/dev-team/product-analyst.md` — **the lead of this command.** It reads the request, interrogates it against its lenses, runs a short focused conversation to close the open decisions, and produces a **purely business-level** requirements document (`.claude/docs/backlog/overview.md`) ready to become sprints. It stays out of technical design.

The `product-analyst` owns the conversation and the deliverable. Planning is business-first: the output is *what* and *why*, not *how*.

## Conditional — software-architect

Spawn `software-architect` at `.claude/agents/dev-team/software-architect.md` **only if** the user **explicitly** asks for technical input in `$ARGUMENTS` — e.g., they request architecture, a technical design, stack/data-model/API decisions, trade-offs, or an ADR. In that case, the software-architect contributes the technical layer **on top of** the product-analyst's business scope; it does not replace the product-analyst as lead.

If the request is purely a feature/business ask (the default), do **not** spawn the software-architect — keep the plan business-only.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.claude/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
