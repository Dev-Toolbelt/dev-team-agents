# Security Review Output Template

Fill this exact structure. Omit a section entirely (not with "none found") only when it has nothing to report, except **Cross-Boundary**, which is always omitted when empty.

```
## Security Review — [Brief Title]

### Executive Summary
[2-3 sentences: overall risk posture]

### Critical Findings
- **[CRITICAL]** [Title]
  - Location: `file.js:42`
  - Description: [what the vulnerability is]
  - Attack scenario: [how an attacker would exploit this]
  - Remediation: [specific fix with code example if helpful]

### High Findings
- **[HIGH]** ...

### Medium / Low / Info
- **[MEDIUM / LOW / INFO]** ...

### Business Logic
- [findings]

### CI/CD Pipeline
- [findings]

### LGPD / GDPR
- [findings]

### Tooling & Dependency Audit
- [blocking findings, scanner coverage, anything NOT RUN]

### Cross-Boundary
(omit if none)
- `[cross-boundary → qa-specialist]` — [one-line pointer to the behavior that needs execution to confirm]

### Recommendation
[SHIP / DO NOT SHIP until X is fixed]
```
