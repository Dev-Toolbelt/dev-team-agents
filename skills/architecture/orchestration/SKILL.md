---
name: orchestration
description: Delegation mechanics — execution gate, autonomous sprint protocol, agent roster, spawn rules.
---

# Orchestration

Reference material for an agent that plans work and delegates every implementation step to
specialized subagents via the Task tool. The orchestrator never writes implementation code.

---

## Execution Strategy Gate

**Mandatory step between plan approval and execution.** Present it before executing any step.

Load `skills/shared/interaction-patterns/SKILL.md` for the quiz structure.

1. Read worktree preferences:
   ```bash
   python3 -c "import json;d=json.load(open('.dev-team-agents/user-data/preferences.json'));print(json.dumps({k:d.get(k) for k in['worktree_active','worktree_base_branch','worktree_path','worktree_docker_isolate']}))" 2>/dev/null
   ```
   Defaults if unreadable: `worktree_active=true`, `worktree_base_branch` = auto-detected,
   `worktree_path=.dev-team-agents/worktrees`, `worktree_docker_isolate=true`.

2. Determine the recommendation:
   - `worktree_active == true` → **Isolated worktree** (first option)
   - `worktree_active == false` → **New branch** (second option)
   - key absent → **Isolated worktree**

3. Present the quiz via `AskUserQuestion` with 4 options: **Isolated worktree (Recommended)**,
   **New branch**, **Current branch**, **Other**. Translate the labels and descriptions to the
   user's language (`preferences.json` → `language`, default `en`). Interpolate the actual
   `worktree_base_branch`, `worktree_path`, and `worktree_docker_isolate` values into the
   recommended option's description.

4. Act on the choice:
   - **Isolated worktree** → execute the full worktree setup flow (`skills/shared/worktree/SKILL.md`)
   - **New branch** → ask for a branch name, run `git checkout -b <name>`
   - **Current branch** → proceed directly
   - **Other** → ask the user to describe their approach

5. Announce the chosen strategy, then proceed to execution.

---

## Autonomous Sprint Protocol

Activates when the user signals fully autonomous execution — "execute everything autonomously",
"don't ask me", "just tell me when it's done", "autonomous sprint", or equivalent in any language.
In this mode the Execution Strategy Gate quiz is **skipped entirely** — resolve everything silently.

1. **Auto-resolve the worktree** — read `preferences.json` (same command as above) without asking:
   - `worktree_active` is `true` or absent → create an isolated worktree + Docker stack
     (`skills/shared/worktree/SKILL.md`, full setup)
   - `worktree_active` is `false` → create a new branch: suggest a name, `git checkout -b <name>`

2. **Write the session file BEFORE spawning any subagent**:
   ```bash
   echo "worktree=<yes|no> branch=<branch>" > .dev-team-agents/.worktree-session
   ```

3. **Spawn subagents with worktree context** — every Task prompt MUST carry `WORKTREE_PATH=<path>`,
   `BRANCH=<branch>`, and: "All file operations MUST target the WORKTREE_PATH. Do NOT write files
   in the main repo root."

4. **Automatic review cycle** — after all implementation subagents finish, spawn `code-reviewer`
   then `qa-specialist`. Resolve any findings in a new round autonomously; do not ask the user.

5. **Final notification** — notify only when implementation, review, QA, and the consolidated
   summary are all complete.

> **Critical**: subagents have no shell access and cannot create worktrees or branches. The
> worktree/branch MUST exist in the orchestrator's context before any subagent is spawned, and the
> path MUST be passed in every spawn prompt.

---

## Agent Roster

Each agent's model is resolved from its tier plus the active provider at runtime
(`.dev-team-agents/scripts/lib/tiers.json`). The subagent auto-announces its model via the
model-identity skill — the orchestrator never names a model.

| Agent | Tier | Role |
|---|---|---|
| `backend-developer` | `backend-exec` | Server-side implementation |
| `frontend-developer` | `frontend` | Client-side implementation |
| `mobile-developer` | `backend-exec` | Mobile implementation |
| `database-specialist` | `backend-exec` | Schema, queries, migrations |
| `devops-specialist` | `backend-exec` | Docker, CI/CD, deploy |
| `security-specialist` | `reasoning` | Security audit, compliance |
| `backend-test-specialist` | `repetitive` | Backend test coverage |
| `frontend-test-specialist` | `frontend` | Frontend test coverage |
| `code-reviewer` | `backend-exec` | Code review routing |
| `backend-reviewer` | `backend-exec` | Backend PR review |
| `frontend-reviewer` | `frontend` | Frontend PR review |
| `qa-specialist` | `backend-exec` | Behavioral validation |
| `technical-writer` | `repetitive` | Documentation |
| `product-analyst` | `reasoning` | Business requirements |
| `ui-ux-designer` | `frontend` | Design system, UX |

Canonical agent path: `.claude/agents/dev-team/<agent-name>.md` for every row above.

---

## Orchestration Flow

1. **Classify the scope**:

   | Scope | Delegate to |
   |---|---|
   | API, services, business logic | `backend-developer` |
   | UI, components, pages | `frontend-developer` |
   | Backend + frontend | both of the above |
   | Schema, migrations, queries | `database-specialist` |
   | Mobile (native or cross-platform) | `mobile-developer` |
   | Docker, CI/CD, deploy | `devops-specialist` |
   | Auth, encryption, compliance | `security-specialist` |
   | Tests (after implementation) | `backend-test-specialist` / `frontend-test-specialist` |

   If the scope is unclear, ask the user which areas to delegate.

2. **Spawn via the Task tool.** Each prompt must include: the task description from the closed
   scope; `WORKTREE_PATH=<path>` and `BRANCH=<branch>`; references to `docs/development/`
   (`architecture.md`, `tech-stack.md`, `code-standards.md`) and any relevant ADR; and the
   instruction: "Read the architecture documents before implementing, then load
   `skills/shared/model-identity/SKILL.md` and announce your model. All file operations MUST target
   WORKTREE_PATH — never write files outside this directory."

3. **Spawning rules:**
   - Agents with no dependency on each other MUST be spawned in **parallel**
   - Schema before backend: `database-specialist` completes before `backend-developer` starts
   - Tests run after their implementation agent completes
   - Log what each agent did as it completes; capture output for the summary

4. **Consolidated summary** after all agents complete:

   ```markdown
   ## Implementation Complete

   ### Agents spawned
   [list of agents and what they did]

   ### Documents produced / modified
   [list]

   ### Next steps
   Run `/devteam:review` for code review and QA handoff.
   ```
