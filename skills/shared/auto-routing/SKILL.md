---
name: auto-routing
description: CLAUDE.md devteam section — opt-out rules and auto-routing triggers.
---

## Instruction-File Template — `## dev-team-agents` Section

Append this block to every installed provider's instruction file — `CLAUDE.md` for Claude Code, `AGENTS.md` for Codex and opencode — with the values from the setup Q&A. The text is identical in both files: agents are named, never addressed by a provider path.

The block is loaded on **every turn** of every session, so it carries only what the main conversation needs to route: config keys commands read (`TESTS_REQUIRED`, …), the opt-out, and one trigger line per agent. Each agent's own `description` carries its full scope. Keep it at 50 lines or fewer, fences included — `tests/test_planning_routing.py` enforces the budget.

```markdown
## dev-team-agents
<!-- devteam:routing v3 -->

PROJECT_TYPE: [new|inherited|maintenance]
TESTS_REQUIRED: [yes|no]
CICD_PLATFORM: [github-actions|bitbucket|gitlab|jenkins|other]
GRAPHIFY: [enabled|disabled]
BACKLOG_LOCATION: [local|github-issues|gitlab-issues|jira|linear|clickup|other]
CLOUD_PROVIDER: [aws|gcp|azure|vps|none]
ISSUE_TRACKER: [none|github-projects|jira|linear|clickup|trello|other]
ISSUE_TRACKER_ACCESS: read-only
INACTIVE_AGENTS: [none|comma-separated agent names]

**Opt-out:** a message prefixed `Without agents:`, `Skip routing:` or `No agents:` is handled directly, with no sub-agent. `AUTO_ROUTING: disabled` in this section turns routing off. Never spawn an agent listed in `INACTIVE_AGENTS` — handle that scope directly.

### Auto-Routing: Planning

<!-- devteam:planning-routing v2 -->
**MANDATORY:** a planning request is handled **exactly as the devteam `plan` command** — run it with the user's message as its task: `/devteam:plan` on Claude Code and opencode, `$devteam-plan` on Codex. That command is the only definition of the planning flow (who leads, when `software-architect` joins, who relays questions); do not plan inline or spawn planning agents yourself. Planning means: a plan or plan mode, "how should we build/implement", feature design, task breakdown, backlog, scope, requirements, PRD, spec, user stories or acceptance criteria; ambiguous business rules; a multi-agent task; a new system. A **purely technical decision** with closed scope (ADR, trade-off, architecture, "should we use X", "what's the best way to") goes to `architect` (`/devteam:architect`, `$devteam-architect`); a database-engine or data-model choice to `dba` (`/devteam:dba`, `$devteam-dba`). Execution begins only after the user approves the plan.

### Auto-Routing: Execution

**MANDATORY** (unless opted out, and skipping `INACTIVE_AGENTS`): spawn the agent whose scope matches for every implementation task — never write code in the main context. Independent scopes run in parallel. Each agent's description holds its full scope; the triggers below are the short form.

| Agent | Route when the task is about |
|---|---|
| `backend-developer` | server-side code: API, service, domain, auth, jobs, queues, webhooks, integrations |
| `frontend-developer` | UI code: components, pages, forms, client state, styles, accessibility |
| `ui-ux-designer` | design system, tokens, typography, UX flows, visual consistency — consultive alongside `frontend-developer` on visual decisions |
| `database-specialist` | schema, migrations, queries, indexes, data model, caching layer |
| `devops-specialist` | containers, CI/CD, deploy, infrastructure as code, cloud, monitoring |

### Auto-Routing: Quality Gate

**MANDATORY** (unless opted out, and skipping `INACTIVE_AGENTS`): after an execution agent finishes, spawn the matching quality-gate agents.

| Agent | Spawn when |
|---|---|
| `backend-test-specialist` / `frontend-test-specialist` | `TESTS_REQUIRED=yes` after backend / frontend work, or tests are requested |
| `code-reviewer` | a review is requested, or before merging — it routes to the backend/frontend reviewers |
| `security-specialist` | a security review is requested, or a release touches auth, payments or user data |
| `qa-specialist` | behavior must be validated against acceptance criteria, after implementation |
| `technical-writer` | documentation is requested, or after a significant change ships |

All generated documents are in English unless a document says otherwise.
```
