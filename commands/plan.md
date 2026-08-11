---
description: Plan a feature with product-analyst (+ architect on request)
argument-hint: <feature description>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

**MANDATORY:** Use the Task tool to spawn the agent below. Do NOT plan inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

## Protagonist — product-analyst

Always spawn:
- `product-analyst` — **the lead of this command.** It reads the request, interrogates it against its lenses, runs a short focused conversation to close the open decisions, and produces a **purely business-level** requirements document (`docs/backlog/overview.md`) ready to become sprints. It stays out of technical design.

The `product-analyst` owns the conversation and the deliverable. Planning is business-first: the output is *what* and *why*, not *how*.

After `overview.md` is approved, `product-analyst` writes a spec per feature (Step 5b — see `skills/shared/spec-gate/SKILL.md`) before generating sprints.

## Conditional — software-architect

Spawn `software-architect` **explicitly** when the user asks for technical input in `$ARGUMENTS`, **or automatically** per the `spec-gate` rule: any spec whose `touches` field spans more than one layer, or that introduces a new API/schema/integration point, gets its `<feature>-contract.md` written by `software-architect` without waiting for the user to ask. Either way it contributes the technical layer **on top of** the product-analyst's business scope; it does not replace the product-analyst as lead.

If the request is purely a feature/business ask and no spec trips the gate, do **not** spawn the software-architect — keep the plan business-only.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
