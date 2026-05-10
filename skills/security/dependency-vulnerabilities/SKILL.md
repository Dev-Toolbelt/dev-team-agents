---
name: dependency-vulnerabilities
description: Dependency vulnerability management — scanning tools, CVE triage, update strategy, and supply chain security.
---

## Scanning Tools by Ecosystem

| Ecosystem | Tool | How to run |
|---|---|---|
| Node.js / npm | **npm audit** | `npm audit --audit-level=high` |
| Node.js / npm | **Snyk** | `snyk test` |
| Node.js / npm | **Dependabot** | GitHub-native; auto PRs |
| Python | **pip-audit** | `pip-audit -r requirements.txt` |
| Ruby | **bundle-audit** | `bundle audit check --update` |
| Go | **govulncheck** | `govulncheck ./...` |
| Rust | **cargo-audit** | `cargo audit` |
| Java | **OWASP Dependency-Check** | Maven/Gradle plugin |
| .NET | **dotnet list package --vulnerable** | Built-in CLI |
| Docker images | **Trivy** | `trivy image <image>` |
| Multi-ecosystem | **Snyk** | SaaS; supports all above |

**Run at minimum:** on every PR and as a nightly scheduled job.

---

## CVE Triage

### Severity-to-SLA mapping (CVSS v3)

| CVSS Score | Severity | Fix SLA | Action |
|---|---|---|---|
| 9.0 – 10.0 | Critical | **24 hours** | Emergency patch; notify security team; hotfix branch |
| 7.0 – 8.9 | High | **7 days** | Prioritize over feature work; tracked in sprint |
| 4.0 – 6.9 | Medium | **30 days** | Schedule in next sprint or Renovate auto-PR |
| 0.1 – 3.9 | Low | **90 days** | Batch with routine dependency updates |
| N/A | Unscored | Assess manually | Treat as Medium until scored |

### Triage questions before escalating severity
1. Is the vulnerable code path reachable in production?
2. Is there a known exploit in the wild (CISA KEV list)?
3. Does the application pass untrusted user data to the affected function?

If the answer to all three is "no", you may downgrade one severity tier — document the reasoning.

---

## Update Strategy

- **Dependabot / Renovate:** enable for automated PRs on patch and minor updates
- **Major version bumps:** always manual — review changelog and test coverage before merging
- **Pinned versions in production:** use exact versions (`1.2.3`), not ranges (`^1.2.3`), to prevent surprise updates
- **`--force` bypass is never acceptable in CI** — if `npm audit` fails, fix the vulnerability or use `npm audit --omit=dev` only when the vulnerable package is provably not in the production bundle

### Renovate config baseline
```json
{
  "extends": ["config:base"],
  "vulnerabilityAlerts": { "enabled": true, "labels": ["security"] },
  "packageRules": [
    { "matchUpdateTypes": ["patch"], "automerge": true },
    { "matchUpdateTypes": ["major"], "automerge": false }
  ]
}
```

---

## Supply Chain Security

| Practice | Why |
|---|---|
| Pin exact versions in `package-lock.json` / `Pipfile.lock` / `go.sum` | Prevents dependency confusion attacks and surprise behavior changes |
| Verify package checksums | Lock files include integrity hashes — commit them and verify in CI |
| Prefer packages with active maintainers | Abandoned packages accumulate unpatched CVEs |
| Check publish dates and download counts | Typosquatting packages mimic popular names with low download counts |
| Enable `npm publish` 2FA for owned packages | Prevents account takeover leading to malicious releases |
| Use a private registry mirror (Artifactory, Nexus) | Cache approved versions; block unknown packages |

### Red flags when evaluating a new dependency
- Last release > 2 years ago with open security issues
- No `SECURITY.md` or responsible disclosure policy
- Dramatically more permissions than the stated purpose requires
- Repository has < 100 stars and no organizational backing

---

## Checklist

- [ ] Dependency scanner runs on every PR
- [ ] Nightly scan scheduled; alerts go to security channel
- [ ] CRITICAL findings are blocked in CI; SLA tracked
- [ ] Lock files committed and verified in CI
- [ ] Dependabot/Renovate configured with auto-merge for patches
- [ ] No `--force` bypass in CI audit steps
