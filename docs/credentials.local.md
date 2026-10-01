# Credentials Reference

Reference for `.dev-team-agents/credentials.local.json`: what each section is for, who uses it, how to create and edit it, and how to fill it safely.

---

## Index

- [Summary](#summary)
- [File Location](#file-location)
- [Creating and Editing](#creating-and-editing)
- [Top-Level Structure](#top-level-structure)
- [DevOps Section](#devops-section)
- [App Section](#app-section)
- [Field-by-Field Reference](#field-by-field-reference)
- [Usage Notes](#usage-notes)
- [Security Guidance](#security-guidance)

---

## Summary

`credentials.local.json` is the local, gitignored credential and environment reference file. It gives selected agents enough structured information to access staging or production systems when a task requires operational validation or deployment support.

It is not a secret manager. It is a local convenience file with a predictable schema.

---

## File Location

```text
.dev-team-agents/credentials.local.json
```

The file is machine-local (never exported or committed) and ignored by the bind-managed `.gitignore` block. It lives in the main checkout's `.dev-team-agents/`; every linked git worktree shares it, and a monorepo subproject keeps its own.

---

## Creating and Editing

The file does not exist by default. Create it in one of three ways:

### Via the Desktop App

Open the **Credentials** tab in the project view. Click **Create file** to create `credentials.local.json` from the standard layout and open a form. Edit fields directly, with automatic validation and JSON error reporting.

Secrets are write-only: only known non-secret fields (hosts, users, URLs, ports, paths) are ever shown, and every other value appears as set / not set, with Replace and Remove.

### Via the CLI

```bash
devteam cred local init
```

Creates the file with the canonical template. Exits with error (code 4) if the file already exists.

### By Hand

Run `devteam cred local init` and edit the result, or write the file yourself following the structure below, then run:

```bash
chmod 600 .dev-team-agents/credentials.local.json
```

---

## Top-Level Structure

| Key | Purpose |
|-----|---------|
| `work_feedback_active` | Enables/disables the periodic status-table check-in while background sub-agents work (`skills/shared/work-feedback/SKILL.md`). Default `true` |
| `work_feedback_interval_minutes` | Interval, in minutes, between status-table check-ins. Default `5` |
| `devops` | Infrastructure-level access for servers, databases, and operational tasks |
| `app` | Application-level access for logging into staging or production environments |

Each section defines:

- Which agents are allowed to use that block
- Separate staging and production environments
- Structured credentials instead of free-form notes

---

## DevOps Section

`devops` is intended for infrastructure-facing tasks.

### Summary

| Key | Meaning |
|-----|---------|
| `agents` | Agent allowlist for infrastructure credentials |
| `staging.ssh` | SSH access data for staging |
| `staging.database` | One or more staging databases |
| `production.ssh` | SSH access data for production |
| `production.docker` | Optional provider-specific Docker metadata |
| `production.database` | One or more production databases |

### Intended use

This block is most relevant when tasks involve:

- deploy diagnostics
- server inspection
- operational reviews
- database validation
- security audits

---

## App Section

`app` is intended for browser or application-login scenarios.

### Summary

| Key | Meaning |
|-----|---------|
| `agents` | Agent allowlist for application credentials |
| `staging.appUrl` | Base URL for the staging app |
| `staging.username` | Login username for staging |
| `staging.password` | Login password for staging |
| `production.appUrl` | Base URL for the production app |
| `production.username` | Login username for production |
| `production.password` | Login password for production |

### Intended use

This block is most relevant when tasks involve:

- QA validation in staging
- review agents checking live behavior
- security validation of accessible environments
- reproducing a bug in a deployed environment

---

## Field-by-Field Reference

### `devops.agents`

List of agent names allowed to consume infrastructure credentials.

Use it to limit high-risk access to the smallest set of roles that actually need it.

### `devops.staging.ssh.user`

SSH username for the staging server.

Example:

```json
"user": "deploy"
```

### `devops.staging.ssh.host`

Hostname or IP address of the staging server.

Example:

```json
"host": "staging.example.com"
```

### `devops.staging.ssh.privateKeyPath`

Absolute or user-relative path to the SSH private key used for staging access.

Example:

```json
"privateKeyPath": "~/.ssh/id_ed25519"
```

### `devops.staging.ssh.path`

Remote application path after login.

Example:

```json
"path": "/var/www/my-app"
```

### `devops.staging.database[]`

Array because staging may have more than one database or service.

Each entry contains:

| Field | Meaning |
|-------|---------|
| `type` | Database engine such as `postgres`, `mysql`, `mongodb` |
| `host` | Database host |
| `port` | Database port |
| `database` | Database name |
| `username` | Database login user |
| `password` | Database password |

### `devops.production.ssh.*`

Same schema and meaning as staging SSH, but for production.

Use with stricter discipline and only when the task really requires production access.

### `devops.production.docker`

Open object reserved for deployment-specific Docker metadata.

Because infrastructure layouts differ, this block is intentionally flexible. Common uses might include:

- compose project names
- container labels
- service names
- registry references

If unused, leave it as `{}`.

### `devops.production.database[]`

Same schema as staging databases, but for production systems.

If production has read replicas, analytics databases, or multiple services, add multiple array entries.

### `app.agents`

List of agent names allowed to consume application login credentials.

This is separate from `devops.agents` because browser-level access and server-level access are not the same trust boundary.

### `app.staging.appUrl`

Base URL used to open the staging environment.

Example:

```json
"appUrl": "https://staging.example.com"
```

### `app.staging.username`

Username or email used to log into staging.

### `app.staging.password`

Password for the staging account.

### `app.production.appUrl`

Base URL of the production application.

### `app.production.username`

Username or email used to log into production.

### `app.production.password`

Password for the production account.

---

## Usage Notes

- Fill only the sections you actually use.
- You can keep unused fields as empty strings.
- Prefer staging credentials whenever the task does not explicitly require production.
- If multiple environments exist, keep the schema consistent rather than adding ad-hoc notes.

Minimal staging-only example:

```json
{
  "app": {
    "agents": ["qa-specialist"],
    "staging": {
      "appUrl": "https://staging.example.com",
      "username": "qa@example.com",
      "password": "..."
    },
    "production": {
      "appUrl": "",
      "username": "",
      "password": ""
    }
  }
}
```

---

## Security Guidance

- Do not commit this file.
- Keep file permissions restrictive.
- Prefer SSH keys over passwords for server access.
- Prefer least-privilege database users.
- Use dedicated non-personal app accounts where possible.
- Treat production credentials as exceptional, not default.
