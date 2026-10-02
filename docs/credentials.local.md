# Credentials Reference

Reference for `.dev-team-agents/credentials.local.json`: how to create and edit it, the two reserved keys, and how to fill it safely.

---

## Index

- [Summary](#summary)
- [File Location](#file-location)
- [Creating and Editing](#creating-and-editing)
- [Structure](#structure)
- [Usage Notes](#usage-notes)
- [Security Guidance](#security-guidance)

---

## Summary

`credentials.local.json` is the local, gitignored credential and environment reference file. It gives selected agents enough structured information to access staging or production systems when a task requires operational validation or deployment support.

It is not a secret manager. It is a local convenience file whose shape you choose.

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

Open the **Credentials** tab in the project view. Click **Create file** to create `credentials.local.json` from the starter example. The tab is a tree editor: add, rename, nest, move between groups and remove groups and fields, mark a field secret or a group production, and search keys and visible values.

Secrets are write-only: a value marked in `$secrets`, or one that looks secret, appears only as set / not set, with Replace.

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

## Structure

The file is free-form. Name, nest and remove groups and fields however suits the project: there is no fixed category, environment or agent list. `devteam cred local init` writes a small `example` group to start from; edit it or delete it.

Two reserved keys may appear in **any** object. Every other key is yours:

| Key | Value | Meaning |
|-----|-------|---------|
| `$production` | `true` | The object and everything nested below it is production. Agents ask before every state-changing action there, one action at a time |
| `$secrets` | list of sibling key names | Those keys hold secrets. The app keeps them write-only, and `devteam cred local show` never prints them |

Two top-level keys are settings, not credentials: `work_feedback_active` (default `true`) and `work_feedback_interval_minutes` (default `5`), read by the agents' periodic progress check-ins.

Example:

```json
{
  "work_feedback_active": true,
  "work_feedback_interval_minutes": 5,
  "api": {
    "staging": {
      "url": "https://staging.example.com",
      "username": "qa@example.com",
      "password": "...",
      "$secrets": ["password"]
    },
    "production": {
      "$production": true,
      "url": "https://example.com",
      "db": { "host": "db.internal", "dsn": "...", "$secrets": ["dsn"] }
    }
  },
  "jira": { "site": "acme.atlassian.net", "token": "...", "$secrets": ["token"] }
}
```

A value stays hidden even without a `$secrets` entry when its key looks secret (`password`, `token`, `secret`, `apiKey`…) or the value does (a URL with `user:password@`, a URL with a query string, pasted key material). That is a safety net, not a substitute: mark your secrets so a value under an innocent name (`conn`, `dsn2`) is protected too.

---

## Usage Notes

- Keep only what the agents actually need.
- Mark every production group with `$production`. A group named `production` without the flag is not marked.
- Prefer staging credentials whenever the task does not explicitly require production.
- Renaming a secret, or moving it to another group, keeps its value and its secret mark: the change happens in the file, and the value never reaches the app.

---

## Security Guidance

- Do not commit this file.
- Keep file permissions restrictive.
- Prefer SSH keys over passwords for server access.
- Prefer least-privilege database users.
- Use dedicated non-personal app accounts where possible.
- Treat production credentials as exceptional, not default.
