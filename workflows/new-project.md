# Workflow A — New Project from Scratch

Use this workflow when starting a project with no existing codebase.

> **Plan Mode**: every agent step below will present a structured plan for your approval before executing anything. You review, adjust if needed, and approve. Nothing runs until you say so.

---

## Pre-requisite: Input Document

Before starting, provide a markdown document with as much business information as possible. No specific format is required — write what you know. The more detail you provide, the fewer clarification rounds the team needs.

**Suggested content:**
- What problem does this product solve?
- Who are the target users?
- What are the main features and capabilities?
- What are the business rules and validations?
- Are there any technical constraints? (must integrate with X, must use Y database, must be mobile-first)
- Are there compliance or regulatory requirements? (LGPD, GDPR, PCI, etc.)
- What are the known non-goals for this phase?
- Are there deadlines or budget constraints?
- What does success look like at launch?

Save this document anywhere and hand it to the `product-analyst`.

---

## Phase 1: DISCOVERY

### 1.1 — Scope Closure (product-analyst)

```
Prompt: "I have a requirements document for a new project. [paste document or attach file]
         Please analyze it as the product-analyst and close the scope."
```

The `product-analyst` will:
- Present a plan covering: gap identification, question generation, iteration cycle
- After approval: identify scope gaps, missing validations, and ambiguous rules
- Generate clarification questions (formatted for the client if needed)
- Iterate until scope is 100% closed
- Produce `.claude/docs/backlog/` with overview, epics, DoD, and sprint plans with estimates

All backlog documents are generated in **English**.

### 1.2 — Architecture Definition (software-architect)

```
Prompt: "The scope is closed. As the software-architect, review the backlog in
         .claude/docs/backlog/ and define the architecture for this project."
```

The `software-architect` will:
- Present a plan covering: architectural decisions, tech stack choices, standards to define
- After approval: decide architecture, tech stack, patterns, and code standards
- Optionally collaborate with `database-specialist` for data decisions
- Produce `.claude/docs/development/` with all technical decisions documented in English

---

## Phase 2: DESIGN (optional — projects with custom UI)

```
Prompt: "As the ui-ux-designer in Design Mode, create the design system and
         visual specifications for this project based on [brief description of product]."
```

The `ui-ux-designer` will:
- Present a plan covering: design system structure, component inventory, visual spec format
- After approval: produce `.claude/docs/design/design-system.md` in English

---

## Phase 3: DEVELOPMENT

Agents work from `.claude/docs/development/` and `.claude/docs/backlog/` as their source of truth.

### Environment Setup (devops-specialist)

```
Prompt: "As the devops-specialist, set up the development environment for this project.
         Stack: [refer to .claude/docs/development/tech-stack.md]"
```

The `devops-specialist` will present a plan (Dockerfile, compose, CI config) and wait for approval before creating any file.

### Backend Implementation (backend-developer)

```
Prompt: "As the backend-developer, implement [TASK-XXX from sprint-01.md].
         Follow the architecture in .claude/docs/development/"
```

The `backend-developer` will present a plan (files to create/modify, approach, risks) and wait for approval before writing code.

### Frontend Implementation (frontend-developer)

```
Prompt: "As the frontend-developer, implement [feature/component].
         Follow the design system in .claude/docs/design/ and the architecture in .claude/docs/development/"
```

The `frontend-developer` will present a plan and wait for approval before writing code.

### Tests (backend-test-specialist / frontend-test-specialist)

Activate only if `TESTS_REQUIRED: yes` in CLAUDE.md:

```
Prompt: "As the backend-test-specialist, write tests for the [feature] just implemented."
```

The test specialist will present a plan (which cases, which files, approach) and wait for approval.

---

## Phase 4: QUALITY GATE

Run in sequence or parallel depending on available capacity:

```
Prompt: "As the code-reviewer, review the changes in [files/PR].
         Use .claude/docs/development/code-standards.md as the review guide."

Prompt: "As the security-specialist, run a security review on [files/PR]."

Prompt: "As the qa-specialist, validate that [feature] meets its acceptance criteria
         in .claude/docs/backlog/sprint-01.md"

Prompt: "As the software-architect, validate that [files/PR] conforms to the
         architecture decisions in .claude/docs/development/architecture.md"
```

Quality gate agents present their findings as a structured report — no plan required, but findings are explicit before any remediation steps are taken.

---

## Coexistence Reminder

All agents read the project's own context first. Project-specific rules in `CLAUDE.md`, `README.md`, or `AGENTS.md` always take precedence over base agent standards. The base standards fill gaps — the project rules define the ceiling.
