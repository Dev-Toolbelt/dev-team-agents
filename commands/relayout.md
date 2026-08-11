---
description: Redesign an existing screen to faithfully match visual references
argument-hint: <screen> following <reference image(s)>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

---

## 0. MANDATORY input gate — check this FIRST, before anything else

This command requires **two things** to be resolvable from $ARGUMENTS before any other action: at least one **visual reference** (an image file — `.png`, `.jpg`, `.jpeg`, `.webp`) and an unambiguous **target screen** in this project.

- **Missing reference(s), missing target screen, or both missing** → STOP immediately. Do NOT load further context, do NOT resolve the worktree decision, do NOT spawn any agent. Respond in the user's language from `preferences.json` naming exactly what is missing, and show usage:

  ```
  /devteam:relayout redesign <screen> following <ref-1.png>, <ref-2.png>
  ```

  If only the target screen is ambiguous (references given, multiple plausible screens/routes match), ask with `AskUserQuestion` (single-select from the candidates found) instead of guessing. If no reference is given, do not proceed on the strength of a description alone — a reference image is mandatory, not optional.

- **Both resolved** → continue below. Resolve every reference to a concrete path and read each one before planning. Resolve the target screen to its concrete feature/route location in the project.

---

## 1. Design context discovery — REQUIRED for every spawned agent

Before proposing or writing any markup, locate this project's design context so the relayout reuses existing patterns instead of inventing new ones:

- **Design system doc** — look in common locations (`docs/design-system.md`, `.claude/docs/ui/design-system.md`, a Storybook config, a Tailwind/theme config) for tokens: color palette, typography, spacing scale, component rules. If none is found, ask the user with `AskUserQuestion` whether to proceed using only inferred conventions from the existing UI code, or to point at the doc.
- **Reusable component library** — locate the project's shared UI primitives directory. Load `skills/shared/reuse-guidelines/SKILL.md` and apply its gate: compose the reference layout from existing primitives first; a new shared component is justified only when nothing existing fits.
- **Feature-local patterns** — inspect the target screen's existing code to match its structure, naming, and state conventions.
- **Quality skills to apply before declaring done:** `skills/shared/frontend-design`, `skills/shared/design-system-audit`, `skills/shared/frontend-code-quality`, `skills/shared/component-patterns`, `skills/shared/css-quality`, `skills/shared/accessibility-patterns`, `skills/shared/mobile-design`, `skills/shared/frontend-done-checklist`.

**Fidelity rule:** the references are the target. The design system defines *how* (tokens, components, spacing); the references define *what* (layout, hierarchy, structure). When a reference detail can be expressed with an existing token/component, use it; only deviate from a reference when it would violate the design system, and surface that trade-off in the plan.

---

## 2. Worktree / Branch

Resolve per the canonical worktree decision cascade in root `CLAUDE.md` and `skills/shared/worktree/SKILL.md` — do not restate it here. If a worktree is set up, isolate any project-specific infra (Docker stack, ports, seeded volumes) per that skill; never touch shared/main infra.

---

## 3. Delegate — spawn the agents

**MANDATORY:** Use the Task tool to delegate. Do NOT handle the relayout in the main context. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

| Phase | Agent | Tier | Role |
|---|---|---|---|
| Visual planning | `ui-ux-designer` | `frontend` | Reads the references, produces the visual spec, maps every region to design-system tokens and existing components, flags conflicts with the design system |
| Implementation | `frontend-developer` | `frontend` | Implements the approved relayout, reusing existing components, verifies the result against each reference (preview/screenshot, responsive + light/dark where applicable) |

Also spawn if the target screen has a mobile counterpart in scope:
- `mobile-developer` — implement the relayout for the mobile platform

Pass to every spawned agent: the resolved reference paths, the target screen path, and the design context from section 1.

Read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`. If `TESTS_REQUIRED=yes` (default), the implementing agent(s) must run the project's existing tests for the touched screen per `skills/shared/scoped-test-execution/SKILL.md`; if `no`, skip and rely on the Phase 4 quality gate below.

---

## 4. PLAN GATE — mandatory for every spawned agent

1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` — including which references map to which screen regions, which existing components will be reused, any new component justified, and the worktree/infra setup — and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS

---

## 5. Post-execution — Automatic review pass

**Trigger:** runs automatically after the relayout is implemented and verified. Do NOT run during the planning phase. Do NOT ask the user for confirmation.

Spawn in parallel:

| Agent | Tier | Scope |
|---|---|---|
| `frontend-reviewer` | `backend-exec` | Files changed this session (`git diff` against base branch): design-system compliance, reuse vs. duplication, re-renders, accessibility, responsive correctness, CSS quality, type safety |
| `qa-specialist` | `backend-exec` | Behavioral validation: fidelity to each reference (pass/fail per reference, not a vague impression), no regression in the screen's flows, edge cases (empty/long-content/error states), responsive + light/dark coverage |

Both agents run independently. Do not wait for one to finish before spawning the other.

**After both complete**, synthesize their findings:

```
## Post-relayout review

### Frontend review findings
[frontend-reviewer output — critical findings only, bullets]

### QA findings
[qa-specialist output — gaps, risks, per-reference fidelity verdict]

### Summary
[1-2 sentences: overall verdict and recommended next step]
```

If both agents report no findings, output exactly:

```
Post-relayout review: no issues found.
```

## Session close (mandatory)

1. **Session summary** — append this session's contribution to today's entry in `.dev-team-agents/user-data/session-summary.md`: one `### <agent-name>` sub-heading per agent that acted, each with **Done** / **Decisions** / **Next**. Create today's entry if none exists; never overwrite another agent's sub-heading.
2. **Hand off** — the working tree is left dirty on purpose. Close with one line naming the next step: `/devteam:commit`, then `/devteam:pr` when the branch is ready for review.
