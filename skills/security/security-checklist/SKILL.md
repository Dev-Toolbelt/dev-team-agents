---
name: security-checklist
description: Security review checklist — OWASP Top 10, LGPD/GDPR, API security, infrastructure.
---

# Security Checklist

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
