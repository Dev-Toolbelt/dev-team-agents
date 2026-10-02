# Terms of Use — dev-team-agents

**DRAFT — Awaiting legal review before publication**

---

## 1. Account Requirement

An account with dev-team-agents is required to use the framework. You may create an account by signing in with:

- Email (passwordless via verification code)
- Email and password
- Google OAuth
- GitHub OAuth

An account is required at first sign-in. Existing installations may continue offline for up to **7 days** without signing in.

---

## 2. Trial and Licensing

### Trial Period

A trial of dev-team-agents is offered to all new accounts. The trial:

- **Duration:** [configurable server-side; currently unrestricted]
- **Features:** [list any trial-exclusive features or limitations]
- **Automatic expiry:** Your account transitions to `trial_expired` status at the end of the trial, and gated commands are blocked until you upgrade to a paid plan or obtain a premium license.

The trial can be enabled or disabled by server configuration without requiring an update; see [ADR-0029](docs/development/adrs/0029-mandatory-accounts-owned-by-the-cli-licensed-through-a-signed-offline-entitlement.md) § 5.

### Offline Window

After signing in, you may use dev-team-agents **offline for up to 7 days** without a network connection. After 7 days without an online check, an internet connection is required to verify your license and continue.

---

## 3. Suspension and Bans

### Account Suspension

We reserve the right to suspend or terminate your account if you:

- Violate these Terms of Use
- Use the service for illegal or harmful purposes
- Abuse the system's resources or other users
- Attempt to reverse-engineer, decompile or circumvent the licensing system

A suspended account loses access to the framework; the decision is communicated through the account's registered email.

### Ban List

If your account is banned, the email address associated with it is added to a ban list to prevent re-registration. The ban persists for:

- **Indefinite** — your email remains in the list permanently
- **Duration** — [specify any time-based bans]

---

## 4. Premium Features

Premium features (if any) are reserved for paid accounts and are not available during a trial. Premium access is:

- **Granted** via your account's entitlement token after subscription or license purchase
- **Verified offline** — the token is signed and cached locally, so premium features work offline within the 7-day cache window
- **Revoked** immediately when your subscription ends, effective at your next online check

---

## 5. MIT License vs. Hosted Service

**The framework code is licensed under the MIT License** and is freely available at <https://github.com/Dev-Toolbelt/dev-team-agents>.

The hosted identity and licensing service (Supabase Auth and the entitlement system) **is not** covered by the MIT License and is provided under these Terms of Use. The service may have availability, performance, or feature limitations.

---

## 6. Limitation of Liability

[PLACEHOLDER — work with your legal counsel to define liability limits appropriate to your jurisdiction and service offering]

To the fullest extent permitted by applicable law, dev-team-agents and its maintainers are not liable for:

- Loss of data, code, or work
- Business interruption or loss of use
- Damages arising from service interruption or outage
- Claims arising from unauthorized access due to your own breach of security

---

## 7. Governing Law

These Terms of Use are governed by the laws of [JURISDICTION — e.g., the Federative Republic of Brazil], and disputes are subject to the exclusive jurisdiction of the courts in [LOCATION — e.g., São Paulo, Brazil].

---

## 8. Changes to These Terms

We may update these Terms of Use at any time. Changes take effect when published; continued use of the service after publication constitutes acceptance of the new terms.

---

## 9. Contact

For questions about these Terms of Use, contact:

**[YOUR LEGAL ENTITY NAME]**  
[EMAIL]  
[ADDRESS]

---

**Last updated:** [DATE]  
**Status:** DRAFT — Legal review pending before enforcement
