# Agent Reference

Full list of agents included in Dev Team Agents, their roles, development phases, and assigned models.

---

## Team

| Agent | Role | Phase | Model |
|-------|------|-------|-------|
| `product-analyst` | Closes scope, generates backlog with estimates | DISCOVERY | Opus |
| `software-architect` | Architecture decisions, tech stack, code standards | DISCOVERY + QUALITY GATE | Opus |
| `backend-developer` | Server-side implementation (API + monolith) | DEVELOPMENT | Sonnet |
| `frontend-developer` | Client-side implementation (SPA + templates) | DEVELOPMENT | Sonnet |
| `mobile-developer` | Mobile implementation (React Native, Expo, Flutter, native iOS/Android) | DEVELOPMENT | Sonnet |
| `ui-ux-designer` | Design system, visual consistency, UX (dual mode) | DESIGN + DEVELOPMENT | Sonnet |
| `database-specialist` | Schema design, query optimization, DB selection | DEVELOPMENT | Sonnet |
| `devops-specialist` | Docker, CI/CD, VPS, cloud deployment | DEVELOPMENT | Sonnet |
| `backend-test-specialist` | Backend test coverage (conditional) | DEVELOPMENT | Sonnet |
| `frontend-test-specialist` | Frontend test coverage (conditional) | DEVELOPMENT | Sonnet |
| `code-reviewer` | Routes to specialist reviewer based on diff (backend / frontend / both) | QUALITY GATE | Sonnet |
| `backend-reviewer` | Backend review: API contracts, transactions, N+1, auth, jobs, SOLID | QUALITY GATE | Sonnet |
| `frontend-reviewer` | Frontend review: components, re-renders, a11y, bundle, state, XSS | QUALITY GATE | Sonnet |
| `security-specialist` | OWASP, LGPD/GDPR, dependency CVEs | QUALITY GATE | Opus |
| `qa-specialist` | Behavioral validation, regression risk | QUALITY GATE | Sonnet |
| `technical-writer` | API docs, READMEs, runbooks, changelogs | SUPPORT | Haiku |
| `setup-assistant` | Project setup + version management | SETUP | Sonnet |

---

## Agent Descriptions

### `product-analyst`
Handles scope definition and backlog generation. Works directly with requirements documents, PRDs, or raw user descriptions. Produces sprint-ready backlog items with effort estimates. Iterates through clarification Q&A until scope is 100% closed before committing to estimates.

### `software-architect`
Owns architecture decisions, technology stack selection, and code standards. Produces `architecture.md`, `tech-stack.md`, and `code-standards.md`. Also acts as quality gate — reviews implementation for conformance to established decisions. Creates Architecture Decision Records (ADRs) for hard-to-reverse choices.

### `backend-developer`
Implements server-side logic: REST APIs, monolithic services, background jobs, authentication, and business rules. Reads project context and code standards before writing any code. Asks once whether to isolate work in a git worktree. Defers test coverage to `backend-test-specialist`.

### `frontend-developer`
Implements client-side UI: SPAs, server-rendered templates, component libraries. Works in tandem with `ui-ux-designer` on visual consistency. Reads project stack and design system before starting. Defers test coverage to `frontend-test-specialist`.

### `mobile-developer`
Implements mobile features across React Native, Expo, Flutter, and native iOS/Android. Adapts to platform-specific patterns (HIG for iOS, Material Design for Android). Conditional agent — spawned only when the task involves mobile scope.

### `ui-ux-designer`
Operates in two modes: **design mode** (produces design system docs, component specs, UX flows) and **development mode** (audits implementation against design system and web interface guidelines). Conditional — spawned when the task involves visual or UX decisions.

### `database-specialist`
Handles schema design, query optimization, index strategy, and database selection. Produces migration files and zero-downtime migration plans. Conditional — spawned when the task touches data models or database infrastructure.

### `devops-specialist`
Configures Docker (dev and prod), CI/CD pipelines (GitHub Actions, GitLab CI, Bitbucket, Jenkins), VPS deployments, and cloud infrastructure (AWS, GCP, Azure, Cloudflare). Conditional — spawned when the task involves infrastructure or deployment.

### `backend-test-specialist`
Writes and maintains backend test coverage: unit tests, integration tests, contract tests. Runs after `backend-developer` completes implementation. Applies test strategy and test pyramid skills.

### `frontend-test-specialist`
Writes and maintains frontend test coverage: component tests, visual regression, snapshot testing. Runs after `frontend-developer` completes implementation.

### `code-reviewer`
Entry-point router for `/devteam:review`. Reads the diff, classifies the change scope, and delegates to `backend-reviewer`, `frontend-reviewer`, or both. Synthesizes results into a single review verdict.

### `backend-reviewer`
Deep backend review: API contract correctness, transaction boundaries, N+1 query detection, authentication and authorization, background job safety, SOLID principles.

### `frontend-reviewer`
Deep frontend review: component design, unnecessary re-renders, accessibility (a11y), bundle size impact, state management correctness, XSS surface.

### `security-specialist`
Security-focused audit: OWASP Top 10, LGPD/GDPR compliance, dependency CVE scanning, secret management, supply chain risk. Runs at the quality gate and also as a standalone audit (`/devteam:security`).

### `qa-specialist`
Validates feature behavior against acceptance criteria. Identifies regression risk, missing edge cases, and behavioral gaps. Does not write code — produces a behavioral validation report.

### `technical-writer`
Produces API documentation, READMEs, runbooks, changelogs, and release notes. Assigned Haiku for cost efficiency on structured, low-ambiguity writing tasks.

### `setup-assistant`
Drives the full project setup and refresh flow. Scans existing files, asks about project type, collects configuration, and generates living context docs in `.claude/docs/`. Re-running on an existing project triggers refresh mode — reads git history since the last run and patches only the affected docs.

---

## Design Skills

Two design skills are bundled and linked automatically by the installer:

| Skill | Path | Purpose |
|-------|------|---------|
| `frontend-design` | `skills/design/frontend-design/` | Component patterns, layout techniques, visual design guidance |
| `web-design-guidelines` | `skills/design/web-design-guidelines/` | Audits UI code against Vercel's Web Interface Guidelines |

Both are required for `frontend-developer` and `ui-ux-designer` to work on UI tasks. No extra setup needed — the installer links them automatically.
