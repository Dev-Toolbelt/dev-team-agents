---
name: security-checklist
description: Security review — OWASP Top 10, LGPD/GDPR, API, infrastructure.
---

# Security Checklist

## Ownership Boundary — Security Audit vs QA

Two agents load this checklist. They do **not** run the same checks. Read this section first and cover only your side; otherwise the same finding is reported twice into one consolidated summary.

| | `security-specialist` (security audit) | `qa-specialist` (behavioral QA) |
|---|---|---|
| **Question asked** | "Can this be abused by an attacker?" | "Does this behave correctly for a legitimate user?" |
| **Method** | Read code, config, dependencies, and infrastructure; reason about attack paths | Exercise the running feature against its acceptance criteria |
| **Evidence** | File and line reference for the weakness | Reproduction steps and observed vs expected behavior |

**Owned by the security audit — QA does not report these:**

| Section | Scope |
|---|---|
| A02 Cryptographic Failures | Hashing algorithms, cost factors, TLS config, secrets in code |
| A05 Security Misconfiguration | Debug mode, default credentials, exposed ports, directory listing |
| A06 Vulnerable Components | Dependency CVEs, audit tooling, update process |
| A08 Integrity Failures | CI/CD integrity, deserialization, SRI hashes |
| A10 SSRF | URL allowlists, internal address blocking, metadata endpoints |
| HTTP Security Headers | Presence and correctness of every header |
| LGPD / GDPR | Legal basis, DPAs, cross-border transfers, breach process |
| Secrets & Credentials | Secret managers, git history, DB user privileges, key rotation |

**Owned by behavioral QA — the security audit assumes QA covers these and does not duplicate them:**

| Section | QA scope (behavior only) |
|---|---|
| A01 Broken Access Control | Sign in as user B, attempt to read user A's record — record the actual response |
| A04 Insecure Design | Invalid state transitions are rejected; rate limits actually trigger and reset |
| A07 Auth Failures | Login, logout, lockout, password reset, and expiry behave as specified end to end |
| A09 Logging Failures | Auth and admin events actually appear in logs; sensitive values do not |
| API-Specific Security | Validation rejects bad input; errors expose no stack traces; pagination is enforced |

**Shared boundary — A03 Injection:** the security audit owns whether the code is structurally safe (parameterized queries, argument arrays, escaping). QA owns whether hostile input is rejected at runtime. Both may report on A03; each must state which of the two it observed.

**When you find something on the other side:**

- Report it — never stay silent because it is not your section.
- Label it explicitly: `[cross-boundary → security-specialist]` or `[cross-boundary → qa-specialist]`.
- Keep it to one line with the pointer; do not write the other agent's full analysis.
- The consolidating command treats a cross-boundary line and the owner's full finding as **one** issue, not two.

---

## OWASP Top 10 (2021)

