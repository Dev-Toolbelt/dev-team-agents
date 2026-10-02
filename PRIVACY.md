# Privacy Policy — dev-team-agents

dev-team-agents can collect **anonymous, aggregate usage data** to help us understand
which agents and commands are most valuable and guide product decisions.

**Telemetry is off unless you turn it on.** Nothing is collected until
`.dev-team-agents/user-data/preferences.json` contains `"telemetry": true`, and the
installer writes that value only after you were actually shown the prompt and
accepted it. See "Consent" below for the exact rules.

---

## Consent

On **first install only**, `install.sh` asks whether to enable anonymous telemetry.
It asks by opening the controlling terminal (`/dev/tty`) rather than testing stdin,
so the prompt appears even on the documented `curl … | bash` path, where stdin is a
pipe.

| Situation at install time | Result |
|---|---|
| Terminal reachable, you press Enter or answer `y` | Enabled |
| Terminal reachable, you answer `n` | Disabled |
| Terminal reachable, no answer within 60 seconds, or stdin hits EOF | **Disabled** — silence is not consent |
| `DEVTEAM_NONINTERACTIVE=1` set (CI, container images, provisioning) | **Disabled**, no prompt shown |
| No terminal reachable at all | **Disabled**, with a printed note on how to enable it later |

Re-installs and updates never re-ask and never change an existing value.

The read path fails closed to match: a missing `preferences.json`, an unreadable one,
a file with no `telemetry` key, or a machine without `python3` all mean "consent was
never recorded", and nothing is queued or sent.

---

## What we collect

Only when telemetry is enabled:

| Event | When | Data sent |
|-------|------|-----------|
| `first_install` | First-time installation | Installed version, OS (`darwin`/`linux`) |
| `install` | Re-install or update via installer | Installed version, OS |
| `update` | Manual update via `update.sh` | Previous version, new version, mode (`manual`) |
| `agent_spawned` | Any time an agent is started via the `Task` tool | OS, installed version |
| `command_invoked` | Any `/devteam:*` slash command executed | Command name (e.g. `plan`, `backend`), OS, version |
| `session_end` | End of each CLI session (any supported provider) | Whether the stop hook was active, OS, version |
| `agent_completed` | An agent invocation finishes | Agent name, the actual resolved model it ran on, token counts (input/output/cache), provider |

All events also include:
- **`$lib`**: always `"dev-team-agents"` (identifies the source)
- **`version`**: the installed version tag (e.g. `v1.2.0`)
- **`os`**: operating system family (`darwin` or `linux`)

---

## What we do NOT collect

- File names, file paths, or directory structures
- Code content or text from your codebase
- Agent conversation content or prompts
- Project names, repository names, or branch names
- Your username, email address, or any personal identifier
- IP addresses — PostHog's `anonymize_ips` project setting is enabled, so the client IP
  is used only transiently by transformations like GeoIP enrichment and then discarded;
  it is not stored with the event.

---

## Anonymous identifier

Each installation generates a one-way **SHA-256 hash** derived from your machine
hostname and home directory path. This hash:

- Is stored locally in `.dev-team-agents/user-data/telemetry-queue.json`
- Cannot be reversed to recover your hostname or home directory
- Is used only to deduplicate install events (not to track individuals)
- Is never transmitted along with any personal data

---

## Data storage

Events are buffered locally in `.dev-team-agents/user-data/telemetry-queue.json`
(gitignored) and sent in batches to **PostHog** (US region, `us.i.posthog.com`) over
HTTPS. The queue is flushed at most once every 24 hours or when it reaches 100 events.
The endpoint can be repointed at a self-hosted PostHog instance with the
`DEVTEAM_POSTHOG_ENDPOINT` environment variable.

PostHog data retention: aggregate metrics are kept indefinitely; raw event logs
are retained for 90 days and then deleted automatically.

**Local only, never sent: task board prompt excerpts.** Separately from telemetry, the
task board keeps, on your machine, a short excerpt (first line, at most 100 characters)
of each prompt that led the session to use a tool — read, search or change files — on
that session's "Direct work" card. Anything shaped like a secret is replaced by `[redacted]` before it is
stored — a best effort, not a guarantee. These excerpts live in the machine-local task
board records, are never transmitted (telemetry included), and are kept until you
delete them; there is no opt-out yet. See `docs/specs/task-board.md` § Direct work. The same records keep the session's title and, for Claude Code, the path of its local transcript, read only to show the title the session currently has; neither is transmitted.

---

## Turning it off (or on)

