---
name: secret-management
description: Secret management patterns — environment variables, vaults, rotation, and preventing secrets in code or logs.
---

## Never-Do Table

| Anti-pattern | Why it's dangerous |
|---|---|
| Hardcode secrets in source code | Committed to git history; visible to anyone with repo access |
| Commit `.env` files with real values | Permanent exposure even after deletion (git history) |
| Log secrets (even partially) | Log aggregators, third-party services, and crash reports may store them |
| Use the same secret across environments | Dev breach compromises production |
| Pass secrets as CLI arguments | Visible in process list (`ps aux`), shell history |
| Store in environment variables of public CI runs | Forked PR pipelines can exfiltrate them |

---

## Detecting Secrets Already in Git History

```bash
# Scan full history for common secret patterns
git log --all -S "sk-" --oneline          # OpenAI keys
git log --all -S "AKIA" --oneline         # AWS access keys
git log --all -S "ghp_" --oneline         # GitHub tokens
git log --all -S "password" --oneline     # Generic passwords

# Use trufflehog for deeper scanning
trufflehog git file://. --only-verified

# Use gitleaks
gitleaks detect --source . --log-level warn
```

If a secret is found in history: **rotate it immediately**, then use `git filter-repo` or BFG to purge — but assume the secret is already compromised.

---

## Vault Options

| Tool | When to use |
|---|---|
| **HashiCorp Vault** | Self-hosted; complex access policies; dynamic secrets; multi-cloud |
| **AWS Secrets Manager** | AWS-native workloads; built-in rotation for RDS/Redshift/DocumentDB |
| **GCP Secret Manager** | GCP-native workloads; IAM-controlled access; regional replication |
| **Azure Key Vault** | Azure-native workloads; HSM-backed secrets; certificate management |
| **Doppler / Infisical** | SaaS option; easy local dev sync; team-friendly; multi-cloud |
| **1Password Secrets Automation** | Teams already using 1Password; low operational overhead |

**Prefer managed services** (AWS/GCP/Azure) when already in that cloud — less infra to maintain and automatic audit trails.

---

## Rotation Policy

| Secret Type | Rotation Frequency | Rotate Immediately If |
|---|---|---|
| Application secrets (JWT, API keys) | Every 90 days | Suspected exposure or team member offboarding |
| Database credentials | Every 90 days | Developer leaves or breach suspected |
| Infrastructure credentials (cloud IAM) | Every 30 days | Any security incident |
| Service-to-service tokens | Every 30 days | Service is decommissioned |
| Human user passwords | Every 180 days | Phishing, breach notification, or MFA reset |

**Rotate immediately** on any confirmed or suspected exposure — do not wait for the scheduled cycle.

---

## Environment Variable Rules

- `.env` — real values, **never committed**; add to `.gitignore`
- `.env.example` — template with placeholder values, **always committed**
- `.env.test` — test-only values (no production secrets); can be committed if values are non-sensitive stubs
- CI/CD — use the platform secret store (GitHub Actions secrets, GitLab CI variables, Doppler integration)

**.gitignore minimum:**
```
.env
.env.local
.env.*.local
*.pem
*.key
secrets/
```

**Loading pattern (12-factor):**
```python
import os
from dotenv import load_dotenv  # dev only

load_dotenv()  # no-op in production where env vars come from the platform

DATABASE_URL = os.environ["DATABASE_URL"]  # fail fast if missing
```

---

## Checklist

- [ ] No secrets in source code, config files, or SQL migrations
- [ ] `.env` is in `.gitignore`; `.env.example` is committed with placeholders
- [ ] CI/CD secrets stored in platform secret store, not in workflow files
- [ ] Rotation schedule documented and assigned
- [ ] Secret scanning (trufflehog/gitleaks) runs in pre-commit or CI