### A01 — Broken Access Control
- [ ] Every endpoint checks authorization — not just authentication
- [ ] Horizontal privilege escalation prevented (user A cannot access user B's data)
- [ ] Admin functions protected by role checks, not just hidden from UI
- [ ] Direct object references use UUIDs or tokens, not sequential integers
- [ ] CORS policy is explicit — `*` is never used in production

### A02 — Cryptographic Failures
- [ ] Sensitive data encrypted at rest (passwords, PII, tokens)
- [ ] Passwords hashed with bcrypt/argon2 (min cost factor 10) — never MD5/SHA1
- [ ] TLS 1.2+ enforced — HTTP disabled or redirected to HTTPS
- [ ] Sensitive data not logged (passwords, tokens, full credit card numbers)
- [ ] Secrets not stored in code, `.env` files not committed to git

### A03 — Injection
- [ ] All SQL uses parameterized queries or ORM — no string concatenation
- [ ] Shell commands use argument arrays, not string interpolation
- [ ] Template engines escape output by default (XSS prevention)
- [ ] File paths sanitized — no user input used directly in filesystem operations
- [ ] XML/HTML input validated and escaped

### A04 — Insecure Design
- [ ] Business logic validates state transitions (e.g., can't cancel a shipped order)
- [ ] Rate limiting on sensitive operations (login, password reset, OTP)
- [ ] Anti-automation measures on critical flows

### A05 — Security Misconfiguration
- [ ] Debug mode / verbose errors disabled in production
- [ ] Default credentials changed (DB, Redis, admin panels)
- [ ] Unnecessary services, ports, and features disabled
- [ ] Security headers present (see Headers section below)
- [ ] Directory listing disabled on web server

### A06 — Vulnerable and Outdated Components
- [ ] Dependencies audited (`npm audit`, `composer audit`, `pip audit`, `trivy`)
- [ ] No known CVEs in critical dependencies
- [ ] Dependency update process defined (automated PRs or scheduled review)

### A07 — Identification and Authentication Failures
- [ ] Passwords have minimum complexity requirements
- [ ] Account lockout or exponential backoff after failed attempts
- [ ] JWT tokens have short expiry (access: 15min, refresh: 7-30 days)
- [ ] JWT signature algorithm is RS256 or ES256 — not `none` or HS256 with weak secret
- [ ] Session invalidated on logout
- [ ] Password reset tokens expire and are single-use

### A08 — Software and Data Integrity Failures
- [ ] CI/CD pipeline integrity — no untrusted scripts injected
- [ ] Deserialization of user-controlled data avoided
- [ ] Third-party scripts loaded from CDN have Subresource Integrity (SRI) hashes

### A09 — Security Logging and Monitoring Failures
- [ ] Authentication events logged (success, failure, lockout)
- [ ] Authorization failures logged
- [ ] Admin actions logged with user ID and timestamp
- [ ] Logs do not contain sensitive data (passwords, tokens, full PII)
- [ ] Log aggregation and alerting configured

### A10 — Server-Side Request Forgery (SSRF)
- [ ] URLs provided by users validated against allowlist
- [ ] Internal network addresses blocked from user-supplied URLs
- [ ] Cloud metadata endpoints (169.254.169.254) protected

---

## HTTP Security Headers

Every HTTP response should include:

```
Content-Security-Policy: default-src 'self'; script-src 'self'; object-src 'none'
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## LGPD / GDPR Checklist

- [ ] Personal data inventory documented (what, where, who accesses)
- [ ] Legal basis for processing documented (consent, legitimate interest, contract)
- [ ] Consent collected explicitly and stored with timestamp
- [ ] Data minimization — only collect what's needed
- [ ] Right to access: endpoint/process to export user data
- [ ] Right to erasure: process to delete or anonymize user data
- [ ] Data breach notification process defined (72h for GDPR)
- [ ] Third-party processors (subprocessors) have DPA (Data Processing Agreement)
- [ ] Cross-border transfers use Standard Contractual Clauses (GDPR) or equivalent

---

## API-Specific Security

- [ ] Authentication required on all non-public endpoints
- [ ] Input validated server-side (never trust client-side validation alone)
- [ ] Response does not expose internal IDs, stack traces, or system paths
- [ ] Mass assignment prevented (explicit allowlist, not blocklist)
- [ ] File uploads: type validated by content (magic bytes), not extension; stored outside web root
- [ ] Pagination enforced — no endpoints return unlimited records
- [ ] Rate limiting per user and per IP

---

## Secrets & Credentials

- [ ] No secrets in source code, git history, or Docker images
- [ ] `.env` in `.gitignore`; `.env.example` committed without values
- [ ] Production secrets in secret manager (AWS SSM, GCP Secret Manager, Azure Key Vault, HashiCorp Vault)
- [ ] CI/CD secrets in platform secret store, not in workflow files
- [ ] Database uses a dedicated user with minimum permissions (not root/admin)
- [ ] API keys rotated on team member departure