The value lives in `.dev-team-agents/user-data/preferences.json`:

```json
{
  "telemetry": false
}
```

Set it to `false` to stop collection, or `true` to opt in if you declined (or were
never asked) at install time. After saving, you can verify the current state with:

```bash
.dev-team-agents/scripts/helpers/telemetry-send.sh --dry-run
```

---

---

## Account Data Processing (LGPD / GDPR)

Mandatory account sign-in was introduced in [ADR-0029](docs/development/adrs/0029-mandatory-accounts-owned-by-the-cli-licensed-through-a-signed-offline-entitlement.md). This section covers the processing of account data.

### Data Controller and Protection Officer

**Data Controller:** [YOUR LEGAL ENTITY NAME]  
**Data Protection Officer (encarregado de dados):** [NAME]  
**Contact:** [CONTACT EMAIL/PHONE]  
**Effective from:** [DATE]

### What We Collect

When you create an account and sign in:

| Data | Purpose | Legal basis |
|------|---------|-------------|
| Email address | Account identity and sign-in | Contract execution (art. 7, V LGPD) |
| Display name | Profile and account identification | Contract execution (art. 7, V LGPD) |
| Identity provider ID (Google, GitHub) | Linking signed-in identities to one account | Contract execution (art. 7, V LGPD) |
| Sign-up method | Account audit and identity confirmation | Contract execution (art. 7, V LGPD) |
| `last_seen_at` (day precision, never hours/minutes) | Monitoring active users; purged after account deletion | Contract execution (art. 7, V LGPD) |
| IP addresses in auth audit logs | Security audit and abuse prevention | Legitimate interest — fraud prevention (art. 7, IX LGPD) |
| **HMAC hash of email** (if account is banned) | Preventing re-registration after a ban | Legitimate interest — fraud prevention (art. 7, IX LGPD) |
| **Trial start marker** (if account is deleted but trial was used) | Preventing trial reset via re-registration within 12 months | Legitimate interest — fraud prevention (art. 7, IX LGPD) |

### Data Processors

Your data is processed by:

- **Supabase Auth** (GoTrue) — hosted in region `sa-east-1` (São Paulo, Brazil) — manages account identity, sign-in methods and the refreshable entitlement token.
- **SMTP Email Provider** [PLACEHOLDER] — sends transactional emails only (sign-in codes, security notices, license state changes).
- **Google and GitHub** — process OAuth sign-in when you choose those methods; see their privacy policies for their data handling.

### Data Storage and Retention

- **Account records** (`email`, `display_name`, `identities`, `created_at`, `last_seen_at`) are retained while your account exists.
- **IP addresses in auth audit logs** — retained by Supabase for 90 days, then deleted automatically.
- **HMAC ban list** — the hash and ban reason are retained indefinitely (fraud prevention under LGPD art. 7, IX).
- **Trial consumption marker** — retained for up to 12 months after account deletion (fraud prevention).

### International Data Transfer

Your data may be transferred to Supabase's servers outside Brazil when they are accessed from a different country. Supabase's privacy and data protection commitments are documented at <https://supabase.com/privacy>.

### Your Rights

Under LGPD art. 18, you have the right to:

- **Access** your data: run `devteam auth profile show --json`
- **Correct** your data: run `devteam auth profile update --name <your name>` or update your email through the app
- **Delete** your account: run `devteam auth delete` (the app's Account menu also offers this)
- **Port** your data: account data is available via `devteam auth profile --json`

Account deletion is **immediate and irreversible**. All personal data is removed, except the HMAC ban list and trial marker (fraud prevention only; they retain no identifying information).

### Registration is the Lead

When you create an account, you become a lead for dev-team-agents product decisions. The basis for this contact is the account contract (art. 7, V LGPD), so we send only **transactional emails**:

- Sign-in codes and security notices
- License state changes (trial starting, ending, premium features)
- Critical security incidents

**Marketing emails require a separate, explicit opt-in** (consent under art. 7, I LGPD) that does not yet exist. We do not send marketing email.

### Telemetry Remains Anonymous and Unlinked

The telemetry system described above is completely separate from accounts:

- Your account ID is **never** added to telemetry
- Telemetry's anonymous ID is **never** sent to Supabase
- No join between account and telemetry data exists or will be built

Your telemetry privacy (anonymous, aggregate, non-personally-identifiable) is unchanged by mandatory accounts.

---

## Questions

Open an issue at <https://github.com/Dev-Toolbelt/dev-team-agents/issues>.
