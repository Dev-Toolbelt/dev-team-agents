---
name: dependency-audit
description: Running the right security scanners for the detected stack — secrets, SAST, deps, images.
---

# Dependency & Secret Audit — Scanner Selection

Purpose: given a repository, decide **which scanners to actually run** and how to report what they find. Detection first — a single-language project should run two or three commands, not nine.

Depth beyond execution lives elsewhere:

| Need | Skill |
|------|-------|
| CVE triage, severity SLAs, update strategy | `skills/security/dependency-vulnerabilities/SKILL.md` |
| Wiring SAST into CI with thresholds | `skills/security/sast-pipeline/SKILL.md` |
| Typosquatting, action pinning, dependency confusion | `skills/security/supply-chain/SKILL.md` |
| Storing and rotating secrets | `skills/security/secret-management/SKILL.md` |

---

## Step 1 — Always Run (Any Repository)

| Goal | Command | Notes |
|------|---------|-------|
| Secrets in git history | `gitleaks detect --source . --log-opts="HEAD~50..HEAD"` | Widen the range for a first full audit (`--log-opts=""`) |
| Secrets, alternative engine | `trufflehog git file://. --since-commit HEAD~50` | Verifies live credentials; slower — use when gitleaks reports candidates |
| Broad SAST | `semgrep --config=auto .` | Language-agnostic; the `auto` ruleset resolves per detected language |

**A secret removed from current code but still present in git history is a live exposure — rotate it.** Deleting the line does not revoke the credential.

---

## Step 2 — Ecosystem Detection → Dependency Scanner

Run only the rows whose signal is present.

| Signal in repo | Ecosystem | Command |
|----------------|-----------|---------|
| `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` | Node.js | `npm audit --audit-level=high` (or `pnpm audit` / `yarn npm audit`) |
| `composer.lock` | PHP | `composer audit` |
| `requirements.txt`, `poetry.lock`, `Pipfile.lock`, `pyproject.toml` | Python | `pip-audit` |
| `Gemfile.lock` | Ruby | `bundle audit check --update` |
| `go.sum` | Go | `govulncheck ./...` |
| `Cargo.lock` | Rust | `cargo audit` |
| `pom.xml`, `build.gradle` | Java | OWASP Dependency-Check plugin |
| `*.csproj`, `packages.lock.json` | .NET | `dotnet list package --vulnerable` |
| Any of the above, org uses a SaaS scanner | Multi | `snyk test` — only if the project already has Snyk configured |

If a manifest exists without a lockfile, say so in the report: results are approximate and the build is not reproducible.

---

## Step 3 — Language-Specific SAST (Add Only If Present)

| Signal | Scanner | Command |
|--------|---------|---------|
| `*.py` files | Bandit | `bandit -r . -ll` |
| `Dockerfile`, `*.tf`, `*.yaml` manifests | Trivy config scan | `trivy config .` |
| Built container image | Trivy image scan | `trivy image <image>:<tag>` |
| `sonar-project.properties` / `SONAR_TOKEN` | SonarQube SAST | See `skills/devops/sonarqube/SKILL.md` — complements, does not replace, the scanners above |

---

## Step 4 — Handle Missing Tools

- A scanner that is not installed is **not** a passing result. Report it as `NOT RUN` with the install hint; never conclude "no vulnerabilities found" from a missing binary.
- Prefer a runner that needs no install where one exists (`npx`, `uvx`, `docker run`) before asking the user to install anything.
- Never bypass a failing audit with a force/ignore flag to make a build pass.

---

## Reporting Thresholds

| Finding | Report as |
|---------|-----------|
| HIGH or CRITICAL CVE in a **direct** dependency | Flag — blocking |
| CRITICAL CVE in a **transitive** dependency | Flag — blocking |
| HIGH in a transitive dependency | Note it; escalate only if the vulnerable path is reachable |
| MEDIUM / LOW anywhere | Batch into routine updates |
| Any secret found in history | Flag — blocking; rotation required, not just removal |
| Scanner unavailable | `NOT RUN` — explicitly listed, never silently omitted |

Before downgrading any severity, apply the reachability triage in `skills/security/dependency-vulnerabilities/SKILL.md` and record the reasoning.

---

## Output Discipline

- Summarize counts and the blocking findings — do not paste full scanner output into the response.
- Cite package name, installed version, fixed version, and CVE id for each blocking finding.
- Recommend the smallest upgrade that clears the finding; flag major-version bumps as needing manual review.
