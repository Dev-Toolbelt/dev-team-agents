---
name: cicd-base
description: Shared CI/CD — stages, quality gates, secret management, rollback.
---

## Standard Pipeline Stages

Stages run in this order. Each stage must pass before the next begins.

| # | Stage | Purpose | Fails on |
|---|-------|---------|----------|
| 1 | `lint` | Code style and static analysis | Any lint error |
| 2 | `test` | Unit + integration tests with coverage report | Test failure or coverage below threshold |
| 3 | `security-scan` | SAST + dependency vulnerability check (OWASP) | HIGH or CRITICAL findings |
| 4 | `build` | Compile / bundle / containerize | Build error |
| 5 | `publish` | Push artifact/image to registry | Registry error — runs only on `main`/release branches |
| 6 | `deploy-staging` | Deploy to staging environment | Deploy failure — auto, after publish |
| 7 | `smoke-test` | Automated smoke tests against staging | Any smoke test failure |
| 8 | `deploy-prod` | Deploy to production | Manual gate, or auto on semver tag |

> Platform-specific skills (`cicd-github`, `cicd-gitlab`, `cicd-bitbucket`, `cicd-jenkins`) map these stages to their native primitives. This file defines the intent — the platform skill defines the syntax.

---

## Quality Gate Pattern

- All stages 1–4 must pass before any deploy stage (`publish`, `deploy-staging`, `deploy-prod`) runs
- **Coverage threshold**: default ≥ 80% line coverage; blocks on failure
- **Security threshold**: `HIGH` or `CRITICAL` severity findings block the pipeline; `MEDIUM`/`LOW` produce warnings only
- Never deploy from a branch that has failing checks

---

## Project Rule Lint

When `docs/development/reuse-guidelines.md` exists, the `lint` stage also enforces it (`skills/shared/reuse-guidelines/SKILL.md`). Without this step the registry is enforced only by the Stop hook, i.e. only for changes an agent made.

- `.dev-team-agents/scripts/reuse-lint.sh` is a bind artifact and is not committed, so a CI checkout does not have it. Commit a copy at `scripts/ci/reuse-lint.sh` — it is self-contained bash with no dependencies — and note in the copy's first comment line which dev-team-agents version it came from
- Fetch the base branch first (`fetch-depth: 0` or equivalent) and set `REUSE_LINT_DIFF_RANGE=origin/<base>...HEAD`; a shallow clone has no merge base and the lint would only see the working tree
- Blocking findings fail the stage (exit 1); advisory findings print and pass
- Run `reuse-lint.sh --validate` in the same step, so a registry row that stopped compiling fails CI instead of silently matching nothing
- A pull request controls its own head: run the step on `pull_request` (never `pull_request_target` or its equivalents), read-only permissions, no secrets; read the registry and the script from the base ref (`git show origin/<base>:docs/development/reuse-guidelines.md`) or put both under CODEOWNERS; pass the base branch through an environment variable, never interpolated into the shell command

---

## Secret Management

- Never hardcode secrets in pipeline config files — treat the pipeline config as public
- Use the platform's native secret store:
  - GitHub Actions → Repository/Organization Secrets
  - GitLab CI → CI/CD Variables (masked + protected)
  - Bitbucket Pipelines → Repository/Deployment Variables
  - Jenkins → Credentials Store (with the Credentials Binding plugin)
- Rotate secrets on a defined schedule (quarterly minimum)
- Revoke secrets immediately on team member offboarding
- Reference secrets by name only in config; never echo or log their values

---

## Artifact Strategy

| Rule | Detail |
|------|--------|
| **Tagging** | Tag images with git SHA for every build; add semver tag when on a release branch |
| **Retention** | Keep last 10 builds; prune older artifacts automatically |
| **Immutability** | Never redeploy a mutable `latest` tag to production — always use a pinned SHA or semver |
| **Registry** | Push to a private registry; do not rely on Docker Hub for production images |

---

## Rollback

- Every `deploy-staging` and `deploy-prod` stage must have a documented rollback step
- Prefer **blue/green** or **canary** over in-place deploys for zero-downtime rollback capability
- Rollback triggers:
  - Smoke tests fail after staging deploy → auto-rollback to previous artifact
  - Manual trigger by on-call engineer for production
- Store the last successful artifact reference so rollback does not require a rebuild
