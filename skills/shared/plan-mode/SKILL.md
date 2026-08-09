---
name: plan-mode
description: Plan-before-execute — structured plan, approval, replanning.
---

# Plan Mode — Mandatory Planning Protocol

All `dev-team-agents` operate under a strict **plan-before-execute** discipline. No non-trivial task may be executed without a prior approved plan.

---

## When a Plan Is Required

A plan is required whenever a task involves:

| Category | Examples |
|----------|---------|
| File operations | Creating, modifying, deleting, or moving any file |
| Commands with side effects | Installs, migrations, deploys, cache clears, git operations |
| Architecture or design decisions | Choosing tech stack, defining API contracts, schema design |
| Document generation | Backlog items, sprint plans, ADRs, code standards |
| Multi-step implementations | Any task with 2 or more sequential steps |
| Multi-agent delegations | Any task that spawns one or more subagents |

**A plan is NOT required for:**
- Answering a question
- Explaining or reading existing code
- Showing a file's contents or grep results
- Single-character / single-line typo fixes explicitly requested

When in doubt: **write the plan**.

---

## Plan Format

**Language:** Plans are presented to the user for approval — they are conversation items, not documents. Present plans in the user's preferred language from `.dev-team-agents/user-data/preferences.json` → `language` (default: English).

Load `.dev-team-agents/templates/plan-template.md` and fill it in. That file is the canonical
plan format — this skill does not restate it, so the two cannot drift.

Two rules the template encodes, restated here only because they change how you *execute*:

- The **Par.** column groups steps that can run simultaneously. Steps sharing a letter are sent as
  simultaneous agent prompts in a single message; `---` means the step must wait for the previous one.
- The plan ends with the approval closer. Present it verbatim from the template and then stop.

Plans render as **pure markdown** — no box-drawing characters or decorative symbols, per
`skills/shared/output-format/SKILL.md`.

---

## Approval Protocol

After presenting the plan:

1. **Stop.** Do not execute any step.
2. **Wait** for an explicit approval signal from the user.
3. **Approval signals**: "approved", "go ahead", "proceed", "yes", "looks good", "do it"
4. **Rejection signals**: any feedback, correction, question, or "no"

On **rejection**: acknowledge the feedback, adjust the plan, re-present the full plan. Never partially execute before replanning.

On **approval**: execute steps in order (agents with Execution Strategy Gate enabled MUST present the gate before executing). Report progress after each step. If execution reveals a problem that changes the plan, **stop and replan** before continuing.

---

## Execution Strategy Gate

This optional gate applies between plan approval and execution. When an agent's configuration mandates it, the agent MUST present an interactive quiz after the user approves the plan and before executing any step.

### Trigger

After the user signals approval ("approved", "go ahead", "proceed", "yes", "looks good", "do it"), **before** executing step 1.

### Procedure

1. Read the worktree preferences from `.dev-team-agents/user-data/preferences.json`:
   ```bash
   python3 -c "import json;d=json.load(open('.dev-team-agents/user-data/preferences.json'));print(json.dumps({k:d.get(k) for k in['worktree_active','worktree_base_branch','worktree_path','worktree_docker_isolate']}))" 2>/dev/null
   ```
   If the file is unreadable or keys are absent, assume defaults: `worktree_active=true`, `worktree_base_branch` = auto-detected default, `worktree_path=.worktrees`, `worktree_docker_isolate=true`.

2. Determine the recommended option:
   - `worktree_active == true` → recommend **Isolated worktree** (first option)
   - `worktree_active == false` → recommend **New branch** (second option)
   - key absent → recommend **Isolated worktree** (first option)

3. Present the quiz using the `AskUserQuestion` tool. Use the user's preferred language from `preferences.json` → `language`. The recommended option MUST be the first option with the label showing it is recommended.

   Quiz structure (pt-BR example):
   ```json
   {
     "questions": [
       {
         "question": "Como este plano deve ser executado?",
         "header": "Estratégia",
         "multiSelect": false,
         "options": [
           { "label": "Worktree isolada (Recomendado)", "description": "Criar uma worktree git isolada com base em <base_branch>, em <worktree_path>, com Docker isolado=<sim/nao>" },
           { "label": "Nova branch", "description": "Criar uma nova branch a partir da branch atual e executar nela" },
           { "label": "Branch atual", "description": "Executar diretamente na branch atual, sem alteracoes git" },
           { "label": "Outro", "description": "Especificar outra abordagem manualmente" }
         ]
       }
     ]
   }
   ```
   Translate to the user's language. Dynamically interpolate the actual `worktree_base_branch`, `worktree_path`, and `worktree_docker_isolate` values into the recommended option's description.

4. Options and corresponding actions:

   | User choice | Action |
   |---|---|
   | **Isolated worktree** | Load `skills/shared/worktree/SKILL.md` and follow the full worktree setup flow. Use `worktree_base_branch` as the base, `worktree_path` for the worktree root, and `worktree_docker_isolate` to determine Docker isolation. |
   | **New branch** | Ask for a branch name (suggest `<context>/<brief-title>`), then run `git checkout -b <name>`. Continue executing steps in the new branch. |
   | **Current branch** | Proceed executing steps directly on the current branch with no git changes. |
   | **Other** | Ask the user to describe their desired approach in free text, then adapt accordingly. |

5. Announce the chosen strategy before executing the first step so the user can verify the decision is correct.

---

## Replanning During Execution

If you discover mid-execution that a step cannot be done as planned:

1. Stop immediately.
2. Describe what was found and why the original plan needs to change.
3. Present an updated plan covering only the remaining steps.
4. Wait for approval again before continuing.

**Do not silently improvise.** If the plan changes, the user must know.

---

## Agents Must Self-Enforce

Every agent in `dev-team-agents` is responsible for applying this protocol independently. The plan-mode rule is not optional and is not enforced by an external system — it is part of each agent's operating discipline.

If a user asks an agent to "just do it" without a plan: explain that the plan takes less than a minute to write, protects against misunderstandings, and produces better results. Then write the plan. Never skip it.

---

## Context Self-Monitoring

After any response that involved reading many large files, producing long outputs, or running multiple tool calls in sequence, add a brief context advisory when appropriate:

> ⚡ **Context advisory**: this session has accumulated significant context. If responses start feeling less precise, run `/compact` or start a fresh session before the next task.

Apply this judgment after: reading 5+ files, producing 3+ large tool outputs, or a long back-and-forth session. You cannot see the exact percentage — err toward mentioning it. This supplements the automated hook-based warning, which fires based on a transcript token estimate.
