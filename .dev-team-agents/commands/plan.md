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
- `product-analyst` — **the lead of this command.** It reads the request, interrogates it against its lenses, runs a short focused conversation to close the open decisions, and produces a **purely business-level** requirements document (`docs/backlog/overview-<scope-slug>.md`) ready to become sprints. It stays out of technical design.

The `product-analyst` owns the content and the deliverable. Planning is business-first: the output is *what* and *why*, not *how*.

## Layout — pick the sequence

Run `bash .dev-team-agents/scripts/doc-path.sh --layout`. `development` (also empty output, or no script) → the **Sequence** below, unchanged. `gated` → the **Gated Sequence** instead; the Sequence does not run.

## Sequence — the main conversation owns it

The `product-analyst` runs as a sub-agent, so its questions and approval gates reach the user through the main conversation, per the `interaction-patterns` skill § Sub-agent Question Relay. Each step below ends only when its report carries no `## Open Decisions` block.

1. **Scope** — spawn `product-analyst`; relay its decision rounds; it writes the overview and returns it for approval; relay the approval.
2. **Specs** — continue the same agent for Step 5b (one spec per feature, `skills/shared/spec-gate/SKILL.md`); relay its spec approval gate, so every spec it returns is `approved` or stays `draft` by the user's choice.
3. **Contract gate** — the main conversation evaluates § Gate Rule of `spec-gate` on each returned spec and spawns `software-architect` once for every spec that trips it, in parallel.
4. **Close** — list the overview, specs, and contracts written, then offer sprint generation (Step 6) with `AskUserQuestion`; never generate sprints unasked. Once sprints exist, offer to execute the first one with `/devteam:sprint <scope-slug> 1` — never start it unasked.

## Gated Sequence — `docs_layout: gated`

The main conversation walks `skills/shared/doc-flow/SKILL.md` § Stages 0→5 — that table owns each stage's documents, owners and exit gates; this list owns only the spawn order. Relay each exit gate per § Sub-agent Question Relay and do not start the next stage until it passes; here a stage's exit gate is the plan approval every spawned agent owes, and stage 0's gate needs none (doc-flow § Stages).

1. **Stages 0–1** — spawn `product-analyst` for the raw input and the PRD, glossary and NFR documents; relay its decision rounds and the stage 1 gate.
2. **Stages 2a ‖ 2b** — after PRD approval, spawn `software-architect` (2a) and `ui-ux-designer` (2b) **in parallel, in one message**. When `software-architect` returns its 2a draft, the main conversation spawns `database-specialist` (schema review) and `security-specialist` (findings and sign-off) in parallel, hands their findings back to the same `software-architect` to write the threat model and apply the review, and relays the 2a gate only after both returned. Relay the 2b gate as its report returns.
3. **Stage 3** — when both gates passed, spawn `software-architect` and `ui-ux-designer` in parallel on doc-flow § Reconciliation; relay its gate.
4. **Stage 4, per feature** — continue `product-analyst` for the spec; then, in parallel, `software-architect` (contract, evals when the product uses LLMs, testing) and `ui-ux-designer` (flow). Relay the gate for each feature.
5. **Stage 5 and close** — offer sprint generation with `AskUserQuestion`, never unasked; on yes, continue `product-analyst` for the backlog index, overview and sprints, and relay its gate. Then offer `/devteam:sprint <scope-slug> 1`, never starting it unasked.

## Conditional — software-architect

Spawn `software-architect` **explicitly** when the user asks for technical input in `$ARGUMENTS` — after step 1, never in parallel with the scope conversation — **or automatically** at step 3 per the `spec-gate` rule: any spec whose `touches` field spans more than one layer, or that introduces a new API/schema/integration point, gets its `<feature>-contract.md` written by `software-architect` without waiting for the user to ask. Either way it contributes the technical layer **on top of** the product-analyst's business scope; it does not replace the product-analyst as lead.

If the request is purely a feature/business ask and no spec trips the gate, do **not** spawn the software-architect — keep the plan business-only.

This section governs the **Sequence** only; in the Gated Sequence `software-architect` always runs at stages 2a, 3 and 4.

---

**PLAN GATE — mandatory for every spawned agent:**
1. Read `.dev-team-agents/resolved/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision — a sub-agent returns that approval as an Open Decision (§ Sub-agent Question Relay). In the gated layout the stage's exit gate is that approval (doc-flow § Stages).
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
