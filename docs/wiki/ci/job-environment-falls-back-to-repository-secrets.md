# A job's `environment:` falls back to repository secrets of the same name

**Origin:** Windows signing sandbox workflow and the reusable `windows-cli.yml` release job (ADR-0055) | 2026-10-31
**Tags:** GitHub Actions, environment secrets, repository secrets, environment:, sandbox, WIN_ESIGNER_SANDBOX, workflow_call, reusable workflow, secrets inherit

> When a job sets `environment:`, a secret the environment does not define silently resolves to the repository secret of the same name. A sandbox environment that reuses production secret names can sign with production credentials when one sandbox secret is missing.

---

## How it works

1. A job with `environment: <name>` reads secrets from that environment first.
2. A secret missing from the environment resolves to the repository-level secret with the same name. No error is raised.
3. In a reusable workflow, a job-level `environment:` makes its environment secrets win over the secrets the caller passes.

## Rules

| Rule | Why |
|------|-----|
| Give sandbox secrets their own names, `WIN_ESIGNER_SANDBOX_*` | A shared name lets a missing sandbox secret fall through to the production value |
| Map sandbox secrets to the names the signing step reads, inside that step | The step sees one set of names, and the sandbox values come only from the sandbox names |

## Gotchas

- An environment does not isolate a secret that also exists at repository level. Check that every sandbox secret exists in the environment before a run.

## References

- `.github/workflows/windows-signing-sandbox.yml`
- `.github/workflows/windows-cli.yml`
