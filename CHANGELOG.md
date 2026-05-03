# Changelog

All notable changes to `dev-team-agents` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

## [v1.0.0] — 2026-05-03

### Added

**Agents (14)**
- `product-analyst` — scope closure, backlog generation with estimates, client clarification cycle
- `software-architect` — architecture decisions, tech stack, code standards, quality gate conformance
- `backend-developer` — server-side implementation (decoupled + monolithic architectures)
- `frontend-developer` — client-side implementation (SPA + server-rendered templates), `anthropic-skills:frontend-design` integration
- `ui-ux-designer` — dual-role: Design Mode (pre-build spec) + Consultive Mode (alongside frontend)
- `database-specialist` — schema design, query optimization, covers 15+ databases and managed cloud services
- `devops-specialist` — Docker-first, VPS setup, CI/CD (5 platforms), AWS/GCP/Azure deployment
- `backend-test-specialist` — conditional activation, ROI-driven test authoring
- `frontend-test-specialist` — conditional activation, component/integration/E2E testing
- `code-reviewer` — code quality, SOLID, Object Calisthenics, DRY, race conditions, silent bugs
- `security-specialist` — OWASP Top 10, LGPD/GDPR, dependency CVEs, severity-rated findings
- `qa-specialist` — behavioral validation, regression risk, legacy project handling
- `technical-writer` — Diátaxis framework, Google Style Guide, OpenAPI docs
- `setup-assistant` — project onboarding (3 project types), issue tracker integration (11 platforms), version management

**Skills (18)**
- `shared/project-context` — coexistence and override rule (foundational, used by all agents)
- `shared/conventional-commits` — Conventional Commits 1.0.0
- `shared/adr` — Architecture Decision Records (MADR format)
- `shared/backlog-template` — backlog structure with estimates and dependencies
- `shared/pr-review` — structured PR review checklist and comment format
- `architecture/design-patterns` — GoF patterns, SOLID, DDD patterns, anti-patterns
- `architecture/object-calisthenics` — 9 rules with examples
- `architecture/api-design` — REST and GraphQL design principles
- `testing/test-strategy` — decision framework, coverage targets, AAA pattern
- `testing/test-pyramid` — unit/integration/E2E patterns and tooling
- `security/security-checklist` — OWASP Top 10, LGPD/GDPR, HTTP headers, API security
- `design/design-system-audit` — design system reading, gap analysis, `anthropic-skills:frontend-design` integration
- `devops/docker-dev` — development environment patterns
- `devops/docker-prod` — multi-stage production builds, security hardening
- `devops/vps-linux` — Linux VPS from scratch
- `devops/cicd-github` — GitHub Actions
- `devops/cicd-bitbucket` — Bitbucket Pipelines
- `devops/cicd-gitlab` — GitLab CI/CD
- `devops/cicd-jenkins` — Jenkins declarative pipelines
- `devops/aws` — ECS, ECR, cost-optimized AWS deployment
- `devops/gcp` — Cloud Run, Artifact Registry, cost-optimized GCP deployment
- `devops/azure` — Container Apps, ACR, Managed Identity, cost-optimized Azure

**Workflows**
- `workflows/new-project.md` — Workflow A: new project from scratch
- `workflows/inherited-project.md` — Workflow B: taking over unfinished project (2 sub-scenarios)
- `workflows/maintenance.md` — Workflow C: live project maintenance with issue tracker support
- `workflows/bug-fix.md` — isolated bug fix workflow
- `workflows/security-patch.md` — security vulnerability patch workflow

**Infrastructure**
- `install.sh` — semantic versioning installation with symlinks
- `scripts/check-updates.sh` — session-start hook with 24h TTL
- Coexistence principle: project rules always override base standards
- Immutability warnings in all agents — guides users to extend at project level
