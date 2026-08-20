---
description: Deep-dive a module or area — bugs, test gaps, security, infra, and a plan
argument-hint: <module or area>
---

Load `skills/shared/current-context/SKILL.md` and restrict all work to the active branch/worktree scope unless $ARGUMENTS requests broader. Load `skills/shared/interaction-patterns/SKILL.md` and use `AskUserQuestion` for every question with a finite set of answers — never a plain-text prompt.

**Agent base path:** `.claude/agents/dev-team/` — the agents named below all live there, one file per agent name; spawn each by name with the Task tool.

Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.

---

You are running the **`/devteam:audit`** command.

**Purpose:** Deep analysis of a specific module/area across the entire codebase (frontend, backend, infrastructure). Finds silent bugs, critical routines needing test coverage, edge cases, high-value fixes (no overengineering), security issues, and infra improvements. Produces a consolidated improvement plan saved to `docs/audit/`.

**Observational Analysis Principle:** The audit is a diagnostic — it analyzes the software as it currently behaves. Agents must NOT propose changes that alter existing business logic, introduce new business rules, or modify the intended behavior of the system. Findings must be grounded in the current codebase context: bugs, missing guards, security gaps, and quality issues that exist today. If a finding requires inventing a new business rule or changing what the software is supposed to do, it is out of scope.

---

## Step 0 — Resolve audit target

If `$ARGUMENTS` already names a target (e.g., `auth`, `billing`, `notifications`, `search`, `api`, `admin`), use it as `<module>` and skip this step.

If `$ARGUMENTS` is **empty**, ask the user with `AskUserQuestion` (single-select with "Other" option for free-text):

> "Which module/area should I audit?"

Offer a few generic examples as options (`auth`, `api`, `database`, `notifications`, `search`, `admin`) or let them type a custom area.

Once resolved, store the target as `<module>`.

---

## Step 1 — Scope guard

If `<module>` is vague ("tudo", "all", "everything", "codebase", "projeto inteiro"), state in one line that this scope may take a long time and consume a significant number of tokens, then ask with `AskUserQuestion` (single-select): **Module by module** (recommended — a checkpoint between each), **All at once**, or **Cancel**.

Do NOT proceed until the user answers.

---

## Step 2 — Worktree + isolated infra

Read `.dev-team-agents/.worktree-session`:

