# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | ✅ Active support  |
| < 1.0   | ❌ Not supported   |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

This repository distributes its primary installer via `curl | bash`, which makes responsible disclosure especially important. If you discover a security issue — including but not limited to path traversal in the installer, hook injection, DNS rebinding in update checks, or credential leakage — report it privately before any public disclosure.

**Contact:** dersonsena@gmail.com

**Subject line:** `[SECURITY] dev-team-agents — <brief description>`

**Expected response time:** 72 hours for acknowledgement, 7 days for a resolution timeline.

## What to Include

- A description of the vulnerability and the affected component (`scripts/install.sh`, a hook, an agent, etc.)
- Steps to reproduce or a proof-of-concept (redacted as needed)
- Your assessment of impact and exploitability
- Whether you have already applied any mitigations

## Disclosure Policy

We follow coordinated disclosure:

1. You report privately.
2. We acknowledge within 72 hours.
3. We agree on a fix timeline (target: ≤ 14 days for critical issues).
4. We publish a fix and credit the reporter (unless you prefer to stay anonymous).
5. You may disclose publicly after the fix is released.

## Scope

| In scope | Out of scope |
|----------|--------------|
| `scripts/install.sh` and `scripts/update.sh` | Issues in third-party tools invoked by agents |
| Hook scripts in `scripts/hooks/` | Claude model behavior or Anthropic API issues |
| Agent instructions that could cause harmful actions | Issues in the user's own project (not this repo) |
| Update check mechanism (`01-check-updates.sh`) | |

## Private Vulnerability Reporting

This repository has GitHub's [Private Vulnerability Reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability) enabled. You can also use the **"Report a vulnerability"** button in the Security tab of this repository.