- If the file exists and contains a decision (`worktree=no` or `worktree=yes branch=<b>`), follow it silently.
- If absent, ask once with `AskUserQuestion` (single-select, in the user's language): **Isolated worktree** — dedicated worktree plus an isolated infrastructure stack — or **New branch** — a new branch in the current checkout.

If **worktree** is selected:
1. Load `skills/shared/worktree/SKILL.md` and follow the full protocol.
2. Context name: `audit/<module>`.
3. After worktree creation, spin up an isolated Docker stack following the worktree's docker-isolation references.

If **branch** is selected:
1. Create a new branch: `audit/<module>` from the detected base branch.
2. Work directly in the main checkout.

Write the decision to `.dev-team-agents/.worktree-session` if not already present.

---

## Step 3 — Explore module structure

Spawn an `explore` agent via the Task tool to map the module's code footprint:

```
Subagent type: explore
Task: Thoroughly explore all code related to the module "<module>" in this project.
Search broadly across the entire project — controllers, models, services, routes, components, pages, hooks, utilities, tests, database migrations, config files.
Detect the project structure first (monorepo? flat? SPA + API? MVC?) and adapt the search accordingly.
Return:
- List of all relevant files with their paths (organized by layer: backend / frontend / database / config)
- Brief description of each file's role
- Key classes/functions/types exported
- Any existing test files and their type (unit, integration, e2e)
- Database tables involved (if any)
- API routes/endpoints involved (if any)
- Architecture pattern detected (e.g., MVC, DDD, layered, serverless)
```

Wait for the exploration result before proceeding.

---

## Step 4 — Spawn analysis agents

**MANDATORY:** Use the Task tool to spawn the agents below in parallel. Do NOT analyze inline — always delegate. The only exception is if the user explicitly asks not to use agents.

Every Task spawn prompt below MUST end with, verbatim: "Before your last paragraph, emit your run-banner table under **Ran on:** exactly as defined in your agent file's `<!-- run-banner -->` block — this is not optional. Then close with a concise report only: files changed (paths, no diffs), key decisions and why, and anything the user must know. Do not paste full file contents, command logs, or a play-by-play of intermediate steps."

### Phase 4a — Module analysis (spawn all in parallel)

1. **`backend-developer`**
   Scope: `<module>` backend code.
   Analyze for:
   - Silent bugs (unhandled nulls, type mismatches, race conditions, missing transactions, incorrect error handling)
   - Critical routines lacking test coverage
   - Edge cases not handled (empty states, boundary values, concurrency, malformed input)
   - High-value fixes that don't require overengineering
   - Code that should exist but doesn't (missing validation, missing authorization checks, missing logging for critical paths)

2. **`frontend-developer`**
   Scope: `<module>` frontend code.
   Analyze for:
   - Silent bugs (unhandled loading/error states, stale closures, race conditions in useEffect, missing key props, incorrect optimistic updates)
   - Critical routines lacking test coverage
   - Edge cases not handled (empty lists, network errors, expired sessions, concurrent edits)
   - High-value fixes
   - Missing loading skeletons, error boundaries, or empty states

3. **`security-specialist`**
   Scope: `<module>` across the entire stack.
   Analyze for:
   - OWASP Top 10 / OWASP API Security Top 10 issues (IDOR, injection, broken auth, excessive data exposure, mass assignment, missing rate limiting)
   - LGPD/GDPR compliance gaps in the module
   - Hardcoded secrets, debug endpoints, overly permissive CORS
   - Missing input sanitization or authorization gates

4. **`devops-specialist`**
   Scope: `<module>` impact on infrastructure.
   Analyze for:
   - Missing or inadequate monitoring/alerting for the module's critical paths
   - Database query patterns that could cause performance issues at scale
   - Caching opportunities (Redis, CDN, HTTP caching)
   - Deployment considerations (migrations, seeders, environment config)
    - Docker/resource concerns specific to the module

> **Relevance rule (applies to all agents above):** Report ONLY findings that would realistically cause production issues, user-facing bugs, data loss, security breaches, or significant maintenance pain. Exclude cosmetic issues, theoretical edge cases requiring impossible preconditions, minor style deviations, and items that "could be improved" without concrete impact. For each finding, state in one sentence why it matters. If you can't articulate real impact — omit it.

> **Observational constraint (applies to all agents above):** Analyze the module based strictly on its current behavior and context. Do NOT propose fixes that introduce new business rules, change existing business logic, or alter the intended behavior of the system. Fixes must address bugs, missing guards, security gaps, or quality issues — not redesign what the software does. If a fix would require deciding what the software "should" do beyond what it currently does, flag it as out of scope instead.

Each agent receives the exploration results from Step 3 as context.

### Phase 4b — Test coverage (conditional)

After Phase 4a completes, check the test gate:
Read the project's `CLAUDE.md` → `## dev-team-agents` section → `TESTS_REQUIRED`. Spawn the test-specialist(s) below **only if `TESTS_REQUIRED=yes`** (or the key is absent — default to running tests). If `TESTS_REQUIRED=no`, **skip this phase entirely**.

- **`backend-test-specialist`** — analyze test gaps and propose tests for the critical backend routines identified in Phase 4a. Do NOT write tests — only identify what should be tested and suggest test scenarios (including edge cases).
- **`frontend-test-specialist`** — same for frontend code.

---

## Step 5 — Synthesize improvement plan

Once all agents from Phase 4 complete, synthesize their findings into a single curated improvement plan. De-duplicate related issues, merge items that describe the same root cause, and discard any finding that doesn't meet the relevance bar from Phase 4a. Discard any finding that proposes new business rules or changes to existing business logic — the audit is observational, not prescriptive. The final report should be shorter than the sum of its parts — every item must justify its inclusion.

Output format (pure markdown, no box-drawing Unicode, no decorative symbols):

```
## Audit Report: <module>

### Scope
<files explored, architecture pattern, brief summary>

### Critical Issues
| # | Severity | Layer | Description | Suggested Fix |
|---|----------|-------|-------------|---------------|
| 1 | high/med/low | BE/FE/Both | <issue> | <fix> |

### Security Findings
<from security-specialist>

### Infrastructure Findings
<from devops-specialist>

### Test Coverage Gaps
| Priority | Routine/Component | Why It Needs Tests | Suggested Scenarios |
|----------|-------------------|--------------------|--------------------|

### Improvement Plan (ordered by value)
1. <item> — <why it matters> — <effort estimate>
2. <item> — <why it matters> — <effort estimate>
...

### Recommended Next Steps
- <actionable recommendation>
```

Then:

1. Write the report to `docs/audit/<module>-audit-YYYY-MM-DD.md` (create `docs/audit/` if it doesn't exist).
   - Use `<module>` in lowercase, hyphens for spaces.
   - Example: audit of module `Billing` → `docs/audit/billing-audit-2026-07-27.md`.
2. Present the report to the user and ask with `AskUserQuestion` (single-select): **Implement the plan now**, **Implement selected items** (then ask which), or **Report only**.
3. Nudge `/devteam:learn` per the merge.md Step 4 marker check (`.dev-team-agents/.learn-last-run`) — this report is a finalization signal even on **Report only**.

---

**PLAN GATE:** Steps 3 and 4 are read-only exploration/analysis — the agents there report findings, they do not touch files, so no plan-and-wait cycle applies to them. The gate applies only when the user picks **Implement the plan now** or **Implement selected items** in Step 5:
1. Read `.dev-team-agents/user-data/preferences.json` → `language` field (default: `en`). Use that language for all responses, plans, and questions directed at the user.
2. Present a structured plan following `skills/shared/plan-mode/SKILL.md` and wait for explicit user approval before executing any file operation, command, or decision.
3. Do not execute and then explain — plan first, execute second. If the user says "just do it": write the plan anyway, explain it protects both parties, and wait for approval.

Task: $ARGUMENTS
